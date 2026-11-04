"""Apply only the HTML wiring/text change to the exact reviewed main baseline.
UI sources are served directly from play/ui; no package installation is needed.
"""
from pathlib import Path
import hashlib
root = Path(__file__).resolve().parents[1]
path = root / 'play/index.html'
raw = path.read_bytes()
if hashlib.sha256(raw).hexdigest() != 'bfcfd5a4c1ec80426c5bb4374228c340c11648859ea54eab7fa63f80fd32ccce':
    raise SystemExit('Unsupported HTML baseline; review the upstream changes before applying.')
s = raw.decode()
start = s.rindex('<style>', 0, s.index('#campPanel .residentRecommendation'))
end = s.index('</style>', start) + len('</style>')
s = s[:start] + '<link rel="stylesheet" href="ui/camp-navigation.css">\n<script defer src="ui/camp-navigation.js"></script>' + s[end:]
old = 'Цена приказа: 0 ресурсов.'
assert s.count(old) == 1
s = s.replace(old, 'Назначение бесплатно. Строительство и снабжение расходуют ресурсы по обычным правилам.')
job_hook = 'A.append(C)}i.append(A,b)'
assert s.count(job_hook) == 1
s = s.replace(job_hook, 'C.dataset.residentJob=E,' + job_hook)
assert len(s.encode()) < len(raw), 'Keep the large HTML from growing'
path.write_text(s)
