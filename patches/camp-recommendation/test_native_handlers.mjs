import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import { recommendResident } from './recommendation.mjs';
const source = fs.readFileSync(new URL('../terra-scout-class-20261104.html', import.meta.url), 'utf8');
const extract = (start, end) => {
  const a=source.indexOf(start), b=source.indexOf(end,a+start.length);
  assert(a>=0&&b>a, 'native handler anchors must be present');
  return source.slice(a,b);
};
// Native availability and efficiency code, with explicit dependency fixtures.
// This is targeted unit coverage, not a full simulation or browser test.
const native=vm.createContext({
  B:{camp:{utility:{restStart:25},start:{need:100},work:{moraleFloor:.35,needsFloor:.25,skillBonus:.1}}},
  Th:(c,s)=>c.fieldCompanion?.settlerId===s.id,
  EO:(c,s)=>s.job==='idle'&&s.order?.stick&&!s.order?.courier&&c.warehouseCourier?.settlerId!==s.id,
  SO:c=>c.targets||[], De:(c,id)=>c.sites?.[id],
  Vs:(s,key)=>(s.traitEffects?.[key]??1), Vu:()=>1,
});
vm.runInContext(extract('function fl(e,t){','function SO(e){')+extract('function Tm(e,t,i){','function CO(e,t,i){')+extract('function ya(e,t,i){','function dP(e,t='),native);
const worker=(id,extra={})=>({id,name:id,job:'idle',status:'idle',order:{},skills:{gather:4,build:4},morale:100,needs:{food:100,water:100,rest:100,safety:100},...extra});
const camp=(...people)=>({sim:{tick:50},buildings:{},res:{wood:10},settlers:Object.fromEntries(people.map(p=>[p.id,p]))});
const api={reason:native.Tm,efficiency:native.ya};
test('actual baseline reason code protects companion, manual/automatic rest, injury, courier, cargo and jobs',()=>{
  const c=camp(worker('free'),worker('companion',{skills:{gather:99}}),worker('manual',{order:{stick:1}}),worker('rest',{order:{rest:1}}),worker('tired',{needs:{rest:20}}),worker('wounded',{wounded:true}),worker('injured',{injuredUntil:60}),worker('courier'),worker('cargo',{trip:{amount:3}}),worker('mission',{mission:'expedition'}),worker('busy',{job:'gather:wood'}),worker('captive',{captive:true}));
  c.fieldCompanion={settlerId:'companion',mode:'follow'};c.warehouseCourier={settlerId:'courier'};
  const before=JSON.stringify(c),result=recommendResident(c,{key:'water'},api);
  assert.equal(result.candidate.id,'free');assert.equal(result.blocked.length,11);assert.equal(JSON.stringify(c),before);
  assert.match(result.blocked.find(p=>p.id==='companion').reason,/Напарник/);
  assert.match(result.blocked.find(p=>p.id==='courier').reason,/Курьер/);
});
test('actual productivity formula ranks health and work traits rather than raw level',()=>{
  const c=camp(worker('high-skill-unwell',{skills:{gather:10},morale:30,needs:{food:30,water:30,rest:60,safety:30}}),worker('fit',{skills:{gather:3},traitEffects:{work:1.2}}));
  assert.equal(recommendResident(c,{key:'wood'},api).candidate.id,'fit');
});
test('actual warehouse-specific restrictions remain in force',()=>{
  const c=camp(worker('gatherer',{prof:'gatherer',pos:{x:0,z:0}}),worker('far-builder',{prof:'builder',pos:{x:100,z:0}}),worker('near-engineer',{prof:'engineer',pos:{x:5,z:0}}));
  c.targets=[{id:'warehouse:zone'}];c.buildings['warehouse:zone']={type:'warehouse'};c.sites={'outpost:zone':{center:{x:0,z:0}}};
  const result=recommendResident(c,{key:'build',target:'warehouse:zone'},api);
  assert.equal(result.candidate.id,'near-engineer');assert.equal(result.blocked.length,2);
});
const quickSource=extract('async function f(m){if(o||Date.now()-a<400','let p=m=>{');
function quickFixture(){
  let release;const waiting=new Promise(r=>release=r);let ensures=0,assigns=0;const requests=[];
  const context=vm.createContext({Date:{now:()=>10000},oi:g=>({player:g.p,camp:g.p.camp,state:g.state}),ie:()=>{ensures++;return waiting;}});
  vm.runInContext(`let o=false,a=0,t={p:{camp:{}},state:'modal',camp:{}},i={isConnected:true,setAttribute(){},querySelector(){return null}},r=1,n=0,h='',u=()=>({scrollTop:42}),d=()=>{};${quickSource};globalThis.fixture={f,game:t,root:i,invalidate(){r++},notice:()=>h,pending:()=>o};`,context);
  context.fixture.game.camp.assignResidentTask=(request)=>{assigns++;requests.push({...request});return {ok:true}};
  return {...context.fixture,context,release,counts:()=>({ensures,assigns}),requests};
}
test('existing native async handler absorbs repeated taps and preserves named request',async()=>{
  const q=quickFixture(),request={residentId:'free',task:'water'};
  const one=q.f(request),two=q.f(request);q.release({ok:true});await Promise.all([one,two]);await q.f({residentId:'other',task:'water'});
  assert.deepEqual(q.counts(),{ensures:1,assigns:1});assert.equal(q.requests[0].residentId,'free');assert.match(q.notice(),/Приказ сохранён/);
});
for(const condition of ['detached','view-changed','player-changed','state-changed'])test('existing native handler refuses stale '+condition,async()=>{
  const q=quickFixture(),pending=q.f({residentId:'free',task:'water'});
  if(condition==='detached')q.root.isConnected=false;
  if(condition==='view-changed')q.invalidate();
  if(condition==='player-changed')q.game.p={camp:{}};
  if(condition==='state-changed')q.game.state='play';
  q.release({ok:true});await pending;assert.equal(q.counts().assigns,0);
});
test('existing native handler does not commit when save-session activation fails',async()=>{
  const q=quickFixture(),pending=q.f({residentId:'free',task:'water'});q.release({ok:false,status:'rejected',reason:'session-blocked'});await pending;
  assert.equal(q.counts().assigns,0);assert.doesNotMatch(q.notice(),/Приказ сохранён/);
});
test('existing native handler reports uncertain storage without retrying',async()=>{
  const q=quickFixture();let calls=0;q.game.camp.assignResidentTask=()=>{calls++;return {ok:false,status:'uncertain'}};
  const pending=q.f({residentId:'free',task:'water'});q.release({ok:true});await pending;await q.f({residentId:'free',task:'water'});
  assert.equal(calls,1);assert.match(q.notice(),/Запись не подтверждена/);
});
