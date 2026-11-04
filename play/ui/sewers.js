import { showRecording } from './sewer-cinematic.js';
/* First sewer sector. Reuses protected native entrances and container persistence.
 * Pump state is per expedition; no new save schema or unique reward writes here.
 */
export const CELLS = [[0,0],[1,0],[1,1],[2,1],[2,2],[3,2],[3,3]];
export const ENTRANCE = {x:12,z:-10,kind:'metro',name:'Канализация · Южный коллектор',sewer:true};
export const LORE = [
  ['Журнал насосной', 'После начала AGI города теряли энергосети один за другим. Коллектор стал убежищем. Не открывайте нижнюю камеру, пока работают аварийные сбросы.'],
  ['Перехват «Ambrala»', 'Непроверенная запись из архива AGI: секретная лаборатория Ambrala в Китае фигурирует в приказе о выпуске вируса. Для подтверждения нужны другие свидетельства кампании.'],
  ['Последний из клана', '«Некоторые звали меня черепашкой-ниндзя. Я — Рафаэль. AGI забрал моих братьев и учителя. Из зелёных пиццеедов остался я. Крыс не трогай: они знают эти тоннели лучше людей». Впереди следы двух саев и красная ткань.'],
  ['Сигнал на Москву', 'Северный ретранслятор всё ещё посылает машинные команды. Чем ближе к Москве, тем чаще в сводках встречаются патрульные роботы и холодное неоновое свечение. Маршрут в этот сектор пока не открыт.'],
];
export function installSewers(game, bridge = window.TERRA_SEWER_BRIDGE) {
  if (!bridge?.Chunk || game.sewers) return;
  let pumps = new Set(), currentPlayer = null, currentDungeon = null, seen = new Set();
  const active = () => game.dg?.sewer === true;
  const center = index => {
    const [i,j] = CELLS[index];
    return {x:game.dg.ch.cx*48+i*16+8,z:game.dg.ch.cz*48+j*16+8};
  };
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
  };
  const transition = game.runDungeonTransition;
  game.runDungeonTransition = function(descriptor, ...args) {
    if (descriptor?.name===ENTRANCE.name) Object.assign(descriptor,{theme:'metro',sewer:true,flood:false,boss:null});
    return transition.call(this,descriptor,...args);
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
  layer.innerHTML='<div class="win"><h2>КАНАЛИЗАЦИЯ <button type="button" class="x" aria-label="Закрыть подземную карту">×</button></h2><p>Южный коллектор · подземный слой</p><div id="sewerRoute"></div><p class="sewerHelp">Вход: 12, −10. Спускайтесь у люка на поверхности. Два насоса снижают давление воды до конца вылазки. Возврат — по лестнице в первом секторе.</p><div id="sewerJournal"></div></div>';
  layer.querySelector('.win').classList.add('scroll');
  document.body.append(layer);
  function renderMap() {
    const route=layer.querySelector('#sewerRoute');route.replaceChildren();
    CELLS.forEach(([x,z],i)=>{
      const cell=document.createElement('div');cell.className='sewerCell';cell.style.gridColumn=String(x+1);cell.style.gridRow=String(z+1);
      cell.textContent=i===0?'↑ Выход':[1,3].includes(i)?`Насос ${pumps.has(i)?'✓':'○'}`:i===6?'След Рафаэля':`Тоннель ${i}`;
      route.append(cell);
    });
    const journal=layer.querySelector('#sewerJournal');journal.replaceChildren();
    for (const [index,[title,text]] of LORE.entries()) {if(index && !seen.has([0,3,6,6][index]))continue;const d=document.createElement('details'),s=document.createElement('summary'),p=document.createElement('p');s.textContent=title;p.textContent=text;d.append(s,p);journal.append(d);}
  }
  function closeMap(){layer.classList.add('hidden');mapButton.focus();}
  const mapButton=document.createElement('button');mapButton.type='button';mapButton.className='campButton';mapButton.id='sewerLayerButton';mapButton.textContent='Подземный слой · канализация';
  mapButton.onclick=()=>{if(game.state!=='modal')return;renderMap();layer.classList.remove('hidden');layer.querySelector('.x').focus();};
  document.querySelector('#wmGrip').after(mapButton);
  layer.querySelector('.x').onclick=closeMap;
  layer.addEventListener('keydown',e=>{if(e.key==='Tab'){const buttons=[...layer.querySelectorAll('button,summary')];const n=buttons.indexOf(document.activeElement);if(e.shiftKey&&n<=0){e.preventDefault();buttons.at(-1)?.focus();}else if(!e.shiftKey&&n===buttons.length-1){e.preventDefault();buttons[0]?.focus();}}if(e.key==='Escape'){e.preventDefault();e.stopPropagation();closeMap();}});
  window.addEventListener('keydown',e=>{if(!layer.classList.contains('hidden')&&e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();closeMap();}},true);
  let nearby=null;
  function useAction() {
    if(game.state!=='play'||game.dungeonTransition||!nearby)return false;
    if(nearby==='entry') {if(!game.world.inDungeon&&Math.hypot(game.p.x-ENTRANCE.x,game.p.z-ENTRANCE.z)<2.6)game.useEntrance({...ENTRANCE});return true;}
    if(!active())return false;
    const i=nearby,c=center(i);
    if(Math.hypot(game.p.x-(c.x+4),game.p.z-c.z)>2.6)return false;
    pumps.add(i);game.ui.toast('Насос включён · давление снижено');return true;
  }
  action.addEventListener('pointerdown',e=>{e.preventDefault();e.stopPropagation();useAction();});
  action.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key))e.stopPropagation();});
  action.addEventListener('click',e=>{if(e.detail===0)useAction();});
  const interact=game.interact;game.interact=function(...args){return useAction()||interact.apply(this,args);};
  const dungeonUpdate=game.dungeonUpdate;
  game.dungeonUpdate=function(dt) {
    if(!active())return dungeonUpdate.call(this,dt);
    if(currentDungeon!==this.dg){currentDungeon=this.dg;pumps=new Set();seen=new Set();}
    for(let i=0;i<CELLS.length;i++){
      const c=center(i);if(Math.hypot(this.p.x-c.x,this.p.z-c.z)>6||seen.has(i))continue;
      seen.add(i);
      if(i===6)showRecording(this,LORE[2][1]);
      else if(i>0){for(let n=0;n<2;n++)this.spawnEnemy('zombie',c.x-2+n*4,c.z,{force:1,aggro:1});}
    }
    // Sewage slows traversal; both pumps clear the channel for this expedition.
    this.dg.flood=pumps.size<2 && CELLS.some((_,i)=>{const c=center(i);return Math.abs(this.p.x-c.x)<1.6&&Math.abs(this.p.z-c.z)<8;});
  };
  setInterval(()=>{
    if(!game.p)return;
    if(currentPlayer!==game.p){currentPlayer=game.p;pumps=new Set();seen=new Set();}
    group.visible=!game.world.inDungeon;
    if(group.visible)group.position.y=(window.TERRA_H?.(ENTRANCE.x,ENTRANCE.z)||0)+.04;
    nearby=null;
    if(game.state!=='modal')layer.classList.add('hidden');
    if(game.state==='play'&&!game.dungeonTransition){
      if(!game.world.inDungeon&&Math.hypot(game.p.x-ENTRANCE.x,game.p.z-ENTRANCE.z)<2.6){nearby='entry';action.textContent='Спуститься · канализация [E]';}
      if(active())for(const i of [1,3]){const c=center(i);if(!pumps.has(i)&&Math.hypot(game.p.x-c.x-4,game.p.z-c.z)<2.6){nearby=i;action.textContent='Включить насос [E]';}}
    }
    action.hidden=nearby===null;
  },150);
  game.sewers={get pumps(){return [...pumps]},active,openMap:mapButton.onclick};
}
