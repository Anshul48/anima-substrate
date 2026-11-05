/* Keeps the site's theme button honest: light is the default, even when the system is dark. */
'use strict';
(function () {
  var root = document.documentElement;
  if (root.getAttribute('data-theme')) return;
  root.setAttribute('data-theme', 'light');
  var btn = document.querySelector('.themebtn');
  if (btn) btn.textContent = 'Dark mode';
})();
