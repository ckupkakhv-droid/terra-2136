// материалы под игру: roughness 1 / metalness 0 (игра всё равно так ставит), стекло BLEND, декали MASK
import {NodeIO} from '@gltf-transform/core'; import {ALL_EXTENSIONS,KHRMaterialsEmissiveStrength} from '@gltf-transform/extensions';
const [,,inp,out]=process.argv; const io=new NodeIO().registerExtensions(ALL_EXTENSIONS); const d=await io.read(inp);
const es=d.createExtension(KHRMaterialsEmissiveStrength);
for(const m of d.getRoot().listMaterials()){m.setRoughnessFactor(1).setMetallicFactor(0).setDoubleSided(true);
 const n=m.getName();
 if(n==='lab_glass'){m.setAlphaMode('BLEND').setBaseColorFactor([.55,.85,.8,.22]);}
 else if(n==='lab_decals'){m.setAlphaMode('MASK').setAlphaCutoff(.5);}
 else m.setAlphaMode('OPAQUE');
 if(n==='lab_glow_teal'){m.setEmissiveFactor([.06,.42,.34]);m.setBaseColorFactor([.08,.35,.3,1]);}
 if(n==='lab_glow_warm'){m.setEmissiveFactor([1,.72,.38]);m.setExtension('KHR_materials_emissive_strength',es.createEmissiveStrength().setEmissiveStrength(3));}
 if(!/glow/.test(n))m.setEmissiveFactor([0,0,0]);}
await io.write(out,d);
