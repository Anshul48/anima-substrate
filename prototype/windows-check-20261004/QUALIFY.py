from __future__ import annotations
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'w1-harden'
CANDIDATE = ROOT / 'candidate'

def hashes(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.iterdir()) if p.is_file()}

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')

if sys.platform != 'win32':
    raise RuntimeError('This runner requires native Windows Python.')
if not CANDIDATE.exists():
    original = hashes(SOURCE)
    write_json(ROOT / 'ORIGINAL-SHA256.json', original)
    CANDIDATE.mkdir()
    for source_file in sorted(SOURCE.glob('*.py')):
        shutil.copyfile(source_file, CANDIDATE / source_file.name)
    patches = []
    for name in ('recovery_exercise.py', 'test_recovery.py'):
        path = CANDIDATE / name
        old = path.read_text(encoding='utf-8')
        needle = 'os.kill(proc.pid, signal.SIGKILL)'
        if old.count(needle) != 1:
            raise RuntimeError(f'{name}: expected exactly one kill call.')
        new = old.replace(needle, 'proc.kill()')
        new = new.replace('import os\n', '').replace('import signal\n', '')
        new = new.replace('a real SIGKILL of a child process', 'a real forced termination of a child process')
        new = new.replace('SIGKILL it, reopen', 'force-terminate it, reopen')
        new = new.replace('mid-run (SIGKILL)', 'mid-run (SIGKILL on POSIX, TerminateProcess on Windows)')
        new = new.replace('R1-real resume after SIGKILL', 'R1-real resume after forced termination')
        new = new.replace('R1 exercise resume after SIGKILL', 'R1 exercise resume after forced termination')
        new = new.replace('test_R1_real_sigkill_child_resume_to_verdict', 'test_R1_real_process_kill_child_resume_to_verdict')
        path.write_text(new, encoding='utf-8', newline='\n')
        patches.extend(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                          fromfile='w1-harden/' + name, tofile='candidate/' + name))
    (ROOT / 'WINDOWS-KILL.patch').write_text(''.join(patches), encoding='utf-8', newline='\n')
else:
    original = json.loads((ROOT / 'ORIGINAL-SHA256.json').read_text(encoding='utf-8'))

runs_root = ROOT / 'runs'
runs_root.mkdir(exist_ok=True)
run_no = 1
while (runs_root / f'attempt-{run_no:03d}').exists():
    run_no += 1
RUN = runs_root / f'attempt-{run_no:03d}'
RUN.mkdir()
TEMP = RUN / 'tmp'
TEMP.mkdir()
env = dict(os.environ)
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(CANDIDATE), TEMP=str(TEMP), TMP=str(TEMP))
runs = {}

def execute(name, args):
    command = [sys.executable, '-B', *args]
    try:
        result = subprocess.run(command, cwd=CANDIDATE, env=env,
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        stdout, stderr, rc = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b''
        stderr = exc.stderr or b''
        stdout = stdout.decode('utf-8', errors='replace') if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode('utf-8', errors='replace') if isinstance(stderr, bytes) else stderr
        stderr += '\nQualification process exceeded 120 seconds.\n'
        rc = None
    (RUN / f'{name}.stdout.log').write_text(stdout, encoding='utf-8', newline='\n')
    (RUN / f'{name}.stderr.log').write_text(stderr, encoding='utf-8', newline='\n')
    runs[name] = {'command': command, 'cwd': str(CANDIDATE), 'returncode': rc}
    print(f'{name}: returncode={rc}', flush=True)
    if rc != 0:
        print((stdout + stderr)[-4000:], flush=True)
    return rc, stdout, stderr

candidate_before = hashes(CANDIDATE)
suite_rc, _, suite_stderr = execute('suite', ['-m', 'unittest', 'test_w1_harden', 'test_failures', 'test_recovery', '-v'])
DEMO = RUN / 'stub-demo'
demo_rc, demo_stdout, _ = execute('stub-demo', ['demo_T.py', '--state-dir', str(DEMO), '--ledger', str(DEMO / 'ledger.jsonl')])
RECOVERY = RUN / 'recovery'
recovery_rc, _, _ = execute('recovery', ['recovery_exercise.py', '--evidence-dir', str(RECOVERY)])

ledger = [json.loads(row) for row in (DEMO / 'ledger.jsonl').read_text(encoding='utf-8').splitlines()] if (DEMO / 'ledger.jsonl').exists() else []
recovery = json.loads((RECOVERY / 'ALL-summary.json').read_text(encoding='utf-8')) if (RECOVERY / 'ALL-summary.json').exists() else []
r1 = next((row for row in recovery if row.get('scenario', '').startswith('R1')), {})
import signal
checks = {
    'suite_33_passed': suite_rc == 0 and bool(re.search(r'Ran 33 tests', suite_stderr)),
    'stub_demo_exit_0': demo_rc == 0,
    'stub_engine_observed': 'stub-deterministic-v1' in demo_stdout,
    'stub_demo_40_ledger_entries': len(ledger) == 40,
    'recovery_exit_0': recovery_rc == 0,
    'forced_termination_nonzero': r1.get('child_returncode') not in (None, 0),
    'zero_reexecuted_invokes': r1.get('re_executed_invokes') == 0,
    'recovery_conservation_ok': r1.get('conservation') == 'ok',
    'candidate_unchanged_by_execution': hashes(CANDIDATE) == candidate_before,
    'original_unchanged': hashes(SOURCE) == original,
}
report = {
    'recorded_at_utc': datetime.datetime.now(datetime.UTC).isoformat(),
    'platform': sys.platform, 'python': sys.version, 'executable': sys.executable,
    'baseline': {'SIGKILL_available': hasattr(signal, 'SIGKILL'), 'source_files': len(original)},
    'scope': 'Native Windows offline TEST/stub qualification; Linux remains the shipping target. No SST or live model qualification.',
    'candidate_sha256': candidate_before, 'checks': checks, 'runs': runs,
    'recovery_summaries': recovery, 'experiment_spend_usd': 0.0,
}
write_json(RUN / 'RESULT.json', report)
write_json(ROOT / 'CANDIDATE-SHA256.json', candidate_before)
print(json.dumps({'result': str(RUN / 'RESULT.json'), 'checks': checks, 'child_returncode': r1.get('child_returncode')}, indent=2), flush=True)
sys.exit(0 if all(checks.values()) else 1)
