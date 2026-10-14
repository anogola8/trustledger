// Draws every <canvas data-chart="id" data-type="line|bar|doughnut"> from a json_script block with that id.
document.addEventListener('DOMContentLoaded', function () {
  if (typeof Chart === 'undefined') { return; }
  document.querySelectorAll('canvas[data-chart]').forEach(function (canvas) {
    var node = document.getElementById(canvas.dataset.chart);
    if (!node) { return; }
    var d = JSON.parse(node.textContent);
    var type = canvas.dataset.type || 'line';
    var colors = ['#0E9AA7', '#1F3A5F', '#B26A00', '#B71C1C', '#2E7D32', '#6b7a8c'];
    new Chart(canvas, {
      type: type,
      data: { labels: d.labels, datasets: [{ label: canvas.dataset.label || '', data: d.values,
        borderColor: '#0E9AA7', backgroundColor: type === 'line' ? 'rgba(14,154,167,.15)' : colors, fill: type === 'line', tension: .3 }] },
      options: { responsive: true, plugins: { legend: { display: type === 'doughnut' } },
        scales: type === 'doughnut' ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } } }
    });
  });
});
