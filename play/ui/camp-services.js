/* Штатные исследования, питание, снабжение и карта в полевом альбоме. */
(() => {
  'use strict';
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;};
  const art=name=>{const n=el('span','dispatchArt serviceArt');n.dataset.dispatchArt=name;n.setAttribute('aria-hidden','true');return n;};
  const readyTrees=new WeakSet(),readyPower=new WeakSet(),warehouses=new WeakMap(),techFocus=new WeakMap();
  const keyPaths={power:'M16 3v13M9 7a12 12 0 1 0 14 0',wood:'M5 9h22v15H5zM5 9l8-6h14v6m-14-6v6m9 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6',scrap:'m10 5 4 3 4-3 2 5 5 1-2 5 3 4-5 2-1 5-5-2-4 3-2-5-5-1 2-5-3-4 5-2 1-5zM16 12a4 4 0 1 0 0 8 4 4 0 0 0 0-8',food:'M7 3v11m4-11v11m-8-5h12M9 14v15m15-26v26m0-26c-8 4-8 13 0 13',water:'M16 3C8 14 5 18 5 22a11 11 0 0 0 22 0c0-4-3-8-11-19',chem:'M11 3h10m-8 0v9L5 27h22l-8-15V3M9 20h14',cloth:'m8 3 8 3 8-3-2 11 3 13H7l3-13-2-11m8 3v21',ammo:'M10 11h12v18H10zm0 0 6-9 6 9M10 24h12',cell:'M6 7h20v20H6zm7 0V3h6v4m-4 5-4 7h7l-4 7'};
  function resourceIcon(key){const s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox','0 0 32 32');s.setAttribute('aria-hidden','true');s.classList.add('serviceSymbol');const p=document.createElementNS(s.namespaceURI,'path');p.setAttribute('d',keyPaths[key]||keyPaths.ammo);s.append(p);return s;}
  function start(){
    const panel=document.getElementById('campPanel'),body=panel?.querySelector('#campBody');if(!body)return;
    let queued=false;
    function technology(root){
      const tree=root.querySelector(':scope > .campTree');if(!tree)return;
      if(!readyTrees.has(tree)){
        readyTrees.add(tree);root.classList.add('serviceTechnology');
        const cards=[...tree.querySelectorAll(':scope > .campTech')],summary=el('header','serviceResearchSummary'),counts=el('div','serviceResearchCounts');
        const open=cards.filter(c=>c.classList.contains('open')).length,available=cards.filter(c=>c.classList.contains('available')).length;
        for(const [label,value] of [['Изучено',open+' / '+cards.length],['Доступно',available],['Закрыто',cards.length-open-available]]){const n=el('span','');n.append(el('b','',String(value)),el('small','',label));counts.append(n);}
        summary.append(art('tech'),counts);tree.before(summary);
        const keys=Object.keys(window.TERRA_DEFENSE_CTX?.B.camp.tech||{});
        cards.forEach((card,index)=>{
          if(keys.length===cards.length)card.dataset.serviceTech=keys[index];
          const state=card.classList.contains('open')?'open':card.classList.contains('available')?'available':'locked';
          card.prepend(el('span','serviceTechStamp',{open:'Изучено',available:'Доступно',locked:'Закрыто'}[state]));
          card.querySelector(':scope > strong')?.setAttribute('tabindex','-1');
          card.querySelector(':scope > small:not(.campLink):not(.campReason)')?.classList.add('serviceTechCost');
          const reason=card.querySelector(':scope > .campReason');
          if(reason){const fold=el('details','serviceTechRequirements');fold.append(el('summary','','Условия'),reason);card.insertBefore(fold,card.querySelector(':scope > button'));}
          for(const button of card.querySelectorAll(':scope > .campButton')){
            button.classList.add('serviceTechAction');for(const n of button.childNodes)if(n.nodeType===Node.TEXT_NODE&&n.textContent.trim()==='Исследовать')n.textContent='Изучить';for(const a of ['aria-label','title']){const label=button.getAttribute(a);if(label?.startsWith('Исследовать'))button.setAttribute(a,label.replace(/^Исследовать/,'Изучить'));}button.querySelector('.campIcon')?.replaceChildren(resourceIcon('chem'));button.addEventListener('click',()=>{if(!button.disabled&&button.isConnected)techFocus.set(root,{key:card.dataset.serviceTech,origin:button,player:window.game?.p});},true);
          }
        });
      }
      const pending=techFocus.get(root);if(pending){techFocus.delete(root);const active=document.activeElement;if(!pending.origin.isConnected&&pending.player===window.game?.p&&(!active||active===document.body||!active.isConnected)){[...tree.children].find(c=>c.dataset.serviceTech===pending.key)?.querySelector('strong')?.focus({preventScroll:true});}}
    }
    function power(root){
      const card=root.querySelector('[data-power-card=generator]');if(!card||readyPower.has(card))return;
      readyPower.add(card);root.classList.add('servicePower');card.classList.add('serviceGenerator');
      const controls=el('div','servicePowerControls');controls.append(...card.childNodes);card.append(art('power'),controls);
      for(const button of controls.querySelectorAll('button')){
        const label=button.getAttribute('aria-label')||button.textContent.trim();
        if(['Включить','Выключить'].includes(label)){button.classList.add('servicePowerSwitch');button.querySelector('.campIcon')?.replaceChildren(resourceIcon('power'));}
        if(label.startsWith('Заправить')){button.classList.add('servicePowerFuel');button.querySelector('.campIcon')?.replaceChildren(resourceIcon('chem'));}
        const people=Object.values(window.game?.p?.camp?.settlers||{}).filter(s=>s.name===label&&s.prof==='engineer');
        if(people.length===1){const photo=el('span','serviceEngineerPhoto');window.terraCampFieldbook?.portrait(photo,people[0]);button.prepend(photo);button.classList.add('serviceEngineer');button.dataset.serviceResident=people[0].id;}
      }
    }
    function supply(root){
      let record=warehouses.get(root);if(!record){record={local:false,shipment:false,focus:null};warehouses.set(root,record);}
      if(root.querySelector(':scope > .serviceSupplyHead'))return;
      root.classList.add('serviceSupply');
      const head=el('header','serviceSupplyHead'),title=root.querySelector(':scope > h3'),intro=root.querySelector(':scope > p:not(.campReason):not(.campCheck)');
      const description=el('div','');if(title)description.append(title);head.append(art('warehouse'),description);
      if(intro){const rules=el('details','serviceSupplyRules');rules.append(el('summary','','О снабжении'),intro);description.append(rules);}
      root.prepend(head);
      const grid=root.querySelector(':scope > .campGrid');if(grid){grid.classList.add('serviceStock');grid.id='service-stock';}
      const fields=[...root.querySelectorAll(':scope > section.campCard')];let local=null,shipment=null;
      for(const section of fields){if(section.querySelector('[data-warehouse-field=local]'))local=section;else if(section.querySelector('[data-warehouse-field=from]')||section.hasAttribute('data-shipment-id'))shipment=section;}
      function folder(section,id,title){
        if(!section)return null;
        const fold=el('details','serviceSupplyFolder');fold.dataset.supplyFolder=id;fold.id='service-supply-'+id;
        fold.open=record[id]||section.hasAttribute('data-shipment-id');if(fold.open)record[id]=true;
        const summary=el('summary','',title);summary.addEventListener('click',()=>{record[id]=!fold.open;});fold.append(summary);
        section.before(fold);fold.append(section);section.classList.add('serviceSupplyForm');
        for(const control of section.querySelectorAll('select[data-warehouse-field]'))control.addEventListener('change',()=>{record.focus={field:control.dataset.warehouseField,origin:control,player:window.game?.p};},true);
        return fold;
      }
      const exchange=folder(local,'local','Рюкзак ↔ склад'),delivery=folder(shipment,'shipment',shipment?.hasAttribute('data-shipment-id')?'Груз в пути':'Отправить груз');
      const nav=el('nav','serviceSupplyNav');nav.setAttribute('aria-label','Листы снабжения');
      for(const [target,label] of [[grid,'Запасы'],[exchange,'Обмен'],[delivery,'Доставка']])if(target){const button=el('button','campButton',label);button.type='button';button.setAttribute('aria-controls',target.id);button.addEventListener('click',()=>{if(target.tagName==='DETAILS'){target.open=true;record[target.dataset.supplyFolder]=true;}target.scrollIntoView({block:'start',behavior:'instant'});});nav.append(button);}
      head.after(nav);
      const items=window.TERRA_DEFENSE_CTX?.Yt||{};
      for(const site of root.querySelectorAll('[data-warehouse-site]')){
        site.classList.add('serviceWarehouse');const inventory=el('div','serviceInventory');
        for(const row of [...site.querySelectorAll(':scope > small:not(.campReason)')]){
          const match=row.textContent.match(/^(.+):\s*([\d.,]+)$/);if(!match)continue;
          const key=({Дерево:'wood',Лом:'scrap',Еда:'food',Вода:'water',Химикаты:'chem',Ткань:'cloth',Энергоячейки:'cell'}[match[1]])||Object.keys(items).find(k=>items[k]?.name===match[1]);
          if(!key||!keyPaths[key])continue;
          row.classList.add('serviceStockRow');row.replaceChildren(resourceIcon(key),el('span','',match[1]),el('b','',match[2]));inventory.append(row);
        }
        if(inventory.children.length){const label=site.querySelector(':scope > small:not(.campReason)');if(label)label.after(inventory);else site.querySelector('strong')?.after(inventory);}
      }
      const pending=record.focus;record.focus=null;
      if(pending&&pending.player===window.game?.p&&!pending.origin.isConnected){const active=document.activeElement;if(!active||active===document.body||!active.isConnected){[...root.querySelectorAll('[data-warehouse-field]')].find(n=>n.dataset.warehouseField===pending.field)?.focus({preventScroll:true});}}
    }
    function territories(root){
      root.classList.add('serviceTerritories');
      const detail=root.querySelector('.territoryDetail');if(!detail)return;
      for(const node of detail.querySelectorAll('.territoryValues > span')){
        if(node.querySelector('b'))continue;
        const match=node.textContent.match(/^(.*)\s+([\d.,%—]+)$/);if(match){node.replaceChildren(el('b','',match[2]),el('small','',match[1]));}
      }
    }
    const observer=new MutationObserver(schedule);
    function decorate(){
      queued=false;observer.disconnect();
      try{
        if(!panel.classList.contains('hidden')){
          const tree=body.querySelector('.campTree');if(tree)technology(tree.parentElement);
          const generator=body.querySelector('[data-power-card=generator]');if(generator)power(generator.parentElement);
          for(const root of body.querySelectorAll('[data-warehouse-panel]'))supply(root);
          const map=body.querySelector('.campTerritories');if(map)territories(map);
        }
      }catch(error){console.error('[camp-services]',error);}
      observer.takeRecords();observer.observe(body,{childList:true,subtree:true});
    }
    function schedule(){if(!queued){queued=true;queueMicrotask(decorate);}}
    panel.addEventListener('terra:camp-tab',schedule);panel.addEventListener('terra:camp-refresh',schedule);
    new MutationObserver(schedule).observe(panel,{attributes:true,attributeFilter:['class']});decorate();
  }
  if(document.readyState==='complete')start();else window.addEventListener('load',start,{once:true});
})();
