/* Publish the native hero when its own asset is ready. Unrelated model loads
 * keep their normal lifecycle; existing cinematic visibility stays native. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{};
  ART.readyHero=function(game) {
    if(!game||game.heroInst||!game.glb?.hero||game.state!=='play'||
        game.dungeonTransition||typeof game.refreshModelMode!=='function')return false;
    game.refreshModelMode(true);
    return !!game.heroInst;
  };
})();
