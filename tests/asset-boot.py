"""Focused real-browser tests for the archive loader, without WebGL/game assets.

Serves the actual boot.js and fflate vendor through tiny Playwright routes. Tests
startup ordering, responsive progress, content-addressed requests, integrity
failures and the embedded/offline path in isolated browser contexts.
"""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8137/play/'
expect.set_options(timeout=15000)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Fixture:
    def __init__(self, *, mode='valid', embedded=False, delay=False):
        self.mode, self.embedded, self.delay = mode, embedded, delay
        self.requests, self.held = [], []
        self.payloads = {
            'TERRA_TEST_A': {'label': 'hero', 'value': 7},
            'TERRA_TEST_B': {'label': 'texture', 'value': 11},
        }
        self.files = {
            name + '.json.gz': gzip.compress(json.dumps(value).encode(), mtime=0)
            for name, value in self.payloads.items()
        }
        if mode == 'invalid-gzip':
            self.files['TERRA_TEST_B.json.gz'] = b'this is not a gzip archive'
        if mode == 'invalid-json':
            self.files['TERRA_TEST_B.json.gz'] = gzip.compress(b'not valid json', mtime=0)
        self.manifest = json.dumps({'v': 1, 'groups': [
            {'name': name, 'file': name + '.json.gz', 'bytes': len(self.files[name + '.json.gz']),
             'sha256': digest(self.files[name + '.json.gz'])}
            for name in self.payloads
        ]}, separators=(',', ':')).encode()
        self.pin = digest(self.manifest)
        self.pack = {'assets/pack/manifest.json': self.manifest}
        self.pack.update({'assets/pack/' + name: raw for name, raw in self.files.items()})
        if mode == 'missing-embedded':
            del self.pack['assets/pack/TERRA_TEST_B.json.gz']
        if mode == 'corrupt-embedded':
            raw = bytearray(self.pack['assets/pack/TERRA_TEST_B.json.gz'])
            # Change MTIME only: still valid gzip/JSON of exactly the same size.
            # Length and decompression alone cannot catch this stale variant.
            raw[4] ^= 1
            self.pack['assets/pack/TERRA_TEST_B.json.gz'] = bytes(raw)

    def html(self):
        packed = ''
        if self.embedded:
            values = {name: base64.b64encode(raw).decode() for name, raw in self.pack.items()}
            packed = '<script>window.TERRA_PACK=' + json.dumps(values) + ';</script>'
        pin = '0' * 64 if self.mode == 'stale-manifest' else self.pin
        register = ('<script type="application/x-terra-module" data-terra-stage="register">'
                    'import "fixture/register";</script>') if self.embedded else (
                    '<script type="application/x-terra-module" data-terra-stage="register" src="ui/fixture-register.js"></script>')
        imports = {'imports': {
            'fixture/register': 'data:text/javascript;base64,' + base64.b64encode(self.registry().encode()).decode(),
            'fixture/dependency': 'data:text/javascript;base64,' + base64.b64encode(b'window.fixture.dependency=true;').decode(),
        }}
        return '''<!doctype html><html><head><meta charset="utf-8">
<script type="importmap">''' + json.dumps(imports) + '''</script></head><body>
<div id="terraBoot" role="status"><div><p id="terraBootMsg">Loading</p>
<div id="terraBootTrack"><i id="terraBootBar" style="display:block;width:0%"></i></div></div></div>
<script>
window.fixture={order:[],ticks:0,frames:0,fetches:[]};
setInterval(()=>fixture.ticks++,10);
(function frame(){fixture.frames++;requestAnimationFrame(frame)})();
const nativeFetch=window.fetch;
window.fetch=function(input,options){fixture.fetches.push(String(input));return nativeFetch.call(this,input,options)};
</script>''' + packed + '''
<script type="application/x-terra-main" id="terraGameBundle">
fixture.order.push('main');
if(!window.TERRA_TEST_A||!window.TERRA_TEST_B)throw Error('main evaluated before archive');
window.TERRA_START_GAME=function(){
  if(!fixture.before||!fixture.registered)throw Error('constructor ran before registration');
  fixture.order.push('construct');window.game={fixture:true};
};
</script>
<script type="application/x-terra-script" data-terra-stage="before-game">
if(window.game)throw Error('before-game ran too late');
fixture.before=true;fixture.order.push('before');
</script>
''' + register + '''
<script type="application/x-terra-script" data-terra-stage="after-game">
if(!window.game||!fixture.registered)throw Error('after-game ran too early');
fixture.after=true;fixture.order.push('after');
</script>
<script src="assets/vendor/fflate.min.js"></script>
<script src="assets/boot.js?v=fixture" data-terra-manifest-sha256="''' + pin + '''"></script>
</body></html>'''

    @staticmethod
    def registry():
        return '''
import "fixture/dependency";
if(!fixture.dependency)throw Error('module dependency was not evaluated');
if(window.game)throw Error('registry ran after constructor');
fixture.registered=true;fixture.order.push('register');
window.TERRA_STARTUP.then(()=>{if(!fixture.after)throw Error('mounted before after-game');fixture.order.push('mounted');fixture.mounted=true;});
'''

    def route(self, route):
        request = route.request
        parsed = urlparse(request.url)
        self.requests.append(request.url)
        path = parsed.path.removeprefix('/play/')
        if path == '':
            route.fulfill(status=200, content_type='text/html', body=self.html())
        elif path in ('assets/boot.js', 'assets/vendor/fflate.min.js'):
            route.fulfill(status=200, content_type='text/javascript', body=(ROOT / 'play' / path).read_bytes())
        elif path == 'ui/fixture-register.js':
            route.fulfill(status=200, content_type='text/javascript', body=self.registry())
        elif path == 'assets/pack/manifest.json':
            route.fulfill(status=200, content_type='application/json', body=self.manifest)
        elif path.startswith('assets/pack/'):
            name = path.split('/')[-1]
            if name == 'TERRA_TEST_B.json.gz' and self.delay:
                self.held.append(route)
                return
            if name == 'TERRA_TEST_B.json.gz' and self.mode == 'http-404':
                route.fulfill(status=404, body='Not found')
                return
            raw = self.files.get(name)
            if raw is None:
                route.fulfill(status=404, body='Unexpected asset')
                return
            if name == 'TERRA_TEST_B.json.gz' and self.mode == 'corrupt-group':
                changed = bytearray(raw)
                changed[4] ^= 1
                raw = bytes(changed)
            route.fulfill(status=200, content_type='application/gzip', body=raw)
        elif parsed.path == '/favicon.ico':
            route.fulfill(status=204, body='')
        else:
            route.fulfill(status=404, body='Unexpected fixture request')

    def release(self):
        self.delay = False
        for route in self.held:
            route.fulfill(status=200, content_type='application/gzip', body=self.files['TERRA_TEST_B.json.gz'])
        self.held.clear()


def open_fixture(browser, fixture, *, portable=False):
    context = browser.new_context()
    if portable:
        context.add_init_script('''
Object.defineProperty(window.crypto,'subtle',{value:undefined,configurable:true});
Object.defineProperty(window,'DecompressionStream',{value:undefined,configurable:true});
''')
    context.route('**/*', fixture.route)
    page = context.new_page()
    page.set_default_timeout(15000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL, wait_until='load')
    return context, page, errors


def check_ready(page, fixture, errors):
    try:
        page.wait_for_function('["ready","error"].includes(window.TERRA_BOOT_STATE?.status)')
    except Exception as error:
        diagnostic = page.evaluate('''() => ({state:TERRA_BOOT_STATE,order:fixture.order,
          message:document.getElementById('terraBootMsg')?.textContent,ready:document.readyState})''')
        raise AssertionError((diagnostic, errors)) from error
    status = page.evaluate('''() => ({state:TERRA_BOOT_STATE,order:fixture.order,
      message:document.getElementById('terraBootMsg')?.textContent})''')
    assert status['state']['status'] == 'ready', (status, errors)
    result = page.evaluate('''() => ({order:fixture.order,after:fixture.after,mounted:fixture.mounted,
      values:[window.TERRA_TEST_A,window.TERRA_TEST_B],fetches:fixture.fetches,game:!!window.game})''')
    assert result['order'] == ['main', 'before', 'register', 'construct', 'after', 'mounted'], result
    assert result['game'] and result['after'] and result['mounted'], result
    assert result['values'] == list(fixture.payloads.values()), result
    expect(page.locator('#terraBoot')).to_have_count(0)
    assert not errors, errors
    if fixture.embedded:
        assert not result['fetches'], result
        assert not [url for url in fixture.requests if '/assets/pack/' in url], fixture.requests
    else:
        fetched = {urlparse(url).path.split('/')[-1]: parse_qs(urlparse(url).query) for url in result['fetches']}
        assert fetched['manifest.json'] == {'v': [fixture.pin]}, fetched
        for name, raw in fixture.files.items():
            assert fetched[name] == {'v': [digest(raw)]}, fetched


with sync_playwright() as p:
    executable = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    browser = p.chromium.launch(executable_path=executable)
    fixture = Fixture(delay=True)
    context, page, errors = open_fixture(browser, fixture)
    page.wait_for_function('TERRA_BOOT_STATE.completed===1 && fixture.ticks>=5 && fixture.frames>=2')
    pending = page.evaluate('''() => ({width:parseFloat(document.getElementById('terraBootBar').style.width),
      partial:!!window.TERRA_TEST_A||!!window.TERRA_TEST_B,game:!!window.game,order:fixture.order})''')
    assert 0 < pending['width'] < 100 and not pending['partial'] and not pending['game'] and not pending['order'], pending
    expect(page.locator('#terraBootTrack')).to_have_attribute('role', 'progressbar')
    fixture.release()
    check_ready(page, fixture, errors)
    context.close()
    print('PASS async progress/timer/rAF, atomic archive publication, ordered registration/startup, SHA-versioned requests', flush=True)

    for portable in [False, True]:
        fixture = Fixture(embedded=True)
        context, page, errors = open_fixture(browser, fixture, portable=portable)
        check_ready(page, fixture, errors)
        if portable:
            assert page.evaluate('!crypto.subtle && typeof DecompressionStream==="undefined"')
        context.close()
        print('PASS embedded archive without fetch' + ('; portable SHA256 + async fflate fallback' if portable else ''), flush=True)

    cases = [
        ('http-404', False, 'network'), ('corrupt-group', False, 'integrity'),
        ('stale-manifest', False, 'integrity'), ('invalid-gzip', False, 'integrity'),
        ('invalid-json', False, 'integrity'), ('missing-embedded', True, 'missing'),
        ('corrupt-embedded', True, 'integrity'),
    ]
    for mode, embedded, code in cases:
        fixture = Fixture(mode=mode, embedded=embedded)
        context, page, errors = open_fixture(browser, fixture)
        page.wait_for_function('window.TERRA_BOOT_STATE?.status==="error"')
        # Other download/decode workers must not overwrite the error message.
        page.wait_for_timeout(150)
        result = page.evaluate('''() => ({code:TERRA_BOOT_STATE.error.code,game:!!window.game,
          partial:!!window.TERRA_TEST_A||!!window.TERRA_TEST_B,order:fixture.order,
          text:document.getElementById('terraBootMsg').textContent})''')
        assert result['code'] == code and not result['game'] and not result['partial'] and not result['order'], result
        assert 'Поднимаем архив' not in result['text'], result
        expect(page.locator('#terraBoot')).to_have_attribute('role', 'alert')
        retry = page.get_by_role('button', name='Повторить загрузку')
        expect(retry).to_be_visible()
        if embedded:
            assert not page.evaluate('fixture.fetches'),fixture.requests
        assert not errors, errors
        if mode == 'http-404':
            fixture.mode = 'valid'
            retry.click()
            check_ready(page, fixture, errors)
        context.close()
        print('PASS', mode, 'fails before game/partial globals; alert and retry' + (' recover' if mode == 'http-404' else ''), flush=True)
    browser.close()
    print('PASS asset boot: focused Chromium fixtures, no WebGL or full assets', flush=True)
