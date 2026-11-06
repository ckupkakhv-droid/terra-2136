/* Походные припасы и каталог чертежей. Команды остаются в штатном invClick. */
(() => {
  'use strict';
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;};
  const normalize=text=>String(text).toLocaleLowerCase('ru-RU').replace(/ё/g,'е').trim();
  const cleanName=node=>(node?.textContent||'').replace(/\s*▸\s*$/u,'').trim();
  let owner=null,mem=null,pending=null,interaction=0;
  function memory(){
    const player=window.game?.p;
    if(player!==owner){owner=player;mem={items:{query:''},craft:{query:'',ready:false,type:'all',selected:null}};pending=null;}
    return mem;
  }
  function start(){
    const inv=document.getElementById('inv'),body=document.getElementById('invBody');if(!inv||!body)return;
    const originalHeading=inv.querySelector('h2 > span'),header=el('span','kitHeaderTitle');header.tabIndex=-1;header.hidden=true;originalHeading?.after(header);
    let queued=false;
    const observer=new MutationObserver(schedule);
    function top(){body.scrollTop=0;}
    function remember(kind,id,origin){pending={kind,id,origin,player:window.game?.p,interaction};}
    function searchBar(kind,state,update){
      const bar=el('div','kitSearch'),label=el('label','kitSearchField'),input=el('input','');
      label.append(el('span','',kind==='items'?'Найти предмет':'Найти чертёж'));
      input.type='search';input.value=state.query;input.placeholder='Название';input.autocomplete='off';input.maxLength=80;input.dataset.kitSearch=kind;
      const clear=el('button','kitClear','×');clear.type='button';clear.setAttribute('aria-label','Очистить поиск');
      input.addEventListener('input',()=>{state.query=input.value;update();});
      input.addEventListener('keydown',event=>{if(!['Escape','Tab'].includes(event.key))event.stopPropagation();});
      clear.addEventListener('click',()=>{state.query='';input.value='';update();input.focus();});
      label.append(input);bar.append(label,clear);return bar;
    }
    function items(){
      const state=memory().items;body.classList.add('kitItems');
      const heading=el('h3','kitTitle','Походные припасы');heading.tabIndex=-1;
      const status=body.querySelector(':scope > .det');if(status)status.classList.add('kitFieldState');
      const pockets=el('div','kitPockets'),groups=[],tiles=[];
      for(const title of [...body.querySelectorAll(':scope > h4')]){
        const grid=title.nextElementSibling;if(!grid?.classList.contains('grid'))continue;
        const group=el('section','kitPocket');group.append(title,grid);groups.push(group);pockets.append(group);
        for(const tile of grid.querySelectorAll(':scope > .tile')){
          const name=tile.querySelector('.nm'),id=tile.dataset.use,original=cleanName(name);
          tile.classList.add('kitItem');tile.dataset.kitName=normalize(original);
          if(name)name.textContent=original;
          if(id){
            tile.dataset.kitItem=id;tile.removeAttribute('data-use');tile.removeAttribute('role');tile.removeAttribute('tabindex');tile.onkeydown=null;
            const action=el('button','kitBrass kitUse','Применить');action.type='button';action.dataset.use=id;action.setAttribute('aria-label',tile.getAttribute('aria-label')||'Использовать: '+original);tile.removeAttribute('aria-label');
            action.addEventListener('click',()=>remember('use',id,action),true);tile.append(action);
          }
          tiles.push(tile);
        }
      }
      for(const hint of body.querySelectorAll(':scope > .invHint'))hint.hidden=true;
      const count=el('span','kitCount'),empty=el('p','kitEmpty','Ничего не найдено');empty.setAttribute('role','status');
      function filter(){
        const query=normalize(state.query);let shown=0;
        for(const tile of tiles){tile.hidden=!!query&&!tile.dataset.kitName.includes(query);if(!tile.hidden)shown++;}
        for(const group of groups)group.hidden=![...group.querySelectorAll('.kitItem')].some(tile=>!tile.hidden);
        count.textContent=shown+' / '+tiles.length;empty.hidden=shown>0;
      }
      const bar=searchBar('items',state,filter);bar.append(count);
      body.prepend(heading);heading.after(bar);if(status)bar.after(status);body.append(pockets,empty);filter();
    }
    function craft(){
      const state=memory().craft,definitions=window.TERRA_DEFENSE_CTX?.B.recipes||[],items=window.TERRA_DEFENSE_CTX?.Yt||{};
      const grid=body.querySelector(':scope > .grid');if(!grid)return;
      body.classList.add('kitCraft');grid.classList.add('kitRecipeSheets');
      const catalog=el('div','kitCatalog'),entries=[],heading=el('h3','kitTitle','Походная мастерская');heading.tabIndex=-1;
      const bar=el('div','kitCraftTools'),filters=el('div','kitRecipeFilters'),listCount=el('span','kitCount');
      const typeButtons=[];
      for(const [id,label] of [['all','Все'],['supplies','Припасы'],['gear','Снаряжение']]){
        const button=el('button','kitType',label);button.type='button';button.dataset.kitType=id;button.addEventListener('click',()=>{state.type=id;filter();});filters.append(button);typeButtons.push(button);
      }
      const ready=el('button','kitReady','Можно сделать');ready.type='button';ready.addEventListener('click',()=>{state.ready=!state.ready;filter();});filters.append(ready);
      const empty=el('p','kitEmpty','Чертежей не найдено');empty.setAttribute('role','status');
      const detail=el('div','kitRecipeDetail'),navigation=el('nav','kitRecipeNavigation'),back=el('button','kitBack','‹ Все чертежи'),previous=el('button','kitStep','‹'),next=el('button','kitStep','›'),position=el('span','kitRecipePosition');
      navigation.setAttribute('aria-label','Выбранный чертёж');back.type=previous.type=next.type='button';previous.setAttribute('aria-label','Предыдущий чертёж');next.setAttribute('aria-label','Следующий чертёж');
      function show(id,focus){
        const chosen=entries.find(entry=>entry.id===id);state.selected=chosen?.id||null;
        const open=!!chosen;catalog.hidden=bar.hidden=empty.hidden=open;detail.hidden=!open;
        for(const entry of entries)entry.card.hidden=entry!==chosen;
        if(open){const choices=entries.filter(entry=>!entry.button.hidden||entry===chosen),at=choices.indexOf(chosen);position.textContent=(at+1)+' / '+choices.length;previous.disabled=at===0;next.disabled=at===choices.length-1;}
        else filter();
        top();if(focus)(chosen?.title||entries.find(entry=>entry.id===id)?.button||header).focus({preventScroll:true});
      }
      back.addEventListener('click',()=>{const id=state.selected;show(null,false);const button=entries.find(entry=>entry.id===id)?.button;if(button&&!button.hidden)button.focus({preventScroll:true});else header.focus({preventScroll:true});});
      for(const [button,delta] of [[previous,-1],[next,1]])button.addEventListener('click',()=>{const choices=entries.filter(entry=>!entry.button.hidden||entry.id===state.selected),at=choices.findIndex(entry=>entry.id===state.selected);show(choices[at+delta]?.id,true);});
      for(const card of [...grid.querySelectorAll(':scope > [data-craft]')]){
        const id=card.dataset.craft,recipe=definitions.find(r=>r.id===id);if(!recipe)continue;
        const title=card.querySelector(':scope > .nm');let art=card.firstElementChild;
        if(recipe.out._weapon&&window.TERRA_FIELD_KIT_DATA?.weaponIcon){const template=document.createElement('template');template.innerHTML=window.TERRA_FIELD_KIT_DATA.weaponIcon(recipe.out._weapon);if(template.content.firstElementChild){art.replaceWith(template.content.firstElementChild);art=card.firstElementChild;}}
        const available=!card.classList.contains('off');if(!title||!art)continue;
        const button=el('button','kitRecipeChoice'),thumb=el('span','kitRecipeThumb'),stamp=el('span','kitRecipeStamp',available?'Можно сделать':'Нет условий');button.type='button';button.dataset.kitChoose=id;button.dataset.ready=String(available);thumb.append(art.cloneNode(true));button.append(thumb,el('span','kitRecipeName',title.textContent),stamp);catalog.append(button);
        const entry={id,card,title,button,available,type:recipe.out._armor||recipe.out._weapon?'gear':'supplies',name:normalize(recipe.name)};entries.push(entry);button.addEventListener('click',()=>show(id,true));
        card.removeAttribute('data-craft');card.dataset.kitRecipe=id;card.classList.add('kitRecipeSheet');card.hidden=true;title.tabIndex=-1;
        const hero=el('div','kitRecipeHero'),drawing=el('div','kitRecipeArt');drawing.append(art);hero.append(drawing,title,el('span','kitSheetStamp',available?'Можно сделать':'Нет условий'));
        const bill=el('div','kitBill'),billTitle=el('h4','','Материалы');bill.append(billTitle);
        const ingredients=[...card.querySelectorAll(':scope > span:not(.nm):not(.gr):not(.eq)')].find(n=>n.children.length&&n.querySelector('span'));
        const requirements=Object.entries(recipe.need);
        if(ingredients&&ingredients.children.length===requirements.length){
          [...ingredients.children].forEach((row,index)=>{
            const [key,amount]=requirements[index],name=items[key]?.name;if(!name)return;
            row.classList.add('kitNeedRow');row.classList.toggle('kitNeedEnough',(window.game?.p?.inv[key]||0)>=amount);
            const figures=el('b','kitNeedNumber');for(const node of [...row.childNodes])if(node.nodeType===Node.TEXT_NODE)figures.append(node);row.append(el('span','kitNeedName',name),figures);
          });ingredients.classList.add('kitIngredients');bill.append(ingredients);
        }
        const conditions=el('div','kitConditions');for(const node of [...card.querySelectorAll(':scope > .gr,:scope > .eq')]){if(node.classList.contains('eq')&&recipe.st)node.style.color=window.game.stationNear(recipe.st)?'#46582d':'#8b3829';conditions.append(node);}
        const action=el('button','kitBrass kitMake','Изготовить');action.type='button';action.dataset.craft=id;action.disabled=!available;action.setAttribute('aria-label','Изготовить: '+recipe.name);action.addEventListener('click',()=>remember('craft',id,action),true);
        card.append(hero,bill,conditions,action);
      }
      function filter(){
        const query=normalize(state.query);let shown=0;
        for(const entry of entries){entry.button.hidden=!!(query&&!entry.name.includes(query)||state.ready&&!entry.available||state.type!=='all'&&entry.type!==state.type);if(!entry.button.hidden)shown++;}
        for(const button of typeButtons)button.setAttribute('aria-pressed',String(button.dataset.kitType===state.type));ready.setAttribute('aria-pressed',String(state.ready));ready.textContent='Можно сделать · '+entries.filter(entry=>entry.available).length;listCount.textContent=shown+' / '+entries.length;empty.hidden=shown>0||!!state.selected;
      }
      bar.append(searchBar('craft',state,filter),filters,listCount);navigation.append(back,previous,position,next);detail.append(navigation,grid);
      const notes=body.querySelector(':scope > .det');if(notes){const fold=el('details','kitGatherNote');fold.append(el('summary','','Где искать материалы'),notes);body.append(fold);}
      body.prepend(heading,bar,catalog,empty,detail);filter();show(state.selected,false);
    }
    function decorate(){
      queued=false;observer.disconnect();
      try{
        const tab=window.game?.ui?.tab,active=!inv.classList.contains('hidden')&&['items','craft'].includes(tab);inv.classList.toggle('fieldKit',active);header.hidden=!active;if(active)header.textContent=tab==='items'?'ПРИПАСЫ':'МАСТЕРСКАЯ';else pending=null;
        if(active){
          memory();
          if(!body.querySelector(':scope > .kitTitle')){body.classList.remove('kitItems','kitCraft');if(tab==='items')items();else craft();}
          const focus=pending;pending=null;
          if(focus&&!focus.origin.isConnected&&focus.player===window.game?.p&&focus.interaction===interaction){
            const current=document.activeElement,nativeItem=current?.classList?.contains('kitItem')&&current.dataset.kitItem===focus.id;
            if(!current||current===document.body||!current.isConnected||nativeItem||current===inv.querySelector('.x')){
              const button=[...body.querySelectorAll(focus.kind==='use'?'button[data-use]':'button[data-craft]')].find(n=>(n.dataset.use||n.dataset.craft)===focus.id&&!n.disabled);
              (button||body.querySelector('[data-kit-recipe="'+focus.id+'"] .nm')||header)?.focus({preventScroll:true});
            }
          }
        }
      }catch(error){console.error('[field-kit]',error);}
      observer.observe(body,{childList:true});observer.observe(inv,{attributes:true,attributeFilter:['class']});
    }
    function schedule(){if(!queued){queued=true;queueMicrotask(decorate);}}
    window.addEventListener('pointerdown',()=>{if(!inv.classList.contains('hidden'))interaction++;},true);
    window.addEventListener('keydown',event=>{
      if(!inv.classList.contains('hidden'))interaction++;
      const target=event.target,inside=inv.contains(target)||target===document.body||target===document.documentElement;
      if(inside&&event.key==='Escape'&&window.game?.state==='modal'&&window.game.ui.tab==='craft'&&!inv.classList.contains('hidden')&&memory().craft.selected){event.preventDefault();event.stopPropagation();body.querySelector('.kitBack')?.click();}
    },true);
    decorate();
  }
  if(document.readyState==='complete')start();else window.addEventListener('load',start,{once:true});
})();
