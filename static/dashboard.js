(function () {
  const read = id => JSON.parse(document.getElementById(id).textContent || 'null');
  const tickets = read('ticket-data') || [];
  const report = read('report-data') || {};
  const CATS = ['Network', 'VPN', 'Password', 'Software', 'Hardware', 'System'];
  const SEVS = ['Critical', 'High', 'Medium', 'Low'];
  const SEV_COLOR = { Critical: '#c0392b', High: '#e07b21', Medium: '#d9a400', Low: '#2e8b57' };
  const BRAND = '#2f4ac2';
  const charts = {};

  // Navigation
  document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + btn.dataset.view));
    if (btn.dataset.view === 'model') drawModel();
    window.scrollTo(0, 0);
  }));

  const count = (list, key, order) => order.map(o => list.filter(t => t[key] === o).length);
  const day = t => (t.created_at || '').slice(0, 10);

  function inRange() {
    const range = document.getElementById('range').value;
    if (range === 'all') return tickets;
    const cutoff = Date.now() - Number(range) * 86400000;
    return tickets.filter(t => new Date(t.created_at).getTime() >= cutoff);
  }

  function draw(id, config) {
    if (charts[id]) charts[id].destroy();
    const canvas = document.getElementById(id);
    if (canvas && typeof Chart !== 'undefined') charts[id] = new Chart(canvas, config);
  }

  const baseOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };
  const axes = { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#eef0f4' } } };

  function renderDashboard() {
    const data = inRange();
    document.getElementById('k-total').textContent = data.length;
    document.getElementById('k-open').textContent = data.filter(t => t.status === 'Open').length;
    document.getElementById('k-p1').textContent = data.filter(t => t.priority === 'P1').length;
    const conf = data.length ? data.reduce((s, t) => s + t.confidence, 0) / data.length : null;
    document.getElementById('k-conf').textContent = conf === null ? '–' : Math.round(conf * 100) + '%';

    draw('c-category', { type: 'bar', data: { labels: CATS, datasets: [{ data: count(data, 'category', CATS), backgroundColor: BRAND, borderRadius: 4 }] },
      options: { ...baseOptions, scales: axes } });
    draw('c-severity', { type: 'doughnut', data: { labels: SEVS, datasets: [{ data: count(data, 'severity', SEVS), backgroundColor: SEVS.map(s => SEV_COLOR[s]), borderWidth: 0 }] },
      options: { ...baseOptions, cutout: '62%', plugins: { legend: { display: true, position: 'right' } } } });
    draw('c-priority', { type: 'bar', data: { labels: ['P1', 'P2', 'P3', 'P4'], datasets: [{ data: count(data, 'priority', ['P1', 'P2', 'P3', 'P4']), backgroundColor: ['#c0392b', '#e07b21', '#d9a400', '#2e8b57'], borderRadius: 4 }] },
      options: { ...baseOptions, indexAxis: 'y', scales: { x: axes.y, y: axes.x } } });

    const days = {};
    data.forEach(t => { days[day(t)] = (days[day(t)] || 0) + 1; });
    const labels = Object.keys(days).sort();
    draw('c-time', { type: 'line', data: { labels, datasets: [{ data: labels.map(l => days[l]), borderColor: BRAND, backgroundColor: 'rgba(47,74,194,.12)', fill: true, tension: .3, pointRadius: 3 }] },
      options: { ...baseOptions, scales: axes } });
  }

  function drawModel() {
    const rep = report.category_report || {};
    const labels = CATS.filter(c => rep[c]);
    if (!labels.length) return;
    draw('c-f1', { type: 'bar', data: { labels, datasets: [{ data: labels.map(c => Math.round(rep[c]['f1-score'] * 1000) / 10), backgroundColor: BRAND, borderRadius: 4 }] },
      options: { ...baseOptions, scales: { x: axes.x, y: { min: 0, max: 100, grid: { color: '#eef0f4' } } } } });
  }

  // Ticket table
  const state = { page: 1, size: 10, sort: 'ticket_id', dir: -1 };
  const catFilter = document.getElementById('f-category');
  CATS.forEach(c => catFilter.insertAdjacentHTML('beforeend', `<option>${c}</option>`));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function renderTable() {
    const q = document.getElementById('search').value.trim().toLowerCase();
    const f = { category: catFilter.value, severity: document.getElementById('f-severity').value, priority: document.getElementById('f-priority').value };
    let rows = tickets.filter(t => (!q || (t.title + ' ' + t.description + ' ' + t.employee_name).toLowerCase().includes(q)) &&
      Object.keys(f).every(k => !f[k] || t[k] === f[k]));
    rows.sort((a, b) => (a[state.sort] > b[state.sort] ? 1 : a[state.sort] < b[state.sort] ? -1 : 0) * state.dir);
    const pages = Math.max(1, Math.ceil(rows.length / state.size));
    state.page = Math.min(state.page, pages);
    const slice = rows.slice((state.page - 1) * state.size, state.page * state.size);
    document.getElementById('rows').innerHTML = slice.length ? slice.map(t => `<tr>
      <td>#${t.ticket_id}</td>
      <td class="title-cell">${esc(t.title)}<small>${esc(t.employee_name)} · ${esc(t.department)}</small></td>
      <td>${esc(t.category)}</td><td><span class="badge sev-${t.severity}">${t.severity}</span></td>
      <td>${t.priority}</td><td>${esc((t.created_at || '').replace('T', ' ').slice(0, 16))}</td>
      <td><span class="badge">${esc(t.status)}</span></td></tr>`).join('')
      : '<tr><td colspan="7" class="empty">No tickets match.</td></tr>';
    document.getElementById('count').textContent = `${rows.length} ticket${rows.length === 1 ? '' : 's'} · page ${state.page} of ${pages}`;
    document.getElementById('prev').disabled = state.page <= 1;
    document.getElementById('next').disabled = state.page >= pages;
  }

  ['search', 'f-category', 'f-severity', 'f-priority'].forEach(id =>
    document.getElementById(id).addEventListener('input', () => { state.page = 1; renderTable(); }));
  document.getElementById('prev').addEventListener('click', () => { state.page--; renderTable(); });
  document.getElementById('next').addEventListener('click', () => { state.page++; renderTable(); });
  document.querySelectorAll('th[data-sort]').forEach(th => th.addEventListener('click', () => {
    state.dir = state.sort === th.dataset.sort ? -state.dir : 1; state.sort = th.dataset.sort; renderTable();
  }));
  document.getElementById('range').addEventListener('change', renderDashboard);

  renderDashboard();
  renderTable();
})();
