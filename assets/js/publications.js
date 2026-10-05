/*
    Publication list loaded from the INSPIRE-HEP API.
    https://github.com/inspirehep/rest-api-doc
*/
(function () {
    var AUTHOR_ID = 'A.Ota.1';
    var MY_NAME = 'Ota, Atsuhisa';
    var MAX_AUTHORS = 10;
    var INITIAL_COUNT = 10;
    var PROFILE_URL = 'https://inspirehep.net/authors?q=ids.value:' + AUTHOR_ID;

    var API_URL = 'https://inspirehep.net/api/literature' +
        '?q=' + encodeURIComponent('a ' + AUTHOR_ID) +
        '&sort=mostrecent&size=250' +
        '&fields=titles,authors.full_name,author_count,collaborations,' +
        'arxiv_eprints,publication_info,dois,citation_count,control_number,earliest_date';

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function link(href, text) {
        var a = el('a', '', text);
        a.href = href;
        a.target = '_blank';
        a.rel = 'noopener';
        return a;
    }

    // "Ota, Atsuhisa" -> "A. Ota"
    function shortName(fullName) {
        var parts = fullName.split(',');
        if (parts.length < 2) return fullName.trim();
        var initials = parts[1].trim().split(/[\s-]+/).filter(Boolean).map(function (n) {
            return n.charAt(0) + '.';
        }).join(' ');
        return initials + ' ' + parts[0].trim();
    }

    function renderAuthors(meta) {
        var span = el('span', 'pub-authors');
        var authors = meta.authors || [];
        var total = meta.author_count || authors.length;
        if (meta.collaborations && total > MAX_AUTHORS) {
            span.textContent = meta.collaborations.map(function (c) { return c.value; }).join(', ') +
                ' Collaboration';
            return span;
        }
        var shown = authors.slice(0, MAX_AUTHORS);
        shown.forEach(function (a, i) {
            if (i > 0) span.appendChild(document.createTextNode(', '));
            var name = shortName(a.full_name);
            span.appendChild(a.full_name === MY_NAME ? el('strong', '', name) : document.createTextNode(name));
        });
        if (total > shown.length) span.appendChild(document.createTextNode(' et al.'));
        return span;
    }

    function journalRef(meta) {
        var info = (meta.publication_info || []).filter(function (p) { return p.journal_title; })[0];
        if (!info) return '';
        var ref = info.journal_title;
        if (info.journal_volume) ref += ' ' + info.journal_volume;
        var page = info.artid || info.page_start;
        if (page) ref += ', ' + page;
        if (info.year) ref += ' (' + info.year + ')';
        return ref;
    }

    function year(meta) {
        var info = (meta.publication_info || []).filter(function (p) { return p.year; })[0];
        if (info) return String(info.year);
        return meta.earliest_date ? meta.earliest_date.slice(0, 4) : '';
    }

    function renderPaper(meta) {
        var li = el('li', 'card pub');
        li.appendChild(el('span', 'pub-year', year(meta) || '—'));

        var title = el('span', 'pub-title');
        title.appendChild(link('https://inspirehep.net/literature/' + meta.control_number,
            (meta.titles && meta.titles[0] && meta.titles[0].title) || 'Untitled'));
        li.appendChild(title);
        li.appendChild(renderAuthors(meta));

        var links = el('span', 'pub-links');
        var ref = journalRef(meta);
        var doi = meta.dois && meta.dois[0] && meta.dois[0].value;
        if (ref) links.appendChild(doi ? link('https://doi.org/' + doi, ref) : el('span', '', ref));
        var arxiv = meta.arxiv_eprints && meta.arxiv_eprints[0] && meta.arxiv_eprints[0].value;
        if (arxiv) links.appendChild(link('https://arxiv.org/abs/' + arxiv, 'arXiv:' + arxiv));
        links.appendChild(link('https://inspirehep.net/literature/' + meta.control_number +
            '?ui-citation-summary=true', 'Citations: ' + (meta.citation_count || 0)));
        li.appendChild(links);
        return li;
    }

    function setStatus(status, text) {
        status.textContent = text + ' ';
        status.appendChild(link(PROFILE_URL, 'See all on INSPIRE-HEP'));
        status.appendChild(document.createTextNode('.'));
    }

    function load() {
        var list = document.getElementById('pub-list');
        var status = document.getElementById('pub-status');
        var more = document.getElementById('pub-more');
        if (!list) return;

        fetch(API_URL, { headers: { Accept: 'application/json' } })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                var hits = data.hits.hits;
                list.textContent = '';
                hits.forEach(function (hit, i) {
                    var item = renderPaper(hit.metadata);
                    if (i >= INITIAL_COUNT) item.hidden = true;
                    list.appendChild(item);
                });
                setStatus(status, hits.length + ' papers, newest first, updated automatically.');
                if (hits.length > INITIAL_COUNT) {
                    var button = more.querySelector('button');
                    button.textContent = 'Show all ' + hits.length + ' papers';
                    more.hidden = false;
                    button.addEventListener('click', function () {
                        Array.prototype.forEach.call(list.children, function (item) { item.hidden = false; });
                        more.hidden = true;
                    });
                }
            })
            .catch(function () {
                list.textContent = '';
                setStatus(status, 'The publication list could not be loaded right now.');
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
