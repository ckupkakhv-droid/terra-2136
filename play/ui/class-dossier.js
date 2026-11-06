/* Presentation only. Native class/skill buttons keep their delegated handlers. */
(() => {
  'use strict';
  const specs = [
    {key:'circuit',label:'Контурщик',role:'Электрические разряды',chips:['1 энергоячейка','Откат 6 с'],color:'#efb861',path:'M38 5 16 33h15l-5 26 23-33H34z'},
    {key:'medic',label:'Полевой медик',role:'Лечение и поддержка',chips:['Помощь союзникам','Откат 6 с'],color:'#a5c68c',path:'M24 8h16v16h16v16H40v16H24V40H8V24h16z'},
    {key:'tech',label:'Полевой техник',role:'Перезарядка · модули',chips:['Точность','Откат 12 с'],color:'#8fbdd1',path:'m41 8-9 9 3 10 10 3 10-9c5 17-7 24-20 18L17 57 7 47l18-18C20 16 28 4 41 8z'},
    {key:'scout',label:'Следопыт',role:'Разведка и скрытность',chips:['Действие 8 с','Откат 20 с'],color:'#c5ba82',path:'M32 3 43 21l18 11-18 11-11 18-11-18L3 32l18-11zm0 13-8 24 24-8-16-16z'},
  ];
  const el=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text!=null)n.textContent=text;return n;};
  const seen=new WeakSet();
  function start() {
    const inv=document.getElementById('inv'),body=document.getElementById('invBody');
    if (!inv||!body) return;
    let pendingFocus=null,queued=false;
    body.addEventListener('click',event=>{
      const b=event.target.closest?.('button');if(!b||!b.closest('[data-circuit-class]'))return;
      const attr=[...b.attributes].find(a=>/^data-(circuit|medic|tech|scout)-(toggle|skill|cancel)$/.test(a.name));
      if(attr)pendingFocus={attr:attr.name.replace(/-cancel$/,'-toggle'),value:attr.name.endsWith('-skill')?attr.value:null,player:window.game?.p};
    },true);
    function decorate(root) {
      if(seen.has(root))return;
      const original=[...root.children];
      const heads=specs.map(s=>original.find(n=>n.matches('div')&&n.querySelector(':scope > b')?.textContent===s.label));
      // visual-fixes.js may already have moved a confirmation button into
      // its native status plate. Accept both original DOM forms.
      const buttons=specs.map(s=>root.querySelector('[data-'+s.key+'-toggle]'));
      if(buttons.some(b=>!b)||heads.some(h=>!h))return;
      seen.add(root);root.classList.add('classDossier');root.setAttribute('aria-label','Специализации бойца');
      const grid=el('div','classRoster'),active=el('div','classActive'),feedback=el('div','classFeedback');
      const head=el('header','classDossierHead');head.append(el('h3','','Специализация'),el('small','','Класс меняется бесплатно'));
      const help=el('details','classFieldGuide'),summary=el('summary','','Правила классов и управление');help.append(summary);
      let returnTo=null;
      const globals=original.filter(n=>n.matches('small[role="status"]'));
      for(const [index,spec] of specs.entries()) {
        const button=buttons[index],legacy=heads[index];
        const start=original.indexOf(legacy)+1,end=index+1<heads.length?original.indexOf(heads[index+1]):original.length;
        const extra=original.slice(start,end).filter(n=>n!==button&&!globals.includes(n));
        const card=el('article','classRecord');card.dataset.classRecord=spec.key;card.style.setProperty('--class-accent',spec.color);
        const selected=button.getAttribute('data-'+spec.key+'-toggle')==='off',confirm=button.getAttribute('data-'+spec.key+'-toggle')==='confirm';
        card.classList.toggle('isSelected',selected);card.classList.toggle('needsConfirmation',confirm);
        const emblem=el('div','classEmblem');emblem.innerHTML='<svg viewBox="0 0 64 64" aria-hidden="true"><path d="'+spec.path+'"/></svg>';
        const title=el('h4','','');title.id='class-title-'+spec.key;title.append(legacy.querySelector(':scope > b'));
        card.setAttribute('aria-labelledby',title.id);
        const badge=el('span','classStamp',selected?'ВЫБРАН':confirm?'ПОДТВЕРДИТЕ':'СПЕЦ. '+String(index+1).padStart(2,'0'));
        const chips=el('div','classTags');for(const text of spec.chips)chips.append(el('span','',text));
        const actions=el('div','classRecordActions');
        if(!button.disabled)button.textContent=selected?'Снять класс':confirm?'Подтвердить':'Выбрать';
        button.setAttribute('aria-label',(selected?'Снять класс: ':confirm?'Подтвердить выбор: ':'Выбрать класс: ')+spec.label);
        const info=el('button','classInfo','i');info.type='button';info.setAttribute('aria-label','Правила: '+spec.label);info.setAttribute('aria-controls','class-guide-'+spec.key);
        const note=el('section','classGuideEntry');note.id='class-guide-'+spec.key;
        const noteTitle=el('h4','',spec.label);noteTitle.tabIndex=-1;note.append(noteTitle,...legacy.querySelectorAll(':scope > small'));
        let confirmation=null;
        for(const n of extra) {
          if(n.matches('.circuitSkills')) {
            const group=el('section','classReadySkills');group.style.setProperty('--class-accent',spec.color);group.append(el('h4','','Приёмы · '+spec.label),n);active.append(group);
          } else if(n.matches('[role="status"]')) {confirmation=n;n.classList.add('classConfirmation');feedback.append(n);}
          else note.append(n);
        }
        info.addEventListener('click',()=>{returnTo=info;help.open=true;noteTitle.focus({preventScroll:true});note.scrollIntoView({block:'nearest'});});
        if(confirm&&confirmation) {
          if(!confirmation.contains(button))confirmation.querySelector('[data-tech-cancel],[data-scout-cancel]')?.before(button);
          actions.append(el('span','classAwaiting','Подтверждение ниже ↓'),info);
        } else actions.append(button,info);
        card.prepend(emblem,badge,title,el('p','classRole',spec.role),chips,actions);
        if(spec.key==='medic')actions.before(el('small','classCompatibility','Старые сборки не откроют профиль'));
        grid.append(card);help.append(note);
      }
      const back=el('button','classGuideBack','К специализациям ↑');back.type='button';
      back.addEventListener('click',()=>{help.open=false;const target=returnTo?.isConnected?returnTo:summary;target.focus({preventScroll:true});target.scrollIntoView({block:'nearest'});});help.append(back);
      root.replaceChildren(head,...globals,grid,feedback,active,help);
      if(pendingFocus&&pendingFocus.player===window.game?.p) {
        const key=pendingFocus,selector='['+key.attr+(key.value==null?'':'="'+CSS.escape(key.value)+'"')+']',target=root.querySelector(selector);
        if(target&&!target.disabled) {
          pendingFocus=null;
          queueMicrotask(()=>{
            if(!target.isConnected||inv.classList.contains('hidden'))return;
            const focused=document.activeElement;
            if(focused?.isConnected&&![document.body,document.documentElement,body,inv,target].includes(focused))return;
            target.focus({preventScroll:true});const notice=target.closest('.classConfirmation');(notice||target).scrollIntoView({block:'nearest'});
          });
        }
      }
    }
    function refresh() {
      queued=false;if(inv.classList.contains('hidden')){pendingFocus=null;return;}
      const root=body.querySelector('[data-circuit-class]');if(root)decorate(root);else pendingFocus=null;
    }
    const schedule=()=>{if(!queued){queued=true;queueMicrotask(refresh);}};
    new MutationObserver(schedule).observe(body,{childList:true,subtree:true});
    new MutationObserver(schedule).observe(inv,{attributes:true,attributeFilter:['class']});refresh();
  }
  if(document.readyState==='complete')start();else window.addEventListener('load',start,{once:true});
})();
