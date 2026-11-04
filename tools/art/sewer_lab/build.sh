#!/bin/sh
# Сборка play/assets/sewer/lab/lab_kit.glb и decals.webp.
# Нужны: Python 3 + Pillow + numpy, шрифт Noto Sans CJK SC (NotoSansCJK-Bold.ttc, OFL; путь — LAB_FONT),
# Blender 4.2 (BLENDER), Node + @gltf-transform/core, extensions, cli 4.x (GLTF — путь к CLI).
set -e
D=$(cd "$(dirname "$0")" && pwd); R=$D/../../..
: "${BLENDER:=blender}" "${GLTF:=gltf-transform}" "${LAB_TEX:=/tmp/sewer_lab/tex/}" "${LAB_OUT:=/tmp/sewer_lab/out/lab_raw.glb}"
export LAB_TEX LAB_OUT; mkdir -p "$LAB_TEX" "$(dirname "$LAB_OUT")"
python3 "$D/lab_tex.py"                                    # тайлы, исходники для запекания, decals.png/.webp + decals.json
"$BLENDER" -b --python "$D/build_lab.py" 2>&1 | grep -E "TRIS|Traceback|Error" | grep -v "Cannot read" || true
O=$(dirname "$LAB_OUT")
node "$D/post.mjs" "$LAB_OUT" "$O/a.glb"                    # roughness 1, стекло BLEND, декали MASK, свечение
"$GLTF" prune "$O/a.glb" "$O/a.glb"; "$GLTF" dedup "$O/a.glb" "$O/a.glb"; "$GLTF" meshopt "$O/a.glb" "$R/play/assets/sewer/lab/lab_kit.glb"
cp "$LAB_TEX/decals.webp" "$R/play/assets/sewer/lab/decals.webp"
