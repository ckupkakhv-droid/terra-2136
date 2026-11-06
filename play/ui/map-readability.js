/* Читаемость поясов и подписей существующей карты. Данные и жесты не меняются. */
(() => {
  'use strict';
  const RANKS = ['I', 'II', 'III', 'IV', 'V'];

  function start() {
    const map = document.getElementById('wmap');
    const leg = document.getElementById('wmLeg');
    const body = document.getElementById('wmBody');
    if (!map || !leg || !body || map.dataset.mapReadability) return;
    map.dataset.mapReadability = '1';

    const layer = document.createElement('div');
    layer.id = 'wmEdgeNames';
    body.append(layer);

    const observer = new MutationObserver(() => decorate(leg));
    observer.observe(leg, {childList: true});
    decorate(leg);

    let logged = false;
    function tick() {
      try {
        if (!map.classList.contains('hidden')) {
          const narrow = window.innerWidth <= 720 || window.innerHeight <= 520;
          map.classList.toggle('mapCompact', narrow);
          placeGoal(narrow);
          placeLegend(leg, narrow);
          markHere(leg);
          placeNames(layer);
        } else {
          layer.replaceChildren();
        }
      } catch (error) {
        if (!logged) { logged = true; console.error('[map-readability]', error); }
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function decorate(leg) {
    const threat = [...leg.querySelectorAll(':scope > h4')].find(node => node.textContent.trim() === 'Угроза');
    if (!threat || threat.nextElementSibling?.classList.contains('mapBelt')) return;
    let node = threat.nextElementSibling;
    let tier = 0;
    while (node && node.tagName === 'DIV' && tier < 5) {
      const next = node.nextElementSibling;
      const name = node.textContent.replace(/^[\s\u2620]+/u, '').trim();
      if (!name) { node = next; continue; }
      tier += 1;
      const color = node.style.color;
      node.classList.add('mapBelt');
      node.dataset.tier = String(tier);
      if (color) node.style.setProperty('--belt', color);
      const mark = document.createElement('i');
      mark.className = 'mapBeltMark';
      mark.setAttribute('aria-hidden', 'true');
      const rank = document.createElement('b');
      rank.className = 'mapBeltRank';
      rank.textContent = RANKS[tier - 1];
      const label = document.createElement('span');
      label.className = 'mapBeltName';
      label.textContent = name;
      node.replaceChildren(mark, rank, label);
      node = next;
    }
  }

  function placeGoal(narrow) {
    const goal = document.getElementById('wmGoalT');
    const reg = document.getElementById('wmReg');
    if (!goal || !reg) return;
    if (!narrow || !goal.textContent.trim()) {
      goal.style.top = '';
      goal.style.maxWidth = '';
      return;
    }
    const box = reg.getBoundingClientRect();
    goal.style.top = Math.round(box.bottom + 4) + 'px';
    goal.style.maxWidth = 'min(260px, calc(100vw - 78px))';
  }

  function placeLegend(leg, narrow) {
    if (!narrow || leg.classList.contains('hidden')) {
      leg.style.left = '';
      leg.style.top = '';
      leg.style.width = '';
      leg.style.maxHeight = '';
      leg.style.right = '';
      return;
    }
    const canvas = document.getElementById('wmC')?.getBoundingClientRect();
    const goal = document.getElementById('wmGoalT')?.getBoundingClientRect();
    const controls = document.getElementById('wmCtl')?.getBoundingClientRect();
    const sheet = document.getElementById('wmSheet')?.getBoundingClientRect();
    if (!canvas || !controls) return;
    const gap = 8;
    const player = {x: canvas.left + canvas.width / 2, y: canvas.top + canvas.height / 2, r: 62};
    const top = Math.max(goal && goal.height ? goal.bottom : canvas.top, canvas.top) + gap;
    const left = canvas.left + gap;
    const footer = 48;
    const sheetOnBottom = sheet && sheet.width > 40 && sheet.top > canvas.top + 80 && sheet.left < canvas.left + 40;
    const mapBottom = (sheetOnBottom ? Math.min(canvas.bottom, sheet.top) : canvas.bottom) - footer;
    const above = player.y - player.r - gap - top;
    const bandRight = Math.min(controls.left, canvas.right) - gap;
    if (above >= 96 && bandRight - left >= 150) {
      setBox(leg, left, top, bandRight - left, above);
      return;
    }
    const sideRight = player.x - player.r - gap;
    if (sideRight - left >= 132) {
      setBox(leg, left, top, sideRight - left, Math.max(96, mapBottom - top));
      return;
    }
    setBox(leg, left, top, Math.max(120, bandRight - left), Math.max(72, Math.min(above, mapBottom - top)));
  }

  function setBox(leg, left, top, width, height) {
    leg.style.left = Math.round(left) + 'px';
    leg.style.top = Math.round(top) + 'px';
    leg.style.width = Math.round(width) + 'px';
    leg.style.maxHeight = Math.round(Math.max(72, height)) + 'px';
    leg.style.right = 'auto';
  }

  function markHere(leg) {
    const here = document.querySelector('#wmReg small')?.textContent.trim() || '';
    for (const row of leg.querySelectorAll('.mapBelt')) {
      const name = row.querySelector('.mapBeltName')?.textContent || '';
      row.classList.toggle('mapBeltHere', !!name && here.startsWith(name));
    }
  }

  function placeNames(layer) {
    const view = window.game?.ui?.mapView;
    const canvasEl = document.getElementById('wmC');
    if (!view || !canvasEl) { layer.replaceChildren(); return; }
    const canvas = canvasEl.getBoundingClientRect();
    const sheetEl = document.getElementById('wmSheet');
    const sheet = sheetEl?.getBoundingClientRect();
    const goal = document.getElementById('wmGoalT')?.getBoundingClientRect();
    const leg = document.getElementById('wmLeg');
    const legend = leg && !leg.classList.contains('hidden') ? leg.getBoundingClientRect() : null;
    const sheetOnBottom = sheet && sheet.width > 40 && sheet.top > canvas.top + 80 && sheet.left < canvas.left + 40;
    const sheetH = sheetOnBottom ? sheetEl.offsetHeight : 0;
    const buttons = [...document.querySelectorAll('#wmCtl button, #wmap .x')].map(node => node.getBoundingClientRect());
    const safe = {
      l: canvas.left + 8,
      t: Math.max(canvas.top + 8, goal && goal.height ? goal.bottom + 4 : canvas.top + 8),
      r: canvas.right - 4,
      b: canvas.top + canvas.height - 30 - sheetH - 22,
    };
    const player = {x: canvas.left + canvas.width / 2, y: canvas.top + canvas.height / 2};
    const seen = new Set();
    for (const marker of view._wmVis || []) {
      if (!marker?.name || !marker.id || marker._cn > 1 || marker.id === view.wmSel) continue;
      const sx = canvas.left + marker.sx;
      const sy = canvas.top + marker.sy;
      if (sx > canvas.left + 56 && sx < canvas.right - 56) continue;
      if (sy < canvas.top - 40 || sy > canvas.bottom + 40) continue;
      let node = layer.querySelector(`[data-marker="${cssEscape(marker.id)}"]`);
      if (!node) {
        node = document.createElement('div');
        node.className = 'wmEdgeName';
        node.dataset.marker = marker.id;
        layer.append(node);
      }
      node.textContent = marker.name;
      node.style.width = 'max-content';
      node.style.whiteSpace = 'nowrap';
      node.style.height = 'auto';
      node.style.transform = 'none';
      let width = node.offsetWidth;
      const room = Math.max(80, safe.r - safe.l);
      if (width > room) {
        node.style.whiteSpace = 'normal';
        node.style.width = room + 'px';
        width = node.offsetWidth;
      }
      const height = node.offsetHeight;
      const playerBox = {left: player.x - 36, right: player.x + 36, top: player.y - 46, bottom: player.y + 28};
      const preferY = clamp(sy + 14, safe.t, Math.max(safe.t, safe.b - height));
      const spots = [
        [sx - width / 2, preferY],
        [safe.r - width, preferY],
        [safe.l, preferY],
        [safe.l, legend ? legend.bottom + 4 : preferY],
        [legend ? legend.right + 6 : safe.l, preferY],
        [safe.l, safe.b - height],
        [safe.r - width, safe.b - height],
      ];
      let placed = null;
      for (const [rawLeft, rawTop] of spots) {
        const left = clamp(rawLeft, safe.l, safe.r - width);
        const top = clamp(rawTop, safe.t, Math.max(safe.t, safe.b - height));
        if (top + height > safe.b + 1) continue;
        if (buttons.some(button => intersects(left, top, width, height, button))) continue;
        if (legend && intersects(left, top, width, height, legend)) continue;
        if (intersects(left, top, width, height, playerBox)) continue;
        placed = {left, top};
        break;
      }
      if (!placed) { node.remove(); continue; }
      seen.add(marker.id);
      node.style.left = placed.left + 'px';
      node.style.top = placed.top + 'px';
      node.style.transform = 'none';
    }
    for (const node of [...layer.children]) {
      if (!seen.has(node.dataset.marker)) node.remove();
    }
  }

  function clamp(value, min, max) {
    if (max < min) return (min + max) / 2;
    return Math.min(max, Math.max(min, value));
  }

  function intersects(x, y, width, height, box) {
    return x < box.right && x + width > box.left && y < box.bottom && y + height > box.top;
  }

  function cssEscape(value) {
    return window.CSS && CSS.escape ? CSS.escape(value) : String(value).replace(/["\\]/g, '\\$&');
  }

  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, {once: true});
})();
