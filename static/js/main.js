(function () {
    'use strict';

    var doc = document;

    var header = doc.querySelector('.header');
    var burger = doc.querySelector('.header__burger');
    if (header && burger) {
        burger.addEventListener('click', function () {
            header.classList.toggle('header--menu-open');
        });
        header.querySelectorAll('.header__nav-link').forEach(function (l) {
            l.addEventListener('click', function () { header.classList.remove('header--menu-open'); });
        });
    }

    doc.querySelectorAll('[data-tabs]').forEach(function (group) {
        var tabs = group.querySelectorAll('[data-tab]');
        var scope = group.getAttribute('data-tabs-scope')
            ? doc.querySelector(group.getAttribute('data-tabs-scope'))
            : group.parentElement;
        function activate(key) {
            tabs.forEach(function (t) { t.classList.toggle('tab--active', t.dataset.tab === key); });
            scope.querySelectorAll('[data-tab-panel]').forEach(function (p) {
                p.hidden = p.dataset.tabPanel !== key;
            });
        }
        tabs.forEach(function (t) {
            t.addEventListener('click', function () { activate(t.dataset.tab); });
        });
        if (tabs.length) activate(tabs[0].dataset.tab);
    });

    doc.querySelectorAll('[data-dropdown]').forEach(function (dd) {
        var toggle = dd.querySelector('[data-dropdown-toggle]');
        var menu = dd.querySelector('.dropdown__menu');
        if (!toggle || !menu) return;
        menu.hidden = true;
        toggle.addEventListener('click', function (e) {
            e.stopPropagation();
            menu.hidden = !menu.hidden;
        });
    });
    doc.addEventListener('click', function () {
        doc.querySelectorAll('.dropdown__menu').forEach(function (m) { m.hidden = true; });
    });

    doc.querySelectorAll('[data-modal-open]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var m = doc.getElementById(btn.dataset.modalOpen);
            if (m) m.hidden = false;
        });
    });
    doc.querySelectorAll('.modal-backdrop').forEach(function (bd) {
        bd.hidden = true;
        bd.addEventListener('click', function (e) {
            if (e.target === bd || e.target.hasAttribute('data-modal-close')) bd.hidden = true;
        });
    });
    doc.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') doc.querySelectorAll('.modal-backdrop:not([hidden])').forEach(function (m) { m.hidden = true; });
    });

    window.toast = function (msg, ms) {
        var region = doc.getElementById('toast-region');
        if (!region) return;
        var el = doc.createElement('div');
        el.className = 'toast';
        el.textContent = msg;
        region.appendChild(el);
        setTimeout(function () { el.remove(); }, ms || 3200);
    };
    doc.querySelectorAll('[data-toast]').forEach(function (b) {
        b.addEventListener('click', function () { window.toast(b.dataset.toast); });
    });

    doc.querySelectorAll('form[data-loading]').forEach(function (f) {
        f.addEventListener('submit', function () {
            var b = f.querySelector('[type=submit]');
            if (b) b.classList.add('is-loading');
        });
    });

    doc.querySelectorAll('input[type=file][data-preview]').forEach(function (input) {
        var target = doc.querySelector(input.dataset.preview);
        if (!target) return;
        input.addEventListener('change', function () {
            target.innerHTML = '';
            Array.prototype.forEach.call(input.files, function (file) {
                if (!file.type.startsWith('image/')) return;
                var img = doc.createElement('img');
                img.style.cssText = 'width:96px;height:96px;object-fit:cover;border-radius:10px';
                img.src = URL.createObjectURL(file);
                target.appendChild(img);
            });
        });
    });

    doc.querySelectorAll('.chip input[type=checkbox], .chip input[type=radio]').forEach(function (input) {
        var chip = input.closest('.chip');
        var sync = function () { chip.classList.toggle('chip--active', input.checked); };
        input.addEventListener('change', function () {
            if (input.type === 'radio' && input.name) {
                doc.querySelectorAll('.chip input[name="' + input.name + '"]').forEach(function (other) {
                    other.closest('.chip').classList.toggle('chip--active', other.checked);
                });
            } else {
                sync();
            }
        });
        sync();
    });

    doc.querySelectorAll('[data-checkin]').forEach(function (checkin) {
        var checkout = doc.querySelector('[data-checkout]');
        if (!checkout) return;
        var today = new Date();
        var iso = function (d) { return d.toISOString().split('T')[0]; };
        var plus = function (n) { var d = new Date(today); d.setDate(d.getDate() + n); return d; };
        checkin.min = iso(today);
        checkout.min = iso(plus(1));
        checkin.addEventListener('change', function () {
            var d = new Date(this.value);
            if (isNaN(d)) return;
            var next = new Date(d); next.setDate(next.getDate() + 1);
            checkout.min = iso(next);
            if (checkout.value && checkout.value < iso(next)) checkout.value = iso(next);
        });
    });
})();
