/* The module is evaluated before window.load, so saved reward gear is registered
 * before the native game constructs its save store. UI mounts after game load. */
import './sewer-register.js';
import { installSewers } from './sewers.js';
window.addEventListener('load',()=>{
  if(window.game)installSewers(window.game);
},{once:true});
