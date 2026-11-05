"""Build the self-contained Chrome/Chromium release: python3 scripts/build-offline.py.

Writes terra.html at the repository root; attach it to a Release, never commit it.
No network access or third-party build packages are required.
"""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import re
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / 'play'
OUTPUT = ROOT / 'terra.html'
MAX_BYTES = 50_000_000


def encoded(raw):
    return base64.b64encode(raw).decode('ascii')


def json_script(value):
    # JSON inside an HTML script must not contain a literal closing script tag.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


html = (PLAY / 'index.html').read_text(encoding='utf-8')
assets = {}
for path in sorted((PLAY / 'assets').rglob('*.glb')):
    raw = path.read_bytes()
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    compressed = len(packed) < len(raw) * .95
    assets[path.relative_to(PLAY).as_posix()] = {
        'gzip': compressed,
        'data': encoded(packed if compressed else raw),
    }

# Асинхронный загрузчик проверяет и поднимает window.TERRA_* до старта игры.
# В офлайне байты лежат в window.TERRA_PACK: версии URL не требуют сети.
pack = {}
for path in sorted((PLAY / 'assets' / 'pack').rglob('*')):
    if path.is_file():
        pack[path.relative_to(PLAY).as_posix()] = encoded(path.read_bytes())
if len(pack) < 2:
    raise ValueError('Offline build did not find play/assets/pack')
boot_scripts = re.compile(
    r'<script\s+src="assets/vendor/fflate\.min\.js"\s*>\s*</script>\s*'
    r'<script([^>]*?)\bsrc="(assets/boot\.js(?:\?[^"<>]*)?)"([^>]*)>\s*</script>')
boot_matches = list(boot_scripts.finditer(html))
if len(boot_matches) != 1:
    raise ValueError('Expected the fflate and boot script tags')
boot_attributes = (boot_matches[0].group(1) + boot_matches[0].group(3)).strip()
boot_raw = (PLAY / 'assets/boot.js').read_bytes()
loader_pins = parse_qs(urlsplit(boot_matches[0].group(2)).query).get('v', [])
if loader_pins != [hashlib.sha256(boot_raw).hexdigest()]:
    raise ValueError('Boot loader cache version is stale; run scripts/assets_boot.py')
manifest_pins = re.findall(r'\bdata-terra-manifest-sha256=["\']([^"\']+)["\']', boot_attributes)
manifest_sha = hashlib.sha256((PLAY / 'assets/pack/manifest.json').read_bytes()).hexdigest()
if manifest_pins != [manifest_sha]:
    raise ValueError('Boot manifest SHA256 does not match the embedded archive')
fflate_source = (PLAY / 'assets/vendor/fflate.min.js').read_text(encoding='utf-8').replace('</script', '<\\/script')
boot_source = boot_raw.decode('utf-8').replace('</script', '<\\/script')
html = boot_scripts.sub(lambda _: (
    '<script>window.TERRA_PACK=' + json_script(pack) + '</script>'
    '<script>' + fflate_source + '</script><script ' + boot_attributes + '>' + boot_source + '</script>'
), html, count=1)

# Match the complete relative path, not a basename: distinct folders may contain
# equally named models. Unrelated requests keep the native fetch behavior.
shim = '''<script>(function(){
var assets=ASSETS,original=window.fetch.bind(window);
window.fetch=function(input,options){
  var url=new URL(String(input&&input.url||input),document.baseURI);
  var base=new URL(document.baseURI),at=url.pathname.lastIndexOf('/assets/');
  var key=at<0?'':url.pathname.slice(at+1),entry=assets[key];
  if(!entry||url.origin!==base.origin)return original(input,options);
  var bytes=Uint8Array.from(atob(entry.data),function(c){return c.charCodeAt(0)});
  var body=entry.gzip?new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')):bytes;
  return Promise.resolve(new Response(body,{status:200,headers:{'Content-Type':'model/gltf-binary'}}));
};})();</script>'''.replace('ASSETS', json_script(assets), 1)

# Browser import maps allow module dependencies to stay separate and avoid an
# eval-based bundler. data: modules use the stable terra/* import-map namespace.
modules = {}
for path in sorted((PLAY / 'ui').glob('*.js')):
    source = path.read_text(encoding='utf-8')
    if re.search(r'^\s*(import|export)\s', source, re.M):
        modules[path.name] = source


def rewrite_module(source):
    def replace(match):
        name = match.group(2)
        if name not in modules:
            raise ValueError(f'Module dependency is not bundled: {name}')
        return match.group(1) + 'terra/' + name + match.group(1)
    return re.sub(r"(['\"])\./([\w-]+\.js)\1", replace, source)


imports = {'imports': {
    'terra/' + name: 'data:text/javascript;base64,' + encoded(rewrite_module(source).encode())
    for name, source in modules.items()
}}
bootstrap = '<script type="importmap">' + json_script(imports) + '</script>' + shim
html, heads = re.subn(r'<head>', lambda _: '<head>' + bootstrap, html, count=1)
if heads != 1:
    raise ValueError('Expected one <head> insertion point')


def classic_source(path):
    source = (PLAY / path).read_text(encoding='utf-8')
    if path == 'ui/camp-navigation.js':
        # Camp add-ons are dynamically injected by the online camp script.
        source, count = re.subn(
            r"\{\s*(?:const base[^;]*;\s*)?const s = document\.createElement\('script'\).*?document\.head\.append\(l\); \}",
            '', source, flags=re.S)
        if count != 3:
            raise ValueError(f'Expected three camp add-on loaders, found {count}')
        for name in ('camp-mobile', 'camp-dossier', 'camp-live'):
            css = (PLAY / f'ui/{name}.css').read_text(encoding='utf-8')
            js = (PLAY / f'ui/{name}.js').read_text(encoding='utf-8')
            source += ('\n;(function(){var st=document.createElement("style");st.textContent='
                       + json_script(css) + ';document.head.append(st);'
                       + 'var sc=document.createElement("script");sc.textContent='
                       + json_script(js) + ';document.head.append(sc);})();')
    return source.replace('</script', '<\\/script')


def inline_script(match):
    attributes = match.group(1) + match.group(3)
    path = urlsplit(match.group(2)).path
    # Preserve staged scripts until boot.js activates them in online order.
    kind = re.search(r'\btype\s*=\s*(["\'])(.*?)\1', attributes)
    opening = '<script' + attributes + '>'
    if kind and kind.group(2) in ('module', 'application/x-terra-module'):
        name = Path(path).name
        if name not in modules:
            raise ValueError(f'Module entry is not bundled: {path}')
        return opening + 'import "terra/' + name + '";</script>'
    return opening + classic_source(path) + '</script>'


html, scripts = re.subn(
    r'<script([^>]*?)src="((?:ui|art)/[^"]+)"([^>]*)>\s*</script>', inline_script, html)
html, styles = re.subn(
    r'<link rel="stylesheet" href="(ui/[^"]+)">',
    lambda match: '<style>' + (PLAY / match.group(1)).read_text(encoding='utf-8') + '</style>', html)
if re.search(r'<(?:script|link)\b[^>]*(?:src|href)="(?:ui|art|assets)/', html):
    raise ValueError('Unresolved local script or stylesheet in offline HTML')
raw = html.encode('utf-8')
if len(raw) > MAX_BYTES:
    raise ValueError(f'Offline build exceeds {MAX_BYTES:,} bytes: {len(raw):,}; no output written')
temporary = OUTPUT.with_suffix('.html.tmp')
temporary.write_bytes(raw)
temporary.replace(OUTPUT)
print(f'Built {OUTPUT.name}: {len(raw):,} bytes; headroom {MAX_BYTES - len(raw):,} bytes')
print(f'Bundled {len(assets)} models, {len(modules)} modules, {scripts} scripts, {styles} stylesheets')
print('SHA256:', hashlib.sha256(raw).hexdigest())
