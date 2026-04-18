document.addEventListener('DOMContentLoaded', function () {
    const toggleButton = document.querySelector('[data-nav-toggle]');
    const navMenu = document.querySelector('[data-nav-menu]');

    if (!toggleButton || !navMenu) {
        return;
    }

    const closeMenu = function () {
        navMenu.classList.remove('is-open');
        toggleButton.setAttribute('aria-expanded', 'false');
    };

    toggleButton.addEventListener('click', function () {
        const isOpen = navMenu.classList.toggle('is-open');
        toggleButton.setAttribute('aria-expanded', String(isOpen));
    });

    navMenu.addEventListener('click', function (event) {
        if (event.target.closest('a, button')) {
            closeMenu();
        }
    });

    document.addEventListener('click', function (event) {
        if (navMenu.contains(event.target) || toggleButton.contains(event.target)) {
            return;
        }

        closeMenu();
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 768) {
            closeMenu();
        }
    });
});