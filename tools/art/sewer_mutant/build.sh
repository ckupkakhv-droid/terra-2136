#!/bin/sh
# Сборка play/assets/sewer/mutant.glb.
# Нужны: Blender 4.2 (BLENDER), glTF-Transform CLI 4.x (GLTF), распакованные zip Quaternius UBC + UAL1 Standard в $MUT_SRC/ubc и $MUT_SRC/ual.
# 1) python3 tex.py            -> текстуры в $MUT_TEX (Pillow + numpy)
# 2) blender -b --python build.py -> $MUT_OUT (геометрия, риг 53 кости, 10 клипов, запекание атласа 1024²/512²)
# 3) glTF-Transform: prune, dedup, resample, meshopt
set -e
D=$(cd "$(dirname "$0")" && pwd)
: "${BLENDER:=blender}" "${GLTF:=gltf-transform}" "${MUT_OUT:=/tmp/sewer_mutant/mutant_raw.glb}"
export MUT_OUT; mkdir -p "$(dirname "$MUT_OUT")"
"$BLENDER" -b --python "$D/build.py" 2>&1 | grep -E "TRIS|Traceback|Error" | grep -v "Cannot read" || true
T=$(dirname "$MUT_OUT")/t.glb
"$GLTF" prune "$MUT_OUT" "$T"; "$GLTF" dedup "$T" "$T"; "$GLTF" resample "$T" "$T"
"$GLTF" meshopt "$T" "$D/../../../play/assets/sewer/mutant.glb"; rm -f "$T"
