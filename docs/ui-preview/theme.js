/* UI preview theme button. Light is the default; the choice is remembered (same key as the main site). */
'use strict';
(function () {
  var root = document.documentElement;
  root.classList.add('js');
  try { if (localStorage.getItem('anima-theme') === 'dark') root.setAttribute('data-theme', 'dark'); } catch (e) { /* storage may be blocked */ }
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('.themebtn');
    if (!btn) return;
    var label = function () { btn.textContent = root.getAttribute('data-theme') === 'dark' ? 'Light mode' : 'Dark mode'; };
    label();
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('anima-theme', next); } catch (e) { /* ignore */ }
      label();
    });
  });
})();
