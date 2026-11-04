"""Ночной рейд и турели: повторяемый замер кадра.

Сравнивает 0, 6 и 18 стационарных турелей при полном рейде camp.raids (60 врагов,
все волны сразу — худший случай; в игре волны идут с паузой 12 с).

Стенд: Chromium, окно 390×844, сенсорный ввод, devicePixelRatio 2 и 3,
качество «Среднее» (как авто на телефоне до просадки), CPU throttle 4× и 6×.
Два запуска браузера: SwiftShader и обычный ANGLE (на этой машине ANGLE часто
тоже программный — в отчёте смотрите строку renderer).

Что пишется по каждому кадру (performance.mark terra-frame / terra-module
и renderer.info после render):
  frameMs   — интервал обработанных кадров (игра сама не пускает чаще ~62 Гц);
  jsMs      — время loop() на главном потоке, вместе с синхронным WebGL;
  moduleMs  — время moduleUpdate, внутри него тик обороны;
  calls, triangles — renderer.info.render за кадр.

Игра на сенсорном «Среднем» сама режет pixel ratio примерно до 1.1.
Основная таблица принудительно ставит pixel ratio экрана (2 или 3), чтобы
сравнить стоимость заполнения. Отдельная строка natural — как оставит игра.

Запуск (из корня репозитория, сервер раздаёт и play/, и tests/):

  python3 -m http.server 8080
  python3 tests/turret-perf.py

Переменные:
  TERRA_TEST_URL     по умолчанию http://127.0.0.1:8080/play/
  TERRA_CHROMIUM     путь к Chrome/Chromium
  TERRA_QA_OUTPUT    каталог JSON и скриншота (по умолчанию /tmp/terra-turret-perf)
  TERRA_PERF_SECONDS длина окна замера, с (по умолчанию 4)
  TERRA_PERF_WARMUP  прогрев после расстановки, с (по умолчанию 1.5)
  TERRA_PERF_QUICK=1 один прогон: SwiftShader, DPR 2, throttle 4×, 0/18

Телефон (удалённая отладка), когда будет устройство:
  1. Компьютер: python3 -m http.server 8080
  2. Телефон в той же сети открывает http://<адрес-компьютера>:8080/play/
     Либо USB: adb reverse tcp:8080 tcp:8080 и http://127.0.0.1:8080/play/
  3. На компьютере chrome://inspect → Inspect у вкладки игры.
  4. В консоли телефона вставить tests/turret-perf.js целиком, затем:
       copy(JSON.stringify(await terraTurretPerf.run({turrets:[0,6,18], seconds:5})))
     Скрипт не трогает сейв, но сюжет и рейд в этой сессии меняет — не жмите «сохранить».
  5. Throttle CPU 4×/6× ставится в Performance той же отладочной панели до run().
  6. Принудительный DPR, если нужен экранный, а не потолок игры:
       await terraTurretPerf.run({pixelRatio: window.devicePixelRatio, turrets:[0,18]})
"""
from pathlib import Path
import json
import os
import shutil
import urllib.request

from playwright.sync_api import sync_playwright

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve().parent / 'turret-perf.js'
OUT = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-turret-perf'))
SECONDS = float(os.environ.get('TERRA_PERF_SECONDS', '4'))
WARMUP = float(os.environ.get('TERRA_PERF_WARMUP', '1.5'))
QUICK = os.environ.get('TERRA_PERF_QUICK') == '1'
CHROME = os.environ.get('TERRA_CHROMIUM') or shutil.which('google-chrome') or shutil.which('chromium')
VIEW = {'width': 390, 'height': 844}


def server_up():
    try:
        urllib.request.urlopen(URL, timeout=3)
        return True
    except Exception:
        return False


def launch_args(kind):
    if kind == 'swiftshader':
        return ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
    return ['--use-gl=angle', '--use-angle=gl', '--ignore-gpu-blocklist', '--enable-webgl']


def start_game(page):
    page.add_init_script(
        "localStorage.setItem('terra_set', JSON.stringify({q:'med', vol:0, vm:0, vs:0, va:0, post:true, fps:false}));"
    )
    page.goto(URL, wait_until='load', timeout=180000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function("window.game && game.state==='play' && game.p && game.scene && window.terraDefense", timeout=180000)
    page.add_script_tag(path=str(SCRIPT))
    page.wait_for_function('window.terraTurretPerf && terraTurretPerf._v===1', timeout=10000)


def summarize(row):
    def g(block, key):
        b = row.get(block) or {}
        v = b.get(key)
        return None if v is None else round(v, 2)

    return {
        'turrets': row['turrets'],
        'frames': row['frames'],
        'frameMs_p50': g('frameMs', 'p50'),
        'frameMs_p95': g('frameMs', 'p95'),
        'jsMs_p50': g('jsMs', 'p50'),
        'jsMs_p95': g('jsMs', 'p95'),
        'moduleMs_p50': g('moduleMs', 'p50'),
        'calls_p50': g('calls', 'p50'),
        'calls_min': g('calls', 'min'),
        'calls_max': g('calls', 'max'),
        'triangles_p50': g('triangles', 'p50'),
        'triangles_min': g('triangles', 'min'),
        'triangles_max': g('triangles', 'max'),
        'defenseMs_p50': g('defenseMs', 'p50'),
        'defenseMs_p95': g('defenseMs', 'p95'),
        'enemies_p50': g('enemies', 'p50'),
        'shots': row['shots'],
        'raidAlive': row['raidAlive'],
        'views': row['views'],
        'okShots': row['okShots'],
        'pixelRatio': (row.get('gl') or {}).get('pixelRatio'),
        'buffer': (row.get('gl') or {}).get('buffer'),
        'defenseEmaMs': row.get('defenseEmaMs'),
    }


def run_matrix(page, kind):
    """natural — pixel ratio, который оставила игра (на телефоне это потолок ~1.1).
    forced — pixel ratio 2 и 3, как у экрана. CPU 6× только на natural: там виден JS,
    а кадр SwiftShader и так упирается в растеризацию."""
    runs = []
    cdp = page.context.new_cdp_session(page)
    page.evaluate("""async () => { await terraTurretPerf.arm(0); }""")
    page.wait_for_timeout(8000)
    natural_counts = [0, 18] if QUICK else [0, 6, 18]
    natural_cpus = [4] if QUICK else [4, 6]
    for cpu in natural_cpus:
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': cpu})
        natural = page.evaluate(
            """async (cfg) => terraTurretPerf.run(cfg)""",
            {'turrets': natural_counts, 'seconds': SECONDS, 'warmup': WARMUP, 'label': f'{kind}/natural/cpu{cpu}'},
        )
        for row in natural['rows']:
            check_row(row)
            runs.append({'backend': kind, 'mode': 'natural', 'cpu': cpu, 'askedDpr': None, **summarize(row),
                         'renderer': natural['gl'].get('renderer'), 'touch': natural['gl'].get('touch'), 'qk': natural['gl'].get('qk')})
    if not QUICK:
        for dpr in (2, 3):
            cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
            forced = page.evaluate(
                """async (cfg) => terraTurretPerf.run(cfg)""",
                {'turrets': [0, 18], 'seconds': SECONDS, 'warmup': WARMUP, 'pixelRatio': dpr,
                 'label': f'{kind}/forced-dpr{dpr}/cpu4'},
            )
            for row in forced['rows']:
                check_row(row)
                runs.append({'backend': kind, 'mode': 'forced', 'cpu': 4, 'askedDpr': dpr, **summarize(row),
                             'renderer': forced['gl'].get('renderer'), 'touch': forced['gl'].get('touch'), 'qk': forced['gl'].get('qk')})
    return runs


def check_row(row):
    enemies = (row.get('enemies') or {}).get('p50', 0)
    if enemies < 50:
        raise SystemExit('на кадре меньше 50 врагов рейда: ' + json.dumps(summarize(row), ensure_ascii=False))
    if not row['okShots']:
        print('ПРЕДУПРЕЖДЕНИЕ: выстрелы не сошлись с числом турелей', json.dumps(summarize(row), ensure_ascii=False))


def main():
    if not CHROME:
        raise SystemExit('не найден Chrome/Chromium, задайте TERRA_CHROMIUM')
    if not server_up():
        raise SystemExit('нет сервера на ' + URL + ' — запустите python3 -m http.server 8080')
    OUT.mkdir(parents=True, exist_ok=True)
    backends = ['swiftshader'] if QUICK else ['swiftshader', 'angle']
    all_runs = []
    with sync_playwright() as p:
        for kind in backends:
            browser = p.chromium.launch(executable_path=CHROME, headless=True, args=launch_args(kind) + [
                '--disable-dev-shm-usage', '--no-first-run', '--mute-audio',
            ])
            context = browser.new_context(
                viewport=VIEW, device_scale_factor=2, is_mobile=True, has_touch=True,
                user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
            )
            page = context.new_page()
            page.set_default_timeout(60000)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            start_game(page)
            info = page.evaluate('terraTurretPerf.glInfo()')
            print(kind, 'renderer:', info.get('renderer'), 'naturalPR', info.get('pixelRatio'), 'touch', info.get('touch'), 'qk', info.get('qk'))
            if kind == 'angle' and info.get('renderer') and 'swift' in info['renderer'].lower():
                print('ANGLE отдал SwiftShader — отдельный GPU-прогон не отличается, пропускаю матрицу')
                browser.close()
                all_runs.append({'backend': 'angle', 'skipped': True, 'renderer': info.get('renderer')})
                continue
            runs = run_matrix(page, kind)
            all_runs.extend(runs)
            if kind == 'swiftshader':
                page.screenshot(path=str(OUT / 'raid-18.png'))
            if errors:
                print('PAGEERRORS', errors[:8])
            browser.close()
    payload = {'url': URL, 'seconds': SECONDS, 'warmup': WARMUP, 'quick': QUICK, 'runs': all_runs}
    dest = OUT / 'results.json'
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps(all_runs, ensure_ascii=False, indent=2))
    print('WROTE', dest)


if __name__ == '__main__':
    main()
