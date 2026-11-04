// Run: node tests/visual-rng.mjs. Exercises shipped methods, no game saves.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const html = fs.readFileSync(new URL('../play/index.html', import.meta.url), 'utf8');
const patch = fs.readFileSync(new URL('../play/art/visual-fixes.js', import.meta.url), 'utf8');
const between = (a, b) => { const start = html.indexOf(a); assert(start >= 0, a); const end = html.indexOf(b, start); assert(end > start, b); return html.slice(start, end); };
const primitive = {p: [0, 0, 0, 1, 0, 0, 0, 0, 1], n: [0, 1, 0, 0, 1, 0, 0, 1, 0]};
const vector = () => ({x: 0, y: 1, z: 0, set(){return this;}, setFromEuler(){}, getNormalMatrix(){}, applyMatrix3(){return this;}, normalize(){return this;}});
const ctx = vm.createContext({window: {}, console, Math,
 L: {disc: primitive, discH: {...primitive}, box: {...primitive}, vplane: {...primitive}},
 L4: vector(), P4: vector(), O4: vector(), D4: vector(), F4: vector(), Wc: vector(),
 h1: {compose(){}, elements: [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]},
 oh: {r: 1,g: 1,b: 1,set(){this.r=this.g=this.b=1;}}, _e: (v,a,b)=>Math.max(a,Math.min(v,b))});
vm.runInContext(`class Batch { constructor(r){this.r=r;this.p=[];this.n=[];this.c=[];this.a=[];this.sink=0;} Y(){return 0;} ${between('add(t,i,n,s,r,o,a,c,l=0,h=0,u=0,d=.07', '}tri(')} } } globalThis.Batch=Batch;`, ctx);
// The end marker includes native box(), so the fallback TV uses real add jitter.
const nativeAdd = ctx.Batch.prototype.add;
vm.runInContext(`globalThis.Builder=class { ${between('seg(e,t,i,n,s,r,o,a,c,l){', ',graf(').replace('},wire(', '} wire(')} };`, ctx);
ctx.window.TERRA_ART = {};
vm.runInContext(patch, ctx);
ctx.window.TERRA_ART.hook({ue: ctx.Batch, Ie: ctx.Builder, L: ctx.L});
const rng = seed => { let n=seed>>>0, calls=0; const r=()=>{calls++;n=(Math.imul(n,1664525)+1013904223)>>>0;return n/4294967296;}; r.calls=()=>calls;return r; };
const tail = r => Array.from({length: 24},()=>[r(),r(),r()]);
const removed=between('l&&this.ch(.35)&&(', 'this.emit.push').split('&&(')[1];
const consumeWire = vm.runInNewContext(`(function(){${removed.slice(0,-1)};})`);
const drawTV = vm.runInContext(`globalThis.tv=function(${between('tv(t,i){','}nightstand(').slice(3)}};globalThis.tv`,ctx);
let cases=0;
for (let seed=0;seed<128;seed++) {
 for (const color of ['#24383a','#3a4a52','#3a3024','#777777']) for(const jitter of [undefined,0,.07,.2]) {
  const a=rng(seed),b=rng(seed),old=new ctx.Batch(a),fixed=new ctx.Batch(b);
  const args=[color==='#3a3024'?ctx.L.discH:ctx.L.disc,7,0,11,3,1,2,color,0,0,0];
  if(jitter!==undefined)args.push(jitter);
  nativeAdd.apply(old,args);fixed.add(...args);
  assert.equal(b.calls(),a.calls(),`puddle draw count ${color}/${jitter}`);
  assert.deepEqual(tail(b),tail(a),'subsequent seeded placements after puddle');cases++;
 }
 const a=rng(seed),b=rng(seed),legacy=new ctx.Builder();legacy.dt=new ctx.Batch(a);
 legacy.R=(x,y)=>x+a()*(y-x);
 legacy.wire(5,7,6,5+legacy.R(-1,1),.3,6+legacy.R(-1,1),.2);
 const replacement={r:b,R:(x,y)=>x+b()*(y-x)};
 consumeWire.call(replacement);
 assert.equal(a.calls(),7);assert.equal(b.calls(),a.calls(),'removed wire consumed all native draws');
 assert.deepEqual(tail(b),tail(a),'subsequent seeded placements after wire');cases++;
 const c=rng(seed),d=rng(seed),tv={s:new ctx.Batch(c),g:new ctx.Batch(c)};
 drawTV.call(tv,1,2);
 const oldTV=new ctx.Batch(d);oldTV.box(1,0,2,1.2,.6,.5,'#4a3a2a');oldTV.box(1,.6,2,1,.7,.15,'#1a1a1a');
 assert.equal(c.calls(),2);assert.deepEqual(tail(c),tail(d),'subsequent seeded placements after fallback TV');cases++;
}
console.log(`PASS ${cases} deterministic cases: puddles, removed wire, fallback TV; 128 seeds, next 24 placements match native stream.`);
