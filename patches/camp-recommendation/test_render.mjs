import test from 'node:test';
import assert from 'node:assert/strict';
import { renderResidentRecommendation } from './recommendation.mjs';
// Minimal DOM doubles: interaction contract only, not browser/layout validation.
class Element {
  constructor(tag) { this.tagName=tag;this.children=[];this.dataset={};this.attrs={};this.listeners={};this.disabled=false; }
  append(...items) { this.children.push(...items); }
  setAttribute(name,value) { this.attrs[name]=value; }
  addEventListener(name,handler) { this.listeners[name]=handler; }
}
globalThis.document={createElement:tag=>new Element(tag)};
const camp={settlers:{a:{id:'a',name:'<img src=x onerror=alert(1)>',efficiency:2},b:{id:'b',name:'Борис',reason:'Ручной отдых'}}};
const api={reason:(_,s)=>s.reason||'',efficiency:(_,s)=>s.efficiency};
const task={key:'water',label:'Вода'};
const button=root=>root.children.find(c=>c.tagName==='button');
test('renders explicit name and zero assignment cost using text nodes',()=>{
  const root=renderResidentRecommendation(camp,task,api,()=>{});
  assert(root.children.some(c=>c.textContent==='Лучший свободный: '+camp.settlers.a.name));
  assert(root.children.some(c=>c.textContent==='Цена приказа: 0 ресурсов.'));
  assert.equal(button(root).type,'button');
  assert(!('innerHTML' in root));
  assert.equal(root.children.at(-1).tagName,'details');
});
test('click forwards only displayed resident and task to the existing handler',()=>{
  let received;
  const root=renderResidentRecommendation(camp,task,api,r=>received=r);
  button(root).listeners.click();
  assert.deepEqual(received,{residentId:'a',task:'water',target:undefined});
});
for(const options of [{pending:true},{available:false}])test('unavailable action does not dispatch: '+JSON.stringify(options),()=>{
  let called=false;const root=renderResidentRecommendation(camp,task,api,()=>called=true,options);
  assert.equal(button(root).disabled,true);button(root).listeners.click();assert.equal(called,false);
});
test('no candidate means no assignment button',()=>{
  const root=renderResidentRecommendation({settlers:{b:camp.settlers.b}},task,api,()=>{});
  assert.equal(button(root),undefined);
});
