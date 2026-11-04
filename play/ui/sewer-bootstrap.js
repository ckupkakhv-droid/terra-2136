/* Register saved reward gear before the constructor. The archive startup gate
 * mounts the legacy sai rewrite and UI as soon as the game is ready. */
import './sewer-register.js';
import { installSewers } from './sewers.js';
import { installSaiSave } from './sewer-save.js';
if (window.game) installSaiSave(window.game);
function mount() {
  if (!window.game) return;
  installSaiSave(window.game);
  installSewers(window.game);
}
if(window.TERRA_STARTUP)window.TERRA_STARTUP.then(mount,()=>{});
else if(document.readyState==='complete')mount();
else window.addEventListener('load',mount,{once:true});
