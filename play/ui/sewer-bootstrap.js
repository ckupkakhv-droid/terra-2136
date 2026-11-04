/* The module is evaluated before window.load, so saved reward gear is registered
 * before the player can load a save. The legacy sai rewrite is installed as soon
 * as the game exists. UI mounts after game load. */
import './sewer-register.js';
import { installSewers } from './sewers.js';
import { installSaiSave } from './sewer-save.js';
if (window.game) installSaiSave(window.game);
window.addEventListener('load',()=>{
  if (!window.game) return;
  installSaiSave(window.game);
  installSewers(window.game);
},{once:true});
