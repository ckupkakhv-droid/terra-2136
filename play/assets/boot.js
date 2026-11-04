/* Verified asynchronous archive boot. Registration precedes native save loading.
 * Offline terra.html provides the same compressed bytes through TERRA_PACK. */
(function () {
  'use strict';
  if (window.TERRA_BOOT_STATE) return;
  var expectedManifest = document.currentScript?.dataset.terraManifestSha256;
  var state = window.TERRA_BOOT_STATE = {status:'loading',received:0,total:0,completed:0,groups:0};
  var msg = document.getElementById('terraBootMsg'), bar = document.getElementById('terraBootBar');
  var resolveStartup, rejectStartup;
  window.TERRA_STARTUP = new Promise(function(resolve,reject){resolveStartup=resolve;rejectStartup=reject;});
  window.TERRA_STARTUP.catch(function(){}); // The overlay handles boot failures.
  var controller = new AbortController();
  function failure(code,resource) { var e=new Error(code+(resource?': '+resource:''));e.code=code;e.resource=resource;return e; }
  function say(text) { if(msg)msg.textContent=text; }
  function paint() {
    if(state.status==='error')return;
    var progress=(state.total?state.received/state.total*.8:0)+(state.groups?state.completed/state.groups*.2:0);
    var pct=Math.min(99,Math.round(progress*100));
    if(bar){bar.style.animation='none';bar.style.transform='none';bar.style.width=pct+'%';
      var track=bar.parentElement;track.setAttribute('role','progressbar');track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');track.setAttribute('aria-valuenow',String(pct));}
    say('Поднимаем архив «ТЕРРА-1»… '+pct+'%');
  }
  function yieldPaint() {
    return new Promise(function(resolve){
      var finished=false,frame;
      function done(){if(finished)return;finished=true;clearTimeout(timer);if(frame)cancelAnimationFrame(frame);resolve();}
      // Allow a rendered frame before parsing the next group/main bundle, but
      // do not stall a background tab whose animation callbacks are suspended.
      var timer=setTimeout(done,50);
      frame=requestAnimationFrame(function(){setTimeout(done,0);});
    });
  }
  function bytesFromBase64(data) {
    var binary=atob(data),bytes=new Uint8Array(binary.length);
    for(var i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);return bytes;
  }
  function hex(bytes) { return Array.from(bytes,function(b){return b.toString(16).padStart(2,'0');}).join(''); }
  async function sha256(bytes) {
    if(globalThis.crypto?.subtle)return hex(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)));
    // HTTP LAN previews may lack SubtleCrypto. Standard SHA-256 with a yield
    // every MiB keeps verification available without a CDN or insecure bypass.
    var k=[1116352408,1899447441,3049323471,3921009573,961987163,1508970993,2453635748,2870763221,3624381080,310598401,607225278,1426881987,1925078388,2162078206,2614888103,3248222580,3835390401,4022224774,264347078,604807628,770255983,1249150122,1555081692,1996064986,2554220882,2821834349,2952996808,3210313671,3336571891,3584528711,113926993,338241895,666307205,773529912,1294757372,1396182291,1695183700,1986661051,2177026350,2456956037,2730485921,2820302411,3259730800,3345764771,3516065817,3600352804,4094571909,275423344,430227734,506948616,659060556,883997877,958139571,1322822218,1537002063,1747873779,1955562222,2024104815,2227730452,2361852424,2428436474,2756734187,3204031479,3329325298];
    var h=[1779033703,3144134277,1013904242,2773480762,1359893119,2600822924,528734635,1541459225];
    var padded=new Uint8Array(Math.ceil((bytes.length+9)/64)*64);padded.set(bytes);padded[bytes.length]=128;
    var view=new DataView(padded.buffer),w=new Uint32Array(64);
    view.setUint32(padded.length-8,Math.floor(bytes.length/0x20000000));view.setUint32(padded.length-4,bytes.length*8);
    function rotate(x,n){return x>>>n|x<<(32-n);}
    for(var offset=0;offset<padded.length;offset+=64){
      if(offset&&offset%1048576===0)await yieldPaint();
      for(var i=0;i<16;i++)w[i]=view.getUint32(offset+i*4);
      for(var i=16;i<64;i++){var s0=rotate(w[i-15],7)^rotate(w[i-15],18)^w[i-15]>>>3,s1=rotate(w[i-2],17)^rotate(w[i-2],19)^w[i-2]>>>10;w[i]=w[i-16]+s0+w[i-7]+s1;}
      var a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],n=h[7];
      for(var i=0;i<64;i++){var t1=n+(rotate(e,6)^rotate(e,11)^rotate(e,25))+(e&f^~e&g)+k[i]+w[i],t2=(rotate(a,2)^rotate(a,13)^rotate(a,22))+(a&b^a&c^b&c);n=g;g=f;f=e;e=d+t1|0;d=c;c=b;b=a;a=t1+t2|0;}
      h=[h[0]+a|0,h[1]+b|0,h[2]+c|0,h[3]+d|0,h[4]+e|0,h[5]+f|0,h[6]+g|0,h[7]+n|0];
    }
    return h.map(function(word){return(word>>>0).toString(16).padStart(8,'0');}).join('');
  }
  async function loadBytes(path,version,onChunk) {
    // Embedded keys never include the online content-version query.
    if(window.TERRA_PACK){
      if(typeof window.TERRA_PACK[path]!=='string')throw failure('missing',path);
      var packed=bytesFromBase64(window.TERRA_PACK[path]);if(onChunk)onChunk(packed.length);return packed;
    }
    var url=new URL(path,document.baseURI);url.searchParams.set('v',version);
    var timer=setTimeout(function(){controller.abort();},120000);
    try{
      var response=await fetch(url,{cache:path.endsWith('manifest.json')?'no-cache':'default',signal:controller.signal});
      if(!response.ok)throw failure('network',path);
      if(!response.body){var raw=new Uint8Array(await response.arrayBuffer());if(onChunk)onChunk(raw.length);return raw;}
      var reader=response.body.getReader(),chunks=[],size=0;
      while(true){var next=await reader.read();if(next.done)break;chunks.push(next.value);size+=next.value.length;if(onChunk)onChunk(next.value.length);}
      var bytes=new Uint8Array(size),at=0;for(var chunk of chunks){bytes.set(chunk,at);at+=chunk.length;}return bytes;
    }catch(error){if(error.code)throw error;throw failure('network',path);}
    finally{clearTimeout(timer);}
  }
  async function inflate(bytes) {
    if(typeof DecompressionStream==='function')return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
    if(!window.fflate||typeof fflate.gunzip!=='function')throw failure('inflate');
    return new Promise(function(resolve,reject){fflate.gunzip(bytes,function(error,raw){if(error)reject(error);else resolve(raw);});});
  }
  async function loadArchive() {
    if(!/^[a-f0-9]{64}$/.test(expectedManifest||''))throw failure('manifest');
    state.version=expectedManifest;
    var raw=await loadBytes('assets/pack/manifest.json',expectedManifest);
    if(await sha256(raw)!==expectedManifest)throw failure('integrity','manifest.json');
    var manifest;try{manifest=JSON.parse(new TextDecoder().decode(raw));}catch(_){throw failure('manifest');}
    if(manifest.v!==1||!Array.isArray(manifest.groups)||!manifest.groups.length||manifest.groups.length>128)throw failure('manifest');
    var names=new Set(),files=new Set();
    for(var group of manifest.groups){
      if(!/^TERRA_[A-Z0-9_]+$/.test(group.name)||!/^TERRA_[A-Z0-9_]+\.json\.gz$/.test(group.file)||!Number.isSafeInteger(group.bytes)||group.bytes<=0||group.bytes>=50000000||!/^[a-f0-9]{64}$/.test(group.sha256)||names.has(group.name)||files.has(group.file))throw failure('manifest');
      names.add(group.name);files.add(group.file);state.total+=group.bytes;
    }
    state.groups=manifest.groups.length;paint();
    var values=Object.create(null),cursor=0;
    async function worker(){
      while(cursor<manifest.groups.length){
        var group=manifest.groups[cursor++],path='assets/pack/'+group.file;
        var bytes=await loadBytes(path,group.sha256,function(count){state.received+=count;paint();});
        if(bytes.length!==group.bytes||await sha256(bytes)!==group.sha256)throw failure('integrity',group.file);
        try{var decoded=await inflate(bytes);await yieldPaint();values[group.name]=JSON.parse(new TextDecoder().decode(decoded));}
        catch(_){throw failure('integrity',group.file);}
        state.completed++;paint();await yieldPaint();
      }
    }
    // Bound download/decode memory on phones. Never publish a partial version.
    await Promise.all([worker(),worker(),worker()]);
    for(var name of Object.keys(values))window[name]=values[name];state.status='assets-ready';
  }
  function loadedDocument(){
    if(document.readyState==='complete')return Promise.resolve();
    return new Promise(function(resolve){window.addEventListener('load',resolve,{once:true});});
  }
  function activate(source){
    return new Promise(function(resolve,reject){
      var target=document.createElement('script'),module=source.type==='application/x-terra-module',objectURL;
      if(module)target.type='module';
      if(source.hasAttribute('src'))target.src=source.getAttribute('src');
      else if(module){objectURL=URL.createObjectURL(new Blob([source.textContent],{type:'text/javascript'}));target.src=objectURL;}
      else target.textContent=source.textContent;
      function cleanup(){if(objectURL)URL.revokeObjectURL(objectURL);}
      if(module||target.src){target.onload=function(){cleanup();resolve();};target.onerror=function(){cleanup();reject(failure('startup',source.getAttribute('src')));};}
      document.head.append(target);if(!module&&!target.src)resolve();
    });
  }
  async function start(){
    await window.TERRA_ASSETS_READY;await loadedDocument();state.status='starting';say('Архив проверен. Готовим мир…');await yieldPaint();
    var main=document.getElementById('terraGameBundle');if(!main)throw failure('startup');await activate(main);
    for(var item of document.querySelectorAll('script[data-terra-stage="before-game"]'))await activate(item);
    for(var item of document.querySelectorAll('script[data-terra-stage="register"]'))await activate(item);
    if(typeof window.TERRA_START_GAME!=='function')throw failure('startup');window.TERRA_START_GAME();if(!window.game)throw failure('startup');
    for(var item of document.querySelectorAll('script[data-terra-stage="after-game"]'))await activate(item);
    resolveStartup(window.game);await Promise.resolve();state.status='ready';document.getElementById('terraBoot')?.remove();
  }
  function showFailure(error){
    controller.abort();state.status='error';state.error={code:error.code||'startup',resource:error.resource||''};
    var overlay=document.getElementById('terraBoot');
    if(!overlay){overlay=document.createElement('div');overlay.id='terraBoot';msg=document.createElement('p');overlay.append(msg);document.body.append(overlay);}
    overlay.setAttribute('role','alert');
    say(state.error.code==='integrity'?'Архив повреждён или устарел. Повторите загрузку.':state.error.code==='network'?'Не удалось загрузить архив. Проверьте соединение и повторите.':state.error.code==='missing'?'Архив офлайн-сборки неполон. Скачайте полный файл игры.':'Не удалось подготовить игру. Обновите страницу.');
    if(bar){bar.style.animation='none';bar.style.width='0%';}
    var retry=document.createElement('button');retry.type='button';retry.textContent='Повторить загрузку';retry.className='btn';retry.onclick=function(){location.reload();};(msg.parentElement||overlay).append(retry);
    rejectStartup(error);
  }
  paint();window.TERRA_ASSETS_READY=loadArchive();start().catch(showFailure);
})();
