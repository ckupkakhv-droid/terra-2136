// Pure, read-only selection. Availability and productivity remain owned by Terra.
export function recommendResident(camp, task, api) {
  const skill = task?.key === 'build' ? 'build' : 'gather';
  const blocked = [];
  let candidate = null;
  if (!task || !['water', 'wood', 'build'].includes(task.key))
    return { candidate, blocked, reason: 'Неизвестный быстрый приказ' };
  if (task.reason) return { candidate, blocked, reason: task.reason };
  for (const resident of Object.values(camp.settlers || {})) {
    if (!resident || resident.dead) continue;
    const request = { residentId: resident.id, task: task.key, target: task.target };
    const reason = api.reason(camp, resident, request);
    if (reason) { blocked.push({ id: resident.id, name: resident.name, reason }); continue; }
    let score;
    try { score = api.efficiency(camp, resident, skill); } catch { score = NaN; }
    if (!Number.isFinite(score) || score < 0) {
      blocked.push({ id: resident.id, name: resident.name, reason: 'Не удалось оценить эффективность' });
      continue;
    }
    // Stable ties avoid reshuffling when object insertion order changes on load.
    if (!candidate || score > candidate.score ||
      (score === candidate.score && String(resident.id) < String(candidate.id)))
      candidate = { id: resident.id, name: resident.name, score, skill, request };
  }
  return { candidate, blocked, reason: candidate ? '' : 'Нет свободного подходящего жителя' };
}

export function renderResidentRecommendation(camp, task, api, assign, options = {}) {
  const model = recommendResident(camp, task, api);
  const node = (tag, className, text) => {
    const element = document.createElement(tag);
    element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const root = node('section', 'residentRecommendation');
  root.setAttribute('aria-label', 'Рекомендация работника');
  if (model.candidate) {
    const candidate = model.candidate;
    root.append(node('strong', '', 'Лучший свободный: ' + candidate.name));
    root.append(node('small', '', 'По текущей эффективности работы: навыки, состояние и черты.'));
    root.append(node('small', '', 'Цена приказа: 0 ресурсов.'));
    const action = node('button', 'campButton residentRecommendAction', 'Назначить: ' + candidate.name);
    action.type = 'button';
    action.dataset.residentRecommended = candidate.id;
    action.disabled = !!options.pending || options.available === false;
    action.addEventListener('click', () => {
      if (action.disabled) return;
      // Never silently replace the named worker with a newly available person.
      assign({ ...candidate.request });
    });
    root.append(action);
  } else {
    root.append(node('strong', 'campReason', model.reason));
  }
  if (model.blocked.length) {
    const details = node('details', 'residentRecommendationReasons');
    details.append(node('summary', '', 'Почему другие недоступны · ' + model.blocked.length));
    const list = node('ul', '');
    for (const person of model.blocked)
      list.append(node('li', '', person.name + ': ' + person.reason));
    details.append(list);
    root.append(details);
  }
  return root;
}
