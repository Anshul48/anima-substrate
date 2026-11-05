/* State-tree screen: builds the tree from RUN/TASKS/NARR and replays records 1..69. */
'use strict';

const NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('tree');
const $ = (id) => document.getElementById(id);

const rowY = (i) => 60 + i * 68;
const TASK_X = 388, TASK_W = 300, R0_CX = 800, R1_CX = 1010;

function el(tag, attrs, parent) {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}
function txt(parent, x, y, str, cls, anchor) {
  const t = el('text', { x, y, class: cls, 'text-anchor': anchor || 'start' }, parent);
  t.textContent = str;
  return t;
}

// ---- static spine: root + coordinator -------------------------------------
const spine = el('g', {}, svg);
el('path', { d: 'M106,332 L224,332', class: 'edge live', pathLength: '1' }, spine);
{
  const g = el('g', { class: 'node' }, spine);
  const gr = el('g', { class: 'grow' }, g);
  el('path', { d: 'M74,300 L106,332 L74,364 L42,332 Z', fill: 'var(--gold)' }, gr);
  txt(gr, 74, 338, 'A', 'att-rung', 'middle').setAttribute('fill', 'var(--bg)');
  txt(spine, 74, 388, 'flagship-run3', 'root-label', 'middle');
  txt(spine, 74, 405, '9 jobs', 'root-label', 'middle');
}
{
  const g = el('g', { class: 'node' }, spine);
  const gr = el('g', { class: 'grow' }, g);
  el('rect', { x: 224, y: 306, width: 52, height: 52, rx: 13, fill: 'var(--teal)' }, gr);
  txt(gr, 250, 339, 'C', 'att-rung', 'middle').setAttribute('fill', 'var(--bg)');
  txt(spine, 250, 388, 'coordinator', 'coord-label', 'middle');
}

// ---- per-task groups -------------------------------------------------------
const built = TASKS.map((t, i) => {
  const y = rowY(i);
  const g = el('g', { class: 'node pre', 'data-task': t.n }, svg);
  const edges = el('g', {}, g);
  const eFan = el('path', {
    d: `M276,332 C 336,332 320,${y} ${TASK_X},${y}`,
    class: 'edge draw', pathLength: '1',
  }, edges);
  const eAtt = el('path', {
    d: `M${TASK_X + TASK_W},${y} L${R0_CX - 23},${y}`,
    class: 'edge draw', pathLength: '1',
  }, edges);
  let eEsc = null;
  if (t.r1) {
    eEsc = el('path', {
      d: `M${R0_CX + 24},${y + 6} C ${R0_CX + 72},${y + 46} ${R1_CX - 76},${y + 46} ${R1_CX - 28},${y + 6}`,
      class: 'edge draw escalate', pathLength: '1',
    }, edges);
  }
  const body = el('g', { class: 'grow' }, g);
  const taskG = el('g', {}, body);
  el('rect', { x: TASK_X, y: y - 26, width: TASK_W, height: 52, rx: 13, class: 'task-rect' }, taskG);
  const bar = el('rect', { x: TASK_X, y: y - 26, width: 6, height: 52, rx: 3, class: 'task-bar', fill: 'var(--faint)' }, taskG);
  txt(taskG, TASK_X + 18, y - 3, '#' + t.n, 'task-num');
  txt(taskG, TASK_X + 44, y - 3, t.short, 'task-name');
  const subT = txt(taskG, TASK_X + 18, y + 17, '', 'task-sub');
  // r0 attempt
  const r0 = el('g', {}, body);
  const r0in = el('g', { class: 'subgrow pre' }, r0);
  el('circle', { cx: R0_CX, cy: y, r: 28, class: 'att-ring' }, r0in);
  el('circle', { cx: R0_CX, cy: y, r: 23, class: 'att-circle' }, r0in);
  txt(r0in, R0_CX, y + 5, 'r0', 'att-rung', 'middle');
  txt(r0in, R0_CX, y - 32, 'Muse Code', 'att-who', 'middle');
  const s0 = el('g', { class: 'stamp pre stamp-pass', transform: `translate(848,${y - 16})` }, body);
  el('rect', { x: 0, y: 0, width: 88, height: 32, rx: 16, 'stroke-width': 2 }, s0);
  const s0t = txt(s0, 44, 22, 'PASS', '', 'middle');
  // r1 attempt (escalated tasks only)
  let r1 = null, s1 = null, s1t = null;
  if (t.r1) {
    r1 = el('g', {}, body);
    const r1in = el('g', { class: 'subgrow pre' }, r1);
    el('circle', { cx: R1_CX, cy: y, r: 28, class: 'att-ring' }, r1in);
    el('circle', { cx: R1_CX, cy: y, r: 23, class: 'att-circle' }, r1in);
    txt(r1in, R1_CX, y + 5, 'r1', 'att-rung', 'middle');
    txt(r1in, R1_CX, y - 32, 'Claude Code', 'att-who', 'middle');
    r1._in = r1in;
    s1 = el('g', { class: 'stamp pre stamp-pass', transform: `translate(1058,${y - 16})` }, body);
    el('rect', { x: 0, y: 0, width: 88, height: 32, rx: 16, 'stroke-width': 2 }, s1);
    s1t = txt(s1, 44, 22, 'PASS', '', 'middle');
  }
  g.addEventListener('click', () => select(t.n, true));
  return { t, i, y, g, eFan, eAtt, eEsc, bar, subT, r0, r0in, s0, s0t, r1, s1, s1t };
});

function attState(t, att, rec) {
  if (rec < att.recStarted) return 'wait';
  if (rec < att.recVerdict) return 'run';
  return att.verdict === 'PASS' ? 'pass' : 'fail';
}

let selected = 6;

function select(n, manual) {
  selected = n;
  built.forEach((b) => b.g.classList.toggle('sel', b.t.n === n));
  if (manual) renderDetail(cur);
}

function countsAt(rec) {
  let v = 0, r = 0, e = 0;
  for (const t of TASKS) {
    const done = t.r1 ? t.r1.recVerdict : t.r0.recVerdict;
    if (rec >= done) v++;
    else if (rec >= t.recStarted) r++;
    if (t.escalated && rec >= t.escalated) e++;
  }
  return { v, r, e };
}

function renderDetail(rec) {
  const t = TASKS[selected - 1];
  $('dName').textContent = '#' + t.n + ' ' + t.name;
  const rows = [];
  const st0 = rec < t.recStarted ? 'wait' : attState(t, { ...t.r0, recStarted: t.recStarted }, rec);
  const pill = (s) => s === 'pass' ? '<span class="verdict-pill verdict-pass">PASS</span>'
    : s === 'fail' ? '<span class="verdict-pill verdict-fail">FAIL</span>'
    : s === 'run' ? '<span class="verdict-pill verdict-run">RUNNING</span>' : 'waiting';
  rows.push(`<div><span class="k">rung 0</span><span>Muse Code · ${st0 === 'wait' ? 'waiting' : t.r0.wall + ' s'} · ${pill(st0)}</span></div>`);
  if (t.r1) {
    const st1 = rec < t.r1.recStarted ? 'wait' : attState(t, t.r1, rec);
    rows.push(`<div><span class="k">rung 1</span><span>Claude Code · ${st1 === 'wait' ? 'not started yet' : t.r1.wall + ' s · ' + pill(st1)}</span></div>`);
  }
  const done = t.r1 ? t.r1.recVerdict : t.r0.recVerdict;
  if (rec >= done) {
    rows.push(`<div><span class="k">checker</span><span>sealed <span class="mono">${t.seal}</span>, linked to the line before</span></div>`);
    rows.push(`<div><span class="k">plainly</span><span>${t.r1
      ? 'The first worker said done, the checker said FAIL, the second worker fixed it.'
      : 'The worker tried a fix. The checker said PASS.'}</span></div>`);
  } else if (rec >= t.recStarted) {
    const gap = t.r1 && rec >= t.r0.recVerdict && rec < t.r1.recStarted;
    rows.push(`<div><span class="k">plainly</span><span>${gap
      ? 'The first answer failed. The second worker starts next.'
      : 'The worker is trying a fix. The checker has not spoken yet.'}</span></div>`);
  } else {
    rows.push('<div><span class="k">plainly</span><span>Waiting in the queue.</span></div>');
  }
  $('dRows').innerHTML = rows.join('');
}

let cur = 1;

function render(rec) {
  cur = Math.max(1, Math.min(69, Math.round(rec)));
  for (const b of built) {
    const { t } = b;
    const born = cur >= t.recCreated;
    b.g.classList.toggle('pre', !born);
    b.eFan.classList.toggle('live', born);
    const started = cur >= t.recStarted;
    b.eAtt.classList.toggle('live', started);
    b.r0in.classList.toggle('pre', !started);
    const st0 = !started ? 'wait' : cur < t.r0.recVerdict ? 'run' : (t.r0.verdict === 'PASS' ? 'pass' : 'fail');
    b.r0.setAttribute('class', st0 === 'run' ? 'att-run' : st0 === 'pass' ? 'att-pass' : st0 === 'fail' ? 'att-fail' : '');
    const showS0 = cur >= t.r0.recVerdict;
    b.s0.classList.toggle('pre', !showS0);
    b.s0.setAttribute('class', `stamp${showS0 ? '' : ' pre'} ${t.r0.verdict === 'PASS' ? 'stamp-pass' : 'stamp-fail'}`);
    b.s0t.textContent = t.r0.verdict;
    if (t.r1) {
      const e1born = cur >= t.r1.recStarted;
      b.eEsc.classList.toggle('live', e1born);
      b.r1._in.classList.toggle('pre', !e1born);
      const st1 = !e1born ? 'wait' : cur < t.r1.recVerdict ? 'run' : 'pass';
      b.r1.setAttribute('class', st1 === 'run' ? 'att-run' : st1 === 'pass' ? 'att-pass' : '');
      const showS1 = cur >= t.r1.recVerdict;
      b.s1.classList.toggle('pre', !showS1);
      b.s1t.textContent = 'PASS';
    }
    // task row text + bar
    const done = t.r1 ? t.r1.recVerdict : t.r0.recVerdict;
    if (cur < t.recCreated) { b.subT.textContent = ''; b.bar.setAttribute('fill', 'var(--faint)'); }
    else if (cur < t.recStarted) { b.subT.textContent = 'queued'; b.bar.setAttribute('fill', 'var(--faint)'); }
    else if (cur < done) {
      const r0failed = t.r1 && cur >= t.r0.recVerdict;
      const r1run = t.r1 && cur >= t.r1.recStarted;
      b.subT.textContent = r1run ? 'Claude Code · working'
        : r0failed ? 'checker said FAIL · escalating' : 'Muse Code · working';
      b.bar.setAttribute('fill', 'var(--amber)');
    } else {
      const wall = t.r1 ? (t.r0.wall + t.r1.wall) : t.r0.wall;
      b.subT.textContent = `checker said PASS · ${wall} s${t.r1 ? ' · escalated' : ''}`;
      b.bar.setAttribute('fill', 'var(--green)');
    }
  }
  // header + panel
  const { v, r, e } = countsAt(cur);
  $('cVerified').textContent = v;
  $('cRunning').textContent = r;
  $('cEsc').textContent = e;
  $('clock').textContent = RUN.clock[cur];
  $('recNum').textContent = `${cur} / 69`;
  $('chainRec').textContent = cur === 69 ? '69' : `1–${cur} of 69`;
  const last = [...NARR].reverse().find((n) => n.rec <= cur);
  $('nowTitle').textContent = cur >= 69 ? 'All 9 jobs verified'
    : cur >= 60 ? 'Job 8 climbs the ladder'
    : cur >= 29 ? 'Jobs finishing, one by one'
    : cur >= 16 ? 'First jobs verified'
    : cur >= 3 ? 'Workers pick up jobs' : 'Run begins';
  $('nowSub').textContent = `record ${cur} of 69 · ${RUN.clock[cur]}`;
  const lines = NARR.filter((n) => n.rec <= cur).slice(-5).reverse();
  $('feed').innerHTML = lines.map((n, k) =>
    `<li class="${k === 0 ? '' : 'old'}">${n.text}<span class="rec">record #${n.rec} · ${RUN.clock[n.rec]}</span></li>`).join('');
  if (document.activeElement !== $('scrubber')) $('scrubber').value = cur;
  if (!playing) $('playBtn').textContent = cur >= 69 ? 'Replay' : 'Play';
  renderDetail(cur);
}

// ---- playback --------------------------------------------------------------
let playing = false, raf = 0, lastT = 0, frac = 1;
const RPS = 69 / 20; // 1x = full replay in 20 s

function tick(ts) {
  if (!playing) return;
  if (!lastT) lastT = ts;
  const speed = parseFloat($('speed').value);
  frac += ((ts - lastT) / 1000) * RPS * speed;
  lastT = ts;
  if (frac >= 69) { frac = 69; pause(); $('playBtn').textContent = 'Replay'; }
  render(frac);
  if (playing) raf = requestAnimationFrame(tick);
}
function play() {
  if (cur >= 69) frac = 1;
  playing = true; lastT = 0;
  $('playBtn').textContent = 'Pause';
  raf = requestAnimationFrame(tick);
}
function pause() {
  playing = false;
  cancelAnimationFrame(raf);
  if ($('playBtn').textContent === 'Pause') $('playBtn').textContent = 'Play';
}
$('playBtn').addEventListener('click', () => (playing ? pause() : play()));
$('scrubber').addEventListener('input', () => { pause(); frac = parseInt($('scrubber').value, 10); render(frac); });
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && e.target === document.body) { e.preventDefault(); playing ? pause() : play(); }
  if (e.key === 'ArrowRight') { pause(); frac = Math.min(69, cur + 1); render(frac); }
  if (e.key === 'ArrowLeft') { pause(); frac = Math.max(1, cur - 1); render(frac); }
});

select(6, false);
render(1);
if (new URLSearchParams(location.search).get('replay') === '1') play();
