/* Полевой альбом: реальные жители, штатные кнопки и данные лагеря. */
/* companion-card-loader */
{ const base = document.currentScript?.src || new URL('ui/', location.href);
  const s = document.createElement('script'); s.src = new URL('companion-card.js', base).href; document.head.append(s);
  const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = new URL('companion-card.css', base).href; document.head.append(l); }
/* /companion-card-loader */
(() => {
  'use strict';
  const el=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text!=null)n.textContent=text;return n;};
  const professions={scientist:'Учёный',engineer:'Инженер',medic:'Медик',scout:'Разведчик',builder:'Строитель',gatherer:'Собиратель',hauler:'Грузчик',guard:'Боец',farmer:'Фермер',crafter:'Мастер',gunsmith:'Оружейник',trader:'Торговец'};
  const jobs={'gather:wood':'Дерево','gather:scrap':'Лом','gather:water':'Вода','gather:food':'Еда',idle:'Отдых',build:'Стройка',repair:'Ремонт',craft:'Ремесло',operate:'Генератор',guard:'Охрана',patrol:'Патруль',scout:'Разведка'};
  const cfg=()=>window.TERRA_DEFENSE_CTX?.B?.camp;
  // Обычная стройка и ремонт пишут status=working ещё на подходе.
  // Место уже есть в сцене: тот же зазор 0.4, что у сбора. В сейв ничего не пишем.
  function buildEnRoute(s){
    const root=String(s?.job||'').split(':')[0];
    if((root!=='build'&&root!=='repair')||s.status!=='working')return false;
    const id=s.order?.target;
    if(!id||id==='generator')return false;
    const g=window.game,b=g?.p?.camp?.buildings?.[id];
    if(!b||b.project?.paused||b.type==='segment'||b.type==='warehouse')return false;
    let site=null;
    try{const ctx=g.workerSceneContext?.();site=ctx?.worksites?.[id]||ctx?.facilityPositions?.[id];}catch(e){return false;}
    if(!Number.isFinite(site?.x)||!Number.isFinite(site?.z))return false;
    if(!Number.isFinite(s.pos?.x)||!Number.isFinite(s.pos?.z))return true;
    return Math.hypot(s.pos.x-site.x,s.pos.z-site.z)>0.4;
  }
  const GENERIC=new Set(['','Нет доступной цели','Сейчас недоступно','Сейчас нельзя','Простой']);
  const DENIAL={
    'courier-busy':'Житель выполняет поручение курьера',
    cargo:'Дождитесь доставки груза',
    unavailable:'Житель занят или ранен',
    job:'Такой работы нет',
    route:'Маршрут недоступен',
    territory:'Нужна территория',
    adjacent:'Нужна связь с домашним районом',
    operator:'Нужен инженер',
    'warehouse-builder':'Нужен доступный строитель или инженер.',
    'warehouse-unavailable':'Склад недоступен: проверьте аванпост и контроль территории.',
    project:'Нет стройки',
    paused:'Стройка на паузе',
    captive:'В плену',
    full:'Уже полный',
    point:'Нужно свободное место 8×8 м',
    outpost:'Аванпост недоступен',
    unloaded:'Путь не загружен',
    obstacle:'Проход перекрыт',
  };
  function denialText(value){return typeof value==='string'&&Object.hasOwn(DENIAL,value)?DENIAL[value]:'';}
  function roleState(camp,s){
    if(!s||s.dead)return {group:'waiting',text:'Недоступен',free:false};
    if(camp?.fieldCompanion?.settlerId===s.id){
      const mode=camp.fieldCompanion.mode;
      return {group:s.status==='blocked'?'waiting':'working',text:mode==='return'?'Напарник · возвращается':mode==='wait'?'Напарник · ждёт здесь':'Напарник · с героем',free:false};
    }
    if(s.mission)return {group:'working',text:'На задании',free:false};
    const tick=camp?.sim?.tick||0;
    const hurt=s.captive?'В плену':s.wounded||s.injuredUntil>tick?'Ранен · ждёт восстановления':'';
    if(hurt)return {group:'waiting',text:hurt,free:false};
    if(camp?.warehouseCourier?.settlerId===s.id){
      const text=s.status==='blocked'?s.workBlock==='unloaded'?'Курьер: путь не загружен':'Курьер: маршрут недоступен':'Курьер · груз закреплён';
      return {group:s.status==='blocked'?'waiting':'working',text,free:false};
    }
    if(s.trip?.amount)return {group:'working',text:'Переносит груз · сначала разгрузка',free:false};
    if(s.job==='idle'){
      const manual=!!s.order?.stick&&!s.order?.courier&&camp?.warehouseCourier?.settlerId!==s.id;
      const rest=!!s.order?.rest||(s.needs?.rest??100)<=(cfg()?.utility?.restStart??25);
      const text=manual?'Ручной отдых · автоназначение выключено':rest?'Восстанавливает силы':'';
      return {group:text?'waiting':'free',text:text||'Готов к приказу',free:!text};
    }
    const building=camp?.buildings?.[s.order?.target];
    let wait='';
    if(s.job==='build'&&building?.project?.paused)wait='Стройка приостановлена';
    else if(s.status==='blocked'){
      if(s.workBlock==='unloaded')wait='Путь не загружен · подойдите к рабочему';
      else if(s.workBlock==='obstacle')wait='Проход перекрыт';
      else if(s.job==='build'&&!building?.project)wait='Стройка завершена · ожидает смены задачи';
      else if(s.job==='build'&&building?.project?.delivery&&!building.project.delivery.delivered&&building.project.delivery.carrier&&building.project.delivery.carrier!==s.id)wait='Материалы несёт другой рабочий';
      else if(s.job==='build'||s.job==='repair')wait='Рабочий подход недоступен';
      else if(String(s.job).startsWith('haul:')){
        const route=camp?.routes?.[s.job.slice(5)];
        const store=route&&(route.from==='camp'?camp.res:camp.buildings?.[route.from]?.store);
        wait=route?store?.[route.res]>0?'Доставка ожидает доступного маршрута':'Нет груза на складе отправления':'Маршрут недоступен';
      }else wait='Ожидает доступной рабочей цели';
    }
    return wait?{group:'waiting',text:wait,free:false}:null;
  }
  function activity(s,camp){
    camp=camp||window.game?.p?.camp||null;
    const role=roleState(camp,s);
    if(role&&!role.free)return role.text;
    if(s.job?.startsWith('gather:')&&!s.facility&&!s.order?.outpost){
      const returning=(s.work||0)/(cfg()?.work.gatherPeriod||45)>=.75;
      if(!s.work&&s.status!=='travel')return 'Назначено';
      return s.status==='travel'?(returning?'Несёт припасы':'Идёт за ресурсом'):(returning?'Сдаёт припасы':'Собирает');
    }
    if(s.status==='travel')return 'В пути';
    if(buildEnRoute(s))return s.job==='repair'?'Идёт к ремонту':'Идёт к стройке';
    return s.job==='idle'?'Свободен':s.status==='working'?'Работает':'Ожидает';
  }
  function jobHold(camp,settler,job){
    if(!camp||!settler||!job||settler.mission)return '';
    const kind=String(job).split(':')[0];
    if(kind==='operate'&&settler.prof!=='engineer')return 'Нужен инженер';
    if(kind==='operate'&&camp.buildings?.generator?.project)return 'Строительство уже идёт';
    if(kind==='build'&&!Object.values(camp.buildings||{}).some(b=>b?.project))return 'Нет свободной стройки';
    if(kind==='haul'&&!Object.keys(camp.routes||{}).length)return 'Маршрут недоступен';
    if(!['gather','guard','patrol','idle'].includes(kind))return '';
    const tick=camp.sim?.tick||0;
    if(settler.captive)return 'В плену';
    if(settler.wounded||settler.injuredUntil>tick)return 'Ранен · ждёт восстановления';
    if(camp.warehouseCourier?.settlerId===settler.id)return 'Житель выполняет поручение курьера';
    if(settler.trip?.amount)return 'Дождитесь доставки груза';
    return '';
  }
  function orderReason(s,button){
    if(!button?.disabled)return '';
    const title=(button.getAttribute('title')||'').trim();
    const label=(button.textContent||'').trim();
    if(title&&title!==label&&!GENERIC.has(title))return title;
    const role=roleState(window.game?.p?.camp,s);
    return role&&!role.free?role.text:'';
  }
  function jobLabel(s){return jobs[s.job]||(String(s.job||'').startsWith('haul:')?'Перевозка':'')||s.facility||s.job||'Отдых';}
  function portrait(node,s) {
    if(!node||node.querySelector('img')||node.classList.contains('fbPhoto'))return;
    const image=window.TERRA_CAMP_ALBUM_DATA?.portrait(s)?.querySelector('img');
    if(image){node.classList.add('fbPhoto');image.alt='Портрет: '+(s.name||'Житель');node.append(image);return;}
    let hash=0;for(const c of String(s.id||s.name||''))hash=(hash*31+c.charCodeAt(0))>>>0;
    const female=/^(Ольга|Анна|Мария|Марина|Елена|Наталья|Татьяна|Ирина|Светлана|Людмила|Марфа|Вера|Надежда|Валентина|Дарья|Алина)(?:\s|$)/u.test(s.name||'');
    const index=female?[1,4,6][hash%3]:({scientist:0,medic:2,scout:3,guard:3,engineer:7,builder:7}[s.prof]??[0,2,3,5,7][hash%5]);
    node.classList.add('fbPhoto','fbFace'+index);
    node.setAttribute('role','img');node.setAttribute('aria-label','Портрет: '+(s.name||'Житель'));
  }
  function start(){
    const panel=document.getElementById('campPanel'),body=document.getElementById('campBody'),tabs=document.getElementById('campTabs');
    if(!panel||!body||!tabs)return;
    panel.classList.add('fieldbook');
    const select=id=>{if(window.game?.state==='modal'&&!panel.classList.contains('hidden'))window.game.ui.campPanel.select(id);};
    const currentTab=()=>window.terraCampUI?.tab||window.game?.ui?.campPanel?.tab||'overview';
    const secondary=id=>!['overview','settlers','build','expansion','more'].includes(id);
    const h=panel.querySelector('h2'),back=el('button','fbBack','←'),heading=el('span','fbHeading','ЛАГЕРЬ'),sections=el('button','fbSections','☰'),meta=el('output','fbMeta');
    back.type=sections.type='button';back.setAttribute('aria-label','Назад к лагерю');back.addEventListener('click',()=>select(secondary(currentTab())?'more':'overview'));
    sections.setAttribute('aria-label','Разделы лагеря');sections.setAttribute('aria-controls','campTabs');sections.setAttribute('aria-expanded','false');tabs.hidden=true;
    sections.addEventListener('click',()=>{tabs.hidden=!tabs.hidden;sections.setAttribute('aria-expanded',String(!tabs.hidden));if(!tabs.hidden)tabs.querySelector('button.on')?.focus();});
    h.prepend(back,heading);h.insertBefore(sections,h.querySelector('.x'));h.after(meta);
    const more=el('button','fbMore','ЕЩЁ');more.type='button';more.addEventListener('click',()=>select(currentTab()==='more'?'overview':'more'));
    const pause=el('button','fbPauseInfo','Ⅱ');pause.type='button';pause.setAttribute('aria-label','Лагерь на паузе: когда жители начнут работу');
    pause.addEventListener('click',()=>window.terraCampUI?.openInfo('Лагерь на паузе',el('p','','Пока открыт альбом, мир стоит на паузе. После «В игру» жители продолжат назначенные работы.')));
    panel.querySelector('footer')?.prepend(more,pause);
    tabs.addEventListener('click',e=>{if(e.target.closest('button')){tabs.hidden=true;sections.setAttribute('aria-expanded','false');back.focus({preventScroll:true});}});
    function home(root){
      if(root.querySelector(':scope > .fbHomeBoard'))return;
      root.classList.add('fbHome');
      const supply=root.querySelector(':scope > .campSupply'),quick=root.querySelector(':scope > .campQuick'),expansion=quick?.querySelector('.campExpansionEntry');
      const board=el('div','fbHomeBoard'),native=el('details','fbOverviewDetails');native.append(el('summary','','Журнал лагеря / запасы и цели'));
      for(const child of [...root.children])if(child!==supply)native.append(child);
      if(supply){
        const help=el('details','fbSupplyRules');help.append(el('summary','','Резерв · i'));
        for(const small of [...supply.querySelectorAll(':scope > small')])help.append(small);
        supply.append(help);board.append(supply);
      }
      const folders=el('nav','fbFolders');folders.setAttribute('aria-label','Дела лагеря');
      const first=Object.values(window.game?.p?.camp?.settlers||{}).find(s=>s&&!s.dead);
      for(const [id,label,kind,note] of [['settlers','ЖИТЕЛИ','people','Личные дела'],['build','РАБОТЫ','work','Постройки и снабжение'],['expansion','РАСШИРЕНИЕ','map',expansion?.querySelector('small')?.textContent||'Развитие лагеря']]){
        const b=el('button','fbFolder fbFolder-'+kind);b.type='button';b.dataset.fieldbookSection=id;
        const art=el('span','fbFolderArt');art.setAttribute('aria-hidden','true');if(id==='settlers')portrait(art,first||{id:'camp-empty',name:'Выжившие',prof:'scientist'});
        const text=el('span','fbFolderText');text.append(el('strong','',label),el('small','',note));b.append(art,text,el('span','fbFolderArrow','›'));
        b.addEventListener('click',()=>{if(id==='expansion'&&expansion)expansion.click();else select(id);});folders.append(b);
      }
      board.append(folders);root.append(board,native);
    }
    function roster(root){
      for(const row of root.querySelectorAll('.residentRow')){
        const summary=row.querySelector('[data-resident]'),s=window.game?.p?.camp?.settlers?.[summary?.dataset.resident];if(!s)continue;
        portrait(row.querySelector('.residentPortrait'),s);
        if(row.dataset.fieldbook)return;row.dataset.fieldbook='1';
        const name=row.querySelector('.residentNameBlock');
        if(name){const p=el('span','fbProfession',professions[s.prof]||s.prof||'Житель');name.querySelector('strong')?.after(p);name.querySelector('.residentBadge')?.classList.add('fbLegacyProfession');}
        const order=row.querySelector('[data-resident-order]');
        const state=activity(s);
        const status=[...name?.querySelectorAll('.residentBadge')[1]?.children||[]].find(node=>node.tagName==='SPAN'&&!node.classList.contains('campIcon'));
        if(status&&state&&['Курьер · недоступен','Свободен','Простой'].includes(status.textContent.trim())&&status.textContent.trim()!==state)status.textContent=state;
        if(order){
          const fold=el('details','fbCardOrder');fold.append(el('summary','','Приказ'),order);
          const reason=orderReason(s,order);
          const same=reason&&(reason===status?.textContent.trim());
          if(reason&&!same){
            const note=el('small','campReason residentOrderReason',reason);
            note.id='resident-order-reason-'+s.id;
            fold.append(note);
            order.setAttribute('aria-describedby',note.id);
          }else if(same){
            if(!status.id)status.id='resident-order-reason-'+s.id;
            order.setAttribute('aria-describedby',status.id);
          }
          row.append(fold);
        }
        if(s.wounded||s.status==='blocked'){const warn=el('span','fbWarning','!');warn.setAttribute('aria-label',activity(s));summary.append(warn);}
      }
    }
    function dossier(root){
      const residentId=root.querySelector('[data-resident-biography]')?.dataset.residentBiography||root.querySelector('[data-resident-order]')?.dataset.residentOrder;
      const s=window.game?.p?.camp?.settlers?.[residentId];
      const head=root.querySelector('.residentIdentityHead');
      if(!s||!head)return;
      portrait(head.querySelector('.residentPortrait'),s);
      const act=root.querySelector('.fbActivity'),actText=activity(s);
      if(act&&act.textContent!==actText)act.textContent=actText;
      if(!root.querySelector(':scope > .fbAssignment')){
        const assignment=el('section','fbAssignment');assignment.setAttribute('aria-label','Текущее назначение');
        const line=el('div','');line.append(el('small','','Назначение'),el('strong','fbAssignmentStamp',jobLabel(s)),el('span','fbActivity',activity(s)));
        const change=el('button','fbChangeJob','Сменить');change.type='button';change.setAttribute('aria-expanded','false');
        change.addEventListener('click',()=>{const open=root.classList.toggle('fbChoosingJob');change.setAttribute('aria-expanded',String(open));if(open)root.querySelector('.campJobs')?.scrollIntoView({block:'nearest'});});
        assignment.append(line,change);root.querySelector('.dossierNeeds')?.after(assignment);
      }
      const radio=root.querySelector('.dossierRadio');
      if(radio&&!radio.querySelector('.fbCurrentPhoto')){const photo=el('span','fbCurrentPhoto');portrait(photo,s);radio.insertBefore(photo,radio.querySelector('.dossierDial'));}
      if(radio){
        let count=radio.querySelector('.fbFileCount');if(!count){count=el('span','fbFileCount');count.setAttribute('aria-hidden','true');radio.querySelector('.dossierDial')?.after(count);}
        const nums=radio.querySelector('.dossierDial')?.textContent.match(/\d+/g)||[],text=nums.length>1?nums[0].padStart(2,'0')+' / '+nums[1].padStart(2,'0'):nums[0]||'0';if(count.textContent!==text)count.textContent=text;
      }
      const stamp=root.querySelector('.fbAssignmentStamp'),activityNode=root.querySelector('.fbActivity');
      const text=activity(s),label=jobLabel(s);
      if(stamp&&stamp.textContent!==label)stamp.textContent=label;
      for(const node of root.querySelectorAll(':scope > small'))if(node.textContent.trim()==='Ручной отдых · автоназначение выключено')node.hidden=node.textContent.trim()!==text;
      const echoed=[...root.querySelectorAll(':scope > small')].some(node=>!node.hidden&&node.textContent.trim()===text);
      if(activityNode&&activityNode.textContent!==text)activityNode.textContent=text;
      if(activityNode)activityNode.hidden=echoed;
    }
    function blueprints(root){
      const grid=root.querySelector(':scope > .campGrid');
      if(grid&&!root.querySelector('.fbOtherPlans')){
        const rest=[...grid.querySelectorAll(':scope > [data-building]')].filter(c=>!['generator','sawmill','pump','watch'].includes(c.dataset.building));
        if(rest.length){const fold=el('details','fbOtherPlans'),extra=el('div','campGrid');fold.append(el('summary','','Ещё постройки · '+rest.length),extra);extra.append(...rest);grid.after(fold);}
      }
      for(const card of root.querySelectorAll('[data-building]')){
        if(!['generator','sawmill','pump','watch'].includes(card.dataset.building)||card.querySelector('.fbBlueprintArt'))continue;
        const art=el('div','fbBlueprintArt');art.dataset.plan=card.dataset.building;art.setAttribute('aria-hidden','true');
        (card.querySelector('.bpLevel')||card.querySelector('strong'))?.after(art);
      }
    }
    function perimeter(){
      const native=body.querySelector('.campDefense'),guns=body.querySelector('[data-defense-turrets]');
      if(!native||!guns)return;
      // The original armory and guard handlers stay in their original nodes.
      // Their duplicate durability summary belongs behind a disclosure.
      if(!native.querySelector(':scope > .fbGuardFile')){
        const file=el('details','fbGuardFile');file.append(el('summary','','Сводка прочности'));
        const durability=native.querySelector(':scope > .defGrid:not(.opsPositions)');
        if(durability)file.append(durability);
        native.append(file);
      }
      if(guns.nextElementSibling!==native)body.insertBefore(guns,native);
      const threat=native.querySelector('.opsThreat');if(threat)body.insertBefore(threat,guns);
    }
    let queued=false;
    const observer=new MutationObserver(schedule);
    function decorate(){
      queued=false;observer.disconnect();
      try{
        if(!panel.classList.contains('hidden')){
          const tab=currentTab(),root=body.firstElementChild,c=window.game?.p?.camp;
          const title={overview:'ЛАГЕРЬ',settlers:'ЖИТЕЛИ',build:'РАБОТЫ',expansion:'РАСШИРЕНИЕ',defense:'ОБОРОНА',more:'ВСЕ РАЗДЕЛЫ',contracts:'КОНТРАКТЫ',tech:'ТЕХНОЛОГИИ',territories:'ТЕРРИТОРИИ',power:'ЭНЕРГИЯ',warehouses:'СКЛАДЫ',pine:'СОСНОВЫЙ УЗЕЛ'}[tab]||panel.querySelector('[data-camp-tab="'+CSS.escape(tab)+'"]')?.getAttribute('aria-label')?.toLocaleUpperCase('ru')||'ЛАГЕРЬ';
          if(heading.textContent!==title)heading.textContent=title;back.disabled=tab==='overview';back.setAttribute('aria-label',secondary(tab)?'Назад ко всем разделам':'Назад к лагерю');if(more.textContent!==(tab==='more'?'← Обзор':'ЕЩЁ'))more.textContent=tab==='more'?'← Обзор':'ЕЩЁ';
          const count=Object.values(c?.settlers||{}).filter(s=>s&&!s.dead).length,level=cfg()?.tiers?.[(c?.tier||1)-1]?.name||'Лагерь';
          const text=level+' · '+(c?.tier||1)+'   |   Жители '+count+'   |   Ценность '+Math.floor(c?.value||0);
          if(meta.textContent!==text)meta.textContent=text;
          body.dataset.fieldbookView=tab;
          if(root){if(tab==='overview')home(root);if(tab==='settlers'){roster(root);if(root.querySelector('.residentIdentityHead'))dossier(root);}if(tab==='build')blueprints(root);if(tab==='defense')perimeter();}
          window.terraCompanionCard?.paint();
        }
      }catch(e){console.error('[camp-fieldbook]',e);}
      observer.takeRecords();observer.observe(body,{childList:true,subtree:true});
    }
    function schedule(){if(!queued){queued=true;queueMicrotask(decorate);}}
    panel.addEventListener('terra:camp-tab',schedule);panel.addEventListener('terra:camp-refresh',schedule);
    new MutationObserver(schedule).observe(panel,{attributes:true,attributeFilter:['class']});decorate();
    window.terraCampFieldbook=Object.freeze({activity,portrait,roleState,jobHold,denialText,orderReason,buildEnRoute});
  }
  if(document.readyState==='complete')start();else window.addEventListener('load',start,{once:true});
})();
