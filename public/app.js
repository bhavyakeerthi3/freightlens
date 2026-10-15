'use strict';

const $ = id => document.getElementById(id);
const state = {
  rows: [],
  notes: [],
  page: 0,
  size: 8,
  filtered: []
};
const fmt = (x, digits = 4) => x == null ? 'N/A' : Number(x).toFixed(digits);
const pct = x => x == null ? 'N/A' : `${x >= 0 ? '+' : ''}${(x * 100).toFixed(1)}%`;
const label = r => r.replaceAll('-', '–');
const dateLabel = value => new Date(`${value}T00:00:00Z`).toLocaleDateString('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC'
});
function node(tag, text, className) {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  if (className) e.className = className;
  return e;
}
function badge(row) {
  return node('span', row.flagged === 'Yes' ? 'Needs review' : row.flagged === 'No (justified)' ? 'Evidence-supported' : 'No alert', `badge ${row.flagged === 'Yes' ? 'review' : row.flagged === 'No (justified)' ? 'supported' : 'normal'}`);
}
async function request(url) {
  const r = await fetch(url);
  let data;
  try {
    data = await r.json();
  } catch {
    throw new Error('The server returned an unreadable response. Restart the demo and try again.');
  }
  if (!r.ok) throw new Error(data.error || `Request failed (${r.status}).`);
  return data;
}
function showPage(page) {
  for (const name of ['overview', 'evidence', 'method']) $(`${name}-page`).hidden = name !== page;
  document.querySelectorAll('.nav-item').forEach(b => {
    const selected = b.dataset.page === page;
    b.classList.toggle('active', selected);
    if (selected) b.setAttribute('aria-current', 'page');else b.removeAttribute('aria-current');
  });
  $('breadcrumb').textContent = {
    overview: 'Cost overview',
    evidence: 'Evidence library',
    method: 'Method & quality'
  }[page];
}
document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => showPage(b.dataset.page)));
function applyFilters() {
  const route = $('route').value,
    status = $('status').value,
    from = $('from').value,
    to = $('to').value;
  state.filtered = state.rows.filter(r => (!route || r.route === route) && (!from || r.week_of >= from) && (!to || r.week_of <= to) && (status === 'all' || (status === 'candidates' ? r.candidate : r.flagged === status))).sort((a, b) => b.week_of.localeCompare(a.week_of) || a.route.localeCompare(b.route));
  state.page = 0;
  renderTable();
}
function renderTable() {
  const body = $('findings-body');
  body.replaceChildren();
  const start = state.page * state.size,
    end = Math.min(start + state.size, state.filtered.length);
  for (const r of state.filtered.slice(start, end)) {
    const tr = node('tr');
    const name = node('td', label(r.route));
    name.append(node('small', `${r.route_type} haul · ${r.shipments} shipments`));
    tr.append(name, node('td', dateLabel(r.week_of)), node('td', fmt(r.cost_per_tonne_km)), node('td', pct(r.own_delta), r.own_delta > .2 ? 'rise' : ''), node('td', pct(r.peer_delta), r.peer_delta > .2 ? 'rise' : ''));
    const status = node('td');
    status.append(badge(r));
    tr.append(status);
    const action = node('td'),
      button = node('button', '↗', 'inspect');
    button.setAttribute('aria-label', `Inspect ${r.route}, week of ${r.week_of}`);
    button.addEventListener('click', () => showDetail(r));
    action.append(button);
    tr.append(action);
    body.append(tr);
  }
  $('finding-count').textContent = state.filtered.length;
  $('empty').hidden = state.filtered.length > 0;
  if ($('from').value && $('to').value && $('from').value > $('to').value) $('empty').textContent = 'The start date is after the end date. Adjust the week range.';else $('empty').textContent = 'No route-weeks match these filters. Try another route or date range.';
  $('table-info').textContent = state.filtered.length ? `Showing ${start + 1}–${end} of ${state.filtered.length} route-weeks` : '0 route-weeks';
  $('page-info').textContent = `${state.page + 1} / ${Math.max(1, Math.ceil(state.filtered.length / state.size))}`;
  $('prev').disabled = state.page === 0;
  $('next').disabled = end >= state.filtered.length;
}
['route', 'status', 'from', 'to'].forEach(id => $(id).addEventListener('change', applyFilters));
$('prev').addEventListener('click', () => {
  if (state.page > 0) {
    state.page--;
    renderTable();
  }
});
$('next').addEventListener('click', () => {
  if ((state.page + 1) * state.size < state.filtered.length) {
    state.page++;
    renderTable();
  }
});
$('reset').addEventListener('click', () => {
  $('route').value = '';
  $('status').value = 'candidates';
  $('from').value = '';
  $('to').value = '';
  applyFilters();
});
function showDetail(r) {
  $('detail-title').textContent = label(r.route);
  $('detail-subtitle').textContent = `Week of ${dateLabel(r.week_of)} · ${r.route_type} haul · ${r.shipments} shipments`;
  const content = $('detail-content');
  content.replaceChildren(badge(r));
  const grid = node('div', null, 'detail-grid');
  for (const [title, value, extra] of [['Weekly rate', fmt(r.cost_per_tonne_km), 'INR / tonne-km'], ['History baseline', fmt(r.history_baseline), `${pct(r.own_delta)} · ${r.history_weeks} prior weeks`], ['Peer baseline', fmt(r.peer_baseline), `${pct(r.peer_delta)} · ${r.peer_routes} other routes`]]) {
    const stat = node('div', title, 'detail-stat');
    stat.append(node('strong', value), node('span', extra));
    grid.append(stat);
  }
  content.append(grid, node('p', r.reason, 'detail-reason'));
  const box = node('div', null, 'evidence-box');
  if (r.evidence) {
    box.append(node('h3', `Source ${r.evidence.note_id} · ${r.evidence.applies_to}`), node('p', r.evidence.note), node('small', `Published ${r.evidence.date} · Reviewed window ${r.evidence_window.join(' to ')}`));
  } else {
    box.append(node('h3', r.candidate ? 'No supporting evidence' : 'Evidence check'), node('p', r.candidate ? 'No reviewed cost-increasing note applies to this route and week. The rise remains unexplained; a human should review it.' : 'This week did not trigger the candidate-rise rule. Notes are consulted only for candidate rises.'));
  }
  content.append(box);
  $('detail').showModal();
}
$('close-detail').addEventListener('click', () => $('detail').close());
$('detail').addEventListener('click', event => {
  if (event.target === $('detail')) {
    const r = $('detail').getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) $('detail').close();
  }
});
function svgNode(tag, attrs = {}, text) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text) e.textContent = text;
  return e;
}
function renderChart() {
  const rows = state.rows.filter(r => r.route === $('chart-route').value).sort((a, b) => a.week_of.localeCompare(b.week_of));
  const wrap = $('chart');
  wrap.replaceChildren();
  if (!rows.length) return;
  const w = 720,
    h = 253,
    left = 38,
    right = 12,
    top = 16,
    bottom = 31;
  const all = rows.flatMap(r => [r.cost_per_tonne_km, r.history_baseline, r.peer_baseline]).filter(x => x != null);
  const low = Math.max(0, Math.min(...all) - .15),
    high = Math.max(...all) + .15;
  const dates = rows.map(r => Date.parse(r.week_of)),
    t0 = dates[0],
    t1 = dates.at(-1);
  const x = i => left + (dates[i] - t0) / (t1 - t0 || 1) * (w - left - right);
  const y = v => h - bottom - (v - low) / (high - low || 1) * (h - top - bottom);
  const svg = svgNode('svg', {
    viewBox: `0 0 ${w} ${h}`,
    role: 'img',
    'aria-label': `${rows[0].route}: weekly rate, eight-week history and same-type peers; select an alert marker for details.`
  });
  for (let i = 0; i <= 4; i++) {
    const v = low + i * (high - low) / 4;
    svg.append(svgNode('line', {
      x1: left,
      x2: w - right,
      y1: y(v),
      y2: y(v),
      stroke: '#edf1e8',
      'stroke-dasharray': '3 4'
    }), svgNode('text', {
      x: left - 9,
      y: y(v) + 3,
      fill: '#98a38f',
      'font-size': 9,
      'text-anchor': 'end'
    }, v.toFixed(1)));
  }
  for (let i = 0; i <= 4; i++) {
    const index = Math.round(i * (rows.length - 1) / 4);
    const d = new Date(`${rows[index].week_of}T00:00:00Z`).toLocaleDateString('en-GB', {
      month: 'short',
      year: '2-digit',
      timeZone: 'UTC'
    });
    svg.append(svgNode('text', {
      x: x(index),
      y: h - 8,
      fill: '#98a38f',
      'font-size': 9,
      'text-anchor': i === 0 ? 'start' : i === 4 ? 'end' : 'middle'
    }, d));
  }
  const area = rows.map((r, i) => `${i ? 'L' : 'M'}${x(i)},${y(r.cost_per_tonne_km)}`).join(' ') + ` L${x(rows.length - 1)},${h - bottom} L${left},${h - bottom} Z`;
  svg.append(svgNode('path', {
    d: area,
    fill: '#f1f6ed'
  }));
  for (const [key, color, dash] of [['peer_baseline', '#b8c3c9', ''], ['history_baseline', '#93a889', '4 4'], ['cost_per_tonne_km', '#20805b', '']]) {
    let d = '',
      open = false;
    rows.forEach((r, i) => {
      if (r[key] == null) {
        open = false;
        return;
      }
      d += `${open ? 'L' : 'M'}${x(i)},${y(r[key])} `;
      open = true;
    });
    svg.append(svgNode('path', {
      d,
      fill: 'none',
      stroke: color,
      'stroke-width': key === 'cost_per_tonne_km' ? 2.3 : 1.5,
      'stroke-dasharray': dash,
      'stroke-linejoin': 'round'
    }));
  }
  rows.forEach((r, i) => {
    if (r.candidate) {
      const dot = svgNode('circle', {
        cx: x(i),
        cy: y(r.cost_per_tonne_km),
        r: 4,
        fill: r.flagged === 'Yes' ? '#c27655' : '#6c9470',
        stroke: '#fff',
        'stroke-width': 1.5,
        tabindex: 0,
        role: 'button',
        'aria-label': `${r.week_of}, ${fmt(r.cost_per_tonne_km)}, ${r.flagged}. Inspect finding.`
      });
      dot.append(svgNode('title', {}, `${dateLabel(r.week_of)} · ${fmt(r.cost_per_tonne_km)} · ${r.flagged}`));
      dot.addEventListener('click', () => showDetail(r));
      dot.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          showDetail(r);
        }
      });
      svg.append(dot);
    }
  });
  wrap.append(svg);
  const candidates = rows.filter(r => r.candidate).length;
  $('chart-caption').textContent = `${rows.length} observed weeks · ${candidates} candidate rises · Select a marker to inspect · Full dataset period`;
}
$('chart-route').addEventListener('change', renderChart);
async function ask(event) {
  event.preventDefault();
  const q = $('question').value.trim();
  if (!q) {
    $('question').focus();
    return;
  }
  $('ask').disabled = true;
  $('answer').hidden = false;
  $('answer').textContent = 'Checking the analysis and source notes…';
  try {
    const data = await request(`/api/ask?q=${encodeURIComponent(q)}`);
    $('answer').textContent = data.answer;
  } catch (err) {
    $('answer').textContent = err.message;
  } finally {
    $('ask').disabled = false;
  }
}
$('ask-form').addEventListener('submit', ask);
document.querySelectorAll('[data-question]').forEach(b => b.addEventListener('click', () => {
  $('question').value = b.dataset.question;
  $('ask-form').requestSubmit();
}));
function renderNotes() {
  const policies = {
    N001: 'Reviewed cost impact · Chennai–Bangalore · 24 Feb–8 Mar 2025',
    N002: 'Reviewed cost impact · Ahmedabad–Mumbai · 20–26 Jan 2025',
    N003: 'Reviewed cost impact · All routes · 5–11 May 2025 · Maximum 7% rise'
  };
  for (const n of state.notes) {
    const card = node('article', null, 'card note-card'),
      meta = node('div', null, 'note-meta');
    meta.append(node('b', n.note_id), node('span', dateLabel(n.date)));
    card.append(meta, node('h2', label(n.applies_to)), node('p', n.note), node('p', policies[n.note_id] || 'Cannot justify a rise: no applicable positive cost impact in this dataset.', 'note-policy'));
    $('notes-list').append(card);
  }
}
async function init() {
  try {
    const [rows, summary, notes] = await Promise.all([request('/api/results'), request('/api/summary'), request('/api/notes')]);
    if (!rows.length) throw new Error('No route-weeks available. Check the shipment input and rerun analysis.');
    state.rows = rows;
    state.notes = notes;
    const routes = [...new Set(rows.map(r => r.route))].sort();
    for (const route of routes) for (const target of ['route', 'chart-route']) {
      const option = node('option', label(route));
      option.value = route;
      $(target).append(option);
    }
    $('chart-route').value = routes.includes('Mumbai-Pune') ? 'Mumbai-Pune' : routes[0];
    $('shipments').textContent = summary.shipments.toLocaleString('en-IN');
    $('weeks').textContent = rows.length.toLocaleString();
    $('route-count').textContent = routes.length;
    $('alerts').textContent = summary.verdict_counts.Yes || 0;
    $('justified').textContent = summary.verdict_counts['No (justified)'] || 0;
    const weeks = rows.map(r => r.week_of).sort();
    $('dataset-range').textContent = `${dateLabel(weeks[0])} – ${dateLabel(weeks.at(-1))} · week-of dates`;
    for (const id of ['from', 'to']) {
      $(id).min = weeks[0];
      $(id).max = weeks.at(-1);
    }
    applyFilters();
    renderChart();
    renderNotes();
  } catch (err) {
    $('load-error').hidden = false;
    $('load-error').textContent = err.message;
    $('table-info').textContent = 'Analysis could not be loaded.';
  }
}
init();

// The same UI runs locally and on the public Vercel sample-data deployment.
if (!['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) {
  document.querySelector('.system-dot').textContent = 'Public demo ready';
  document.querySelector('.sidebar-bottom > p').textContent = 'Synthetic shipment data · public demo';
  document.querySelector('.offline').lastChild.textContent = ' Public demo';
  document.querySelector('.assistant-foot').textContent = 'Grounded retrieval · Structured answers · No model calls';
}