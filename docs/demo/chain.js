/* The check, in JavaScript. It follows the same rule as
 * docs/evidence/flagship-run3/check_chain.py, step for step:
 *
 *   - the file is a list of records, one per line (lines are split on the
 *     newline byte; empty lines are skipped, and numbering counts the rest)
 *   - the first record must say "prev": "GENESIS"
 *   - every later record must carry, as "prev", the SHA-256 (as 64 lowercase
 *     hex characters) of the exact bytes of the line before it, without the
 *     newline
 *   - a line that is not valid JSON stops the check
 *
 * It works in a browser (WebCrypto) and in node (node docs/demo/check-in-node.js).
 * It only reads the record. It does not re-run any job. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.AnimaChain = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var NEWLINE = 10;

  // Like Python's bytes.split(b"\n"): keeps empty pieces, and a trailing newline gives a last empty piece.
  function splitLines(bytes) {
    var lines = [];
    var start = 0;
    for (var i = 0; i < bytes.length; i++) {
      if (bytes[i] === NEWLINE) {
        lines.push(bytes.subarray(start, i));
        start = i + 1;
      }
    }
    lines.push(bytes.subarray(start));
    return lines;
  }

  function toHex(bytes) {
    var out = "";
    for (var i = 0; i < bytes.length; i++) out += (bytes[i] < 16 ? "0" : "") + bytes[i].toString(16);
    return out;
  }

  // --- SHA-256 ---------------------------------------------------------------
  // The browser's own implementation (WebCrypto) is used whenever it exists.
  // The plain-JavaScript version below is only a fallback for pages opened in a
  // setting where WebCrypto is switched off (for example plain http on a network
  // address). The test script runs both against the same data.

  function webCryptoSha256(bytes) {
    return globalThis.crypto.subtle.digest("SHA-256", bytes).then(function (buf) {
      return toHex(new Uint8Array(buf));
    });
  }

  var K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);

  function plainSha256(bytes) {
    var h = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ]);
    var length = bytes.length;
    var paddedLength = (((length + 9 + 63) >> 6) << 6);
    var data = new Uint8Array(paddedLength);
    data.set(bytes);
    data[length] = 0x80;
    var view = new DataView(data.buffer);
    view.setUint32(paddedLength - 8, Math.floor(length / 0x20000000), false);
    view.setUint32(paddedLength - 4, (length << 3) >>> 0, false);
    var w = new Uint32Array(64);
    var rotr = function (x, n) { return (x >>> n) | (x << (32 - n)); };
    for (var offset = 0; offset < paddedLength; offset += 64) {
      for (var t = 0; t < 16; t++) w[t] = view.getUint32(offset + t * 4, false);
      for (t = 16; t < 64; t++) {
        var s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3);
        var s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10);
        w[t] = (w[t - 16] + s0 + w[t - 7] + s1) >>> 0;
      }
      var a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
      for (t = 0; t < 64; t++) {
        var S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        var ch = (e & f) ^ (~e & g);
        var t1 = (hh + S1 + ch + K[t] + w[t]) >>> 0;
        var S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        var maj = (a & b) ^ (a & c) ^ (b & c);
        var t2 = (S0 + maj) >>> 0;
        hh = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }
    var out = new Uint8Array(32);
    var outView = new DataView(out.buffer);
    for (var i = 0; i < 8; i++) outView.setUint32(i * 4, h[i], false);
    return Promise.resolve(toHex(out));
  }

  function hasWebCrypto() {
    return typeof globalThis !== "undefined" && !!globalThis.crypto && !!globalThis.crypto.subtle &&
      typeof globalThis.crypto.subtle.digest === "function";
  }

  // Returns { name, hash(bytes) -> Promise<hex> }
  function pickSha256(forcePlain) {
    if (!forcePlain && hasWebCrypto()) return { name: "WebCrypto", hash: webCryptoSha256 };
    return { name: "plain JavaScript", hash: plainSha256 };
  }

  // --- the check -------------------------------------------------------------

  // Returns { ok, why, count, fingerprint, brokenAt, expected, found }.
  //   why        same words as check_chain.py ("every link matches", "line 7 does not match the line before it", ...)
  //   brokenAt   number of the first record that does not match (1-based), or 0
  //   expected   what the record before it fingerprints to now (hex), or "GENESIS" for the first record
  //   found      what the record itself says its predecessor was
  // opts.onRecord(n) is called after record n passes (may return a promise; used to animate).
  async function checkChain(bytes, sha256, opts) {
    var onRecord = opts && opts.onRecord;
    var lines = splitLines(bytes).filter(function (line) { return line.length > 0; });
    var decoder = new TextDecoder("utf-8", { fatal: true });
    var result = { ok: true, why: "every link matches", count: lines.length, brokenAt: 0, expected: "", found: "" };
    var previous = "GENESIS";
    for (var n = 1; n <= lines.length; n++) {
      var line = lines[n - 1];
      var event;
      try {
        event = JSON.parse(decoder.decode(line));
      } catch (err) {
        result.ok = false;
        result.why = "line " + n + " is not valid JSON";
        result.brokenAt = n;
        break;
      }
      var stated = event !== null && typeof event === "object" ? event.prev : undefined;
      if (stated !== previous) {
        result.ok = false;
        result.why = "line " + n + " does not match the line before it";
        result.brokenAt = n;
        result.expected = previous;
        result.found = stated === undefined ? "" : String(stated);
        break;
      }
      previous = await sha256.hash(line);
      if (onRecord) await onRecord(n);
    }
    result.fingerprint = await sha256.hash(bytes);
    return result;
  }

  // check_chain.py --tamper: in a COPY, change the first character after "kind":" on the 6th line to "X".
  // The input is never modified. Returns { bytes, line, offset, before, after }.
  function tamperedCopy(bytes) {
    var copy = new Uint8Array(bytes); // a new array: the original stays as it is
    var pieces = splitLines(copy);
    var victim = pieces[5];
    var needle = new TextEncoder().encode('"kind":"');
    var at = -1;
    for (var i = 0; i + needle.length <= victim.length && at < 0; i++) {
      var same = true;
      for (var j = 0; j < needle.length; j++) if (victim[i + j] !== needle[j]) { same = false; break; }
      if (same) at = i;
    }
    if (at < 0) throw new Error("could not find the place to change");
    var offset = at + needle.length;
    var before = String.fromCharCode(victim[offset]);
    victim[offset] = "X".charCodeAt(0); // victim is a view into copy
    return { bytes: copy, line: 6, offset: offset, before: before, after: "X" };
  }

  return {
    splitLines: splitLines,
    pickSha256: pickSha256,
    checkChain: checkChain,
    tamperedCopy: tamperedCopy,
    toHex: toHex,
  };
});
