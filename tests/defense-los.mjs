// Regression: a turret ray grazing a wall must match native solidAt tolerance.
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { test } from 'node:test';
import { strict as assert } from 'node:assert';
const source=readFileSync(new URL('../play/ui/defense.js',import.meta.url),'utf8');
const a=source.indexOf('  function losBlocked('),b=source.indexOf('  function eachEnemyIn(',a);
assert.ok(a>=0 && b>a,'defense line-of-sight function not found');
function fixture(walls) {
  let full=0;
  const world={
    query(x0,z0,x1,z1,accept) {return walls.some(w=>w.x0<=x1&&w.x1>=x0&&w.z0<=z1&&w.z1>=z0&&accept(w));},
    segHit(x,z,ex,ez,h) {
      full++; const dx=ex-x,dz=ez-z,n=Math.max(1,Math.ceil(Math.hypot(dx,dz)/.35));
      for(let i=1;i<=n;i++){const xx=x+dx*i/n,zz=z+dz*i/n;if(this.query(xx-.01,zz-.01,xx+.01,zz+.01,w=>w.h>=h))return i/n;}
      return -1;
    },
  };
  const blocked=runInNewContext('('+source.slice(a,b).trim()+')',{game:{world},S:{}});
  return {world,blocked,full:()=>full};
}
test('grazing and axis-aligned shots use the same wall tolerance as native',()=>{
  for(const z of [-.02,-.01,-.005,0,.005,.01,.02]) {
    const f=fixture([{x0:1,x1:2,z0:z,z1:z+.1,h:3}]);
    const expected=f.world.segHit(0,0,3,0,2.7)>=0;
    assert.equal(f.blocked(0,0,3,0),expected,`wall starts at z=${z}`);
  }
  const f=fixture([{x0:.005,x1:.1,z0:1,z1:2,h:3}]);
  assert.equal(f.blocked(0,0,0,3),true,'vertical shot grazing wall');
});
test('clear line skips the full trace, low obstacles do not block',()=>{
  const f=fixture([{x0:1,x1:2,z0:0,z1:1,h:1}]);
  assert.equal(f.blocked(0,0,3,0),false);
  assert.equal(f.full(),0);
});
