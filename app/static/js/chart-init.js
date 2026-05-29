document.addEventListener('DOMContentLoaded', function () {
    var canvas = document.getElementById('movementsChart');
    if (!canvas) return;

    var labels, inflows, outflows;
    try {
        labels = JSON.parse(document.getElementById('chart-labels').textContent);
        inflows = JSON.parse(document.getElementById('chart-inflows').textContent);
        outflows = JSON.parse(document.getElementById('chart-outflows').textContent);
    } catch (e) {
        return;
    }

    var ctx = canvas.getContext('2d');
    var isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';

    function buildGradient(chart, idx, color) {
        var area = chart.chartArea;
        var g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
        g.addColorStop(0, color.replace('ALPHA', '0.2'));
        g.addColorStop(1, color.replace('ALPHA', '0.01'));
        return g;
    }

    var gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    var tooltipBg = isDark ? '#1e293b' : '#ffffff';
    var tooltipBorder = isDark ? '#334155' : '#e2e8f0';
    var tooltipText = isDark ? '#f1f5f9' : '#0f172a';
    var axisColor = isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.35)';

    var fmt = function (v) { return Number(v).toLocaleString('pt-AO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' Kz'; };

    var chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Entradas',
                    data: inflows,
                    borderColor: '#10b981',
                    backgroundColor: function (c) { return buildGradient(c.chart, 0, 'rgba(16,185,129,ALPHA)'); },
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: isDark ? '#0f172a' : '#ffffff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#10b981',
                    pointHoverBorderWidth: 3
                },
                {
                    label: 'Saídas',
                    data: outflows,
                    borderColor: '#ef4444',
                    backgroundColor: function (c) { return buildGradient(c.chart, 1, 'rgba(239,68,68,ALPHA)'); },
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: isDark ? '#0f172a' : '#ffffff',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#ef4444',
                    pointHoverBorderWidth: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 800, easing: 'easeOutQuart' },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: { usePointStyle: true, boxWidth: 8, boxHeight: 8, padding: 16, font: { family: 'Inter', size: 12, weight: '600' } }
                },
                tooltip: {
                    backgroundColor: tooltipBg,
                    titleColor: tooltipText,
                    bodyColor: tooltipText,
                    borderColor: tooltipBorder,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    titleFont: { family: 'Inter', size: 12, weight: '600' },
                    bodyFont: { family: 'Inter', size: 13 },
                    displayColors: true,
                    boxPadding: { x: 6, y: 4 },
                    callbacks: {
                        label: function (c) { return c.dataset.label + ': ' + fmt(c.raw); }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor, drawBorder: false },
                    ticks: {
                        color: axisColor,
                        font: { family: 'Inter', size: 11 },
                        callback: function (v) { return fmt(v); }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: axisColor, font: { family: 'Inter', size: 11 } }
                }
            }
        },
        plugins: [{
            id: 'gradientFill',
            beforeDraw: function (chart) {
                var area = chart.chartArea;
                if (!area) return;
                chart.data.datasets.forEach(function (ds, i) {
                    var meta = chart.getDatasetMeta(i);
                    if (!meta.hidden && meta.data && meta.data.length) {
                        var g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
                        var base = i === 0 ? '16,185,129' : '239,68,68';
                        g.addColorStop(0, 'rgba(' + base + ',0.18)');
                        g.addColorStop(1, 'rgba(' + base + ',0.01)');
                        ds.backgroundColor = g;
                    }
                });
            }
        }]
    });
});
