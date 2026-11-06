/* Альбом разделов, путь развития и доска нарядов. Штатные команды не заменяются. */
(() => {
  'use strict';
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;};
  const names={delivery:'Доставка',clear:'Зачистка',escort:'Конвой',bounty:'Охота',rescue:'Спасение',liberate:'Освободить район',defend:'Защитить блокпост'};
  const goals={delivery:'Доставить груз',clear:'Зачистить район',escort:'Сопроводить конвой',bounty:'Устранить цель',rescue:'Освободить пленного',liberate:'Освободить район',defend:'Защитить блокпост'};
  const states={offered:'Доступен',squad:'Отряд в пути',player:'Личное задание',done:'Выполнен',failed:'Провален'};
  const artFor={delivery:'convoy',escort:'convoy',clear:'defense',bounty:'trail',rescue:'trail',liberate:'outpost',defend:'defense'};
  const roman=n=>['','I','II','III','IV','V'][n]||String(n);
  const art=(name,cls='')=>{const n=el('span','dispatchArt '+cls);n.dataset.dispatchArt=name;n.setAttribute('aria-hidden','true');return n;};
  const person=(node,s)=>window.terraCampFieldbook?.portrait(node,s);
  function revealTab(rail){const tab=rail.querySelector('[aria-selected=true]');if(!tab)return;const horizontal=getComputedStyle(rail).flexDirection==='row';rail.setAttribute('aria-orientation',horizontal?'horizontal':'vertical');if(horizontal){const t=tab.getBoundingClientRect(),r=rail.getBoundingClientRect();if(t.left<r.left)rail.scrollLeft-=r.left-t.left;else if(t.right>r.right)rail.scrollLeft+=t.right-r.right;}}
  function start(){
    const panel=document.getElementById('campPanel'),body=panel?.querySelector('#campBody');if(!body)return;
    let selected=null,owner=null,queued=false;
    const chooseTab=id=>{if(!panel.classList.contains('hidden')&&window.game?.state==='modal')window.game.ui.campPanel.select(id);};
    function index(root){
      if(root.classList.contains('dispatchIndex')&&[...root.querySelectorAll(':scope > [data-camp-tab]')].every(c=>c.dataset.dispatchIndex))return;
      root.classList.add('dispatchIndex');root.setAttribute('aria-label','Все разделы лагеря');
      const order=['defense','tech','territories','contracts','power','warehouses','pine'];
      const images={defense:'defense',tech:'tech',territories:'map',contracts:'convoy',power:'power',warehouses:'warehouse',pine:'outpost'};
      const cards=[...root.querySelectorAll(':scope > [data-camp-tab]')];
      cards.sort((a,b)=>{const x=order.indexOf(a.dataset.campTab),y=order.indexOf(b.dataset.campTab);return(x<0?99:x)-(y<0?99:y);});
      for(const card of cards){
        if(card.dataset.dispatchIndex)continue;card.dataset.dispatchIndex='1';const id=card.dataset.campTab;if(id==='defense')card.classList.add('campMobileKeep');card.prepend(art(images[id]||'map','dispatchIndexArt'));
        const text=el('span','dispatchIndexText');for(const n of [...card.children])if(n.matches('strong,small'))text.append(n);
        const arrow=el('span','dispatchIndexArrow','›');arrow.setAttribute('aria-hidden','true');card.append(text,arrow);root.append(card);
      }
      root.append(...cards);
    }
    function expansion(root){
      const task=root.querySelector(':scope > .campCard');if(!task||task.classList.contains('dispatchTask'))return;
      const c=window.game?.p?.camp,api=window.TERRA_CAMP_ALBUM_DATA,cfg=window.TERRA_DEFENSE_CTX?.B.camp;
      if(!c||!api||!cfg)return;
      const route=api.progression(c),step=api.expansion(window.game);if(!route)return;
      root.classList.add('dispatchExpansion');task.classList.add('dispatchTask');task.dataset.dispatchStage=step?.stage||'';
      const journey=el('ol','dispatchJourney');journey.setAttribute('aria-label','Уровни поселения');
      cfg.tiers.forEach((tier,i)=>{const item=el('li','');item.dataset.reached=String(i<c.tier);if(i===c.tier-1)item.setAttribute('aria-current','step');item.append(el('span','dispatchTierMark',i<c.tier-1?'✓':roman(i+1)),el('strong','',tier.name));journey.append(item);});
      const scene=el('figure','dispatchCampScene');scene.append(art(c.tier<3?'camp':'outpost'));
      const caption=el('figcaption','');caption.append(el('strong','',route.name),el('span','','Уровень '+roman(route.current)));scene.append(caption);
      const next=route.next[0],note=el('section','dispatchNext');note.setAttribute('aria-label',next?'Следующий уровень поселения':'Развитие поселения');
      if(next){
        const drawing=el('div','dispatchNextDrawing');drawing.setAttribute('aria-hidden','true');
        for(const name of ['watch','sawmill']){const image=el('span','fbBlueprintArt');image.dataset.plan=name;drawing.append(image);}
        const title=el('h3','','Следующая ступень');title.append(el('strong','',next.name+' · '+roman(next.tier)));
        const checks=el('ul','dispatchTierChecks');checks.setAttribute('aria-label','Условия следующего уровня');
        for(const goal of next.goals.filter(g=>g.max>0)){
          const li=el('li','');li.dataset.met=String(goal.ok);li.append(el('span','dispatchCheck',goal.ok?'✓':'○'),el('span','',goal.label.trim()),el('b','',goal.value+' / '+goal.max));checks.append(li);
        }
        note.append(title,drawing,checks);
      }else note.append(el('h3','','Поселение достигло высшей ступени'),art('outpost'));
      root.prepend(journey,scene,note);
    }
    function contracts(board){
      if(board.dataset.dispatchPrepared)return;
      const c=window.game?.p?.camp;if(!c?.contracts)return;
      const offers=[...c.contracts.active,...c.contracts.board,...c.contracts.history.filter(x=>['done','failed'].includes(x.state)).slice(-3).reverse()];
      const cards=[...board.querySelectorAll(':scope > .contractCard')];
      if(cards.length!==offers.length)return; // Changed native renderer: keep every original card visible.
      board.dataset.dispatchPrepared='1';board.classList.add('dispatchBoard');
      const legends=el('header','dispatchBoardSummary');
      for(const legend of [...board.querySelectorAll(':scope > .contractLegend')])legends.append(legend);
      const rep=el('small','dispatchBoardRep','Репутация '+Math.floor(c.rep||0));rep.id='dispatch-board-reputation';legends.append(rep);const reroll=legends.querySelector('button');if(reroll){reroll.setAttribute('aria-describedby',rep.id);if(reroll.disabled)reroll.title=c.contracts.rerollDay===c.contracts.day?'Доска уже обновлена сегодня':'Недостаточно репутации';}board.prepend(legends);
      const hunt=board.querySelector(':scope > .campHunting');
      if(hunt){const fold=el('details','dispatchHunt');fold.open=!!c.hunting?.active;fold.append(el('summary','','Охота с силками'),hunt);board.append(fold);}
      if(!cards.length){board.append(el('p','dispatchEmpty','Новых нарядов пока нет.'));return;}
      const deck=el('div','dispatchDeck'),rail=el('nav','dispatchContractRail'),sheets=el('div','dispatchSheets'),control=el('div','dispatchDeckControls');
      rail.setAttribute('role','tablist');rail.setAttribute('aria-label','Контракты и результаты');
      const previous=el('button','','‹'),count=el('output','dispatchDeckCount'),next=el('button','','›');
      previous.type=next.type='button';previous.setAttribute('aria-label','Предыдущий контракт');next.setAttribute('aria-label','Следующий контракт');control.append(previous,count,next);
      const tabs=[];let current=offers.findIndex(o=>o.id===selected);if(current<0)current=0;
      function show(index,focus=false){
        current=Math.max(0,Math.min(cards.length-1,index));selected=offers[current].id;
        cards.forEach((card,i)=>{card.hidden=i!==current;tabs[i].setAttribute('aria-selected',String(i===current));tabs[i].tabIndex=i===current?0:-1;});
        count.textContent=String(current+1).padStart(2,'0')+' / '+String(cards.length).padStart(2,'0');previous.disabled=current===0;next.disabled=current===cards.length-1;
        revealTab(rail);if(focus){tabs[current].focus({preventScroll:true});tabs[current].scrollIntoView({block:'nearest',inline:'nearest'});}
      }
      cards.forEach((card,i)=>{
        const offer=offers[i],type=offer.type;card.dataset.contractId=offer.id;card.dataset.contractState=offer.state;card.dataset.contractType=type;
        card.id='dispatch-contract-'+i;card.setAttribute('role','tabpanel');card.setAttribute('aria-labelledby','dispatch-tab-'+i);
        const tab=el('button','dispatchContractTab');tab.type='button';tab.id='dispatch-tab-'+i;tab.setAttribute('role','tab');tab.setAttribute('aria-controls',card.id);
        tab.append(art(artFor[type]||'map'),el('strong','',names[type]||type),el('small','',states[offer.state]||offer.state));tab.dataset.contractId=offer.id;
        tab.addEventListener('click',()=>show(i));tabs.push(tab);rail.append(tab);
        const head=card.querySelector('.contractHead'),risk=head?.querySelector('small');
        if(head){head.querySelector('b')?.setAttribute('role','heading');head.querySelector('b')?.setAttribute('aria-level','3');head.after(art(artFor[type]||'map','dispatchContractImage'));}
        const stamp=el('span','dispatchStateStamp',states[offer.state]||offer.state);stamp.dataset.state=offer.state;card.prepend(stamp);
        if(risk){
          const facts=el('div','dispatchContractFacts'),danger=el('span','dispatchDanger');danger.setAttribute('aria-hidden','true');danger.style.setProperty('--danger',Math.max(0,Math.min(1,offer.risk)));facts.append(el('span','','Опасность / срок'),risk,danger);card.querySelector('.dispatchContractImage')?.after(facts);
        }
        const objective=el('div','dispatchObjective');objective.append(el('span','',goals[type]||names[type]||type));
        if(Number.isFinite(offer.goal)&&offer.goal>0)objective.append(el('b','',(offer.progress||0)+' / '+offer.goal));
        const region=card.querySelector('.contractRegion');region?.classList.add('dispatchPrimaryRegion');region?.after(objective);
        for(const reward of card.querySelectorAll('.contractReward > span'))if(reward.title)reward.append(el('small','dispatchRewardName',reward.title));
        const members=[...card.querySelectorAll('.contractSquad > button')],residents=Object.values(c.settlers).filter(s=>!s.dead);
        if(members.length===residents.length)members.forEach((button,index)=>{
          const s=residents[index],photo=el('span','dispatchMemberPhoto');person(photo,s);button.prepend(photo);button.append(el('span','dispatchMemberName',s.name.split(' ')[0]));button.dataset.residentId=s.id;
        });
        for(const action of card.querySelectorAll('.contractActions > button')){
          action.dataset.dispatchAction=action.textContent==='Взять'?'take':action.textContent==='Отправить'?'send':'open';
          action.setAttribute('aria-label',action.textContent+': '+(names[type]||type));
        }
        sheets.append(card);
      });
      previous.addEventListener('click',()=>{show(current-1);sheets.scrollIntoView({block:'nearest'});});next.addEventListener('click',()=>{show(current+1);sheets.scrollIntoView({block:'nearest'});});
      rail.addEventListener('keydown',event=>{
        if(!event.target.matches('[role=tab]'))return;
        if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)){
          event.preventDefault();event.stopPropagation();const index=tabs.indexOf(event.target);show(event.key==='Home'?0:event.key==='End'?cards.length-1:(index+(['ArrowLeft','ArrowUp'].includes(event.key)?-1:1)+cards.length)%cards.length,true);
        }else if(['Enter',' '].includes(event.key))event.stopPropagation();
      });
      deck.append(rail,control,sheets);legends.after(deck);show(current);
    }
    window.addEventListener('resize',()=>requestAnimationFrame(()=>body.querySelectorAll('.dispatchContractRail').forEach(revealTab)));
    const observer=new MutationObserver(schedule);
    function decorate(){
      queued=false;observer.disconnect();
      try{
        if(!panel.classList.contains('hidden')){
          if(owner!==window.game?.p){owner=window.game?.p;selected=null;}
          const root=body.querySelector(':scope > .campMore');if(root)index(root);
          const expansionRoot=body.querySelector(':scope > .campExpansionNavigation');if(expansionRoot)expansion(expansionRoot);
          const board=body.querySelector(':scope > .contractBoard');if(board)contracts(board);
        }
      }catch(error){console.error('[camp-dispatch]',error);}
      observer.takeRecords();observer.observe(body,{childList:true,subtree:true});
    }
    function schedule(){if(!queued){queued=true;queueMicrotask(decorate);}}
    panel.addEventListener('terra:camp-tab',schedule);panel.addEventListener('terra:camp-refresh',schedule);
    new MutationObserver(schedule).observe(panel,{attributes:true,attributeFilter:['class']});decorate();
  }
  if(document.readyState==='complete')start();else window.addEventListener('load',start,{once:true});
})();
