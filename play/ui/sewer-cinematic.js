/* A staged recording, not the unfinished Raphael boss/model. No save writes. */
export function showRecording(game, message) {
  if (game.state !== 'play' || document.getElementById('sewerRecording')) return;
  const owner = game.p, previousFocus = document.activeElement;
  const frames = [
    ['АГИ · ПАДЕНИЕ СЕТЕЙ', 'Города гасли по одному. За приказами машин пришла эпидемия. Внизу остались только следы тех, кто пытался удержать проход.'],
    ['ПОСЛЕДНИЙ ИЗ КЛАНА', message],
    ['ЮЖНЫЙ КОЛЛЕКТОР · СЛЕД ПРОДОЛЖАЕТСЯ', 'У стены — красная ткань и две глубокие борозды. Крысы не боятся этого места. Самого охотника здесь уже нет.'],
  ];
  const root = document.createElement('section');
  root.id = 'sewerRecording';
  root.setAttribute('role', 'dialog');
  root.setAttribute('aria-modal', 'true');
  root.setAttribute('aria-labelledby', 'recordingTitle');
  root.innerHTML = '<div class="recordingLetterbox"></div><div class="recordingCard scroll"><small>НАЙДЕННАЯ ЗАПИСЬ · ЮЖНЫЙ КОЛЛЕКТОР</small><h2 id="recordingTitle"></h2><p id="recordingText"></p><div class="recordingControls"><span id="recordingStep"></span><button type="button" id="recordingSkip">Пропустить</button><button type="button" id="recordingNext">Далее</button></div></div><div class="recordingLetterbox"></div>';
  const clearInput = () => {
    game.keys?.clear();
    if (game.mouse) game.mouse.down = false;
    game.meleeRelease?.(true);
    for (const [stick,id] of [[game.stL,'stickL'],[game.stR,'stickR']]) {
      if (stick) Object.assign(stick,{on:false,x:0,y:0,id:-1});
      const element=document.getElementById(id);if(element)element.style.display='none';
    }
  };
  clearInput();
  game.state = 'modal';
  document.body.append(root);
  let frame=0, closed=false;
  const next=root.querySelector('#recordingNext');
  function draw() {
    root.querySelector('#recordingTitle').textContent=frames[frame][0];
    root.querySelector('#recordingText').textContent=frames[frame][1];
    root.querySelector('#recordingStep').textContent=`${frame+1} / ${frames.length}`;
    next.textContent=frame===frames.length-1?'В тоннель':'Далее';
  }
  function close(restore=true) {
    if(closed)return;
    closed=true;clearInterval(lifecycle);window.removeEventListener('keydown',keyboard,true);root.remove();
    if(restore && game.p===owner && game.state==='modal') {
      clearInput();game.state='play';
      if(previousFocus?.isConnected)previousFocus.focus({preventScroll:true});
    }
  }
  function keyboard(event) {
    if(event.key==='Escape'){event.preventDefault();event.stopImmediatePropagation();close();}
    else if(event.key==='Tab') {
      event.preventDefault();event.stopImmediatePropagation();
      const buttons=[root.querySelector('#recordingSkip'),next];
      const i=buttons.indexOf(document.activeElement);
      buttons[(i+(event.shiftKey?-1:1)+buttons.length)%buttons.length].focus();
    }
  }
  root.querySelector('#recordingSkip').onclick=()=>close();
  next.onclick=()=>{if(game.p!==owner)return close(false);if(++frame===frames.length)close();else draw();};
  window.addEventListener('keydown',keyboard,true);
  const lifecycle=setInterval(()=>{if(game.p!==owner||game.state!=='modal')close(false);},100);
  draw();next.focus();
  return {close};
}
