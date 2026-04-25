/**
 * Chart.js initialization and configuration for CGM Insights.
 *
 * Provides functions to create:
 * - Time in Range doughnut chart
 * - Glucose trend line chart
 * - Daily patterns bar chart
 */

// Glucose zone colors (matching clinical standards)
const GLUCOSE_COLORS = {
    very_low: '#ef4444',    // red - severe hypoglycemia
    low: '#f87171',        // light red - hypoglycemia
    target: '#22c55e',     // green - euglycemia
    high: '#facc15',       // yellow - hyperglycemia
    very_high: '#f97316',  // orange - severe hyperglycemia
};

// Chart.js default options
Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
Chart.defaults.color = '#6b7280';

/**
 * Create a Time in Range doughnut chart.
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Object} data - TIR data with very_low, low, target, high, very_high percentages
 */
function createTIRChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error('Canvas not found:', canvasId);
        return null;
    }

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [
                'Very Low (<54 mg/dL)',
                'Low (54-70 mg/dL)',
                'Target (70-180 mg/dL)',
                'High (180-250 mg/dL)',
                'Very High (>250 mg/dL)'
            ],
            datasets: [{
                data: [
                    data.very_low || 0,
                    data.low || 0,
                    data.target || 0,
                    data.high || 0,
                    data.very_high || 0
                ],
                backgroundColor: [
                    GLUCOSE_COLORS.very_low,
                    GLUCOSE_COLORS.low,
                    GLUCOSE_COLORS.target,
                    GLUCOSE_COLORS.high,
                    GLUCOSE_COLORS.very_high
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '60%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create a glucose trend line chart.
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} data - Array of {timestamp, glucose} objects
 */
function createGlucoseTrendChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error('Canvas not found:', canvasId);
        return null;
    }

    if (!data || data.length === 0) {
        console.warn('No glucose data provided');
        return null;
    }

    // Sort data by timestamp
    const sortedData = [...data].sort((a, b) =>
        new Date(a.timestamp) - new Date(b.timestamp)
    );

    // Prepare chart data
    const labels = sortedData.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
               ' ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    });
    const glucoseValues = sortedData.map(d => d.glucose);

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Glucose (mg/dL)',
                data: glucoseValues,
                borderColor: GLUCOSE_COLORS.target,
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                borderWidth: 1.5,
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: GLUCOSE_COLORS.target
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 10
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    min: 40,
                    max: 400,
                    title: {
                        display: true,
                        text: 'Glucose (mg/dL)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Glucose: ${context.raw} mg/dL`;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        targetRange: {
                            type: 'box',
                            yMin: 70,
                            yMax: 180,
                            backgroundColor: 'rgba(34, 197, 94, 0.1)',
                            borderColor: 'transparent',
                            drawTime: 'beforeDatasetsDraw'
                        },
                        lowLine: {
                            type: 'line',
                            yMin: 70,
                            yMax: 70,
                            borderColor: GLUCOSE_COLORS.low,
                            borderWidth: 1,
                            borderDash: [5, 5]
                        },
                        highLine: {
                            type: 'line',
                            yMin: 180,
                            yMax: 180,
                            borderColor: GLUCOSE_COLORS.high,
                            borderWidth: 1,
                            borderDash: [5, 5]
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create a daily patterns bar chart.
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} patterns - Array of pattern objects with time_period, avg_glucose, severity
 */
function createDailyPatternsChart(canvasId, patterns) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error('Canvas not found:', canvasId);
        return null;
    }

    if (!patterns || patterns.length === 0) {
        console.warn('No pattern data provided');
        return null;
    }

    // Filter to time-of-day patterns only
    const timePatterns = patterns.filter(p => p.type === 'time_of_day');

    if (timePatterns.length === 0) {
        return null;
    }

    // Sort by time period
    timePatterns.sort((a, b) => {
        const timeA = parseInt(a.time_period.split('-')[0]) || 0;
        const timeB = parseInt(b.time_period.split('-')[0]) || 0;
        return timeA - timeB;
    });

    const labels = timePatterns.map(p => p.time_period);
    const values = timePatterns.map(p => p.avg_glucose);

    // Color based on glucose level
    const colors = values.map(v => {
        if (v < 70) return GLUCOSE_COLORS.low;
        if (v <= 180) return GLUCOSE_COLORS.target;
        if (v <= 250) return GLUCOSE_COLORS.high;
        return GLUCOSE_COLORS.very_high;
    });

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Glucose (mg/dL)',
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Time Period'
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    min: 0,
                    max: 300,
                    title: {
                        display: true,
                        text: 'Average Glucose (mg/dL)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const pattern = timePatterns[context.dataIndex];
                            return [
                                `Average: ${context.raw.toFixed(0)} mg/dL`,
                                `Readings: ${pattern.reading_count}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize all charts on page load.
 * Called when the DOM is ready.
 */
function initializeCharts() {
    // Initialize TIR chart if data is available
    if (typeof tirData !== 'undefined' && tirData) {
        createTIRChart('tirChart', tirData);
    }

    // Initialize glucose trend chart if data is available
    if (typeof glucoseReadings !== 'undefined' && glucoseReadings && glucoseReadings.length > 0) {
        createGlucoseTrendChart('glucoseTrendChart', glucoseReadings);
    }

    // Initialize daily patterns chart if data is available
    if (typeof patterns !== 'undefined' && patterns && patterns.length > 0) {
        createDailyPatternsChart('dailyPatternsChart', patterns);
    }
}

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});