// Small, separate visualization layer. It reads the ticket list supplied by Flask.
(function () {
  const dataElement = document.getElementById('ticket-data');
  if (!dataElement || typeof Chart === 'undefined') return;
  const tickets = JSON.parse(dataElement.textContent || '[]');
  const countBy = (field, order) => {
    const counts = {};
    tickets.forEach(ticket => { counts[ticket[field]] = (counts[ticket[field]] || 0) + 1; });
    const labels = order || Object.keys(counts).sort();
    return { labels, values: labels.map(label => counts[label] || 0) };
  };
  const makeChart = (id, type, summary) => {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    new Chart(canvas, {
      type,
      data: { labels: summary.labels, datasets: [{ label: 'Tickets', data: summary.values }] },
      options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: type !== 'bar' } } }
    });
  };
  makeChart('categoryChart', 'bar', countBy('category', ['Network', 'VPN', 'Password', 'Software', 'Hardware', 'System']));
  makeChart('priorityChart', 'doughnut', countBy('priority', ['P1', 'P2', 'P3', 'P4']));
  makeChart('severityChart', 'bar', countBy('severity', ['Critical', 'High', 'Medium', 'Low']));
})();
