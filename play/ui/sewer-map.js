/* Municipal collector schematic. Geometry reflects the actual connected sectors. */
export function drawSewerMap(host, cells, {seen, pumps, playerIndex = -1}) {
  const ns='http://www.w3.org/2000/svg';
  const node=(tag,attributes={},text)=>{
    const element=document.createElementNS(ns,tag);
    for(const [name,value] of Object.entries(attributes))element.setAttribute(name,String(value));
    if(text!==undefined)element.textContent=text;
    return element;
  };
  const svg=node('svg',{viewBox:'0 0 400 405',role:'img','aria-labelledby':'sewerPlanTitle sewerPlanDescription'});
  svg.append(node('title',{id:'sewerPlanTitle'},'План Южного коллектора'),node('desc',{id:'sewerPlanDescription'},'Связанные проходы. Лестница в первом секторе, насосы в двух камерах. Жёлтая метка обозначает ваше положение. Пунктир — неисследованный участок.'));
  const point=([x,z])=>[50+x*100,50+z*100];
  for(let i=1;i<cells.length;i++){
    const [x,z]=point(cells[i-1]),[a,b]=point(cells[i]);
    svg.append(node('path',{d:`M${x} ${z} L${a} ${b}`,class:'sewerPipe'}));
    if(seen.has(i-1)&&seen.has(i))svg.append(node('path',{d:`M${x} ${z} L${a} ${b}`,class:'sewerPipeExplored'}));
  }
  cells.forEach((cell,index)=>{
    const [x,y]=point(cell),explored=seen.has(index),pump=[1,3].includes(index);
    const group=node('g',{class:`sewerCell ${explored?'explored':''}`,transform:`translate(${x},${y})`});
    group.append(node('circle',{r:23,class:'sewerJunction'}));
    const icon=index===0?'↑':pump?(pumps.has(index)?'✓':'○'):explored?'·':'?';
    const label=index===0?'Лестница':pump?`Насос ${index===1?'I':'II'}`:index===2&&explored?'Объект 7':index===6?(explored?'Ткань':'Неизвестно'):`Проход ${index}`;
    group.append(node('text',{y:6,'text-anchor':'middle',class:'sewerPlanIcon'},icon),node('text',{y:43,'text-anchor':'middle',class:'sewerPlanLabel'},label));
    if(index===playerIndex)group.append(node('circle',{r:30,class:'sewerPlayer','aria-label':'Вы здесь'}));
    svg.append(group);
  });
  const legend=document.createElement('p');legend.className='sewerLegend';legend.textContent='Жёлтое кольцо — вы · ✓ насос включён · пунктир — не исследовано';
  host.replaceChildren(svg,legend);
}
