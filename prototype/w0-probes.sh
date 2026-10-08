#!/bin/sh
# W0 pin/capability probes — SUBSTRATE track, launch anima-20261003.
# READ-ONLY: inspects workspace + /tmp scratch; writes only under /tmp.
# Never modifies stc/, sst/, ANIMA/, programme state, or any source tree.
# Expected outputs recorded in tracks/substrate/W0-HOST-STUDY.md (2026-10-03).
# Usage: sh substrate/prototype/w0-probes.sh  (from workspace root)
set -u
export PYTHONDONTWRITEBYTECODE=1  # keep import probes from writing __pycache__ into stc//sst/ (V2 note)
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "PASS: $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL: $1"; }

ROOT="$(pwd)"
[ -f "$ROOT/stc/dsh-plugin-stc/DSH_PIN" ] || { echo "run from workspace root"; exit 2; }

echo "=== P1/P15 git HEADs ==="
STC_HEAD="$(git -C stc rev-parse HEAD 2>&1)" && ok "stc HEAD $STC_HEAD" || bad "stc rev-parse: $STC_HEAD"
SST_HEAD="$(git -C sst rev-parse HEAD 2>&1)" && ok "sst HEAD $SST_HEAD" || bad "sst rev-parse: $SST_HEAD"
git -C stc status --short 2>&1 | head -5

echo "=== P2 DSH_PIN ==="
cat stc/dsh-plugin-stc/DSH_PIN

echo "=== P3/P4 DSH upstream + vendored cordis ==="
if [ -d /tmp/dsh-upstream ]; then
  echo "dsh HEAD: $(git -C /tmp/dsh-upstream rev-parse HEAD 2>&1)"
  echo "dsh status: [$(git -C /tmp/dsh-upstream status --short 2>&1 | head -5)] (empty=clean)"
  node -p "require('/tmp/dsh-upstream/package.json').version" 2>&1
  node -p "require('/tmp/dsh-upstream/vendor/cordis/package.json').version" 2>&1
else bad "/tmp/dsh-upstream absent"; fi

echo "=== P6/P7/P10 plugin manifest + entry + build ==="
node -p "require('$ROOT/stc/dsh-plugin-stc/package.json').version" 2>&1
wc -l stc/dsh-plugin-stc/src/index.ts
ls -la stc/dsh-plugin-stc/lib/index.js 2>&1

echo "=== P8 module resolution ==="
readlink -f stc/dsh-plugin-stc/node_modules/@deepseek-ai/dsh-tools 2>&1
(cd stc/dsh-plugin-stc && node --input-type=module -e "
try{console.log('dsh-tools -> '+(await import.meta.resolve('@deepseek-ai/dsh-tools')))}catch(e){console.log('FAIL dsh-tools: '+e.message)}
try{console.log('cordis -> '+(await import.meta.resolve('@deepseek-ai/cordis')))}catch(e){console.log('FAIL cordis (expected): '+e.message)}
try{console.log('esbuild -> '+(await import.meta.resolve('esbuild')))}catch(e){console.log('FAIL esbuild: '+e.message)}" 2>&1)
(cd stc/dsh-plugin-stc && ./node_modules/.bin/esbuild --version 2>&1)

echo "=== P9 plugin tests under node22 ==="
if [ -x /tmp/toolchain/node22/bin/node ]; then
  (cd stc/dsh-plugin-stc && /tmp/toolchain/node22/bin/node --test tests/dossier-read.test.ts tests/stc-exec.test.ts tests/stc-run.test.ts tests/policy.test.ts tests/packaging.test.ts tests/stc-present.test.ts tests/client-smoke.test.ts 2>&1 | tail -8)
else bad "node22 toolchain absent"; fi

echo "=== P11 toolchain survey ==="
command -v node; node --version 2>&1
command -v pnpm || echo "(pnpm absent on PATH)"
command -v dsh || echo "(dsh absent on PATH)"
python3 --version 2>&1; uv --version 2>&1 | head -1
[ -x /tmp/toolchain/node22/bin/node ] && /tmp/toolchain/node22/bin/node --version 2>&1
[ -x /tmp/toolchain/node22/bin/pnpm ] && (export PATH=/tmp/toolchain/node22/bin:$PATH COREPACK_HOME=/tmp/toolchain/corepack-home; pnpm --version 2>&1 | tail -1)

echo "=== P13/P14 DSH CLI + STC patch composition (needs node22 toolchain) ==="
if [ -d /tmp/dsh-upstream ] && [ -x /tmp/toolchain/node22/bin/node ]; then
  export PATH=/tmp/toolchain/node22/bin:$PATH COREPACK_HOME=/tmp/toolchain/corepack-home
  export XDG_DATA_HOME=/tmp/toolchain/xdg-data XDG_CACHE_HOME=/tmp/toolchain/xdg-cache DSH_HOME=/tmp/muse-w0-dsh-home
  unset http_proxy https_proxy all_proxy ftp_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY FTP_PROXY
  (cd /tmp/dsh-upstream && timeout 100 pnpm dsh --version 2>&1 | tail -2)
  (cd /tmp/dsh-upstream && timeout 110 pnpm dsh --profile web --dump-config 2>&1 | grep -c "^      - id:")
  (cd /tmp/dsh-upstream && timeout 110 pnpm dsh --profile web --patch "$ROOT/stc/dsh-plugin-stc/cordis.dev.yml" --dump-config 2>&1 | grep -n "stc-bundle" | head -3)
else bad "DSH boot probe skipped (scratch deps absent)"; fi

echo "=== P17/P18 SST identity + search API ==="
head -8 sst/pyproject.toml
grep -n "^class \|^    def \|^    async def " sst/src/sst/search/controller.py sst/src/sst/search/policy.py sst/src/sst/search/engine.py 2>&1 | head -20

echo "=== P19/P20 import probes ==="
PYTHONPATH=sst/src python3 -c "import sst; print('sst imports OK')" 2>&1 | tail -1
PYTHONPATH=stc/src python3 -c "import stc; print('stc imports OK')" 2>&1 | tail -1

echo "=== P21/P22 STC bus + protocols ==="
sed -n '11,19p' stc/src/stc/services/hormones.py
grep -n "^class .*Protocol" stc/src/stc/protocols/interfaces.py 2>&1 | head

echo "=== P24 absences ==="
ls /home/anshul/dsh 2>&1 | head -1
git -C substrate rev-parse HEAD 2>&1 | head -1

echo "=== probes done: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ]
