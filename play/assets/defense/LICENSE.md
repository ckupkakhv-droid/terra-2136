# Модели обороны лагеря

| Файл | Источник | Автор | Лицензия | Обработка |
|---|---|---|---|---|
| `turrets.glb` | собственная процедурная геометрия и атлас PBR (albedo, normal, ORM) | Команда «Терры» | права как у игры, отдельная лицензия не выбиралась | `tools/art/turret_gen.py`. Три вида в одном файле: «Спарка ПКМ», «Гвоздомёт», «Огнемёт „Пропан“». Узлы `base`, `lv2`, `lv3` и группа `gun`. Треугольники: ПКМ 1752, гвоздомёт 1310, огнемёт 1140. Атлас 1024² WebP. Надписи на табличках набраны [DejaVu Sans](https://dejavu-fonts.github.io) (уже в благодарностях). |
| `ammo-crate.glb` | Survival Kit 2.0, `box` — https://kenney.nl/assets/survival-kit | Kenney | CC0 1.0 | gltfpack + meshopt |

Прежние модели турелей (Quaternius, Turret Pack, CC0) заменены этим набором и в сборку больше не входят.

CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/
