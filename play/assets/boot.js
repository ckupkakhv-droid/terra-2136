/* Классический скрипт: синхронно собирает window.TERRA_* до игрового бандла.
   Так load срабатывает уже с архивом, и первый кадр не остаётся без текстур.
   Офлайн-сборка кладёт байты в window.TERRA_PACK, сеть не нужна. */
(function () {
  var msg = document.getElementById('terraBootMsg');
  var bar = document.getElementById('terraBootBar');

  function say(text) {
    if (msg) msg.textContent = text;
  }

  function fail(text) {
    say(text);
    if (bar) bar.style.width = '0%';
    throw new Error(text);
  }

  function paint(got, total) {
    var pct = total ? Math.min(100, Math.round(got / total * 100)) : 0;
    if (bar) bar.style.width = pct + '%';
    say('Поднимаем архив «ТЕРРА-1»… ' + pct + '%');
  }

  function bytesFromBinaryString(text) {
    var out = new Uint8Array(text.length);
    for (var i = 0; i < text.length; i++) out[i] = text.charCodeAt(i) & 255;
    return out;
  }

  function bytesFromBase64(data) {
    return bytesFromBinaryString(atob(data));
  }

  function loadBytes(url) {
    var packed = window.TERRA_PACK && window.TERRA_PACK[url];
    if (typeof packed === 'string') return bytesFromBase64(packed);
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, false);
    try { xhr.overrideMimeType('text/plain; charset=x-user-defined'); } catch (e) {}
    xhr.send(null);
    if (!(xhr.status === 200 || (xhr.status === 0 && xhr.responseText))) {
      fail('Архив не открылся (' + url + '). Запустите игру через сервер, не как одиночный файл.');
    }
    return bytesFromBinaryString(xhr.responseText);
  }

  if (!window.fflate || typeof window.fflate.gunzipSync !== 'function') {
    fail('Нечем распаковать архив.');
  }

  say('Ищем архив капсулы…');
  var manifestBytes = loadBytes('assets/pack/manifest.json');
  var manifest = JSON.parse(new TextDecoder().decode(manifestBytes));
  if (!manifest || !manifest.groups || !manifest.groups.length) fail('Опись архива пуста.');
  var total = 0;
  for (var i = 0; i < manifest.groups.length; i++) total += manifest.groups[i].bytes || 0;
  var got = 0;
  paint(0, total || 1);
  for (var g = 0; g < manifest.groups.length; g++) {
    var group = manifest.groups[g];
    var bytes = loadBytes('assets/pack/' + group.file);
    if (group.bytes && bytes.byteLength !== group.bytes) fail(group.name + ': размер не сошёлся');
    var text = new TextDecoder().decode(window.fflate.gunzipSync(bytes));
    window[group.name] = JSON.parse(text);
    got += bytes.byteLength;
    paint(got, total || got);
  }
  var boot = document.getElementById('terraBoot');
  if (boot) boot.remove();
})();
