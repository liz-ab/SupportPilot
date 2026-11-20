// Separate visualization layer. Analytics are revealed through the sidebar or after submission.
(function () {
  const dataElement = document.getElementById('ticket-data');
  if (!dataElement || typeof Chart === 'undefined') return;
  const tickets = JSON.parse(dataElement.textContent || '[]');
  const charts = {};
  const countBy = (list, field, order) => {
    const counts = {};
    list.forEach(ticket => { counts[ticket[field]] = (counts[ticket[field]] || 0) + 1; });
    const labels = order || Object.keys(counts).sort();
    return { labels, values: labels.map(label => counts[label] || 0) };
  };
  function render() {
    const range = document.getElementById('analytics-range')?.value || '5';
    const selected = range === 'all' ? tickets : tickets.slice(0, 5);
    const summaries = {
      categoryChart: countBy(selected, 'category', ['Network', 'VPN', 'Password', 'Software', 'Hardware', 'System']),
      priorityChart: countBy(selected, 'priority', ['P1', 'P2', 'P3', 'P4']),
      severityChart: countBy(selected, 'severity', ['Critical', 'High', 'Medium', 'Low'])
    };
    Object.entries(summaries).forEach(([id, summary]) => {
      if (charts[id]) {
        charts[id].data.labels = summary.labels;
        charts[id].data.datasets[0].data = summary.values;
        charts[id].update();
      } else {
        const canvas = document.getElementById(id);
        if (canvas) charts[id] = new Chart(canvas, {
          type: id === 'priorityChart' ? 'doughnut' : 'bar',
          data: { labels: summary.labels, datasets: [{ label: 'Tickets', data: summary.values }] },
          options: { responsive: true, plugins: { legend: { display: id === 'priorityChart' } } }
        });
      }
    });
  }
  const section = document.getElementById('analytics');
  document.getElementById('analytics-nav')?.addEventListener('click', () => {
    section.hidden = false;
    render();
  });
  document.getElementById('analytics-range')?.addEventListener('change', render);
  if (!section.hidden) render();
})();
