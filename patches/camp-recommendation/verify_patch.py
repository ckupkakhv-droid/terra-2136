#!/usr/bin/env python3
import hashlib, sys, tempfile, re, subprocess
from pathlib import Path
from apply_patch import apply, BASE_SHA256, UI_START, UI_HOOK, HOOK_REPLACEMENT
root = Path(__file__).resolve().parent
base, output = map(Path, sys.argv[1:3])
code = (root / 'recommendation.mjs').read_text().replace('export function ', 'function ')
css = (root / 'recommendation.css').read_text()
html = output.read_text()
restored = html.replace(code + '\n' + UI_START, UI_START, 1).replace(HOOK_REPLACEMENT, UI_HOOK, 1).replace('<style>\n' + css + '\n</style>\n</head>', '</head>', 1)
assert restored.encode() == base.read_bytes(), 'Unexpected unrelated changes'
assert hashlib.sha256(base.read_bytes()).hexdigest() == BASE_SHA256
with tempfile.TemporaryDirectory(dir=root) as directory:
    bad, target = Path(directory) / 'bad.html', Path(directory) / 'output.html'
    bad.write_text('unsupported')
    try: apply(bad, target)
    except ValueError: pass
    else: raise AssertionError('Wrong baseline accepted')
    assert not target.exists()
    try: apply(base, base)
    except ValueError: pass
    else: raise AssertionError('Baseline overwrite accepted')
    runtime = Path(directory) / 'runtime.js'
    runtime.write_text(re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)[-1])
    subprocess.run(['node', '--check', str(runtime)], check=True)
print('PASS: full runtime syntax; baseline unchanged; exact reversible additions; wrong baseline/overwrite rejected')
print('Added bytes:', output.stat().st_size - base.stat().st_size)
