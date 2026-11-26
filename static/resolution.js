(function () {
  const read = id => JSON.parse(document.getElementById(id).textContent || 'null');
  const tickets = read('ticket-data') || [];
  const resolutions = read('resolution-data') || {};
  let metrics = read('metrics-data') || {};
  let kb = read('kb-data') || [];
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pct = v => (v === null || v === undefined) ? '–' : Math.round(v * 100) + '%';
  const refId = t => `T-${String(t.created_at || '').slice(0, 4) || new Date().getFullYear()}-${String(t.ticket_id).padStart(4, '0')}`;
  const STAGE_NAMES = ['Ticket Analysis & Query Generation', 'Knowledge Base Retrieval', 'Context Augmentation', 'Response Generation'];
  let current = null;

  function renderMetrics() {
    $('m-retrieval').textContent = pct(metrics.retrieval_accuracy);
    $('m-rate').textContent = pct(metrics.resolution_rate);
    $('m-time').textContent = metrics.average_response_time_s == null ? '–' : (metrics.average_response_time_s < 1 ? Math.round(metrics.average_response_time_s * 1000) + ' ms' : metrics.average_response_time_s.toFixed(2) + ' s');
    $('m-note').textContent = `Retrieval accuracy is measured on a labelled test set. Resolution rate uses agent feedback (${metrics.feedback_count || 0} so far). Response time is the average across ${metrics.resolutions_generated || 0} runs.`;
  }

  function renderTicket(id) {
    const ticket = tickets.find(t => t.ticket_id === Number(id));
    if (!ticket) return;
    current = ticket;
    const res = resolutions[ticket.ticket_id];
    $('r-ref').textContent = refId(ticket);
    $('r-title').textContent = ticket.title;
    $('r-desc').textContent = ticket.description;
    $('r-status').textContent = ticket.status;
    $('r-chips').innerHTML = `<span class="badge">${esc(ticket.category)}</span><span class="badge sev-${ticket.severity}">${esc(ticket.severity)}</span><span class="badge">${esc(ticket.priority)}</span>`;
    $('r-query').value = res ? res.query : '';
    if (!res) { $('r-docs').innerHTML = '<div class="empty">No resolution yet.</div>'; $('r-gen').innerHTML = ''; $('r-workflow').innerHTML = ''; return; }
    $('r-docs').innerHTML = res.documents.length ? res.documents.map(d => `<div class="doc"><div class="row"><span class="t">${esc(d.title)} <span class="badge">${esc(d.id)}</span></span><span class="rel">${Math.round(d.score * 100)}% match</span></div><small>${esc(d.category)}${d.last_updated ? ' · updated ' + esc(d.last_updated) : ''}</small></div>`).join('') : '<div class="empty">No article matched closely enough.</div>';
    $('r-workflow').innerHTML = '<strong>RAG workflow status</strong>' + res.workflow.map((s, i) => `<div class="stage"><span class="dot ${s.status}">${s.status === 'completed' ? '✓' : s.status === 'failed' ? '!' : s.status === 'skipped' ? '–' : i + 1}</span><span>${esc(s.name || STAGE_NAMES[i])}</span><span class="ms">${s.status}${s.duration_ms ? ' · ' + s.duration_ms.toFixed(1) + ' ms' : ''}</span></div>`).join('');
    if (res.status === 'INSUFFICIENT_KNOWLEDGE') {
      $('r-gen').innerHTML = `<strong>Insufficient knowledge</strong><p>${esc(res.resolution_text)}</p>`;
    } else {
      $('r-gen').innerHTML = `<strong>Generated resolution</strong><p class="note">${esc(res.summary)}</p><ol>${res.steps.map(s => `<li>${esc(s.text)}<span class="src">Source: ${esc(s.source_id)} – ${esc(s.source_title)}</span></li>`).join('')}</ol>` +
        (res.low_confidence ? '<div class="warn">The match with the knowledge base is weak. Verify these steps before applying them.</div>' : '') +
        (res.escalate ? '<div class="warn">High-priority ticket: escalate immediately if these steps do not restore service.</div>' : '');
    }
    $('r-outcome').textContent = res.outcome ? `Outcome: ${res.outcome}` : '';
    renderMetrics();
  }

  function fillSelect() {
    const select = $('res-ticket');
    select.innerHTML = tickets.map(t => `<option value="${t.ticket_id}">${refId(t)} · ${esc(t.title).slice(0, 50)}</option>`).join('');
    $('res-empty').hidden = tickets.length > 0;
    $('res-body').hidden = tickets.length === 0;
    select.hidden = tickets.length === 0;
    const start = window.LATEST_TICKET || (tickets[0] && tickets[0].ticket_id);
    if (start) { select.value = start; renderTicket(start); }
    select.addEventListener('change', () => renderTicket(select.value));
  }

  async function post(url, body) {
    const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    return { ok: response.ok, data: await response.json() };
  }

  document.querySelectorAll('#r-actions [data-outcome]').forEach(button => button.addEventListener('click', async () => {
    if (!current) return;
    const { ok, data } = await post(`/api/tickets/${current.ticket_id}/feedback`, { outcome: button.dataset.outcome });
    if (!ok) return;
    resolutions[current.ticket_id].outcome = data.outcome;
    current.status = data.outcome;
    metrics = data.metrics;
    renderTicket(current.ticket_id);
  }));
  $('r-regen').addEventListener('click', async () => {
    if (!current) return;
    const { ok, data } = await post(`/api/tickets/${current.ticket_id}/resolve`);
    if (ok) { resolutions[current.ticket_id] = data; renderTicket(current.ticket_id); }
  });
  const open = $('open-resolution');
  if (open) open.addEventListener('click', e => { e.preventDefault(); document.querySelector('[data-view="resolution"]').click(); });

  // Knowledge base page
  function renderKb(list) {
    $('kb-count').textContent = kb.length;
    $('kb-list').innerHTML = list.length ? list.map(a => `<details class="kb-item"><summary>${esc(a.title)} <span class="meta">${esc(a.id)} · ${esc(a.category)}${a.score !== undefined ? ' · ' + Math.round(a.score * 100) + '% match' : ''}</span></summary><pre>${esc(a.content)}</pre></details>`).join('') : '<div class="empty">No articles found.</div>';
  }
  let timer;
  $('kb-search').addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = $('kb-search').value.trim();
      if (!q) return renderKb(kb);
      const response = await fetch('/api/knowledge-base/search?top_k=8&q=' + encodeURIComponent(q));
      renderKb(response.ok ? await response.json() : []);
    }, 250);
  });
  $('kb-form').addEventListener('submit', async e => {
    e.preventDefault();
    const { ok, data } = await post('/api/knowledge-base', { title: $('kb-title').value, category: $('kb-category').value || 'General', ticket_category: $('kb-tc').value, content: $('kb-content').value });
    $('kb-msg').textContent = ok ? `Added ${data.id}.` : (data.error || 'Could not add article.');
    if (ok) { kb = await (await fetch('/api/knowledge-base')).json(); renderKb(kb); $('kb-form').reset(); }
  });

  fillSelect();
  renderMetrics();
  renderKb(kb);
})();
