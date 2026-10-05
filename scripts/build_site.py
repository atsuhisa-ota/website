#!/usr/bin/env python3
"""Build the English, Japanese and Chinese pages of the website.

Usage:
    python3 scripts/build_site.py [path/to/mycv]     # default: ../mycv

Inputs:
    _src/page.html      page template: {{t:key}} text, {{b:name}} generated blocks
    _src/strings.yaml   text in en / ja / zh
    _src/cv.yaml        translations of the CV items that come from mycv
    mycv                data/profile.yaml and data/presentations.yaml (private repository)

Outputs: index.html (English), ja/index.html, zh/index.html

Only public fields of mycv are written: internal fields such as sources,
unverified, remarks and notes, grant amounts, numbers and project titles are
never output, and funding entries listed in HIDDEN_FUNDING are skipped.
"""
import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MYCV = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'mycv'
SRC = ROOT / '_src'

LANGS = {
    # code: (html lang, output path, path back to the site root, menu label, short label)
    'en': ('en', 'index.html', '', 'English', 'EN'),
    'ja': ('ja', 'ja/index.html', '../', '日本語', '日本語'),
    'zh': ('zh-Hans', 'zh/index.html', '../', '简体中文', '中文'),
}
FONTS = {
    'en': 'family=Fredoka:wght@400;500;600&family=Nunito:wght@400;600;700',
    'ja': 'family=Fredoka:wght@400;500;600&family=Nunito:wght@400;600;700&family=M+PLUS+Rounded+1c:wght@400;500;700',
    'zh': 'family=Fredoka:wght@400;500;600&family=Nunito:wght@400;600;700&family=Noto+Sans+SC:wght@400;500;700',
}
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()

# Funding entries that must not appear on the website, matched by a hash of
# their Japanese name so the names are not written in this public repository.
HIDDEN_FUNDING = {'7c8351dc9414bc5b'}

warnings = []


def esc(text):
    return html.escape(str(text), quote=True)


def pick(value, lang):
    """Text of an {en, ja} pair from mycv, falling back to English."""
    if isinstance(value, dict):
        return value.get(lang) or value.get('en') or value.get('ja') or ''
    return value or ''


def hidden(entry):
    return hashlib.sha256((entry.get('ja') or '').encode()).hexdigest()[:16] in HIDDEN_FUNDING


# Dates -----------------------------------------------------------------------

def fmt_month(d, lang):
    return f'{MONTHS[d.month - 1]} {d.year}' if lang == 'en' else f'{d.year}年{d.month}月'


def fmt_day(d, lang):
    return f'{d.day} {MONTHS[d.month - 1]} {d.year}' if lang == 'en' else f'{d.year}年{d.month}月{d.day}日'


def fmt_period(a, b, lang):
    if a == b:
        return fmt_day(a, lang)
    if lang == 'en':
        if (a.year, a.month) == (b.year, b.month):
            return f'{a.day}–{b.day} {MONTHS[b.month - 1]} {b.year}'
        if a.year == b.year:
            return f'{a.day} {MONTHS[a.month - 1]} – {fmt_day(b, lang)}'
        return f'{fmt_day(a, lang)} – {fmt_day(b, lang)}'
    sep = '〜' if lang == 'ja' else '—'
    if (a.year, a.month) == (b.year, b.month):
        return f'{a.year}年{a.month}月{a.day}日{sep}{b.day}日'
    if a.year == b.year:
        return f'{a.year}年{a.month}月{a.day}日{sep}{b.month}月{b.day}日'
    return f'{fmt_day(a, lang)}{sep}{fmt_day(b, lang)}'


def fmt_span(start, end, lang, present):
    """A span of months, such as a position."""
    last = fmt_month(end, lang) if end else present
    return f'{fmt_month(start, lang)} – {last}' if lang == 'en' else \
        f'{fmt_month(start, lang)}{"〜" if lang == "ja" else ("—" if end else "")}{last}'


def zh_period(ja_text):
    """Chinese version of a period written in Japanese in mycv."""
    text = ja_text
    for a, b in [('〜現在', '至今'), ('（再入会）', '（重新入会）'), ('博士課程在学中', '博士在读期间'),
                 ('年度', '学年'), ('〜', '—')]:
        text = text.replace(a, b)
    if re.search(r'[぀-ヿ]', text):
        warnings.append(f'zh period may need a translation: {ja_text}')
    return text


def period(value, lang):
    if lang == 'zh':
        return zh_period(value.get('ja') or value.get('en'))
    return pick(value, lang)


def talk_date(t, lang):
    """(sort key, label) using the most precise date available."""
    if t.get('date'):
        return t['date'], fmt_day(t['date'], lang)
    if t.get('period'):
        p = t['period']
        return p['start'], fmt_period(p['start'], p['end'], lang)
    year, month = map(int, str(t['month']).split('-'))
    return dt.date(year, month, 1), fmt_month(dt.date(year, month, 1), lang)


# Blocks ----------------------------------------------------------------------

PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 4l14 8-14 8z"/></svg>'
FULLWIDTH_NUMBER = re.compile(r'（(?=[^）]*\d)[A-Z0-9-]+）')
GRANT_NUMBER = re.compile(r'\s*\((?=[^)]*\d)[A-Z0-9-]+\)')


class Builder:
    def __init__(self, lang, strings, cv, profile, talks):
        self.lang, self.strings, self.cv, self.profile, self.talks = lang, strings, cv, profile, talks

    def t(self, key):
        return self.strings[key][self.lang]

    def tr(self, section, en_text, field=None, ja_fallback=None):
        """Translation of a CV item from _src/cv.yaml."""
        if self.lang == 'en':
            return en_text
        entry = (self.cv.get(section) or {}).get(en_text, {}).get(self.lang)
        if entry is None:
            if self.lang == 'ja' and ja_fallback:
                return ja_fallback
            warnings.append(f'no {self.lang} translation in _src/cv.yaml [{section}]: {en_text}')
            return en_text if field is None else None
        return entry if field is None else entry[field]

    def tag(self, en_label, soft=False):
        text = self.tr('tags', en_label) if en_label in (self.cv.get('tags') or {}) else en_label
        return f' <span class="tag{" is-soft" if soft else ""}">{esc(text)}</span>'

    def positions(self):
        rows = []
        for pos in self.profile['positions']:
            en_text = pos['en']
            title, _, where = en_text.replace('College of Physics', 'School of Physics').partition(', ')
            if self.lang != 'en':
                entry = self.tr('positions', en_text)
                if isinstance(entry, dict):
                    title, where = entry['title'], entry['where']
            when = fmt_span(pos['start'], pos.get('end'), self.lang, self.t('cv.present'))
            rows.append(f'<li><span class="when">{esc(when)}</span>'
                        f'<span class="what">{esc(title)}<span class="where">{esc(where)}</span></span></li>')
        return '<ol class="timeline">' + ''.join(rows) + '</ol>'

    def memberships(self):
        rows = []
        for m in self.profile['memberships']:
            name = self.tr('memberships', m['en'], ja_fallback=m.get('ja'))
            rows.append(f'<li><span class="when">{esc(period(m["period"], self.lang))}</span>{esc(name)}</li>')
        return '<ul class="plain-list">' + ''.join(rows) + '</ul>'

    def grants(self):
        rows = []
        for g in self.profile['funding']:
            if hidden(g):
                continue
            en_name = GRANT_NUMBER.sub('', g['en'])          # no grant numbers, amounts or project titles
            ja_name = FULLWIDTH_NUMBER.sub('', g.get('ja', '')).strip()
            name = self.tr('grants', en_name, ja_fallback=ja_name)
            role = pick(g.get('role'), 'en')
            rows.append(f'<li><span class="when">{esc(period(g["period"], self.lang))}</span>{esc(name)}'
                        + (self.tag(role) if role else '') + '</li>')
        return '<ul class="plain-list">' + ''.join(rows) + '</ul>'

    def teaching(self):
        rows = []
        for c in self.profile['teaching']:
            if c.get('optional'):            # e.g. private tutoring
                continue
            course, _, detail = c['en'].partition(' — ')
            course = re.sub(r'\s*\([^)]*;[^)]*\)', '', course)   # internal notes such as '(cosmology; taught twice)'
            role, *extras = [s.strip() for s in re.sub(r'\s*\(.*?\)', '', detail).split(',')]
            role = {'TA': 'Teaching assistant'}.get(role, role[:1].upper() + role[1:])
            ja_course = re.sub(r'（[^）]*、[^）]*）', '', c.get('ja', '').partition(' — ')[0])
            name = self.tr('teaching', course, ja_fallback=ja_course)
            rows.append(f'<li><span class="when">{esc(period(c["period"], self.lang))}</span>{esc(name)}'
                        + self.tag(role) + ''.join(self.tag(e, soft=True) for e in extras if e) + '</li>')
        return '<ul class="plain-list">' + ''.join(rows) + '</ul>'

    def talks_block(self):
        out = ['<div class="talk-groups">']
        for key in ('invited', 'contributed', 'domestic', 'seminar'):
            items = sorted((t for t in self.talks if t['category'] == key),
                           key=lambda t: talk_date(t, 'en')[0], reverse=True)
            if not items:
                continue
            out.append(f'<details class="card talk-group"{" open" if key == "invited" else ""}>'
                       f'<summary><span>{esc(self.t("talks." + key))}</span><span class="count">{len(items)}</span></summary>'
                       '<ol class="timeline talk-list">')
            out.extend(self.talk(t) for t in items)
            out.append('</ol></details>')
        out.append('</div>')
        return '\n'.join(out)

    def talk(self, t):
        meta = [pick(t['event'], 'en')] if t.get('event') else []
        place = ', '.join(p for p in (pick(t.get(k), 'en') for k in ('venue', 'city', 'country')) if p)
        if place:
            meta.append(place)
        if t.get('online'):
            meta.append(self.t('talks.online'))
        tags = []
        if t.get('language') == 'ja':
            tags.append(f'<span class="tag">{esc(self.t("talks.in_japanese"))}</span>')
        if t.get('recording'):
            tags.append(f'<a class="tag is-link" href="{esc(t["recording"])}" target="_blank" rel="noopener">'
                        f'{PLAY}{esc(self.t("talks.recording"))}</a>')
        return ('<li>'
                f'<span class="when">{esc(talk_date(t, self.lang)[1])}</span>'
                '<span class="what">'
                f'<span class="talk-title" lang="en">{esc(pick(t["title"], "en"))}</span>'
                f'<span class="where" lang="en">{esc(" · ".join(meta))}</span>'
                + (f'<span class="tags">{"".join(tags)}</span>' if tags else '') +
                '</span></li>')

    def langmenu(self):
        root = LANGS[self.lang][2]
        items = []
        for code, (hl, path, _, label, _) in LANGS.items():
            href = (root or './') if code == 'en' else f'{root}{code}/'
            current = ' aria-current="true"' if code == self.lang else ''
            items.append(f'<li><a href="{href}" hreflang="{hl}" lang="{hl}" data-lang-link{current}>{label}</a></li>')
        return ('<details class="lang-menu">'
                f'<summary aria-label="{esc(self.t("ui.language"))}">'
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                'aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9'
                'c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/></svg>'
                f'<span>{LANGS[self.lang][4]}</span></summary>'
                f'<ul>{"".join(items)}</ul></details>')

    def alternates(self):
        root = LANGS[self.lang][2]
        links = [f'    <link rel="alternate" hreflang="{hl}" href="{(root or "./") if code == "en" else root + code + "/"}">'
                 for code, (hl, *_rest) in LANGS.items()]
        return '\n'.join(links)

    def fonts(self):
        return (f'    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?{FONTS[self.lang]}&display=swap">')

    def js_strings(self):
        keys = {k[3:]: v[self.lang] for k, v in self.strings.items() if k.startswith('js.')}
        return json.dumps(keys, ensure_ascii=False)

    def render(self, template):
        blocks = {
            'positions': self.positions, 'memberships': self.memberships, 'grants': self.grants,
            'teaching': self.teaching, 'talks': self.talks_block, 'langmenu': self.langmenu,
            'alternates': self.alternates, 'fonts': self.fonts, 'js_strings': self.js_strings,
        }
        page = re.sub(r'\{\{b:(\w+)\}\}', lambda m: blocks[m.group(1)](), template)
        page = re.sub(r'\{\{t:([\w.]+)\}\}', lambda m: self.t(m.group(1)), page)
        page = page.replace('{{lang}}', LANGS[self.lang][0]).replace('{{root}}', LANGS[self.lang][2])
        left = re.findall(r'\{\{.*?\}\}', page)
        if left:
            sys.exit(f'unfilled placeholders in {self.lang}: {left}')
        return page


def main():
    template = (SRC / 'page.html').read_text(encoding='utf-8')
    strings = yaml.safe_load((SRC / 'strings.yaml').read_text(encoding='utf-8'))
    cv = yaml.safe_load((SRC / 'cv.yaml').read_text(encoding='utf-8'))
    profile = yaml.safe_load((MYCV / 'data/profile.yaml').read_text(encoding='utf-8'))
    talks = yaml.safe_load((MYCV / 'data/presentations.yaml').read_text(encoding='utf-8'))

    missing = [f'{k} ({lang})' for k, v in strings.items() for lang in LANGS if lang not in v]
    if missing:
        sys.exit('missing strings: ' + ', '.join(missing))

    for lang, (_, path, *_rest) in LANGS.items():
        out = ROOT / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(Builder(lang, strings, cv, profile, talks).render(template), encoding='utf-8')
        print(f'wrote {path}')
    for w in dict.fromkeys(warnings):
        print('warning:', w)


if __name__ == '__main__':
    main()
