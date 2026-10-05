#!/usr/bin/env python3
"""Fill the CV and Talks parts of index.html from the private mycv repository.

Usage:
    python3 scripts/build_cv.py [path/to/mycv]     # default: ../mycv

Reads data/profile.yaml and data/presentations.yaml from mycv and rewrites the
blocks between <!--NAME:START--> and <!--NAME:END--> markers in index.html.
Only public fields are written: internal fields such as sources, unverified,
remarks and grant amounts, numbers and project titles are never output,
and funding entries listed in HIDDEN_FUNDING are skipped.
"""
import datetime as dt
import hashlib
import html
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MYCV = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'mycv'
INDEX = ROOT / 'index.html'

MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def esc(text):
    return html.escape(str(text), quote=True)


def en(value):
    """English text of a {en, ja} pair (or a plain string)."""
    if isinstance(value, dict):
        return value.get('en') or value.get('ja') or ''
    return value or ''


# Dates -----------------------------------------------------------------------

def fmt_day(d):
    return f'{d.day} {MONTHS[d.month - 1]} {d.year}'


def fmt_period(start, end):
    if start == end:
        return fmt_day(start)
    if start.year == end.year and start.month == end.month:
        return f'{start.day}–{end.day} {MONTHS[end.month - 1]} {end.year}'
    if start.year == end.year:
        return f'{start.day} {MONTHS[start.month - 1]} – {fmt_day(end)}'
    return f'{fmt_day(start)} – {fmt_day(end)}'


def talk_date(t):
    """(sort key, label) using the most precise date available."""
    if t.get('date'):
        d = t['date']
        return d, fmt_day(d)
    if t.get('period'):
        p = t['period']
        return p['start'], fmt_period(p['start'], p['end'])
    year, month = map(int, str(t['month']).split('-'))
    return dt.date(year, month, 1), f'{MONTHS[month - 1]} {year}'


# Talks -----------------------------------------------------------------------

CATEGORIES = [
    ('invited', 'Invited talks', True),
    ('contributed', 'Talks at conferences and workshops', False),
    ('domestic', 'Talks at the Physical Society of Japan meetings', False),
    ('seminar', 'Seminars', False),
]

PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 4l14 8-14 8z"/></svg>'


def place(t):
    parts = [en(t.get(k)) for k in ('venue', 'city', 'country')]
    return ', '.join(p for p in parts if p)


def talk_item(t, label):
    meta = [en(t['event'])] if t.get('event') else []
    if place(t):
        meta.append(place(t))
    if t.get('online'):
        meta.append('online')
    tags = []
    if t.get('language') == 'ja':
        tags.append('<span class="tag">in Japanese</span>')
    if t.get('recording'):
        tags.append(f'<a class="tag is-link" href="{esc(t["recording"])}" target="_blank" rel="noopener">{PLAY}Recording</a>')
    return (
        '<li>'
        f'<span class="when">{esc(label)}</span>'
        '<span class="what">'
        f'<span class="talk-title">{esc(en(t["title"]))}</span>'
        f'<span class="where">{esc(" · ".join(meta))}</span>'
        + (f'<span class="tags">{"".join(tags)}</span>' if tags else '') +
        '</span></li>'
    )


def build_talks(talks):
    out = []
    out.append('<div class="talk-groups">')
    for key, title, is_open in CATEGORIES:
        items = sorted((t for t in talks if t['category'] == key), key=lambda t: talk_date(t)[0], reverse=True)
        if not items:
            continue
        out.append(
            f'<details class="card talk-group"{" open" if is_open else ""}>'
            f'<summary><span>{esc(title)}</span><span class="count">{len(items)}</span></summary>'
            '<ol class="timeline talk-list">'
        )
        out.extend(talk_item(t, talk_date(t)[1]) for t in items)
        out.append('</ol></details>')
    out.append('</div>')
    return '\n'.join(out)


# CV --------------------------------------------------------------------------

def build_memberships(profile):
    rows = [
        f'<li><span class="when">{esc(en(m["period"]))}</span>{esc(en(m))}</li>'
        for m in profile['memberships']
    ]
    return '<ul class="plain-list">' + ''.join(rows) + '</ul>'


# Funding entries that must not appear on the website, matched by a hash of
# their Japanese name so the names are not written in this public repository.
HIDDEN_FUNDING = {'7c8351dc9414bc5b'}


def hidden(entry):
    return hashlib.sha256(en_ja(entry).encode()).hexdigest()[:16] in HIDDEN_FUNDING


def en_ja(entry):
    return entry.get('ja') or ''


GRANT_NUMBER = re.compile(r'\s*\((?=[^)]*\d)[A-Z0-9-]+\)')


def build_grants(profile):
    rows = []
    for g in profile['funding']:
        if hidden(g):
            continue
        name = GRANT_NUMBER.sub('', en(g))   # no grant numbers, amounts or project titles
        role = en(g.get('role'))
        rows.append(
            f'<li><span class="when">{esc(en(g["period"]))}</span>{esc(name)}'
            + (f' <span class="tag">{esc(role)}</span>' if role else '') + '</li>'
        )
    return '<ul class="plain-list">' + ''.join(rows) + '</ul>'


def build_teaching(profile):
    rows = []
    for c in profile['teaching']:
        if c.get('optional'):            # e.g. private tutoring
            continue
        course, _, detail = en(c).partition(' — ')
        course = re.sub(r'\s*\([^)]*;[^)]*\)', '', course)   # drop internal notes such as '(cosmology; taught twice)'
        role, *extras = [s.strip() for s in re.sub(r'\s*\(.*?\)', '', detail).split(',')]
        role = {'TA': 'Teaching assistant'}.get(role, role[:1].upper() + role[1:])
        extras = [e for e in extras if e]
        rows.append(
            f'<li><span class="when">{esc(en(c["period"]))}</span>{esc(course)}'
            f' <span class="tag">{esc(role)}</span>'
            + ''.join(f' <span class="tag is-soft">{esc(e)}</span>' for e in extras) + '</li>'
        )
    return '<ul class="plain-list">' + ''.join(rows) + '</ul>'


def month_label(d):
    return f'{MONTHS[d.month - 1]} {d.year}'


def build_positions(profile):
    rows = []
    for pos in profile['positions']:
        title, _, where = en(pos).replace('College of Physics', 'School of Physics').partition(', ')
        when = f'{month_label(pos["start"])} – {month_label(pos["end"]) if pos.get("end") else "present"}'
        rows.append(
            f'<li><span class="when">{esc(when)}</span>'
            f'<span class="what">{esc(title)}<span class="where">{esc(where)}</span></span></li>'
        )
    return '<ol class="timeline">' + ''.join(rows) + '</ol>'


# Main ------------------------------------------------------------------------

def replace_block(page, name, content):
    pattern = re.compile(rf'(<!--{name}:START-->).*?(<!--{name}:END-->)', re.S)
    if not pattern.search(page):
        sys.exit(f'marker {name} not found in index.html')
    return pattern.sub(lambda m: m.group(1) + '\n' + content + '\n' + m.group(2), page)


def main():
    profile = yaml.safe_load((MYCV / 'data/profile.yaml').read_text(encoding='utf-8'))
    talks = yaml.safe_load((MYCV / 'data/presentations.yaml').read_text(encoding='utf-8'))
    page = INDEX.read_text(encoding='utf-8')
    page = replace_block(page, 'POSITIONS', build_positions(profile))
    page = replace_block(page, 'MEMBERSHIPS', build_memberships(profile))
    page = replace_block(page, 'GRANTS', build_grants(profile))
    page = replace_block(page, 'TEACHING', build_teaching(profile))
    page = replace_block(page, 'TALKS', build_talks(talks))
    INDEX.write_text(page, encoding='utf-8')
    print(f'Updated index.html: {len(profile["positions"])} positions, {len(talks)} talks, '
          f'{sum(not hidden(g) for g in profile["funding"])} grants, '
          f'{len(profile["teaching"])} teaching entries, {len(profile["memberships"])} memberships')


if __name__ == '__main__':
    main()
