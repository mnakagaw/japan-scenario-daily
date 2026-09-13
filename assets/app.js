'use strict';
document.documentElement.classList.add('js');
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const escapeHTML = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatP = v => v == null ? '未設定' : `${Math.round(v * 100)}%`;
function difference(a, b, from, to) {
  if (!a || !b || a.p_final == null || b.p_final == null || a.definition_version !== b.definition_version || a.target !== b.target || from.series_id !== to.series_id || Date.parse(from.deadline) !== Date.parse(to.deadline) || Date.parse(from.forecast_start) !== Date.parse(to.forecast_start)) return null;
  return Math.round((b.p_final - a.p_final) * 1000) / 10;
}
function changeMarkup(v) {
  if (v === null) return '<span class="change unavailable">— 比較不可</span>';
  if (v === 0) return '<span class="change flat">→ 0 pt</span>';
  return `<span class="change ${v > 0 ? 'up' : 'down'}">${v > 0 ? '▲ +' : '▼ '}${v} pt</span>`;
}
const form = $('#news-filters');
if (form) {
  const items = $$('.news-item');
  const filter = () => {
    const query = $('#news-search').value.trim().normalize('NFKC').toLocaleLowerCase();
    const category = $('#news-category').value, scenario = $('#news-scenario').value, status = $('#news-status').value;
    let count = 0;
    items.forEach(item => {
      const match = (!query || item.textContent.normalize('NFKC').toLocaleLowerCase().includes(query)) && (!category || category === item.dataset.category) && (!scenario || item.dataset.scenarios.includes(scenario)) && (!status || status === item.dataset.status);
      item.hidden = !match; if (match) count++;
    });
    $('#news-count').textContent = `${items.length}件中 ${count}件を表示`;
    $('#news-empty').hidden = count !== 0;
  };
  form.addEventListener('input', filter); form.addEventListener('change', filter);
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('reset', () => setTimeout(filter, 0));
}
$('#scenario-sort')?.addEventListener('change', event => {
  const rows = $$('#scenario-rows tr');
  rows.sort((a,b) => event.target.value === 'probability' ? Number(b.dataset.probability) - Number(a.dataset.probability) || a.dataset.scenario.localeCompare(b.dataset.scenario) : a.dataset.scenario.localeCompare(b.dataset.scenario));
  rows.forEach(row => $('#scenario-rows').appendChild(row));
});
$$('.print-button').forEach(button => button.addEventListener('click', () => window.print()));
const fromInput = $('#compare-from'), toInput = $('#compare-to');
if (fromInput && toInput) {
  const {history} = JSON.parse($('#page-data').textContent);
  const render = () => {
    const from = history.find(d => d.date === fromInput.value), to = history.find(d => d.date === toInput.value);
    if (from.date === to.date) {
      $('#date-comparison').innerHTML = `<p class="empty-state">${history.length < 2 ? '初回の公開です。2日目から日付を選んで比較できます。' : '異なる日付を選ぶと、その間の変化を表示します。'}</p>`; return;
    }
    if (from.date > to.date) {
      $('#date-comparison').innerHTML = '<p class="empty-state">比較先には比較元より後の日付を選んでください。</p>'; return;
    }
    const rows = to.scenarios.filter(b => b.id !== 'I' && b.id !== 'J').map(b => {
      const a = from.scenarios.find(s => s.id === b.id), diff = difference(a,b,from,to);
      return `<tr><th scope="row">${escapeHTML(b.id+' '+b.label)}</th><td>${formatP(a?.p_final)}</td><td>${formatP(b.p_final)}</td><td>${changeMarkup(diff)}</td><td>${escapeHTML(a?.reason || '記録なし')}<span class="compare-reason-arrow">↓</span>${escapeHTML(b.reason)}</td></tr>`;
    }).join('');
    $('#date-comparison').innerHTML = `<h2>${escapeHTML(from.date)} → ${escapeHTML(to.date)}</h2><p>比較元 ${escapeHTML(from.prepared_at)} 作成版 → 比較先 ${escapeHTML(to.prepared_at)} 作成版</p><div class="table-scroll"><table><thead><tr><th>シナリオ</th><th>比較元の最終</th><th>比較先の最終</th><th>指定日間の差</th><th>判断の理由：比較元 → 比較先</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  };
  if (history.length > 1) fromInput.value = history.at(-2).date;
  else {fromInput.disabled = true; toInput.disabled = true;}
  fromInput.addEventListener('change',render); toInput.addEventListener('change',render); render();
}
