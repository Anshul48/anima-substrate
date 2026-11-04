/* Real run data for the ANIMA UI preview.
   Sources: flagship-run3 decision log (69 records, chain OK, fingerprint
   acd95bf03497057c…) via READY/anima-build/ui/RUN-LOG.md, and the integrate
   fresh-clone RUN-LOG (tiny-bug PASS runs, memory recall, voice timings).
   Every number below traces to one of those two logs. */
'use strict';

const RUN = {
  name: 'flagship-run3',
  records: 69,
  fingerprint: 'acd95bf03497057c',
  tasksTotal: 9,
  // Record clock (HH:MM:SS) per record number, 1-based, from the real log.
  clock: (() => {
    const c = new Array(70).fill('');
    const set = (from, to, t) => { for (let i = from; i <= to; i++) c[i] = t; };
    set(1, 1, '23:17:28'); set(2, 5, '23:17:29'); set(6, 7, '23:17:30');
    set(8, 11, '23:17:31'); set(12, 13, '23:17:32'); set(14, 19, '23:19:18');
    set(20, 23, '23:19:25'); set(24, 25, '23:19:26'); set(26, 32, '23:21:21');
    set(33, 34, '23:21:22'); set(35, 38, '23:22:03'); set(39, 42, '23:22:10');
    set(43, 44, '23:22:20'); set(45, 46, '23:22:21'); set(47, 50, '23:22:30');
    set(51, 51, '23:22:38'); set(52, 54, '23:22:39'); set(55, 56, '23:24:18');
    set(57, 58, '23:24:19'); set(59, 64, '23:27:24'); set(65, 65, '23:27:25');
    set(66, 69, '23:28:23');
    return c;
  })(),
};

// One entry per task. rec* = real record numbers; wall = real wall seconds;
// seal = real checker seal prefix from the verbose tree output.
const TASKS = [
  { n: 1, name: 'semver-bump-prerelease', short: 'semver-bump', recCreated: 2, recStarted: 3,
    r0: { harness: 'Muse Code', recVerdict: 37, verdict: 'PASS', wall: 270 }, seal: '0e1a7fc136b1' },
  { n: 2, name: 'packaging-licenseref-case', short: 'packaging-case', recCreated: 4, recStarted: 5,
    r0: { harness: 'Muse Code', recVerdict: 16, verdict: 'PASS', wall: 105 }, seal: '2ea62656a0ad' },
  { n: 3, name: 'dateutil-tzstr-doy-rules', short: 'dateutil-tzstr', recCreated: 6, recStarted: 7,
    r0: { harness: 'Muse Code', recVerdict: 49, verdict: 'PASS', wall: 298 }, seal: '96f032df231d' },
  { n: 4, name: 'moreiter-peekable-slice', short: 'moreiter-peekable', recCreated: 8, recStarted: 9,
    r0: { harness: 'Muse Code', recVerdict: 22, verdict: 'PASS', wall: 113 }, seal: '407e7c6f85bb' },
  { n: 5, name: 'cachetools-cachedmethod-pickle', short: 'cachetools-pickle', recCreated: 10, recStarted: 11,
    r0: { harness: 'Muse Code', recVerdict: 53, verdict: 'PASS', wall: 307 }, seal: '27cc42a9ac5e' },
  { n: 6, name: 'cachetools-unbound-keyword', short: 'cachetools-keyword', recCreated: 12, recStarted: 13,
    r0: { harness: 'Muse Code', recVerdict: 27, verdict: 'FAIL', wall: 229 },
    r1: { harness: 'Claude Code', recStarted: 32, recVerdict: 41, verdict: 'PASS', wall: 49 },
    escalated: 29, seal: '58c837bd2930' },
  { n: 7, name: 'cachetools-stacked-decorators', short: 'stacked-decorators', recCreated: 18, recStarted: 19,
    r0: { harness: 'Muse Code', recVerdict: 45, verdict: 'PASS', wall: 182 }, seal: 'edf04205e06c' },
  { n: 8, name: 'click-short-help-abbrev', short: 'click-help-abbrev', recCreated: 24, recStarted: 25,
    r0: { harness: 'Muse Code', recVerdict: 60, verdict: 'FAIL', wall: 478 },
    r1: { harness: 'Claude Code', recStarted: 65, recVerdict: 68, verdict: 'PASS', wall: 57 },
    escalated: 62, seal: '893a62f023d2' },
  { n: 9, name: 'click-pager-params', short: 'click-pager-params', recCreated: 33, recStarted: 34,
    r0: { harness: 'Muse Code', recVerdict: 57, verdict: 'PASS', wall: 176 }, seal: '3f86c79c9ef8' },
];

// Plain-words narration keyed to real record numbers.
const NARR = [
  { rec: 1,  text: 'The run begins. Nine bug-fix jobs wait in the queue.' },
  { rec: 3,  text: 'A Muse Code worker picks up job 1, semver-bump, and starts work.' },
  { rec: 7,  text: 'More workers start jobs 2 and 3. Each works in its own folder.' },
  { rec: 11, text: 'Jobs 4 and 5 are running now. Nobody can see the checker.' },
  { rec: 13, text: 'Job 6, cachetools-keyword, starts on a Muse Code worker.' },
  { rec: 16, text: 'Job 2 is done. The worker tried a fix. The checker said PASS.' },
  { rec: 19, text: 'Job 7 starts while the checker seals job 2 into the record.' },
  { rec: 22, text: 'Job 4 is done. The worker tried a fix. The checker said PASS.' },
  { rec: 25, text: 'Job 8, click-help-abbrev, starts on a Muse Code worker.' },
  { rec: 27, text: 'Job 6 said done, but the checker said FAIL. The answer is refused.' },
  { rec: 29, text: 'Job 6 climbs the ladder: a Claude Code worker takes it over.' },
  { rec: 34, text: 'Job 9, the last one, starts on a Muse Code worker.' },
  { rec: 37, text: 'Job 1 is done. The worker tried a fix. The checker said PASS.' },
  { rec: 41, text: 'Job 6 is fixed by the second worker. The checker said PASS.' },
  { rec: 45, text: 'Job 7 is done. The worker tried a fix. The checker said PASS.' },
  { rec: 49, text: 'Job 3 is done after 298 seconds. The checker said PASS.' },
  { rec: 53, text: 'Job 5 is done. The worker tried a fix. The checker said PASS.' },
  { rec: 57, text: 'Job 9 is done. The worker tried a fix. The checker said PASS.' },
  { rec: 60, text: 'Job 8 said done, but the checker said FAIL. The answer is refused.' },
  { rec: 62, text: 'Job 8 climbs the ladder: a Claude Code worker takes it over.' },
  { rec: 68, text: 'Job 8 is fixed by the second worker. The checker said PASS.' },
  { rec: 69, text: 'All 9 jobs verified. 2 wrong answers were caught, then fixed.' },
];

// Dashboard facts, each from the integrate fresh-clone RUN-LOG.
const DASH = {
  harnesses: ['Muse Code', 'Claude Code', 'Codex'],
  verified: '9 / 9',
  caughtFixed: 2,
  recallHits: 1,
  recallSim: '0.73',
  voiceLatency: 'about 1 s a clip',
  install: 'curl -fsSL https://raw.githubusercontent.com/Anshul48/anima-substrate/main/install.sh | sh',
  stream: [
    { t: '21:20Z', text: 'Install finished. ANIMA found Muse Code, Claude Code and Codex.', tag: 'install' },
    { t: '21:20Z', text: 'Doctor check: all three harnesses READY, none live-tested yet.', tag: 'setup' },
    { t: '21:22Z', text: 'Memory set up: model downloaded and verified, store ready.', tag: 'setup' },
    { t: '21:26Z', text: 'Run 1, tiny-bug: memory empty, worker ran anyway. Checker said PASS in 159 s.', tag: 'run' },
    { t: '21:28Z', text: 'Run 1 recorded: 1 fix searchable in memory.', tag: 'memory' },
    { t: '21:29Z', text: 'Run 2, tiny-bug: 1 similar past fix recalled into the prompt. PASS in 135 s.', tag: 'run' },
    { t: '21:31Z', text: 'Direct recall: 1 hit, similarity 0.73, source check OK.', tag: 'memory' },
    { t: '–', text: 'Voice heard “Show status” in 1.9 s. Printed the tree, changed nothing.', tag: 'voice' },
    { t: '–', text: 'Voice heard “Pause task 3”. Asked first, then wrote one command file.', tag: 'voice' },
    { t: '21:55Z', text: 'State tree seen in the browser. Chain OK, 7 records, fingerprint matches.', tag: 'tree' },
    { t: '23:28Z', text: 'flagship-run3 replay: 9 jobs verified, 2 caught and fixed, chain OK, 69 records.', tag: 'run' },
  ],
};
