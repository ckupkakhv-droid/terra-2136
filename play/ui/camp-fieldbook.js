/* Полевой альбом: реальные жители, штатные кнопки и данные лагеря. */
(() => {
  'use strict';
  const el=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text!=null)n.textContent=text;return n;};
  const professions={scientist:'Учёный',engineer:'Инженер',medic:'Медик',scout:'Разведчик',builder:'Строитель',gatherer:'Собиратель',hauler:'Грузчик',guard:'Боец',farmer:'Фермер',crafter:'Мастер',gunsmith:'Оружейник',trader:'Торговец'};
  const jobs={'gather:wood':'Дерево','gather:scrap':'Лом','gather:water':'Вода','gather:food':'Еда',idle:'Отдых',build:'Стройка',repair:'Ремонт',craft:'Ремесло',operate:'Генератор',guard:'Охрана',patrol:'Патруль',scout:'Разведка'};
  const cfg=()=>window.TERRA_DEFENSE_CTX?.B?.camp;
  function activity(s) {
    if(s.wounded||s.status==='injured')return 'Ранен';
    if(s.status==='blocked')return s.workBlock==='unloaded'?'Маршрут не загружен':s.workBlock==='obstacle'?'Проход перекрыт':'Простой';
    if(s.job?.startsWith('gather:')&&!s.facility&&!s.order?.outpost){
      const returning=(s.work||0)/(cfg()?.work.gatherPeriod||45)>=.75;
      if(!s.work&&s.status!=='travel')return 'Назначено';
      return s.status==='travel'?(returning?'Несёт припасы':'Идёт за ресурсом'):(returning?'Сдаёт припасы':'Собирает');
    }
    if(s.status==='travel')return 'В пути';
    return s.job==='idle'?'Свободен':s.status==='working'?'Работает':'Ожидает';
  }
  function portrait(node,s) {
    if(!node||node.querySelector('img')||node.classList.contains('fbPhoto'))return;
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
    const h=panel.querySelector('h2'),back=el('button','fbBack','←'),heading=el('span','fbHeading','ЛАГЕРЬ'),sections=el('button','fbSections','☰'),meta=el('output','fbMeta');
    back.type=sections.type='button';back.setAttribute('aria-label','Назад к лагерю');back.addEventListener('click',()=>select('overview'));
    sections.setAttribute('aria-label','Разделы лагеря');sections.setAttribute('aria-controls','campTabs');sections.setAttribute('aria-expanded','false');tabs.hidden=true;
    sections.addEventListener('click',()=>{tabs.hidden=!tabs.hidden;sections.setAttribute('aria-expanded',String(!tabs.hidden));if(!tabs.hidden)tabs.querySelector('button.on')?.focus();});
    h.prepend(back,heading);h.insertBefore(sections,h.querySelector('.x'));h.after(meta);
    const more=el('button','fbMore','ЕЩЁ');more.type='button';more.addEventListener('click',()=>select('more'));
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
        if(order){const fold=el('details','fbCardOrder');fold.append(el('summary','','Приказ'),order);row.append(fold);}
        if(s.wounded||s.status==='blocked'){const warn=el('span','fbWarning','!');warn.setAttribute('aria-label',activity(s));summary.append(warn);}
      }
    }
    function dossier(root){
      const residentId=root.querySelector('[data-resident-biography]')?.dataset.residentBiography||root.querySelector('[data-resident-order]')?.dataset.residentOrder;
      const s=window.game?.p?.camp?.settlers?.[residentId];
      const head=root.querySelector('.residentIdentityHead');
      if(!s||!head)return;
      portrait(head.querySelector('.residentPortrait'),s);
      if(!root.querySelector(':scope > .fbAssignment')){
        const assignment=el('section','fbAssignment');assignment.setAttribute('aria-label','Текущее назначение');
        const line=el('div','');line.append(el('small','','Назначение'),el('strong','fbAssignmentStamp',jobs[s.job]||s.facility||s.job||'Отдых'),el('span','fbActivity',activity(s)));
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
      const companion=root.querySelector(':scope > .campCompanion');
      if(companion){const fold=el('details','fbCompanionFold');fold.append(el('summary','','Вылазка и развитие'));companion.before(fold);fold.append(companion);}
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
    let queued=false;
    const observer=new MutationObserver(schedule);
    function decorate(){
      queued=false;observer.disconnect();
      try{
        if(!panel.classList.contains('hidden')){
          const tab=window.game?.ui?.campPanel?.tab||'overview',root=body.firstElementChild,c=window.game?.p?.camp;
          const title={overview:'ЛАГЕРЬ',settlers:'ЖИТЕЛИ',build:'РАБОТЫ',expansion:'РАСШИРЕНИЕ',defense:'ОБОРОНА',more:'ПОЛЕВОЙ ЖУРНАЛ'}[tab]||'ЛАГЕРЬ';
          if(heading.textContent!==title)heading.textContent=title;back.disabled=tab==='overview';
          const count=Object.values(c?.settlers||{}).filter(s=>s&&!s.dead).length,level=cfg()?.tiers?.[(c?.tier||1)-1]?.name||'Лагерь';
          const text=level+' · '+(c?.tier||1)+'   |   Жители '+count+'   |   Ценность '+Math.floor(c?.value||0);
          if(meta.textContent!==text)meta.textContent=text;
          body.dataset.fieldbookView=tab;
          if(root){if(tab==='overview')home(root);if(tab==='settlers'){roster(root);if(root.querySelector('.residentIdentityHead'))dossier(root);}if(tab==='build')blueprints(root);}
        }
      }catch(e){console.error('[camp-fieldbook]',e);}
      observer.takeRecords();observer.observe(body,{childList:true,subtree:true});
    }
    function schedule(){if(!queued){queued=true;queueMicrotask(decorate);}}
    panel.addEventListener('terra:camp-tab',schedule);panel.addEventListener('terra:camp-refresh',schedule);
    new MutationObserver(schedule).observe(panel,{attributes:true,attributeFilter:['class']});decorate();
    window.terraCampFieldbook=Object.freeze({activity});
  }
  if(document.readyState==='complete')start();else window.addEventListener('load',start,{once:true});
})();
