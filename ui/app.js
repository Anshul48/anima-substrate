/* ANIMA state tree screen. Vanilla JS, no build step, no network except the
   local server that served this page. All record text is inserted with
   textContent (never innerHTML). */
'use strict';

const COLW = [188, 252, 372, 340], GAP = 44, PITCH = 80, NODEH = 72;
const COLX = COLW.map((_, i) => COLW.slice(0, i).reduce((a, b) => a + b, 0) + GAP * i);
const DEPTH = { owner: 0, workstream: 1, task: 2, attempt: 3 };
const SPEEDS = [10, 20, 40, 80, 160];
const TYPE_NAME = { owner: 'Owner', workstream: 'Workstream', task: 'Task', attempt: 'Attempt' };

const $ = (s, r = document) => r.querySelector(s);
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
const params = new URLSearchParams(location.search);

const S = {
  meta: null, tree: null, n: 0, total: 0, timeline: [], t0: 0, t1: 0,
  clock: 0, playing: false, speed: Number(params.get('speed')) || 40,
  sel: params.get('sel') || 'owner', selEvents: [], selKey: '',
  shownN: -1, wantN: null, inflight: false,
  els: new Map(), prev: new Map(), nodes: new Map(), parent: new Map(),
  cmdVerb: null, previewed: null, confirmTimer: null, lastLiveOk: null,
};

async function api(path, opts) {
  const r = await fetch(path, Object.assign({ cache: 'no-store' }, opts));
  const body = await r.json();
  if (!r.ok) throw new Error(body.error || r.statusText);
  return body;
}

/* ---------------------------------------------------------------- formatting */
function secs(v) {
  if (v === null || v === undefined) return '-';
  return Math.round(v).toLocaleString('en-US') + ' s';
}
function clockStr(epoch, ms) {
  if (!epoch) return '-';
  const d = new Date(epoch * 1000);
  const p = (x, n = 2) => String(x).padStart(n, '0');
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}` + (ms ? '.' + p(d.getUTCMilliseconds(), 3) : '');
}
function nowEpoch() { return S.meta && S.meta.mode === 'demo' ? S.clock : Date.now() / 1000; }

function nodeCost(n) {
  if (n.children && n.children.length) return n.children.reduce((a, c) => a + nodeCost(c), 0);
  if (n.running && n.started_epoch) return Math.max(0, nowEpoch() - n.started_epoch);
  return n.cost ? (n.cost.wall_s || 0) : 0;
}
function usdText(n) {
  const u = n.cost && n.cost.usd;
  return u === null || u === undefined ? 'not recorded' : '$' + u.toFixed(2);
}

/* ---------------------------------------------------------------- tree layout */
function index(tree) {
  S.nodes = new Map(); S.parent = new Map();
  (function walk(n, p) {
    S.nodes.set(n.id, n); if (p) S.parent.set(n.id, p.id);
    (n.children || []).forEach(c => walk(c, n));
  })(tree, null);
}
function layout(tree) {
  let row = 0;
  (function walk(n, depth) {
    n._col = DEPTH[n.type] !== undefined ? DEPTH[n.type] : depth;
    if (!n.children || !n.children.length) { n._y = row * PITCH; row++; }
    else {
      n.children.forEach(c => walk(c, depth + 1));
      n._y = (n.children[0]._y + n.children[n.children.length - 1]._y) / 2;
    }
  })(tree, 0);
  return row;
}

/* ---------------------------------------------------------------- node text */
function r2text(n) {
  const cost = secs(nodeCost(n));
  if (n.type === 'owner') {
    const c = n.counts || {};
    return `${c.tasks || 0} tasks`;
  }
  if (n.type === 'workstream') return cost;
  if (n.type === 'task') return `${n.harness || '-'} · ${cost}${n.escalated ? ' · escalated' : ''}`;
  const gate = n.gate ? `gate ${n.gate} · ` : '';
  return `${gate}${cost}${n.rule ? ' · ' + n.rule : ''}`;
}
function r3text(n) {
  if (n.type === 'owner') {
    const ch = S.tree && S.tree.chain;
    if (!ch) return 'no hash-chained record';
    return (ch.ok ? 'chain OK' : 'CHAIN BROKEN') + ' · ' + ch.sha256.slice(0, 8);
  }
  if (n.type === 'attempt' && n.via && n.chained !== false) return 'via ' + n.via;
  if (n.last) return `#${n.last.n} ${n.last.text}`;
  return '';
}
function nameText(n) {
  if (n.type === 'attempt') return `${n.label} · ${n.harness || '-'}`;
  return n.label;
}
function stText(n) { return n.overlay ? n.overlay : n.status; }

/* ---------------------------------------------------------------- render tree */
function nodeEl(n) {
  let e = S.els.get(n.id);
  if (e) return e;
  e = el('div', 'node entering');
  e.tabIndex = 0; e.setAttribute('role', 'button'); e.dataset.id = n.id;
  e._f = { num: el('span', 'num'), name: el('span', 'name'), st: el('span', 'st'), r2: el('span', 'r2'), r3: el('div', 'r3') };
  const r1 = el('div', 'r1'); r1.append(e._f.num, e._f.name);
  const r2 = el('div', 'r2row'); r2.append(e._f.r2, e._f.st);
  e.append(r1, r2, e._f.r3);
  e.addEventListener('click', ev => { ev.stopPropagation(); select(n.id); });
  e.addEventListener('keydown', ev => { if (ev.key === 'Enter') select(n.id); });
  $('#nodes').append(e);
  S.els.set(n.id, e);
  requestAnimationFrame(() => requestAnimationFrame(() => e.classList.remove('entering')));
  return e;
}
function setText(node, text) { if (node.textContent !== text) node.textContent = text; }

function renderTree() {
  const tree = S.tree;
  index(tree);
  const rows = layout(tree);
  $('#tree').style.height = Math.max(rows, 1) * PITCH + 'px';
  $('#empty').hidden = rows > 0 && tree.children.some(w => w.children.length);
  const seen = new Set();
  S.nodes.forEach(n => {
    seen.add(n.id);
    const e = nodeEl(n);
    e.className = e.className.replace(/\b(s-\w+|t-\w+)\b/g, '').replace(/\s+/g, ' ').trim();
    e.classList.add('node', 's-' + n.status, 't-' + n.type);
    if (n.id === S.sel) e.classList.add('sel');
    e.style.left = COLX[n._col] + 'px';
    e.style.width = COLW[n._col] + 'px';
    e.style.top = n._y + 'px';
    setText(e._f.num, n.type === 'task' ? String(n.num) : '');
    e._f.num.style.display = n.type === 'task' ? '' : 'none';
    setText(e._f.name, nameText(n));
    setText(e._f.st, stText(n));
    e._f.st.classList.toggle('ov', !!n.overlay);
    setText(e._f.r2, r2text(n));
    setText(e._f.r3, r3text(n));
    e.title = `${TYPE_NAME[n.type]}: ${nameText(n)}\n${stText(n)}\n${r3text(n)}`;
    const key = n.status + '|' + (n.last ? n.last.n : '') + '|' + (n.overlay || '');
    if (S.prev.has(n.id) && S.prev.get(n.id) !== key) {
      e.classList.remove('pulse'); void e.offsetWidth; e.classList.add('pulse');
    }
    S.prev.set(n.id, key);
  });
  S.els.forEach((e, id) => { if (!seen.has(id)) { e.remove(); S.els.delete(id); S.prev.delete(id); } });
  renderEdges();
}

function renderEdges() {
  const svg = $('#edges');
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const ns = 'http://www.w3.org/2000/svg';
  const add = (d, cls) => { const p = document.createElementNS(ns, 'path'); p.setAttribute('d', d); if (cls) p.setAttribute('class', cls); svg.append(p); };
  S.nodes.forEach(n => {
    (n.children || []).forEach((c, i) => {
      const x1 = COLX[n._col] + COLW[n._col], y1 = n._y + NODEH / 2;
      const x2 = COLX[c._col], y2 = c._y + NODEH / 2, mx = (x1 + x2) / 2;
      add(`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`);
      if (n.type === 'task' && i > 0) {   // escalation edge between two attempts of one task
        const p = n.children[i - 1], x = COLX[c._col] + 26;
        add(`M${x},${p._y + NODEH} L${x},${c._y - 2} M${x - 5},${c._y - 8} L${x},${c._y - 1} L${x + 5},${c._y - 8}`, 'esc');
      }
    });
  });
}

function tickCosts() {
  S.nodes.forEach(n => { const e = S.els.get(n.id); if (e) setText(e._f.r2, r2text(n)); });
  if (S.tree) renderFactsCost();
}

/* ---------------------------------------------------------------- header / bars */
function renderHeader() {
  const m = S.meta, t = S.tree;
  const mode = $('#mode');
  mode.className = 'badge ' + (m.mode === 'demo' ? 'replay' : 'live');
  if (m.mode === 'demo') {
    const a = S.timeline[0], b = S.timeline[S.timeline.length - 1];
    const day = a ? new Date(a.epoch * 1000).toISOString().slice(0, 10) : '';
    mode.textContent = `REPLAY of a recorded run · ${(m.names || []).join(', ')} · ${day} ${clockStr(a && a.epoch)}-${clockStr(b && b.epoch)}Z · not live`;
  } else {
    mode.textContent = `LIVE · ${(m.chains[0] || m.jobs || '').split('/').slice(-2).join('/')}`;
  }
  const ch = $('#chain'), c = t.chain;
  ch.textContent = '';
  if (!c) { ch.className = 'badge'; ch.textContent = 'job folders only: not hash-chained'; }
  else if (c.waiting) { ch.className = 'badge'; ch.textContent = 'waiting for the decision record to appear'; }
  else {
    const partial = S.n < S.total;
    const ok = partial ? c.shown_ok : c.ok;
    ch.className = 'badge ' + (ok ? 'ok' : 'bad');
    ch.title = 'Each record carries the SHA-256 of the line before it. This screen re-checks every link each time it reads the file.';
    ch.append(document.createTextNode(ok ? (partial ? `chain linked · records 1-${S.n} of ${c.records}` : `chain OK · ${c.records} records`)
      : `CHAIN BROKEN at line ${c.broken_at}`));
    const f = el('span', 'mono', ' ' + c.sha256.slice(0, 8)); ch.append(f);
  }
  const cn = t.counts;
  const s = $('#summary'); s.textContent = '';
  const b = (x) => { const e = el('b', '', String(x)); return e; };
  s.append(b(cn.tasks), ' tasks · ', b(cn.verified), ' verified · ', b(cn.running), ' running · ', b(cn.escalated), ' escalated');
}

function renderBar() {
  const now = $('#now');
  if (S.meta.mode === 'demo') {
    const ev = S.timeline[S.n - 1];
    now.textContent = '';
    if (!ev) { now.append(el('span', 'k', 'Recorded run'), 'press Play to replay what the agents did'); }
    else { now.append(el('span', 'n', '#' + ev.n), el('span', 'k', ev.kind), `${clockStr(ev.epoch)}Z  ${ev.task ? ev.task + ': ' : ''}${ev.text}`); }
    const span = S.t1 - S.t0;
    $('#clock').textContent = `${clockStr(S.clock)}Z  +${Math.max(0, Math.round(S.clock - S.t0))}/${Math.round(span)} s  record ${S.n}/${S.total}`;
    $('#b-play').textContent = S.playing ? 'Pause' : (S.clock >= S.t1 ? 'Replay' : 'Play');
    const r = $('#range'); if (document.activeElement !== r || !S.dragging) r.value = String(S.clock);
    $('#ticks u').style.width = Math.max(0, Math.min(1, (S.clock - S.t0 + 1) / (span + 1))) * 100 + '%';
  } else {
    const live = $('#livebar'); live.hidden = false;
    live.textContent = `LIVE · read from disk every 2 s · ${S.total} records · last read ${clockStr(Date.now() / 1000)}Z` +
      (S.lastLiveOk === false ? ' · READ FAILED' : '');
  }
}

function buildTransport() {
  const demo = S.meta.mode === 'demo';
  $('#transport').hidden = !demo; $('#now').hidden = !demo; $('#livebar').hidden = demo;
  if (!demo) return;
  const sp = $('#speeds');
  SPEEDS.forEach(v => {
    const b = el('button', '', v + 'x'); b.type = 'button'; b.dataset.v = v;
    b.addEventListener('click', () => { S.speed = v; markSpeed(); });
    sp.append(b);
  });
  markSpeed();
  const ticks = $('#ticks'), span = Math.max(S.t1 - S.t0, 1);
  S.timeline.forEach(ev => {
    const i = el('i'); i.style.left = ((ev.epoch - S.t0) / span * 100) + '%';
    if (ev.kind === 'decision.made') i.className = 'dec'; else if (ev.kind === 'task.blocked') i.className = 'blk'; else if (ev.kind === 'task.done') i.className = 'done';
    i.title = `#${ev.n} ${ev.kind} ${ev.task}`;
    ticks.append(i);
  });
  ticks.append(el('u'));
  const r = $('#range'); r.min = String(S.t0 - 1); r.max = String(S.t1); r.step = '0.05'; r.value = String(S.clock);
  r.addEventListener('input', () => { S.dragging = true; S.clock = Number(r.value); S.playing = false; });
  r.addEventListener('change', () => { S.dragging = false; });
  $('#b-play').addEventListener('click', togglePlay);
  $('#b-prev').addEventListener('click', () => stepRecord(-1));
  $('#b-next').addEventListener('click', () => stepRecord(1));
}
function markSpeed() { document.querySelectorAll('#speeds button').forEach(b => b.classList.toggle('on', Number(b.dataset.v) === S.speed)); }
function togglePlay() {
  if (!S.playing && S.clock >= S.t1) S.clock = S.t0 - 1;
  S.playing = !S.playing;
}
function stepRecord(d) {
  S.playing = false;
  const target = Math.max(0, Math.min(S.total, S.n + d));
  S.clock = target === 0 ? S.t0 - 1 : S.timeline[target - 1].epoch + 0.001;
}

/* ---------------------------------------------------------------- replay engine */
function countAt(clock) {
  let lo = 0, hi = S.timeline.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (S.timeline[mid].epoch <= clock) lo = mid + 1; else hi = mid; }
  return lo;
}
async function requestN(n) {
  S.wantN = n;
  if (S.inflight) return;
  S.inflight = true;
  try {
    while (S.wantN !== null) {
      const want = S.wantN; S.wantN = null;
      const d = await api('/api/tree?upto=' + want);
      applyTree(d, want);
    }
  } catch (e) { setError(e); } finally { S.inflight = false; }
}
let lastTs = 0, lastTick = 0;
function frame(ts) {
  const dt = lastTs ? (ts - lastTs) / 1000 : 0; lastTs = ts;
  if (S.meta.mode === 'demo') {
    if (S.playing) {
      S.clock += dt * S.speed;
      if (S.clock >= S.t1) { S.clock = S.t1; S.playing = false; }
    }
    const n = countAt(S.clock);
    if (n !== S.shownN) { S.shownN = n; requestN(n); }
  }
  if (S.tree && ts - lastTick > 200) { lastTick = ts; tickCosts(); renderBar(); }
  requestAnimationFrame(frame);
}

/* ---------------------------------------------------------------- data in */
function applyTree(d, wantN) {
  S.tree = d.tree; S.n = d.n; S.total = d.total;
  S.lastLiveOk = true;
  renderHeader(); renderTree(); renderBar();
  if (!S.nodes.has(S.sel)) S.sel = 'owner';
  if (S.cmdFor !== S.sel) renderCmdPanel();
  loadSelected();
}
function setError(e) {
  const m = $('#mode'); m.className = 'badge bad'; m.textContent = 'cannot read the data: ' + e.message;
  S.lastLiveOk = false;
}
async function pollLive() {
  try { applyTree(await api('/api/tree'), null); } catch (e) { setError(e); }
}

/* ---------------------------------------------------------------- selection + details */
function select(id) { S.sel = id; S.selKey = ''; renderTree(); renderCmdPanel(); loadSelected(true); }
function selNode() { return S.nodes.get(S.sel) || S.tree; }
function recordNodeId(n) {
  if (n.type === 'owner') { const w = n.children[0]; return w ? w.id : null; }
  return n.id;
}
async function loadSelected(force) {
  const n = selNode(); if (!n) return;
  const key = n.id + '|' + ((n.events || []).length) + '|' + S.n;
  renderDetail(n);
  if (!force && key === S.selKey) return;
  S.selKey = key;
  const rid = recordNodeId(n);
  if (!rid) { S.selEvents = []; renderRecords(n); return; }
  try {
    const up = S.meta.mode === 'demo' ? '&upto=' + S.n : '';
    const d = await api('/api/events?node=' + encodeURIComponent(rid) + up);
    if (S.selKey === key) { S.selEvents = d.events; renderRecords(n); }
  } catch (e) { S.selEvents = []; renderRecords(n); }
}

function fact(dl, k, v, cls) {
  dl.append(el('dt', '', k)); const dd = el('dd', cls || '', v); dl.append(dd); return dd;
}
function renderDetail(n) {
  $('#d-type').textContent = TYPE_NAME[n.type] + (n.type === 'task' ? ` ${n.num}` : '');
  $('#d-name').textContent = nameText(n);
  const p = $('#d-status'); p.className = 'pill s-' + n.status; p.textContent = stText(n);
  renderFacts(n);
  renderLast(n);
}
/* the command panel is rebuilt only when the selection changes, never on a data refresh,
   so a half-typed command or its output is not wiped every 2 seconds */
function renderCmdPanel() {
  const n = selNode(); S.cmdFor = n.id; S.cmdVerb = null; S.previewed = null;
  clearTimeout(S.confirmTimer); S.confirmTimer = null;
  renderCmdVerbs(n);
}
function renderFacts(n) {
  const dl = $('#d-facts'); dl.textContent = '';
  const ch = S.tree.chain;
  if (n.type === 'owner') {
    fact(dl, 'Workstreams', String(n.children.length));
    const c = n.counts; fact(dl, 'Tasks', `${c.tasks}: ${c.verified} verified, ${c.running} running, ${c.escalated} escalated`);
    if (ch) fact(dl, 'Fingerprint', ch.sha256, 'mono');
    if (ch && ch.head_match !== null) fact(dl, 'Saved fingerprint', ch.head_match ? 'matches' : 'DOES NOT MATCH', ch.head_match ? 'linkok' : 'linkbad');
  } else {
    if (n.type === 'workstream') fact(dl, 'Mode', n.mode || '-');
    if (n.type !== 'workstream') fact(dl, 'Harness', `${n.harness || '-'}${n.pool ? ' (' + n.pool + ')' : ''}`);
    if (n.type === 'task') fact(dl, 'Attempts', String(n.children.length) + (n.escalated ? ' (escalated)' : ''));
    if (n.type === 'attempt') {
      fact(dl, 'Rung', String(n.rung));
      if (n.gate) fact(dl, 'Hidden checker', n.gate + (n.rule ? ' (rule ' + n.rule + ')' : ''));
      if (n.said_done !== null && n.said_done !== undefined) fact(dl, 'Agent said done', n.said_done ? 'yes' : 'no');
      if (n.job_id) fact(dl, 'Job', n.job_id, 'mono');
      if (n.started_epoch) fact(dl, 'Started', clockStr(n.started_epoch) + 'Z');
    }
  }
  const cost = fact(dl, 'Wall time', '-'); cost.id = 'f-cost';
  fact(dl, 'Tokens / $', n.cost && n.cost.usd !== null && n.cost.usd !== undefined ? usdText(n) : 'not recorded here');
  renderFactsCost();
}
function renderFactsCost() {
  const c = $('#f-cost'); if (c) { const n = selNode(); c.textContent = secs(nodeCost(n)) + (n.running ? ' and counting' : ''); }
}
function lastOf(n) {
  if (n.last) return n.last;
  let best = null;
  (n.children || []).forEach(c => { const l = lastOf(c); if (l && (!best || l.n > best.n)) best = l; });
  return best;
}
function renderLast(n) {
  const box = $('#d-last'); box.textContent = '';
  box.append(el('h3', '', 'Last decision'));
  const l = lastOf(n);
  if (!l) { box.append(el('div', 'meta', 'no record yet')); return; }
  box.append(el('div', 'big', l.text));
  const meta = el('div', 'meta');
  if (l.chained) {
    meta.append(`#${l.n} · ${l.kind} · ${l.actor} · ${l.ts ? l.ts.slice(11, 19) : ''}Z · seal `, el('span', 'mono', l.seal), ' · ');
    meta.append(el('span', l.link_ok ? 'linkok' : 'linkbad', l.link_ok ? 'linked to the line before' : 'LINK BROKEN'));
  } else {
    meta.append(`${l.kind} · from the job log · `, el('span', 'unchained', 'not hash-chained'));
  }
  box.append(meta);
}
function renderRecords(n) {
  const ol = $('#d-records'); ol.textContent = '';
  const evs = S.selEvents.slice().reverse();
  $('#d-rec-title').textContent = `Decision records · ${evs.length} · newest first`;
  const lastN = lastOf(n) ? lastOf(n).n : -1;
  evs.forEach(ev => {
    const li = el('li'); if (ev.n === lastN) li.classList.add('hl');
    const h = el('div', 'h');
    h.append(el('span', 'mono', '#' + ev.n), el('span', 'k', ev.kind), el('span', '', (ev.ts || '').slice(11, 23) + 'Z'));
    if (ev.chained) h.append(el('span', ev.link_ok ? 'linkok' : 'linkbad', ev.link_ok ? 'linked' : 'BROKEN'));
    else h.append(el('span', 'unchained', 'unchained'));
    li.append(h, el('div', 'tx', ev.text));
    li.addEventListener('click', () => {
      const ex = li.querySelector('pre');
      if (ex) { ex.remove(); return; }
      const pre = el('pre');
      pre.textContent = JSON.stringify({ actor: ev.actor, task: ev.task, kind: ev.kind, ts: ev.ts, data: ev.data, prev: ev.prev, 'this line SHA-256': ev.seal }, null, 1);
      li.append(pre);
    });
    ol.append(li);
  });
  if (!evs.length) ol.append(el('li', '', 'no records for this node yet'));
}

/* ---------------------------------------------------------------- commands */
function taskTargetOf(n) {
  if (n.type === 'task') return n;
  if (n.type === 'attempt') return S.nodes.get(S.parent.get(n.id));
  return null;
}
function renderCmdVerbs(n) {
  const box = $('#cmd-verbs'); box.textContent = '';
  $('#cmd-title').textContent = S.meta.commands_enabled ? 'Change it (file-format test only: nothing reads the files)' : 'Change it (disabled: nothing reads commands yet)';
  if (!S.meta.commands_enabled) {   // nothing reads command files yet: no button that could not change a run
    $('#cmd-form').hidden = true;
    $('#cmd-note').textContent = 'Controls are disabled. Nothing in ANIMA reads command files yet, so a button here could not change a run. '
      + 'This screen is a live read-only view of the decision record. (Start with --enable-command-files to test the file format only.)';
    return;
  }
  const t = taskTargetOf(n);
  const verbs = t ? ['pause', 'resume', 'reprioritise', 'redirect', 'cancel'] : ['run-next'];
  verbs.forEach(v => {
    const b = el('button', S.cmdVerb === v ? 'on' : '', v === 'run-next' ? 'Run next job' : v[0].toUpperCase() + v.slice(1));
    b.type = 'button'; b.title = (S.meta.verbs || {})[v] || '';
    b.addEventListener('click', () => { S.cmdVerb = v; S.previewed = null; renderCmdVerbs(n); });
    box.append(b);
  });
  renderCmdForm(n, t);
  const demo = S.meta.mode === 'demo';
  $('#cmd-note').textContent = demo
    ? `Replay mode: a written command goes to ${S.meta.commands} and nothing reads it. Real mode writes to the live commands folder for anima to read.`
    : `Commands are files in ${S.meta.commands}. anima reads them; this screen never kills or edits a running agent.`;
}
function renderCmdForm(n, t) {
  const form = $('#cmd-form'); form.hidden = !S.cmdVerb;
  $('#cmd-out').textContent = '';
  if (!S.cmdVerb) return;
  const f = $('#cmd-fields');
  {
    f.textContent = '';
    const row = (label, ctl) => { f.append(el('label', '', label), ctl); };
    if (S.cmdVerb === 'reprioritise') {
      const s = el('select'); s.id = 'f-priority';
      (S.meta.priorities || []).forEach(p => s.append(new Option(p, p, false, p === 'high')));
      row('Priority', s);
    }
    if (S.cmdVerb === 'redirect' || S.cmdVerb === 'run-next') {
      const s = el('select'); s.id = 'f-harness';
      (S.meta.harnesses || []).forEach(h => s.append(new Option(h, h)));
      row('Harness', s);
    }
    const r = el('input'); r.id = 'f-reason'; r.type = 'text'; r.placeholder = 'optional reason'; r.maxLength = 300;
    row('Reason', r);
    if (S.cmdVerb === 'cancel' && S.meta.hand_run && S.meta.mode !== 'demo' && t && t.id.startsWith('job:')) {
      const c = el('input'); c.id = 'f-forward'; c.type = 'checkbox';
      const w = el('span', '', ' also run the real `hand-run cancel`'); const lab = el('label'); lab.append(c, w);
      f.append(el('span'), lab);
    }
  }
  $('#cmd-write').disabled = true; $('#cmd-write').textContent = 'Write command file';
  const wireBtn = (id, fn) => { const b = $(id); const nb = b.cloneNode(true); b.replaceWith(nb); nb.addEventListener('click', fn); return nb; };
  wireBtn('#cmd-preview', () => cmdPost(t, true));
  wireBtn('#cmd-write', () => cmdWriteClick(t));
  $('#cmd-write').disabled = true;
}
function cmdBody(t, dry) {
  const v = S.cmdVerb, args = {};
  if (v === 'reprioritise') args.priority = $('#f-priority').value;
  if (v === 'redirect' || v === 'run-next') args.harness = $('#f-harness').value;
  const body = { verb: v, args, reason: $('#f-reason').value, dry_run: dry };
  if (t) body.target = t.id;
  const fw = $('#f-forward'); if (fw && fw.checked) body.forward = true;
  return body;
}
async function cmdPost(t, dry) {
  const out = $('#cmd-out');
  try {
    const d = await api('/api/command', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Anima-Token': S.meta.token }, body: JSON.stringify(cmdBody(t, dry)) });
    out.textContent = '';
    out.append(el('b', '', 'command: '), d.cli + '\n');
    if (dry) {
      out.append(el('b', '', 'file content:\n'), JSON.stringify(d.command, null, 1));
      S.previewed = d; $('#cmd-write').disabled = false;
    } else {
      out.append(el('b', '', 'written: '), d.written + '\n');
      out.append(d.demo ? 'Replay: nothing reads this file.' : 'Waiting for anima to read it.');
      if (d.forwarded) out.append('\nforwarded to hand-run: ' + (d.forwarded.ran ? 'yes - ' : 'no - ') + d.forwarded.message);
      $('#cmd-write').disabled = true; $('#cmd-write').textContent = 'Write command file';
      if (S.meta.mode === 'demo') requestN(S.shownN); else pollLive();
    }
  } catch (e) { out.textContent = 'refused: ' + e.message; }
}
function cmdWriteClick(t) {
  const b = $('#cmd-write');
  if (!S.previewed) return;
  if (!S.confirmTimer) {
    b.textContent = 'Confirm: write it now';
    S.confirmTimer = setTimeout(() => { S.confirmTimer = null; b.textContent = 'Write command file'; }, 6000);
    return;
  }
  clearTimeout(S.confirmTimer); S.confirmTimer = null;
  cmdPost(t, false);
}

/* ---------------------------------------------------------------- keyboard + boot */
document.addEventListener('keydown', ev => {
  if (/^(INPUT|SELECT|TEXTAREA)$/.test(ev.target.tagName) && ev.target.type !== 'range') return;
  if (S.meta.mode !== 'demo') return;
  if (ev.key === ' ') { ev.preventDefault(); togglePlay(); }
  else if (ev.key === 'ArrowRight') stepRecord(1);
  else if (ev.key === 'ArrowLeft') stepRecord(-1);
  else if (ev.key === 'Home') { S.playing = false; S.clock = S.t0 - 1; }
  else if (ev.key === 'End') { S.playing = false; S.clock = S.t1; }
});
$('#treepane').addEventListener('click', () => select('owner'));

async function boot() {
  try {
    S.meta = await api('/api/meta');
    if (S.meta.mode === 'demo') {
      S.timeline = await api('/api/timeline');
      S.total = S.timeline.length;
      S.t0 = S.timeline[0].epoch; S.t1 = S.timeline[S.total - 1].epoch;
      const at = params.get('at');
      S.clock = at !== null ? (Number(at) <= 0 ? S.t0 - 1 : S.timeline[Math.min(Number(at), S.total) - 1].epoch + 0.001) : S.t0 - 1;
      S.playing = at === null && params.get('autoplay') !== '0';
      if (params.get('autoplay') === '1') S.playing = true;
    }
    buildTransport();
    if (S.meta.mode === 'demo') {
      S.shownN = countAt(S.clock);
      applyTree(await api('/api/tree?upto=' + S.shownN), S.shownN);
    } else {
      await pollLive();
      setInterval(pollLive, 2000);
    }
  } catch (e) { setError(e); }
  requestAnimationFrame(frame);
}
boot();
