"""Refresh the static deployment snapshot after running assistant.py."""
import shutil
from assistant import ROOT

public = ROOT / 'public'
(public / 'download').mkdir(parents=True, exist_ok=True)
for name in ('index.html', 'app.css', 'app.js'):
    shutil.copyfile(ROOT / name, public / name)
shutil.copyfile(ROOT / 'results/output.csv', public / 'download/output.csv')
print('Prepared public assets and CSV. Deploy the project root to Vercel.')
