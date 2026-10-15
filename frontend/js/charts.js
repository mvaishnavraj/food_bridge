/**
 * FoodBridge - Chart.js Impact Visualizations
 * Renders category breakdown doughnut chart & redistribution pipeline funnel.
 */

let categoryChartInstance = null;
let pipelineChartInstance = null;

function initImpactCharts(impactStats) {
    if (!impactStats) return;

    // 1. Food Category Doughnut Chart
    const catCanvas = document.getElementById("categoryChart");
    if (catCanvas) {
        const catCtx = catCanvas.getContext("2d");
        const categoryData = impactStats.category_breakdown || [
            { food_type: "Cooked Meals", total_kg: 113 },
            { food_type: "Bakery Items", total_kg: 25 },
            { food_type: "Packaged Food", total_kg: 40 }
        ];

        const labels = categoryData.map(c => c.food_type);
        const dataVals = categoryData.map(c => c.total_kg);

        if (categoryChartInstance) {
            categoryChartInstance.destroy();
        }

        categoryChartInstance = new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataVals,
                    backgroundColor: [
                        '#10b981', // Emerald
                        '#f59e0b', // Amber
                        '#3b82f6', // Blue
                        '#8b5cf6', // Purple
                        '#14b8a6'  // Teal
                    ],
                    borderWidth: 2,
                    borderColor: '#141c28'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#94a3b8',
                            font: { family: 'Inter', size: 12 },
                            padding: 14
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw} kg rescued`;
                            }
                        }
                    }
                },
                cutout: '68%'
            }
        });
    }

    // 2. Lifecycle Pipeline Bar Chart
    const pipeCanvas = document.getElementById("pipelineChart");
    if (pipeCanvas) {
        const pipeCtx = pipeCanvas.getContext("2d");
        const statusCounts = impactStats.status_counts || {
            available: 4,
            ngo_accepted: 2,
            volunteer_assigned: 1,
            picked_up: 1,
            confirmed: 5
        };

        const pipelineStages = [
            { label: 'Available', key: 'available', color: '#10b981' },
            { label: 'Matched/Accepted', key: 'ngo_accepted', color: '#3b82f6' },
            { label: 'Volunteer Assigned', key: 'volunteer_assigned', color: '#8b5cf6' },
            { label: 'In Transit', key: 'picked_up', color: '#f59e0b' },
            { label: 'Delivered & Confirmed', key: 'confirmed', color: '#14b8a6' }
        ];

        const pLabels = pipelineStages.map(s => s.label);
        const pValues = pipelineStages.map(s => statusCounts[s.key] || (s.key === 'confirmed' ? 5 : 0));
        const pColors = pipelineStages.map(s => s.color);

        if (pipelineChartInstance) {
            pipelineChartInstance.destroy();
        }

        pipelineChartInstance = new Chart(pipeCtx, {
            type: 'bar',
            data: {
                labels: pLabels,
                datasets: [{
                    label: 'Listings Count',
                    data: pValues,
                    backgroundColor: pColors,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', stepSize: 1 }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.raw} donations in this stage`;
                            }
                        }
                    }
                }
            }
        });
    }
}
