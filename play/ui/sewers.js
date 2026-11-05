import { installSewerRats } from './sewer-rats.js';
import { drawSewerMap } from './sewer-map.js';
import { installSewerReward } from './sewer-reward.js';
import { installRaphael } from './sewer-raphael.js';
import { showRecording } from './sewer-cinematic.js';
import { installMoscowSignal } from './moscow-signal.js';
import { installMoscowScout } from './moscow-scout.js';
import { installSewerNavigation } from './sewer-navigation.js';
import { buildSewerLab, LAB_TERMINAL } from './sewer-lab.js';
import { installMetroTransition, installMetroMarkers } from './metro-entrance.js';
/* First sewer sector. Reuses protected native entrances and container persistence.
 * Pump state is per expedition; no new save schema or unique reward writes here.
 */
export const CELLS = [[0,0],[1,0],[1,1],[2,1],[2,2],[3,2],[3,3]];
export const ENTRANCE = {x:12,z:-10,kind:'metro',name:'Канализация · Южный коллектор',sewer:true};
const RAPHAEL_LINE = '«Некоторые звали меня черепашкой-ниндзя. Я — Рафаэль. AGI забрал моих братьев и учителя. Из зелёных пиццеедов остался я. Крыс не трогай: они знают эти тоннели лучше людей».';
export const LORE = [
  ['Журнал насосной', 'После начала AGI города теряли энергосети один за другим. Коллектор стал убежищем. Не открывайте нижнюю камеру, пока работают аварийные сбросы.'],
  ['Перехват «Ambrala»', 'Объект 7 · НИИ «Полынь». Российский филиал Ambrala исследовал штамм «Полынь-7». В журнале сохранился приказ AGI о выпуске вируса из секретной лаборатории в Китае. Местный узел принимал те же команды. Следующие записи ведут к московскому контуру.'],
  ['Последний из клана', `${RAPHAEL_LINE} Впереди следы двух саев и красная ткань.`],
  ['Сигнал на Москву', 'Северный ретранслятор всё ещё посылает машинные команды. Чем ближе к Москве, тем чаще в сводках встречаются патрульные роботы и холодное неоновое свечение. Маршрут в этот сектор пока не открыт.'],
];
export function installSewers(game, bridge = window.TERRA_SEWER_BRIDGE) {
  if (!bridge?.Chunk || game.sewers) return;
  const reward=installSewerReward(game,bridge), raphael=installRaphael(game,bridge), rats=installSewerRats(game);
  const moscowScout=installMoscowScout(game);
  const moscowSignal=installMoscowSignal(game,()=>moscowScout.start(),()=>moscowScout.engaged);
  let pumps = new Set(), currentPlayer = null, currentDungeon = null, seen = new Set(), warnedLocked=false;
  let lab = null;
  const labForCols = new WeakMap();
  function syncLab() {
    const next = game.dg?.sewer && game.world.inDungeon ? labForCols.get(game.dg.ch.cols) : null;
    if (lab !== next) { lab?.removeFromParent(); lab = next || null; }
    if (!lab) return;
    if (lab.parent !== game.world.scene) game.world.scene.add(lab);
    const distance = Math.hypot(game.p.x-lab.position.x,game.p.z-lab.position.z);
    lab.visible = distance < 30;
    for (const child of lab.children) if (child.isLight) child.visible = distance < 22;
  }
  const active = () => game.dg?.sewer === true;
  const center = index => {
    const [i,j] = CELLS[index];
    return {x:game.dg.ch.cx*48+i*16+8,z:game.dg.ch.cz*48+j*16+8};
  };
  const navigation=installSewerNavigation(game,{active,pumps:()=>pumps,center,boss:()=>raphael.enemy});
  const originalDungeon = bridge.Chunk.prototype.dungeon;
  bridge.Chunk.prototype.dungeon = function(theme, ...args) {
    if (theme !== 'metro' || args[0] !== '12,-10') return originalDungeon.call(this, theme, ...args);
    const {s,ox,oz} = this;
    this.d='dungeon'; this.inDg=true; this.rooms=[];
    for (let k=0;k<CELLS.length;k++) {
      const [i,j]=CELLS[k], x=ox+i*16+8,z=oz+j*16+8;
      this.rooms.push({x,z,i,j,start:k===0,boss:false});
      s.box(x,-.08,z,16,.16,16,'#303c36');
      s.box(x,.01,z,3,.02,14,'#24453c');
      for (const dx of [-3.6,3.6]) {
        s.box(x+dx,.1,z,3,.2,15,'#596058');
        s.add(bridge.shapes.cyl,x+dx,2.5,z,.18,15,.18,'#735d43',0,Math.PI/2);
      }
      const neighbors=CELLS.filter(([a,b])=>Math.abs(a-i)+Math.abs(b-j)===1);
      for (const [dx,dz] of [[0,-1],[0,1],[-1,0],[1,0]]) {
        const open=neighbors.some(([a,b])=>a===i+dx&&b===j+dz);
        if (!open) {
          s.box(x+dx*8,0,z+dz*8,dx?.4:16,3.4,dz?.4:16,'#46514c');
          this.col(x+dx*8-(dx?.2:8),z+dz*8-(dz?.2:8),x+dx*8+(dx?.2:8),z+dz*8+(dz?.2:8),3.4);
        }
      }
      for (const dz of [-6,6]) s.box(x,2.8,z+dz,15,.2,.25,'#343b37');
      if ([1,3].includes(k)) {
        s.box(x+4,.2,z,1.4,1.3,1.2,'#567567');
        s.add(bridge.shapes.sph,x+4,1.6,z,.6,.16,.6,'#b78745');
      }
      if (k===0) {this.ents.push({x,z:z-4,kind:'exit',name:'Лестница на поверхность'});s.box(x,.04,z-4,2,.04,2,'#8fbba2');}
      if (k>0 && k<6) this.cont(x-4,z+3,'toolbox');
    }
    this.poi={x:ox+8,z:oz+8};
    this.bld.push({x0:ox,z0:oz,x1:ox+64,z1:oz+64});
    const labGroup = buildSewerLab(this,game,bridge);
    // World.build copies selected Chunk fields but keeps the collider array.
    if (labGroup) labForCols.set(this.cols,labGroup);
  };
  const transition = game.runDungeonTransition;
  game.runDungeonTransition = function(descriptor, ...args) {
    if (descriptor?.name===ENTRANCE.name && descriptor.key==='12,-10' && descriptor.seed==='12,-10' && descriptor.theme==='metro') Object.assign(descriptor,{theme:'metro',sewer:true,flood:false,boss:null});
    return transition.call(this,descriptor,...args);
  };
  installMetroTransition(game);
  installMetroMarkers(game);
  const useEntrance=game.useEntrance;
  game.useEntrance=function(entry,...args) {
    const ours=entry?.name===ENTRANCE.name&&entry.x===ENTRANCE.x&&entry.z===ENTRANCE.z&&['metro','sewer'].includes(entry.kind);
    if(!ours)return useEntrance.call(this,entry,...args);
    if(this.p.dungeonAttempt?.status==='active'){this.ui.toast('Сначала завершите текущую вылазку в глубины у её входа');return false;}
    if(this._coopGuest||this.net?.role){this.ui.toast('Коллектор доступен в одиночной игре');return false;}
    if(Math.hypot(this.p.x-entry.x,this.p.z-entry.z)>=2.6||this.world.segHit(this.p.x,this.p.z,entry.x,entry.z,1.1)>=0)return false;
    // A collector has no procedural depth ladder. Keep native lease/transition
    // checks, but do not offer metro depth attempts after its one-time boss.
    return useEntrance.call(this,{...entry,kind:'sewer'},...args);
  };
  const refresh = game.world.refreshLists;
  game.world.refreshLists = function(...args) {
    const result=refresh.apply(this,args);
    if (!this.inDungeon && !this.ents.some(e=>e.sewer)) this.ents.push({...ENTRANCE});
    return result;
  };
  game.world.refreshLists();
  const group=new bridge.Group(), material=new bridge.Material({color:0x698975,roughness:.85});
  const marker=new bridge.Mesh(new bridge.Sphere(1,16,8),material);
  marker.scale.set(1.1,.07,1.1);group.add(marker);group.position.set(ENTRANCE.x,0,ENTRANCE.z);
  game.world.scene.add(group);
  const action=document.createElement('button');action.id='sewerAction';action.type='button';action.hidden=true;document.body.append(action);
  const layer=document.createElement('section');layer.id='sewerMap';layer.className='modal hidden';layer.setAttribute('role','dialog');layer.setAttribute('aria-modal','true');layer.setAttribute('aria-label','Канализация · подземный слой');
  layer.innerHTML='<div class="win"><h2>КАНАЛИЗАЦИЯ <button type="button" class="x" aria-label="Закрыть подземную карту">×</button></h2><p>Южный коллектор · одиночная вылазка</p><div id="moscowRoute"></div><div id="sewerRoute"></div><p class="sewerHelp">Опасность: заражённые и особый охотник. Вход: 12, −10. Спускайтесь у люка на поверхности. Два насоса снижают давление воды до конца вылазки. Возврат — по лестнице в первом секторе.</p><div id="sewerJournal"></div></div>';
  layer.querySelector('.win').classList.add('scroll');
  const nativeMap=document.getElementById('wmap');
  nativeMap.querySelector('.win').append(layer);
  let mapContext=null;
  function renderMap() {
    let playerIndex=-1;
    if(active()) {
      let distance=Infinity;
      CELLS.forEach((_,i)=>{const p=center(i),d=Math.hypot(game.p.x-p.x,game.p.z-p.z);if(d<distance){playerIndex=i;distance=d;}});
      if(distance>12)playerIndex=-1;
    }
    drawSewerMap(layer.querySelector('#sewerRoute'),CELLS,{seen,pumps,playerIndex});
    const journal=layer.querySelector('#sewerJournal');journal.replaceChildren();
    for (const [index,[title,text]] of LORE.entries()) {if(index && !seen.has([0,2,6,6][index]))continue;const d=document.createElement('details'),s=document.createElement('summary'),p=document.createElement('p');s.textContent=title;p.textContent=text;d.append(s,p);journal.append(d);}
    const moscowRoute=layer.querySelector('#moscowRoute');moscowRoute.replaceChildren();
    if(moscowSignal.eligible()) {
      const d=document.createElement('details'),s=document.createElement('summary'),p=document.createElement('p');
      s.textContent='Московский перехват';
      p.textContent='Проверьте Радиопост Ноль к югу от стартовой области, в районе X≈24, Z≈124. Точное положение зависит от местности. У старого ящика можно повторно прочитать перехват.';
      d.append(s,p);moscowRoute.append(d);
    }
  }
  function closeMap(restoreFocus=true) {
    const context=mapContext;mapContext=null;
    layer.classList.add('hidden');
    if(context)for(const [element,inert] of context.surfaces)element.inert=inert;
    if(restoreFocus&&context?.player===game.p&&game.state==='modal'&&!nativeMap.classList.contains('hidden'))mapButton.focus();
  }
  const mapButton=document.createElement('button');mapButton.type='button';mapButton.className='campButton';mapButton.id='sewerLayerButton';mapButton.textContent='Подземный слой · канализация';
  mapButton.onclick=()=>{
    if(game.state!=='modal'||nativeMap.classList.contains('hidden')||mapContext)return;
    mapContext={player:game.p,surfaces:[...nativeMap.querySelectorAll('#wmBody,#wmTop')].map(element=>[element,element.inert])};
    for(const [element] of mapContext.surfaces)element.inert=true;
    renderMap();layer.classList.remove('hidden');layer.querySelector('.x').focus();
  };
  document.querySelector('#wmGrip').after(mapButton);
  layer.querySelector('.x').onclick=closeMap;
  window.addEventListener('keydown',event=>{
    if(!mapContext)return;
    if(mapContext.player!==game.p||game.state!=='modal'||nativeMap.classList.contains('hidden')){closeMap(false);return;}
    event.stopImmediatePropagation();
    if(event.key==='Escape'){event.preventDefault();closeMap();}
    else if(event.key==='Tab') {
      event.preventDefault();
      const targets=[...layer.querySelectorAll('button,summary')].filter(element=>element.getClientRects().length);
      const index=targets.indexOf(document.activeElement);
      targets[(index+(event.shiftKey?-1:1)+targets.length)%targets.length]?.focus();
    }
  },true);
  let nearby=null;
  function nearTerminal() {
    if (!active() || !lab?.parent || !lab.visible) return false;
    const c=center(2),x=c.x+LAB_TERMINAL.x,z=c.z+LAB_TERMINAL.z;
    return Math.hypot(game.p.x-x,game.p.z-z)<2.2 &&
      game.world.segHit(game.p.x,game.p.z,x,z,1.8)<0;
  }
  function useAction() {
    if(game.state!=='play'||game.dungeonTransition||!nearby)return false;
    if(nearby==='entry') {if(!game.world.inDungeon&&Math.hypot(game.p.x-ENTRANCE.x,game.p.z-ENTRANCE.z)<2.6)game.useEntrance({...ENTRANCE});return true;}
    if(!active())return false;
    if(nearby==='terminal') {
      if (!nearTerminal()) return false;
      showRecording(game,'',{
        presentation:'terminal',
        heading:'ОБЪЕКТ 7 · АВАРИЙНЫЙ ТЕРМИНАЛ',skipLabel:'Закрыть',finishLabel:'Отойти от терминала',
        frames:[
          ['ПОСЛЕДНЯЯ СМЕНА','На тусклом экране остался журнал российского филиала Ambrala: «Объект 7 · НИИ „Полынь“». Статус гермозоны — нарушен. Рядом с клавиатурой засохли следы бирюзового раствора.'],
          ['ПРИКАЗ AGI',LORE[1][1]],
          ['ЧУЖОЙ СЛЕД','Архив заканчивается записью дежурного: «Кто-то вскрыл нижний шлюз двумя клинками. Не стрелять в крыс. Если услышите шаги — уйдите с лотка». Сначала включите оба насоса; охотник скрывается за водосбросом.'],
        ],
      });
      return true;
    }
    const i=nearby,c=center(i);
    if(Math.hypot(game.p.x-(c.x+4),game.p.z-c.z)>2.6)return false;
    pumps.add(i);game.ui.toast('Насос включён · давление снижено');return true;
  }
  action.addEventListener('pointerdown',e=>{
    e.stopPropagation();
    // Reading opens a modal on completed activation, after the touch releases.
    if(nearby!=='terminal'){e.preventDefault();useAction();}
  });
  action.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key))e.stopPropagation();});
  action.addEventListener('click',e=>{e.stopPropagation();if(e.detail===0||nearby==='terminal')useAction();});
  const interact=game.interact;game.interact=function(...args){return useAction()||interact.apply(this,args);};
  const dungeonUpdate=game.dungeonUpdate;
  game.dungeonUpdate=function(dt) {
    if(!active()){rats.clear();return dungeonUpdate.call(this,dt);}
    const ratChamber=center(6);
    if(Math.hypot(this.p.x-ratChamber.x,this.p.z-ratChamber.z)<28)rats.update(dt,ratChamber);else rats.clear();
    if(currentDungeon!==this.dg){currentDungeon=this.dg;pumps=new Set();seen=new Set();warnedLocked=false;}
    for(let i=0;i<CELLS.length;i++){
      const c=center(i);if(Math.hypot(this.p.x-c.x,this.p.z-c.z)>6||seen.has(i))continue;
      if(i===6) {
        if(pumps.size<2){if(!warnedLocked){warnedLocked=true;this.ui.toast('Охотник скрыт за сбросами · включите оба насоса');}continue;}
        if(this.defeated?.[this.dg.key]){seen.add(i);continue;}
        if(!reward?.canSpawn())continue;
        const enemy=raphael.spawn(c.x,c.z+3);
        if(!enemy)continue;
        seen.add(i);
        showRecording(this,LORE[2][1],{
          subject:enemy,
          heading:'ВСТРЕЧА · ПОСЛЕДНИЙ ИЗ КЛАНА',skipLabel:'К бою',finishLabel:'Начать бой',
          frames:[
            ['ШАГИ ЗА ВОДОСБРОСОМ','Насосы смолкли. Из темноты выходит мутант в красной повязке. В руках — два сая. За его спиной шевелятся тени крыс.'],
            ['РАФАЭЛЬ',RAPHAEL_LINE],
            ['НЕ ТРОГАЙ КРЫС','Охотник перекрывает проход. Красные кольца предупреждают об ударе и рывке. Отойдите с линии атаки и бейте, пока он восстанавливается. Награда ждёт в сундуке после победы.'],
          ],
        });
      }
      else if(i>0){for(let n=0;n<2;n++)this.spawnEnemy('zombie',c.x-2+n*4,c.z,{force:1,aggro:1});}
      seen.add(i);
    }
    // Sewage slows traversal; both pumps clear the channel for this expedition.
    this.dg.flood=pumps.size<2 && CELLS.some((_,i)=>{const c=center(i);return Math.abs(this.p.x-c.x)<1.6&&Math.abs(this.p.z-c.z)<8;});
  };
  function updateSurfaceUI() {
    if(!game.p)return;
    syncLab();
    moscowScout.check();
    moscowSignal.update();
    navigation.sync();
    if(currentPlayer!==game.p){currentPlayer=game.p;pumps=new Set();seen=new Set();}
    group.visible=!game.world.inDungeon&&Math.hypot(game.p.x-ENTRANCE.x,game.p.z-ENTRANCE.z)<40;
    if(!active())rats.clear();
    if(group.visible)group.position.y=(window.TERRA_H?.(ENTRANCE.x,ENTRANCE.z)||0)+.04;
    nearby=null;
    if(mapContext&&(game.state!=='modal'||game.p!==mapContext.player||nativeMap.classList.contains('hidden')))closeMap(false);
    if(game.state==='play'&&!game.dungeonTransition){
      if(!game.world.inDungeon&&Math.hypot(game.p.x-ENTRANCE.x,game.p.z-ENTRANCE.z)<2.6){nearby='entry';action.textContent='Спуститься · канализация [E]';}
      if(active())for(const i of [1,3]){const c=center(i);if(!pumps.has(i)&&Math.hypot(game.p.x-c.x-4,game.p.z-c.z)<2.6){nearby=i;action.textContent='Включить насос [E]';}}
      if(nearTerminal()){nearby='terminal';action.textContent='Прочитать терминал [E]';}
    }
    if(action.hidden!==(nearby===null))action.hidden=nearby===null;
  }
  const loop=game.loop;let lastUI=-Infinity;
  game.loop=function(time){const result=loop.call(this,time);if(time-lastUI>=150){lastUI=time;updateSurfaceUI();}return result;};
  updateSurfaceUI();
  game.sewers={get pumps(){return [...pumps]},get ratCount(){return rats.count},active,openMap:mapButton.onclick};
}
