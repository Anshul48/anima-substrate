/* Dashboard: activity stream entrance + install-line copy button. */
'use strict';

const stream = document.getElementById('stream');
DASH.stream.forEach((e) => {
  const li = document.createElement('li');
  const t = document.createElement('span');
  t.className = 't';
  t.textContent = e.t;
  const b = document.createElement('span');
  const k = document.createElement('span');
  k.className = 'k';
  k.textContent = e.tag;
  b.appendChild(k);
  b.appendChild(document.createTextNode(e.text));
  li.appendChild(t);
  li.appendChild(b);
  stream.appendChild(li);
});

// Staggered entrance; ?replay=1 replays it for a clean recording.
function entrance() {
  const items = stream.querySelectorAll('li');
  items.forEach((li) => li.classList.remove('in'));
  items.forEach((li, i) => setTimeout(() => li.classList.add('in'), 120 + i * 160));
}
if (new URLSearchParams(location.search).get('replay') === '1') {
  setTimeout(entrance, 400);
} else {
  entrance();
}

document.getElementById('copyBtn').addEventListener('click', async (ev) => {
  const line = document.getElementById('installLine').textContent;
  const btn = ev.currentTarget;
  try {
    await navigator.clipboard.writeText(line);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = line;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
  }
  btn.textContent = 'Copied';
  setTimeout(() => { btn.textContent = 'Copy'; }, 1600);
});
