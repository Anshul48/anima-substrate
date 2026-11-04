#!/usr/bin/env node
/* Run the demo page's check outside the browser, with the same code (chain.js).
 * It prints the same words as check_chain.py, so the two can be compared line by line:
 *
 *   node docs/demo/check-in-node.js --tamper
 *   python3 docs/evidence/flagship-run3/check_chain.py --tamper
 *
 *   --embedded   use the copy inside data.js (what the page uses) instead of the file on disk
 *   --plain      use the plain-JavaScript SHA-256 instead of the built-in one
 *   path         check another file instead of decisions.jsonl
 */
"use strict";
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
// Older node versions do not expose WebCrypto as a global; browsers always do.
if (!globalThis.crypto) globalThis.crypto = crypto.webcrypto;
const chain = require("./chain.js");

const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const positional = args.filter((a) => !a.startsWith("--"));
const runDir = path.join(__dirname, "..", "evidence", "flagship-run3");

function load() {
  if (flag("--embedded")) {
    global.window = global;
    require("./data.js");
    return { bytes: new Uint8Array(Buffer.from(global.ANIMA_DATA.decisions, "latin1")), head: JSON.parse(global.ANIMA_DATA.head) };
  }
  const file = positional[0] || path.join(runDir, "decisions.jsonl");
  const headFile = path.join(path.dirname(file), "decisions.jsonl.head.json");
  return {
    bytes: new Uint8Array(fs.readFileSync(file)),
    head: fs.existsSync(headFile) ? JSON.parse(fs.readFileSync(headFile, "utf8")) : null,
  };
}

async function report(label, bytes, sha) {
  const r = await chain.checkChain(bytes, sha);
  console.log(`${label}: ${r.ok ? "CHAIN OK" : "CHAIN BROKEN"} - ${r.count} records, ${r.why}`);
  console.log(`  file fingerprint (SHA-256): ${r.fingerprint}`);
  return r;
}

(async () => {
  const { bytes, head } = load();
  const sha = chain.pickSha256(flag("--plain"));
  if (flag("--plain") === (sha.name === "WebCrypto")) throw new Error("wrong SHA-256 chosen: " + sha.name);
  const original = await report("recorded run", bytes, sha);
  if (head) console.log("  matches the fingerprint saved at the end of the run:", original.fingerprint === head.sha256 ? "yes" : "NO");
  // belt and braces: the fingerprint must equal node's own SHA-256 of the same bytes
  const nodeDigest = crypto.createHash("sha256").update(bytes).digest("hex");
  if (nodeDigest !== original.fingerprint) throw new Error("fingerprint differs from node crypto: " + nodeDigest);
  if (!flag("--tamper")) process.exit(original.ok ? 0 : 1);
  const before = Buffer.from(bytes).toString("latin1");
  const copy = chain.tamperedCopy(bytes);
  console.log(`\nchanged one character on line ${copy.line} of a temporary copy (the original is untouched)`);
  const edited = await report("edited copy", copy.bytes, sha);
  if (Buffer.from(bytes).toString("latin1") !== before) throw new Error("the original was modified");
  process.exit(original.ok && !edited.ok ? 0 : 1);
})().catch((err) => { console.error(err); process.exit(2); });
