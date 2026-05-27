document.addEventListener('DOMContentLoaded', function () {
    var canvas = document.getElementById('movementsChart');
    if (!canvas) return;

    var labels, inflows, outflows;
    try {
        labels = JSON.parse(canvas.dataset.labels);
        inflows = JSON.parse(canvas.dataset.inflows);
        outflows = JSON.parse(canvas.dataset.outflows);
    } catch (e) {
        return;
    }

    var isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';

    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Entradas',
                    data: inflows,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointBackgroundColor: '#10b981'
                },
                {
                    label: 'Saídas',
                    data: outflows,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointBackgroundColor: '#ef4444'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: { usePointStyle: true, boxWidth: 6, font: { family: 'Inter', size: 12, weight: '600' } }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor, drawBorder: false },
                    ticks: { font: { family: 'Inter', size: 11 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { family: 'Inter', size: 11 } }
                }
            }
        }
    });
});
