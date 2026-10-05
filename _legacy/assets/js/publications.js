/*
    Publication list loaded from the INSPIRE-HEP API.
    https://github.com/inspirehep/rest-api-doc
*/
(function () {
    var AUTHOR_ID = 'A.Ota.1';
    var MY_NAME = 'Ota, Atsuhisa';
    var MAX_AUTHORS = 10;

    var API_URL = 'https://inspirehep.net/api/literature' +
        '?q=' + encodeURIComponent('a ' + AUTHOR_ID) +
        '&sort=mostrecent&size=250' +
        '&fields=titles,authors.full_name,author_count,collaborations,' +
        'arxiv_eprints,publication_info,dois,citation_count,control_number,earliest_date';

    function el(tag, text) {
        var node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function link(href, text) {
        var a = el('a', text);
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
        var span = el('span');
        span.className = 'pub-authors';
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
            span.appendChild(a.full_name === MY_NAME ? el('strong', name) : document.createTextNode(name));
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

    function renderPaper(meta) {
        var li = el('li');
        li.className = 'pub';

        var title = el('span', (meta.titles && meta.titles[0] && meta.titles[0].title) || 'Untitled');
        title.className = 'pub-title';
        li.appendChild(title);
        li.appendChild(el('br'));
        li.appendChild(renderAuthors(meta));
        li.appendChild(el('br'));

        var details = el('span');
        details.className = 'pub-details';
        var ref = journalRef(meta);
        var doi = meta.dois && meta.dois[0] && meta.dois[0].value;
        if (ref) {
            details.appendChild(doi ? link('https://doi.org/' + doi, ref) : document.createTextNode(ref));
        }
        var arxiv = meta.arxiv_eprints && meta.arxiv_eprints[0] && meta.arxiv_eprints[0].value;
        if (arxiv) {
            if (ref) details.appendChild(document.createTextNode(' · '));
            details.appendChild(link('https://arxiv.org/abs/' + arxiv, 'arXiv:' + arxiv));
        }
        if (!ref && !arxiv && meta.earliest_date) {
            details.appendChild(document.createTextNode(meta.earliest_date.slice(0, 4)));
        }
        details.appendChild(document.createTextNode(' · '));
        details.appendChild(link('https://inspirehep.net/literature/' + meta.control_number,
            'Citations: ' + (meta.citation_count || 0)));
        li.appendChild(details);
        return li;
    }

    function load() {
        var container = document.getElementById('publications');
        if (!container) return;
        var status = document.getElementById('publications-status');

        fetch(API_URL, { headers: { Accept: 'application/json' } })
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                var hits = data.hits.hits;
                var list = el('ol');
                list.className = 'pub-list';
                hits.forEach(function (hit) { list.appendChild(renderPaper(hit.metadata)); });
                container.appendChild(list);
                status.textContent = hits.length + ' papers, newest first. Automatically retrieved from ';
                status.appendChild(link('https://inspirehep.net/authors?q=ids.value:' + AUTHOR_ID, 'INSPIRE-HEP'));
                status.appendChild(document.createTextNode('.'));
            })
            .catch(function () {
                status.textContent = 'The publication list could not be loaded. Please see ';
                status.appendChild(link('https://inspirehep.net/authors?q=ids.value:' + AUTHOR_ID, 'INSPIRE-HEP'));
                status.appendChild(document.createTextNode('.'));
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
