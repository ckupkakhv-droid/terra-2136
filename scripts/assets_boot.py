"""Gate the extracted archive before bundle evaluation, with checked anchors.

Used by extract-assets.py; rerun directly after changing boot.js to refresh the
content-version URL. Does not change the game simulation or save format.
"""
from pathlib import Path
import hashlib
import re


def once(html, old, new):
    if html.count(old) != 1:
        raise ValueError(f'Expected exactly one asset boot anchor: {old[:90]}')
    return html.replace(old, new, 1)


def configure_boot(html, manifest, loader):
    if 'id="terraGameBundle"' not in html:
        html = once(html, '<script defer src="ui/defense.js"></script>',
                    '<script type="application/x-terra-script" data-terra-stage="before-game" src="ui/defense.js"></script>')
        html = once(html, '<script defer src="ui/camp-navigation.js"></script>',
                    '<script type="application/x-terra-script" data-terra-stage="after-game" src="ui/camp-navigation.js"></script>')
        html = once(html, '<script type="module" src="ui/sewer-bootstrap.js"></script>',
                    '<script type="application/x-terra-module" data-terra-stage="register" src="ui/sewer-bootstrap.js"></script>')
        html = once(html, '<script>(()=>{', '<script type="application/x-terra-main" id="terraGameBundle">(()=>{')
        # Assets are captured by lazy initializers while the bundle evaluates.
        # Export only its native startup callback; invoke it after registration.
        html = once(html, 'window.addEventListener("load",()=>{if(Hp.tier',
                    'window.TERRA_START_GAME=()=>{if(Hp.tier')
        html = once(html,
                    'e&&Promise.resolve().then(()=>(pM(),fM)).then(t=>t.autoJoin(window.game,e)).catch(()=>{})})});rot();',
                    'e&&Promise.resolve().then(()=>(pM(),fM)).then(t=>t.autoJoin(window.game,e)).catch(()=>{})};});rot();')
    for marker in ['data-terra-stage="before-game"', 'data-terra-stage="after-game"',
                   'data-terra-stage="register"', 'window.TERRA_START_GAME=()=>{if(Hp.tier']:
        if html.count(marker) != 1:
            raise ValueError(f'Asset boot marker changed: {marker}')
    manifest_sha = hashlib.sha256(manifest).hexdigest()
    loader_sha = hashlib.sha256(loader).hexdigest()
    tag = (f'<script src="assets/boot.js?v={loader_sha}" '
           f'data-terra-manifest-sha256="{manifest_sha}"></script>')
    html, count = re.subn(r'<script\b[^>]*\bsrc="assets/boot\.js(?:\?[^"<>]*)?"[^>]*>\s*</script>',
                         lambda _: tag, html)
    if count != 1:
        raise ValueError('Expected exactly one archive loader script')
    return html


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    path = root / 'play/index.html'
    html = configure_boot(path.read_text(encoding='utf-8'), (root / 'play/assets/pack/manifest.json').read_bytes(),
                          (root / 'play/assets/boot.js').read_bytes())
    path.write_text(html, encoding='utf-8')
    print('Asset boot gate and content versions updated')
