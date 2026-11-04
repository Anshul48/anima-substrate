# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""Text encoders for ANIMA memory.

Two encoders, always named in every record and every report:

  minilm-onnx   sentence-transformers/all-MiniLM-L6-v2 at the revision TRACE's own
                embedding cache names (1110a243...), run on CPU through onnxruntime,
                mean pooling, max_seq_length 256, then L2 normalize (the model's own last layer;
                matches TRACE's cached vectors to ~1e-7). 384 dimensions.
  hash-384      OFFLINE FALLBACK, NOT a language model: signed hashed word and
                bigram counts in 384 dimensions. Only for machines that cannot
                download the model; recall quality is plainly lower. Labelled as such.
"""
from __future__ import annotations

import hashlib
import os
import re
import urllib.request
from pathlib import Path

DIM = 384
MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"  # the revision in TRACE's emb_cache meta.json
MAX_SEQ = 256
# (path inside the model repo, sha256 of the file at MODEL_REVISION)
MODEL_FILES = {
    "onnx/model.onnx": "6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
}


def anima_home() -> Path:
    return Path(os.environ.get("ANIMA_HOME", str(Path.home() / ".anima")))


def model_dir() -> Path:
    return anima_home() / "models" / "all-MiniLM-L6-v2" / MODEL_REVISION[:8]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def model_ready() -> bool:
    d = model_dir()
    return all((d / rel).is_file() for rel in MODEL_FILES)


def download_model(verbose: bool = True) -> Path:
    """Fetch the two model files (about 90 MB) from huggingface.co. No key needed."""
    d = model_dir()
    for rel, want in MODEL_FILES.items():
        dest = d / rel
        if dest.is_file() and (not want or _sha256(dest) == want):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{rel}"
        if verbose:
            print(f"downloading {url}", flush=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                block = r.read(1 << 20)
                if not block:
                    break
                f.write(block)
        got = _sha256(tmp)
        if want and got != want:
            tmp.unlink()
            raise RuntimeError(f"model file {rel}: sha256 {got} != pinned {want}")
        os.replace(tmp, dest)
    return d


class MiniLMOnnx:
    name = "minilm-onnx"
    describe = ("sentence-transformers/all-MiniLM-L6-v2 @ " + MODEL_REVISION[:8] +
                " (ONNX fp32, CPU, mean pooling, max_seq 256, unit length; the encoder named in TRACE's cache)")

    def __init__(self):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        d = model_dir()
        if not model_ready():
            raise FileNotFoundError(f"model files missing under {d}; run: anima memory setup")
        self._np = np
        so = ort.SessionOptions()
        so.intra_op_num_threads = max(1, min(8, (os.cpu_count() or 2)))
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(str(d / "onnx" / "model.onnx"), so,
                                         providers=["CPUExecutionProvider"])
        self.tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        self.tok.enable_truncation(max_length=MAX_SEQ)
        self.tok.enable_padding(pad_id=0, pad_token="[PAD]")
        self.input_names = {i.name for i in self.sess.get_inputs()}

    def embed(self, texts, batch: int = 16):
        np = self._np
        out = []
        texts = list(texts)
        for i in range(0, len(texts), batch):
            enc = self.tok.encode_batch(texts[i:i + batch])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.input_names:
                feed["token_type_ids"] = np.zeros_like(ids)
            hidden = self.sess.run(None, feed)[0]  # (b, t, 384)
            m = mask[..., None].astype(np.float32)
            pooled = (hidden * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
            # The sentence-transformers pipeline for this model ends in a Normalize layer, so
            # TRACE's cached vectors are unit length (checked: max abs diff ~1e-7 after this).
            pooled = pooled / np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
            out.extend(pooled.astype(np.float32))
        return out


_WORD = re.compile(r"[a-z0-9_]+")


class HashEncoder:
    name = "hash-384"
    describe = ("OFFLINE FALLBACK hash-384: signed hashed word and bigram counts, 384 dims. "
                "Not a language model; recall quality is plainly lower than minilm-onnx.")

    def __init__(self):
        import numpy as np
        self._np = np

    def embed(self, texts):
        np = self._np
        out = []
        for t in texts:
            v = np.zeros(DIM, dtype=np.float32)
            words = _WORD.findall(t.lower())
            grams = words + [a + "_" + b for a, b in zip(words, words[1:])]
            for g in grams:
                h = hashlib.blake2b(g.encode(), digest_size=8).digest()
                idx = int.from_bytes(h[:4], "little") % DIM
                sign = 1.0 if h[4] & 1 else -1.0
                v[idx] += sign
            out.append(v)
        return out


def get_encoder(kind: str = "auto"):
    """kind: auto | minilm | hash. auto = minilm if its files and packages are present, else hash (said out loud)."""
    if kind in ("auto", "minilm"):
        try:
            return MiniLMOnnx()
        except Exception as exc:  # missing files or packages
            if kind == "minilm":
                raise
            import sys
            print(f"anima memory: minilm-onnx unavailable ({type(exc).__name__}: {exc}); "
                  "falling back to hash-384 (not a language model)", file=sys.stderr)
    return HashEncoder()
