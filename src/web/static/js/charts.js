/**
 * Chart.js initialization and configuration for CGM Insights.
 *
 * Provides functions to create:
 * - Time in Range doughnut chart
 * - Glucose trend line chart (with 3-week diurnal average overlay)
 * - Time-of-Day patterns bar chart (hourly, with weekday/weekend toggle)
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
 * Compute per-30-minute bucket averages from glucose readings over the last N days.
 *
 * @param {Array} sortedData - Sorted array of {timestamp, glucose} objects
 * @param {number} days - How many trailing days to include (default 21 = 3 weeks)
 * @returns {number[]} Array of 48 averages (null if no data for that bucket)
 */
function computeDiurnalAverages(sortedData, days = 21) {
    if (!sortedData || sortedData.length === 0) return new Array(48).fill(null);

    const latestTs = new Date(sortedData[sortedData.length - 1].timestamp);
    const cutoff = new Date(latestTs);
    cutoff.setDate(cutoff.getDate() - days);

    const sums = new Array(48).fill(0);
    const counts = new Array(48).fill(0);

    for (const d of sortedData) {
        const ts = new Date(d.timestamp);
        if (ts < cutoff) continue;
        const bucket = ts.getHours() * 2 + (ts.getMinutes() >= 30 ? 1 : 0);
        sums[bucket] += d.glucose;
        counts[bucket]++;
    }

    return sums.map((sum, i) => (counts[i] > 0 ? sum / counts[i] : null));
}

/**
 * Create a glucose trend line chart with a 3-week diurnal average overlay.
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

    // Compute 3-week diurnal bucket averages and map back to each timestamp
    const bucketAvgs = computeDiurnalAverages(sortedData, 21);
    const avgOverlay = sortedData.map(d => {
        const ts = new Date(d.timestamp);
        const bucket = ts.getHours() * 2 + (ts.getMinutes() >= 30 ? 1 : 0);
        return bucketAvgs[bucket] !== null ? Math.round(bucketAvgs[bucket] * 10) / 10 : null;
    });

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Glucose (mg/dL)',
                    data: glucoseValues,
                    borderColor: GLUCOSE_COLORS.target,
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    borderWidth: 1.5,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: GLUCOSE_COLORS.target,
                    order: 2
                },
                {
                    label: '3-Week Avg (30-min)',
                    data: avgOverlay,
                    borderColor: 'rgba(99, 102, 241, 0.85)',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 3,
                    borderDash: [5, 3],
                    order: 1
                }
            ]
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
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 20,
                        padding: 12,
                        usePointStyle: false
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            if (context.datasetIndex === 0) {
                                return `Glucose: ${context.raw} mg/dL`;
                            }
                            return context.raw !== null
                                ? `3-Wk Avg: ${context.raw} mg/dL`
                                : null;
                        }
                    }
                }
            }
        }
    });
}

// Module-level reference to the Time-of-Day chart instance for updates
let todChart = null;

/**
 * Extract hourly (60-min boundary) patterns from behavioral_patterns, keyed by day type.
 *
 * @param {Object|null} bp - behavioralPatterns global (may be null)
 * @returns {Object} { hourly: Array, hasWeekdaySplit: boolean }
 */
function extractHourlyPatterns(bp) {
    if (!bp || bp.insufficient_data || !bp.patterns) {
        return { hourly: [], hasWeekdaySplit: false };
    }

    const hourly = bp.patterns.filter(p =>
        p.window_size_min === 60 && p.bucket_start_minute % 60 === 0
    );

    const hasWeekdaySplit = hourly.some(
        p => p.weekday_avg_glucose !== null && p.weekend_avg_glucose !== null
    );

    return { hourly, hasWeekdaySplit };
}

/**
 * Get the glucose value for a pattern given the current day type filter.
 *
 * @param {Object} pattern
 * @param {string} dayType - 'all' | 'weekdays' | 'weekends'
 * @returns {number|null}
 */
function patternGlucoseForDayType(pattern, dayType) {
    if (dayType === 'weekdays' && pattern.weekday_avg_glucose !== null) {
        return pattern.weekday_avg_glucose;
    }
    if (dayType === 'weekends' && pattern.weekend_avg_glucose !== null) {
        return pattern.weekend_avg_glucose;
    }
    return pattern.avg_glucose;
}

/**
 * Color a bar based on glucose value.
 */
function glucoseBarColor(v) {
    if (v < 70) return GLUCOSE_COLORS.low;
    if (v <= 180) return GLUCOSE_COLORS.target;
    if (v <= 250) return GLUCOSE_COLORS.high;
    return GLUCOSE_COLORS.very_high;
}

/**
 * Update the Time-of-Day chart dataset when the day-type filter changes.
 *
 * @param {string} dayType - 'all' | 'weekdays' | 'weekends'
 */
function updateToDChart(dayType) {
    if (!todChart) return;

    const bp = typeof behavioralPatterns !== 'undefined' ? behavioralPatterns : null;
    const { hourly } = extractHourlyPatterns(bp);

    if (hourly.length === 0) return;

    const values = hourly.map(p => {
        const v = patternGlucoseForDayType(p, dayType);
        return v !== null ? Math.round(v * 10) / 10 : null;
    });

    todChart.data.datasets[0].data = values;
    todChart.data.datasets[0].backgroundColor = values.map(v =>
        v !== null ? glucoseBarColor(v) : 'transparent'
    );
    todChart.update();
}

/**
 * Create the Time-of-Day patterns bar chart.
 * Uses 60-min hourly behavioral patterns when available; falls back to legacy pattern data.
 *
 * @param {string} canvasId - Canvas element ID
 * @param {Array} legacyPatterns - Fallback array of time_of_day pattern objects
 * @param {Object|null} bp - behavioralPatterns data (may be null)
 */
function createDailyPatternsChart(canvasId, legacyPatterns, bp) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error('Canvas not found:', canvasId);
        return null;
    }

    const { hourly, hasWeekdaySplit } = extractHourlyPatterns(bp);

    // Prefer behavioral hourly patterns; fall back to legacy
    const useBehavioral = hourly.length > 0;

    let labels, values;

    if (useBehavioral) {
        labels = hourly.map(p => p.bucket_label);
        values = hourly.map(p => Math.round(p.avg_glucose * 10) / 10);
    } else {
        if (!legacyPatterns || legacyPatterns.length === 0) {
            console.warn('No pattern data provided');
            return null;
        }
        const timePatterns = legacyPatterns.filter(p => p.type === 'time_of_day');
        if (timePatterns.length === 0) return null;
        timePatterns.sort((a, b) => {
            const timeA = parseInt(a.time_period.split('-')[0]) || 0;
            const timeB = parseInt(b.time_period.split('-')[0]) || 0;
            return timeA - timeB;
        });
        labels = timePatterns.map(p => p.time_period);
        values = timePatterns.map(p => p.avg_glucose);
    }

    const colors = values.map(v => glucoseBarColor(v));

    // Disable the filter dropdown if no weekday/weekend split is available
    if (!hasWeekdaySplit) {
        const filter = document.getElementById('todDayTypeFilter');
        if (filter) {
            filter.disabled = true;
            filter.title = 'Weekday/weekend split requires at least 5 days of data';
        }
    }

    todChart = new Chart(ctx, {
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
                        text: 'Hour'
                    },
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 24
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
                            return [`Average: ${context.raw} mg/dL`];
                        }
                    }
                }
            }
        }
    });

    return todChart;
}

/**
 * Initialize all charts on page load.
 */
function initializeCharts() {
    if (typeof tirData !== 'undefined' && tirData) {
        createTIRChart('tirChart', tirData);
    }

    if (typeof glucoseReadings !== 'undefined' && glucoseReadings && glucoseReadings.length > 0) {
        createGlucoseTrendChart('glucoseTrendChart', glucoseReadings);
    }

    const bp = typeof behavioralPatterns !== 'undefined' ? behavioralPatterns : null;
    const legacyPatterns = typeof patterns !== 'undefined' ? patterns : [];
    createDailyPatternsChart('dailyPatternsChart', legacyPatterns, bp);
}

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});
