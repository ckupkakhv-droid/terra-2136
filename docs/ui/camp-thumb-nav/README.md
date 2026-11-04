# [ui] Каркас лагеря под большой палец (PR 1 из плана #11)

Скриншоты: `before-*` — main 6f5aaf0, `after-*` — эта ветка. Headless Chromium, сенсорная эмуляция, `p390` = 390×844, `l844` = 844×390, `p360` = 360×740. `test-*-safe-area.png` — кадры из `tests/camp-mobile.py` с имитацией выреза и полоски жестов (портрет: сверху 47, снизу 34 px; альбом: по бокам 47, снизу 21 px).

## Точки встраивания для разделов-дополнений ([defense] и др.)

`play/ui/camp-mobile.js` создаёт `window.terraCampUI` (version 1):

```js
terraCampUI.registerSection({
  id: 'defense',          // латиница; штатные overview/settlers/build/expansion/more заняты
  native: true,           // true — штатный раздел игры, открывается game.ui.campPanel.select(id)
  label: 'Оборона', icon: '<svg class="gi" …>', order: 1,
  render(container, game) { /* необязательно: дорисовать в container */ },
});
terraCampUI.setBadge('defense', 2, 'bad');   // число на вкладке; tone: ok | warn | bad | idle; 0 — убрать
terraCampUI.openInfo('Турель «Сверчок»', node); // общий лист «i» снизу; Esc/✕ закрывают только его
terraCampUI.closeInfo(); terraCampUI.tab;     // текущая вкладка; terraCampUI.sections()
```

- Контейнер раздела: `#campBody > section.campSection[data-camp-section="<id>"]` со слотами `.campSection__summary` и `.campSection__list`. Для `native: true` контейнер дописывается после штатного содержимого (если задан `render`).
- Классы: `.campItemCard` (`__icon`, `__title`, `__meta`, `__actions`, `data-tone`), `.campMeter[data-kind][data-level]` с `--value: 0..1`, `.campStatusBadge[data-tone]`, `.campInfoButton`, `.campPrimaryAction` (≥ 48 px). Переменные: `--camp-tap`, `--camp-ok/warn/bad/idle`, `--camp-accent`.
- События на `#campPanel`: `terra:camp-tab` (`detail.tab`, при смене вкладки) и `terra:camp-refresh` (после каждой штатной перерисовки).
- Если вкладок больше, чем помещается без прокрутки (по 48 px), дополнительные разделы показываются карточками в «Ещё».
- Приказы — только через штатные функции игры; формат сохранений не меняется.
