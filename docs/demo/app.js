/* ANIMA demo page. Everything shown here is computed in the browser from the
 * copy of the recorded run in data.js. Nothing is sent anywhere. */
(function () {
  "use strict";

  var D = window.ANIMA_DATA;
  var C = window.AnimaChain;
  var $ = function (id) { return document.getElementById(id); };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  if (!D || !C) {
    $("provenance").textContent = "The record data did not load, so the check cannot run here. The same check runs in a terminal; see the repository.";
    return;
  }

  // ---- the data (the original bytes are never modified) -----------------------
  var original = new TextEncoder().encode(D.decisions); // the file is plain ASCII, so these are the file's bytes
  var head = JSON.parse(D.head);                         // fingerprint saved at the end of the run
  var sha = C.pickSha256(false);
  var recordCount = C.splitLines(original).filter(function (l) { return l.length > 0; }).length;
  var reduceMotion = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var busy = false;

  // ---- 1. the nine jobs, read from the real log -------------------------------
  function parseLog(text) {
    var rows = [];
    var summary = null;
    text.split("\n").forEach(function (line) {
      if (!line) return;
      var m = /^REAL (\S+) rung=(\d+) pool=(\S+) said-done=(\S+) gate=(\S+) rule=(\S+)$/.exec(line);
      if (m) rows.push({ job: m[1], rung: +m[2], pool: m[3], said: m[4], gate: m[5], rule: m[6] });
      else if (line.indexOf("REAL {") === 0) summary = JSON.parse(line.slice(5));
    });
    return { rows: rows, summary: summary };
  }

  // what the hidden checker printed for a caught job, from the recorded "task.blocked" decision
  function checkerLines() {
    var found = {};
    D.decisions.split("\n").forEach(function (line) {
      if (!line) return;
      var ev = JSON.parse(line);
      if (ev.kind !== "task.blocked" || !ev.data || typeof ev.data.reason !== "string") return;
      var parts = ev.data.reason.split("; "); // rule; pool=...; hand=...; <what the checker printed>
      found[ev.task] = parts.slice(3).join("; ").replace(/^E\s+/, "");
    });
    return found;
  }

  var RULE_WORDS = { "target-tests": "the tests written for this bug failed" };

  function renderJobs() {
    var log = parseLog(D.log);
    var saw = checkerLines();
    var order = [];
    var jobs = {};
    log.rows.forEach(function (r) {
      if (!jobs[r.job]) { jobs[r.job] = {}; order.push(r.job); }
      jobs[r.job][r.rung === 0 ? "first" : "second"] = r;
    });

    var list = $("job-list");
    order.forEach(function (name) {
      var j = jobs[name];
      var caught = j.first.gate !== "PASS";
      var li = el("li", "job " + (caught ? "caught" : "clean"));

      var c1 = el("div", "cell job-name");
      c1.appendChild(el("span", "cap", "Job"));
      c1.appendChild(document.createTextNode(name));
      li.appendChild(c1);

      var c2 = el("div", "cell");
      c2.appendChild(el("span", "cap", "Small local model said"));
      var v2 = el("div", "val", j.first.said === "yes" ? "done" : "not done");
      c2.appendChild(v2);
      li.appendChild(c2);

      var c3 = el("div", "cell");
      c3.appendChild(el("span", "cap", "Hidden checker said"));
      var v3 = el("div", "val");
      v3.appendChild(el("span", "verdict-word " + (j.first.gate === "PASS" ? "pass" : "fail"), j.first.gate));
      if (caught) v3.appendChild(el("span", "why", RULE_WORDS[j.first.rule] || ("rule: " + j.first.rule)));
      c3.appendChild(v3);
      li.appendChild(c3);

      var c4 = el("div", "cell");
      c4.appendChild(el("span", "cap", "Next helper (Claude Sonnet)"));
      var v4 = el("div", "val");
      if (j.second) {
        v4.appendChild(document.createTextNode(j.second.said === "yes" ? "Said done. " : "Did not say done. "));
        v4.appendChild(document.createTextNode("Checker said "));
        v4.appendChild(el("span", "verdict-word " + (j.second.gate === "PASS" ? "pass" : "fail"), j.second.gate));
      } else {
        v4.appendChild(el("span", "muted", "not needed"));
      }
      c4.appendChild(v4);
      li.appendChild(c4);

      if (caught && saw[name]) {
        var d = el("p", "job-detail");
        d.appendChild(document.createTextNode("What the checker saw:"));
        d.appendChild(el("code", "", saw[name]));
        d.appendChild(document.createTextNode("The next helper was handed the job plus this one line."));
        li.appendChild(d);
      }
      list.appendChild(li);
    });

    // summary tiles: numbers come from the log's own summary line
    var s = log.summary;
    if (s) {
      var tiles = $("tiles");
      var add = function (cls, big, what) {
        var t = el("div", "tile " + cls);
        t.appendChild(el("span", "big", String(big)));
        t.appendChild(el("span", "what", what));
        tiles.appendChild(t);
      };
      add("t-teal", s.N, "real bug-fixing jobs");
      add("t-green", s.rung0_verified, "right the first time: the small local model said done and the hidden tests agreed");
      add("t-orange", s.rung0_said_done - s.rung0_verified, "said done but were wrong: the checker caught both and the next helper fixed them");
      if (s.ladder_verified === s.N && s.exhausted === 0) {
        $("tiles-note").textContent = "All " + s.N + " ended verified by the checker.";
      }
    }
  }

  // ---- 2. check the record ----------------------------------------------------
  var strip = $("strip");
  var cells = [];
  function buildStrip() {
    var kinds = D.decisions.split("\n").filter(Boolean).map(function (l) { return JSON.parse(l).kind; });
    for (var i = 1; i <= recordCount; i++) {
      var li = el("li");
      li.dataset.state = "idle";
      li.dataset.n = String(i);
      li.title = "Record " + i + ": " + kinds[i - 1];
      strip.appendChild(li);
      cells.push(li);
    }
  }
  function resetStrip(label) {
    cells.forEach(function (c) { c.dataset.state = "idle"; });
    strip.setAttribute("aria-label", label || ("One square per record, " + recordCount + " in all. Not checked yet."));
  }
  function pause(ms) {
    return reduceMotion ? Promise.resolve() : new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function plainWhy(why) {
    return why.replace(/\bline (\d+)/, "record $1").replace("the line before it", "the one before it");
  }

  function resultCard(which, r, extraFacts) {
    var card = el("div", "result " + (r.ok ? "ok" : "broken"));
    card.appendChild(el("p", "which", which));
    card.appendChild(el("p", "verdict", (r.ok ? "CHAIN OK" : "CHAIN BROKEN") + " - " + r.count + " records, " + plainWhy(r.why)));
    var facts = el("dl", "facts");
    var row = function (term, valueNode) {
      facts.appendChild(el("dt", "", term));
      var dd = el("dd");
      dd.appendChild(valueNode);
      facts.appendChild(dd);
    };
    row("Digital fingerprint of the whole file (SHA-256)", el("span", "hash", r.fingerprint));
    var same = r.fingerprint === head.sha256;
    row("Matches the fingerprint saved at the end of the run", el("span", same ? "yes" : "no", same ? "yes" : "NO"));
    (extraFacts || []).forEach(function (f) { row(f[0], f[1]); });
    card.appendChild(facts);
    return card;
  }

  function computedBy() {
    return el("span", "", sha.name === "WebCrypto"
      ? "your browser's built-in SHA-256 (WebCrypto)"
      : "plain JavaScript (WebCrypto is switched off in this setting)");
  }

  function setBusy(on) {
    busy = on;
    $("btn-check").disabled = on;
    $("btn-tamper").disabled = on;
    if (on) $("btn-reset").disabled = true;
  }

  async function animate(bytes, editedRecord) {
    resetStrip("Checking the records one by one.");
    if (editedRecord) cells[editedRecord - 1].dataset.state = "edited";
    var delay = editedRecord ? 90 : 9;
    var result = await C.checkChain(bytes, sha, {
      onRecord: function (n) {
        if (n !== editedRecord) cells[n - 1].dataset.state = "ok";
        return pause(delay);
      },
    });
    if (result.brokenAt) {
      cells[result.brokenAt - 1].dataset.state = "bad";
      for (var i = result.brokenAt; i < cells.length; i++) cells[i].dataset.state = "idle";
      await pause(delay);
    }
    return result;
  }

  async function doCheck() {
    if (busy) return;
    setBusy(true);
    var results = $("results");
    results.textContent = "";
    $("tamper").hidden = true;
    $("status").textContent = "";
    var r = await animate(original, 0);
    results.appendChild(resultCard("Recorded run", r, [["Computed by", computedBy()]]));
    strip.setAttribute("aria-label", r.ok ? "All " + r.count + " records match the one before them." : "A record does not match the one before it.");
    $("status").textContent = r.ok ? "Every record carries the right fingerprint of the one before it." : "The check found a break.";
    setBusy(false);
    $("btn-reset").disabled = false;
  }

  function excerpt(bytes, lineNumber, offset) {
    var text = new TextDecoder().decode(C.splitLines(bytes)[lineNumber - 1]);
    var from = Math.max(0, offset - 30);
    var to = Math.min(text.length, offset + 27);
    return {
      before: (from > 0 ? "…" : "") + text.slice(from, offset),
      char: text.charAt(offset),
      after: text.slice(offset + 1, to) + (to < text.length ? "…" : ""),
    };
  }

  async function doTamper() {
    if (busy) return;
    setBusy(true);
    var results = $("results");
    var box = $("tamper");
    results.textContent = "";
    box.hidden = true;
    box.textContent = "";
    $("status").textContent = "";

    var copy = C.tamperedCopy(original); // a new array; `original` is not touched
    resetStrip();
    var edited = await animate(copy.bytes, copy.line);
    // re-check the original AFTER the edit, to show it was not touched
    var untouched = await C.checkChain(original, sha);
    results.appendChild(resultCard("Recorded run (checked again after the edit)", untouched));
    results.appendChild(resultCard("Edited copy (temporary, in memory)", edited));

    // show what changed and why the next record notices
    var before = excerpt(original, copy.line, copy.offset);
    var after = excerpt(copy.bytes, copy.line, copy.offset);
    var n = copy.line;
    box.appendChild(el("h3", "", "What changed"));
    box.appendChild(el("p", "", "One character in record " + n + " of the temporary copy was changed. Here is that spot, before and after:"));
    var diff = el("div", "diff");
    [["Before", before, ""], ["After", after, "edit"]].forEach(function (row) {
      var line = el("div");
      line.appendChild(el("span", "tag", row[0]));
      var text = el("span", "text");
      text.appendChild(document.createTextNode(row[1].before));
      text.appendChild(el("mark", row[2], row[1].char));
      text.appendChild(document.createTextNode(row[1].after));
      line.appendChild(text);
      diff.appendChild(line);
    });
    box.appendChild(diff);
    if (edited.brokenAt) {
      var cmp = el("dl", "compare");
      cmp.appendChild(el("dt", "", "Record " + edited.brokenAt + " says the record before it has this fingerprint:"));
      var dd1 = el("dd"); dd1.appendChild(el("span", "hash", edited.found)); cmp.appendChild(dd1);
      cmp.appendChild(el("dt", "", "Record " + (edited.brokenAt - 1) + ", as it is now, has this fingerprint:"));
      var dd2 = el("dd"); dd2.appendChild(el("span", "hash", edited.expected)); cmp.appendChild(dd2);
      box.appendChild(cmp);
      box.appendChild(el("p", "", "They differ, so the check stops here: record " + edited.brokenAt + " does not match the one before it. The original record was not changed and still checks OK."));
    }
    box.hidden = false;

    strip.setAttribute("aria-label", edited.brokenAt
      ? "Records 1 to " + (n - 1) + " match. Record " + n + " was edited. Record " + edited.brokenAt + " does not match the one before it."
      : "No break found.");
    $("status").textContent = edited.brokenAt ? "The edit was noticed." : "The edit was not noticed.";
    setBusy(false);
    $("btn-reset").disabled = false;
  }

  function doReset() {
    if (busy) return;
    $("results").textContent = "";
    var idle = el("p", "idle", "Not checked yet. Press “Check the record”.");
    $("results").appendChild(idle);
    var box = $("tamper");
    box.hidden = true;
    box.textContent = "";
    resetStrip();
    $("status").textContent = "Reset. The temporary edited copy is gone. The original record was never changed.";
    $("btn-reset").disabled = true;
  }

  // ---- start ------------------------------------------------------------------
  renderJobs();
  buildStrip();
  $("btn-check").addEventListener("click", doCheck);
  $("btn-tamper").addEventListener("click", doTamper);
  $("btn-reset").addEventListener("click", doReset);

  // is the copy inside this page the same file that was saved at the end of the run?
  sha.hash(original).then(function (hex) {
    var same = hex === head.sha256;
    var p = $("provenance");
    p.textContent = "";
    p.appendChild(document.createTextNode("This page holds a copy of the run’s record files (decisions.jsonl and real3.log). The copy’s fingerprint matches the one saved at the end of the run: "));
    p.appendChild(el("strong", same ? "yes" : "no", same ? "yes" : "NO"));
    p.appendChild(document.createTextNode("."));
  }).catch(function () {
    $("provenance").textContent = "This page holds a copy of the run’s record files. Press “Check the record” to check it.";
  });
})();
