/* ANIMA site: copy buttons and the theme button. Nothing else; the pages work without it. */
(function () {
  var root = document.documentElement;
  function stored() { try { return localStorage.getItem('anima-theme'); } catch (e) { return null; } }
  function store(v) { try { localStorage.setItem('anima-theme', v); } catch (e) {} }
  function current() {
    var t = root.getAttribute('data-theme');
    if (t) return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  var btn = document.querySelector('.themebtn');
  if (btn) {
    var label = function () { btn.textContent = current() === 'dark' ? 'Light mode' : 'Dark mode'; };
    label();
    btn.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      store(next);
      label();
    });
  }
  var buttons = document.querySelectorAll('.copy[data-copy]');
  Array.prototype.forEach.call(buttons, function (b) {
    b.addEventListener('click', function () {
      var text = b.getAttribute('data-copy');
      var done = function () { var old = b.textContent; b.textContent = 'Copied'; setTimeout(function () { b.textContent = old; }, 1600); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { window.prompt('Copy this line:', text); });
      } else { window.prompt('Copy this line:', text); }
    });
  });
})();
