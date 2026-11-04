/* Native weapon geometry: hand/grip origin matches Xg's katana at y≈-.66.
 * Both sai point along -Y. The native builder merges vertex colours/normals;
 * this factory needs no textures, scene nodes, loaders or extra Three copy.
 */
export function makeSaiGeometry(bridge) {
  const shapes = bridge?.shapes;
  if (!bridge?.WeaponBuilder || !shapes?.cyl || !shapes?.cylT || !shapes?.cone4 || !shapes?.ico) {
    throw new Error('Native sai geometry bridge is unavailable');
  }
  const geometry = new bridge.WeaponBuilder();
  const steel = '#a8afaa', darkSteel = '#69756f', edge = '#d5d8c9';
  const wrap = '#803d34', wornWrap = '#a16b50';

  function sai(x, z) {
    // Short wrapped handle, pommel and the steel collar above the yoku.
    geometry.o(shapes.cyl, x, -.665, z, .052, .225, .052, '#40342b');
    for (let i = 0; i < 7; i++) {
      geometry.o(shapes.cyl, x, -.568 - i * .03, z, .058, .019, .058,
        i === 1 || i === 5 ? wornWrap : wrap);
    }
    geometry.o(shapes.ico, x, -.532, z, .067, .045, .067, darkSteel);
    geometry.o(shapes.cyl, x, -.787, z, .065, .035, .065, darkSteel);

    // Central tapered steel spike and its sharp, downward-facing tip.
    geometry.o(shapes.cylT, x, -.995, z, .047, .36, .047, steel, Math.PI);
    geometry.o(shapes.cone4, x, -1.215, z, .035, .09, .035, edge, Math.PI);
    // A narrow polished ridge helps the short spike read in the dark HUD view.
    geometry.b(x, -.985, z + .023, .011, .31, .004, edge);

    // Each sai has two hooked side prongs, joined by one solid crossguard.
    geometry.b(x, -.807, z, .215, .03, .047, darkSteel);
    for (const side of [-1, 1]) {
      geometry.b(x + side * .092, -.83, z, .035, .065, .04, steel, 0, 0, side * .28);
      geometry.o(shapes.cylT, x + side * .105, -.916, z, .031, .145, .031, steel, Math.PI);
      geometry.o(shapes.cone4, x + side * .101, -1.006, z, .03, .06, .03, edge,
        Math.PI, 0, side * -.14);
    }
  }

  // Distinct silhouettes, held as a compact pair rather than one broad blade.
  sai(-.155, -.025);
  sai(.155, .025);
  return geometry.geometry();
}
