/*
    Small interactions: color theme toggle, email link, and highlighting
    the current section in the navigation.
*/
(function () {
    var root = document.documentElement;

    // Theme toggle ---------------------------------------------------------
    var toggle = document.querySelector('.theme-toggle');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

    function currentTheme() {
        return root.dataset.theme || (prefersDark.matches ? 'dark' : 'light');
    }

    function syncToggle() {
        var dark = currentTheme() === 'dark';
        root.dataset.theme = currentTheme();
        toggle.setAttribute('aria-pressed', String(dark));
    }

    toggle.addEventListener('click', function () {
        root.dataset.theme = currentTheme() === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
        syncToggle();
    });
    syncToggle();

    // Email: assembled here so the address is not in the HTML source ------
    var email = document.getElementById('email');
    if (email) {
        var address = email.dataset.user + '@' + email.dataset.domain;
        email.href = 'mailto:' + address;
        email.querySelector('span').textContent = address;
    }

    // Highlight the section currently in view --------------------------------
    var links = Array.prototype.slice.call(document.querySelectorAll('.nav-links a'));
    if (!('IntersectionObserver' in window)) return;

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            links.forEach(function (link) {
                if (link.getAttribute('href') === '#' + entry.target.id) {
                    link.setAttribute('aria-current', 'true');
                } else {
                    link.removeAttribute('aria-current');
                }
            });
        });
    }, { rootMargin: '-40% 0px -55% 0px' });

    links.forEach(function (link) {
        var section = document.querySelector(link.getAttribute('href'));
        if (section) observer.observe(section);
    });
})();
