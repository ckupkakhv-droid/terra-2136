#!/usr/bin/env python3
"""Produce a separate local candidate, never overwrite the supplied baseline."""
import argparse, hashlib, json
from pathlib import Path

BASE_SHA256 = 'b4e07d6cf5d370a812463f4a1f609275eb6e756a7c623afddf1bf629ce6d6550'
UI_START = 'function _et(e,t){let i=q("div","campResidents")'
UI_HOOK = 'let E=q("div","residentRows");'
HOOK_REPLACEMENT = 'i.append(renderResidentRecommendation(e,A,{reason:Tm,efficiency:ya},m=>f(m),{pending:o,available:typeof t.camp.assignResidentTask==="function"}));' + UI_HOOK


def apply(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('Refusing to overwrite baseline')
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != BASE_SHA256:
        raise ValueError(f'Unsupported baseline SHA-256: {digest}; no output written')
    html = raw.decode('utf-8')
    for anchor in [UI_START, UI_HOOK, '</head>', 'function ya(e,t,i)', 'function Tm(e,t,i)']:
        if html.count(anchor) != 1:
            raise ValueError(f'Expected one verified anchor: {anchor!r}')
    root = Path(__file__).resolve().parent
    code = (root / 'recommendation.mjs').read_text().replace('export function ', 'function ')
    if 'function recommendResident(' in html or 'function renderResidentRecommendation(' in html:
        raise ValueError('Recommendation names already present')
    html = html.replace(UI_START, code + '\n' + UI_START, 1)
    html = html.replace(UI_HOOK, HOOK_REPLACEMENT, 1)
    html = html.replace('</head>', '<style>\n' + (root / 'recommendation.css').read_text() + '\n</style>\n</head>', 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as target:
        target.write(html)
    manifest = {
        'status': 'local_candidate_not_published',
        'baseline_file': source.name,
        'baseline_sha256': digest,
        'output_file': output.name,
        'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'change': 'Read-only best-free-resident recommendation; existing guarded assignment handler reused',
        'save_schema_changed': False,
        'runtime_dependencies_added': [],
        'asset_or_license_changes': False,
    }
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(apply(args.source, args.output), ensure_ascii=False, indent=2))
