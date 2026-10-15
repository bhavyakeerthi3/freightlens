"""Run the eval suite and three independent full CLI executions."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from assistant import ROOT

test = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-v'], cwd=ROOT, capture_output=True, text=True)
(ROOT / 'results').mkdir(exist_ok=True)
(ROOT / 'results/evaluation.txt').write_text(test.stdout + test.stderr, encoding='utf-8')
if test.returncode:
    print(test.stdout + test.stderr)
    raise SystemExit(test.returncode)
checks = []
with tempfile.TemporaryDirectory() as tmp:
    for i in range(3):
        out = Path(tmp) / str(i)
        subprocess.run([sys.executable, str(ROOT / 'assistant.py'), '--out', str(out)], check=True, capture_output=True)
        checks.append({name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                       for name in ('output.csv', 'audit.json', 'cost_log.json')})
assert checks[0] == checks[1] == checks[2]
(ROOT / 'results/reproducibility.json').write_text(json.dumps({'independent_cli_runs': 3, 'identical': True, 'sha256': checks}, indent=2), encoding='utf-8')
print('Evaluation passed; all three independent CLI runs are byte-identical.')
