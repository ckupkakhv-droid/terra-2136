#!/usr/bin/env python3
"""Вынести window.TERRA_* из play/index.html в play/assets/pack/.

Одноразовый патч базовой сборки: SHA256 проверяется до правки, каждая
замена в бандле — ровно одно вхождение. Текстуры паразита, ползуна,
сирены и токсика пережимаются в WebP (цвет q90, нормали и ORM q95);
контрольные суммы и длины в бандле обновляются под новые байты.
Нужны node и ffmpeg. Повторный запуск по уже разрезанному HTML откажется.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / 'play' / 'index.html'
PACK = ROOT / 'play' / 'assets' / 'pack'
BASELINE_SHA = '0f1dcb3ea7056f9636088b778ea251aef59133604140f27aee67118f937fcec2'

NAMES = [
    'TERRA_ASSETS', 'TERRA_AUDIO', 'TERRA_G07_ASSETS', 'TERRA_MODULE_MODELS',
    'TERRA_CREATURE_CRAWLER', 'TERRA_CREATURE_PARASITE', 'TERRA_EVENT_ENEMIES',
    'TERRA_RAT', 'TERRA_VAT', 'TERRA_PROPS', 'TERRA_KIT', 'TERRA_CAMP',
    'TERRA_CAMP_POT', 'TERRA_CAMP_TIMBER', 'TERRA_CHEST', 'TERRA_BUILDER_WORKPIECE',
    'TERRA_SALVAGE_FENCE', 'TERRA_SWORDS', 'TERRA_DECALS', 'TERRA_CLASS_ATLAS',
    'TERRA_SHOP_ART', 'TERRA_TEX', 'TERRA_CREDITS',
]

# Индекс изображения в GLB → качество WebP. JPEG не трогаем.
IMAGE_QUALITY = {
    'parasite': {0: 90, 1: 95, 2: 95, 3: 90},
    'crawler': {0: 90},
    'c_siren_event': {0: 90, 1: 95, 2: 90},
    'c_toxic_event': {0: 95, 2: 95, 4: 95},
}

BOOT_STYLE = (
    '<style id="terraBootStyle">'
    '#terraBoot{position:fixed;inset:0;z-index:20000;display:flex;align-items:center;'
    'justify-content:center;background:#07080b;text-align:center;padding:24px}'
    '#terraBootTrack{width:min(360px,80vw);height:6px;margin:18px auto 0;background:#1a1e18;'
    'border:1px solid #3c4636;overflow:hidden}#terraBootBar{display:block;height:100%;width:35%;'
    'background:#c4a46a;animation:terraBoot 1.1s ease-in-out infinite}'
    '@keyframes terraBoot{0%{transform:translateX(-120%)}100%{transform:translateX(280%)}}'
    '</style>'
)
BOOT_OVERLAY = (
    '<div id="terraBoot" role="status" aria-live="polite">'
    '<div><div class="logo">ТЕРРА</div>'
    '<div class="sub" id="terraBootMsg">Поднимаем архив «ТЕРРА-1»…</div>'
    '<div id="terraBootTrack"><i id="terraBootBar"></i></div></div></div>'
)


def must_replace(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: ожидалось одно вхождение, найдено {count}')
    return text.replace(old, new, 1)


def slice_literals(blob):
    positions = []
    for name in NAMES:
        token = f'window.{name}='
        at = blob.find(token)
        if at < 0:
            raise SystemExit(f'нет присваивания {name}')
        if blob.find(token, at + 1) != -1:
            raise SystemExit(f'{name} встречается больше одного раза')
        positions.append((at, name))
    positions.sort()
    literals = {}
    for index, (at, name) in enumerate(positions):
        value_at = at + len(f'window.{name}=')
        end = positions[index + 1][0] if index + 1 < len(positions) else len(blob)
        raw = blob[value_at:end].rstrip()
        if raw.endswith(';'):
            raw = raw[:-1]
        literals[name] = raw
    return literals


def js_literal_to_json(literal):
    node = shutil.which('node')
    if not node:
        raise SystemExit('нужен node, чтобы разобрать объект ассетов')
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'in.js'
        out = Path(tmp) / 'out.json'
        src.write_text(literal, encoding='utf-8')
        program = (
            "const fs=require('fs');"
            "const src=fs.readFileSync(process.argv[1],'utf8');"
            "const val=Function('\"use strict\"; return ('+src+');')();"
            "fs.writeFileSync(process.argv[2], JSON.stringify(val));"
        )
        subprocess.run([node, '-e', program, str(src), str(out)], check=True)
        return json.loads(out.read_text(encoding='utf-8'))


def parse_glb(buf):
    if buf[:4] != b'glTF':
        raise ValueError('не GLB')
    length = struct.unpack_from('<I', buf, 8)[0]
    if length != len(buf):
        raise ValueError('длина GLB не сходится')
    offset = 12
    document = None
    binary = None
    while offset + 8 <= len(buf):
        chunk_len, chunk_type = struct.unpack_from('<I4s', buf, offset)
        offset += 8
        chunk = buf[offset:offset + chunk_len]
        offset += chunk_len
        if chunk_type == b'JSON':
            document = json.loads(chunk.decode('utf-8').rstrip(' \x00'))
        elif chunk_type == b'BIN\x00':
            binary = chunk
    if document is None or binary is None:
        raise ValueError('в GLB нет JSON или BIN')
    return document, binary


def build_glb(document, binary):
    payload = json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    payload += b' ' * ((4 - len(payload) % 4) % 4)
    binary += b'\x00' * ((4 - len(binary) % 4) % 4)
    total = 12 + 8 + len(payload) + 8 + len(binary)
    return b''.join((
        struct.pack('<4sII', b'glTF', 2, total),
        struct.pack('<I4s', len(payload), b'JSON'),
        payload,
        struct.pack('<I4s', len(binary), b'BIN\x00'),
        binary,
    ))


def to_webp(src, quality):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('нужен ffmpeg')
    if src[:8] == b'\x89PNG\r\n\x1a\n':
        suffix = '.png'
    elif src[:4] == b'RIFF' and src[8:12] == b'WEBP':
        suffix = '.webp'
    elif src[:2] == b'\xff\xd8':
        suffix = '.jpg'
    else:
        raise SystemExit(f'неизвестная текстура {src[:12]!r}')
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = folder / ('in' + suffix)
        target = folder / 'out.webp'
        source.write_bytes(src)
        base = [
            ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
            '-i', str(source), '-c:v', 'libwebp',
            '-quality', str(quality), '-compression_level', '6',
        ]
        run = subprocess.run(base + ['-alpha_quality', '100', str(target)], capture_output=True)
        if run.returncode != 0:
            subprocess.run(base + [str(target)], check=True)
        data = target.read_bytes()
    if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        raise SystemExit('ffmpeg вернул не WebP')
    return data


def recompress_glb(glb, qualities):
    document, binary = parse_glb(glb)
    views = document['bufferViews']
    slices = []
    for view in views:
        start = view.get('byteOffset', 0)
        slices.append(bytearray(binary[start:start + view['byteLength']]))
    saved = 0
    changed = False
    for index, quality in qualities.items():
        image = document['images'][index]
        if 'bufferView' not in image:
            continue
        view_index = image['bufferView']
        old = bytes(slices[view_index])
        new = to_webp(old, quality)
        if len(new) >= len(old):
            continue
        slices[view_index] = bytearray(new)
        image['mimeType'] = 'image/webp'
        saved += len(old) - len(new)
        changed = True
    if not changed:
        return glb, 0
    cursor = 0
    packed = bytearray()
    for view, data in zip(views, slices):
        pad = (4 - cursor % 4) % 4
        packed += b'\x00' * pad
        cursor += pad
        view['byteOffset'] = cursor
        view['byteLength'] = len(data)
        packed += data
        cursor += len(data)
    document['buffers'][0]['byteLength'] = len(packed)
    return build_glb(document, bytes(packed)), saved


def gzip_b64(glb):
    packed = gzip.compress(glb, compresslevel=9, mtime=0)
    return base64.b64encode(packed).decode('ascii'), len(packed), len(glb), hashlib.sha256(glb).hexdigest()


def recompress_payload(b64, qualities):
    glb = gzip.decompress(base64.b64decode(b64))
    glb, saved = recompress_glb(glb, qualities)
    encoded, packed_len, raw_len, digest = gzip_b64(glb)
    # Проверка, что браузерный gzip-раундтрип хотя бы в Python сходится.
    if gzip.decompress(base64.b64decode(encoded)) != glb:
        raise SystemExit('gzip GLB не сходится')
    return encoded, packed_len, raw_len, digest, saved


def apply_texture_pass(groups):
    report = []
    parasite = groups['TERRA_CREATURE_PARASITE']
    encoded, packed, raw, digest, saved = recompress_payload(parasite['gzip'], IMAGE_QUALITY['parasite'])
    old = parasite['sha256']
    parasite['gzip'] = encoded
    parasite['sha256'] = digest
    if parasite.get('curve', {}).get('model_sha256') != old:
        raise SystemExit('у паразита нет model_sha256')
    parasite['curve']['model_sha256'] = digest
    report.append(('c_parasite', packed, raw, digest, saved))

    crawler = groups['TERRA_CREATURE_CRAWLER']
    encoded, packed, raw, digest, saved = recompress_payload(crawler['gzip'], IMAGE_QUALITY['crawler'])
    old = crawler['sha256']
    crawler['gzip'] = encoded
    crawler['sha256'] = digest
    if crawler.get('curve', {}).get('model_sha256') != old:
        raise SystemExit('у ползуна нет model_sha256')
    crawler['curve']['model_sha256'] = digest
    report.append(('c_crawler', packed, raw, digest, saved))

    enemies = groups['TERRA_EVENT_ENEMIES']
    for key in ('c_siren_event', 'c_toxic_event'):
        asset = enemies['assets'][key]
        encoded, packed, raw, digest, saved = recompress_payload(asset['gzip'], IMAGE_QUALITY[key])
        old = asset['sha256']
        asset['gzip'] = encoded
        asset['sha256'] = digest
        curve = asset.get('curve')
        if curve is not None:
            if curve.get('model_sha256') != old:
                raise SystemExit(f'у {key} нет model_sha256')
            curve['model_sha256'] = digest
        report.append((key, packed, raw, digest, saved))
    return report


def patch_bundle(suffix, report):
    by_name = {name: (packed, raw, digest) for name, packed, raw, digest, _saved in report}
    crawler = by_name['c_crawler']
    parasite = by_name['c_parasite']
    siren = by_name['c_siren_event']
    toxic = by_name['c_toxic_event']
    old_bit = (
        'bit={c_crawler:{packed:1005731,raw:1902484,height:.7086614,meshes:1,joints:59,'
        'clips:["Idle","crawl","attack","death"]},c_parasite:{packed:4757795,raw:5297404,'
        'height:2.6,meshes:2,joints:70,clips:["idle","walk","attack","death"]}}'
    )
    new_bit = (
        f'bit={{c_crawler:{{packed:{crawler[0]},raw:{crawler[1]},height:.7086614,meshes:1,joints:59,'
        f'clips:["Idle","crawl","attack","death"]}},c_parasite:{{packed:{parasite[0]},raw:{parasite[1]},'
        f'height:2.6,meshes:2,joints:70,clips:["idle","walk","attack","death"]}}}}'
    )
    old_git = (
        'git={c_siren_event:{raw:4699936,packed:4015070,meshes:1,joints:34,height:2.2},'
        'c_toxic_event:{raw:4485928,packed:3712297,meshes:4,joints:63,height:2.6}}'
    )
    new_git = (
        f'git={{c_siren_event:{{raw:{siren[1]},packed:{siren[0]},meshes:1,joints:34,height:2.2}},'
        f'c_toxic_event:{{raw:{toxic[1]},packed:{toxic[0]},meshes:4,joints:63,height:2.6}}}}'
    )
    suffix = must_replace(suffix, old_bit, new_bit, 'bit')
    suffix = must_replace(suffix, old_git, new_git, 'git')
    suffix = must_replace(
        suffix,
        '311c975ba2e80d30926be1283e0dc26ca3eaec0a2d8afdf11c6febab49616804',
        siren[2],
        'sha сирены',
    )
    suffix = must_replace(
        suffix,
        '1b954c161023fc91f4bd2d069cdd3942a30e96756dda088d611f065d3bb1faf7',
        toxic[2],
        'sha токсика',
    )
    return suffix


def main():
    raw = HTML_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != BASELINE_SHA:
        raise SystemExit(f'Неподдерживаемая база HTML {digest}; патч только для проверенного main.')
    html = raw.decode('utf-8')
    marker = '<script>window.TERRA_ASSETS='
    start = html.find(marker)
    end = html.find('</script>', start)
    if start < 0 or end < 0:
        raise SystemExit('не найден скрипт ассетов')
    if html.count(marker) != 1:
        raise SystemExit('скрипт ассетов не единственный')
    end += len('</script>')
    prefix, blob, suffix = html[:start], html[start:end], html[end:]
    literals = slice_literals(blob[len('<script>'):blob.rfind('</script>')])
    groups = {name: js_literal_to_json(literal) for name, literal in literals.items()}
    before = {name: len(literal.encode('utf-8')) for name, literal in literals.items()}
    report = apply_texture_pass(groups)
    suffix = patch_bundle(suffix, report)

    if '</head>' not in prefix or prefix.count('<body>') != 1:
        raise SystemExit('не удалось найти единственные </head> и <body>')
    prefix = must_replace(prefix, '</head>', BOOT_STYLE + '</head>', 'style')
    prefix = must_replace(prefix, '<body>', '<body>' + BOOT_OVERLAY, 'overlay')

    PACK.mkdir(parents=True, exist_ok=True)
    manifest_groups = []
    pack_total = 0
    for name in NAMES:
        payload = json.dumps(groups[name], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        packed = gzip.compress(payload, compresslevel=9, mtime=0)
        if len(packed) >= 50_000_000:
            raise SystemExit(f'{name} больше 50 МБ: {len(packed)}')
        filename = f'{name}.json.gz'
        (PACK / filename).write_bytes(packed)
        file_sha = hashlib.sha256(packed).hexdigest()
        manifest_groups.append({
            'name': name,
            'file': filename,
            'bytes': len(packed),
            'sha256': file_sha,
        })
        pack_total += len(packed)
        print(f'{name:28} было {before[name]/1e6:6.2f} МБ текста → пакет {len(packed)/1e6:6.2f} МБ')
    manifest = {'v': 1, 'groups': manifest_groups}
    (PACK / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8',
    )

    html_out = prefix + '<script src="assets/vendor/fflate.min.js"></script>\n<script src="assets/boot.js"></script>' + suffix
    HTML_PATH.write_text(html_out, encoding='utf-8')
    print('--- текстуры ---')
    texture_saved = 0
    for name, packed, raw_len, digest, saved in report:
        texture_saved += saved
        print(f'{name:16} raw={raw_len/1e6:.2f} МБ packed={packed/1e6:.2f} МБ срез текстур {saved/1e6:.2f} МБ sha={digest[:12]}')
    new_size = HTML_PATH.stat().st_size
    print(f'HTML {len(raw)/1e6:.2f} → {new_size/1e6:.2f} МБ')
    print(f'Пакет на диске {pack_total/1e6:.2f} МБ, экономия текстур {texture_saved/1e6:.2f} МБ несжатых')
    print('SHA256 HTML', hashlib.sha256(HTML_PATH.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
