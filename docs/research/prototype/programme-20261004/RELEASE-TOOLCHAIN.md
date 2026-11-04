# Release-workstream toolchain (project-local .venv)

Bootstrap (from repo root; network authorized for deps):

```
python3 -m venv --without-pip .venv
./.venv/bin/python /tmp/get-pip.py   # from https://bootstrap.pypa.io/get-pip.py
export PIP_CACHE_DIR=/tmp/pipcache PIP_NO_INPUT=1
./.venv/bin/python -m pip install build pytest ruff
```

Pinned 2026-10-07: build 1.6.1, pytest 9.1.1, ruff 0.16.10, pip 26.2.1,
CPython 3.12.3 (Ubuntu). Tooling venv ONLY (dev/test/packaging) — the
shipped package keeps zero runtime dependencies (stdlib-only base).

Conventions: use ./.venv/bin/python explicitly (or activate); .venv is
gitignored and never published. Never --break-system-packages.
