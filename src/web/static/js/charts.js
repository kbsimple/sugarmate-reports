/**
 * Chart.js initialization and configuration for CGM Insights.
 *
 * Provides:
 * - Time in Range doughnut chart
 * - Glucose Trend: daily % in-range bar chart
 * - Time-of-Day patterns bar chart (hourly, weekday/weekend toggle)
 * - Behavioral Patterns diurnal line chart
 * - computeWindowDetails() for expandable Time Windows rows
 */

// Glucose zone colors (matching clinical standards)
const GLUCOSE_COLORS = {
    very_low: '#ef4444',
    low: '#f87171',
    target: '#22c55e',
    high: '#facc15',
    very_high: '#f97316',
};

Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
Chart.defaults.color = '#6b7280';

// ─── TIR Doughnut ────────────────────────────────────────────────────────────

function createTIRChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

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
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.label}: ${ctx.raw.toFixed(1)}%`
                    }
                }
            }
        }
    });
}

// ─── Glucose Trend: daily % in-range bar chart ────────────────────────────────

/**
 * Group raw glucose readings by calendar date and compute daily % in-range.
 *
 * @param {Array} readings - Array of {timestamp, glucose}
 * @returns {Array} Sorted array of {date, pctInRange, total, inRange}
 */
function computeDailyTIR(readings) {
    const byDate = {};
    for (const r of readings) {
        const ts = new Date(r.timestamp);
        // Use LOCAL calendar date as key — toISOString() shifts to UTC and misgroups late-night readings
        const isoKey = `${ts.getFullYear()}-${String(ts.getMonth()+1).padStart(2,'0')}-${String(ts.getDate()).padStart(2,'0')}`;
        const dateStr = ts.toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric'
        });
        if (!byDate[isoKey]) byDate[isoKey] = { dateStr, total: 0, inRange: 0, ts };
        byDate[isoKey].total++;
        if (r.glucose >= 70 && r.glucose <= 180) byDate[isoKey].inRange++;
    }
    const all = Object.entries(byDate)
        .sort(([, a], [, b]) => a.ts - b.ts)
        .map(([, v]) => ({
            date: v.dateStr,
            pctInRange: Math.round(v.inRange / v.total * 100),
            total: v.total,
            inRange: v.inRange
        }));
    return all.slice(-21);
}

function createGlucoseTrendChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    if (!data || data.length === 0) return null;

    const daily = computeDailyTIR(data);
    if (daily.length === 0) return null;

    const labels = daily.map(d => d.date);
    const values = daily.map(d => d.pctInRange);

    // Color each bar: green ≥70%, yellow 50-70%, red <50%
    const colors = values.map(v =>
        v >= 70 ? 'rgba(34,197,94,0.8)' :
        v >= 50 ? 'rgba(250,204,21,0.85)' :
                  'rgba(239,68,68,0.8)'
    );

    // Dashed 70% reference line via custom plugin
    const refLinePlugin = {
        id: 'refLine70',
        afterDatasetsDraw(chart) {
            const { ctx: c, scales: { y }, chartArea: { left, right } } = chart;
            const yPx = y.getPixelForValue(70);
            c.save();
            c.strokeStyle = 'rgba(34,197,94,0.6)';
            c.lineWidth = 1.5;
            c.setLineDash([6, 4]);
            c.beginPath();
            c.moveTo(left, yPx);
            c.lineTo(right, yPx);
            c.stroke();
            c.restore();
        }
    };

    return new Chart(ctx, {
        type: 'bar',
        plugins: [refLinePlugin],
        data: {
            labels,
            datasets: [{
                label: '% In Range',
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                borderRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 21 }
                },
                y: {
                    min: 0, max: 100,
                    title: { display: true, text: '% Time in Range (70-180)' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const d = daily[ctx.dataIndex];
                            return [
                                `In range: ${ctx.raw}%`,
                                `Readings: ${d.inRange} / ${d.total}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

// ─── Time-of-Day patterns bar chart (with weekday/weekend toggle) ─────────────

let todChart = null;

function extractHourlyPatterns(bp) {
    if (!bp || bp.insufficient_data || !bp.patterns) return { hourly: [], hasWeekdaySplit: false };
    const hourly = bp.patterns.filter(p => p.window_size_min === 60 && p.bucket_start_minute % 60 === 0);
    const hasWeekdaySplit = hourly.some(p => p.weekday_avg_glucose !== null && p.weekend_avg_glucose !== null);
    return { hourly, hasWeekdaySplit };
}

function patternGlucoseForDayType(pattern, dayType) {
    if (dayType === 'weekdays' && pattern.weekday_avg_glucose !== null) return pattern.weekday_avg_glucose;
    if (dayType === 'weekends' && pattern.weekend_avg_glucose !== null) return pattern.weekend_avg_glucose;
    return pattern.avg_glucose;
}

function glucoseBarColor(v) {
    if (v < 70) return GLUCOSE_COLORS.low;
    if (v <= 180) return GLUCOSE_COLORS.target;
    if (v <= 250) return GLUCOSE_COLORS.high;
    return GLUCOSE_COLORS.very_high;
}

function updateToDChart(dayType) {
    if (!todChart) return;
    const bp = typeof behavioralPatterns !== 'undefined' ? behavioralPatterns : null;
    const { hourly } = extractHourlyPatterns(bp);
    if (!hourly.length) return;
    const values = hourly.map(p => {
        const v = patternGlucoseForDayType(p, dayType);
        return v !== null ? Math.round(v * 10) / 10 : null;
    });
    todChart.data.datasets[0].data = values;
    todChart.data.datasets[0].backgroundColor = values.map(v => v !== null ? glucoseBarColor(v) : 'transparent');
    todChart.update();
}

function createDailyPatternsChart(canvasId, legacyPatterns, bp) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const { hourly, hasWeekdaySplit } = extractHourlyPatterns(bp);
    const useBehavioral = hourly.length > 0;

    let labels, values;
    if (useBehavioral) {
        labels = hourly.map(p => p.bucket_label);
        values = hourly.map(p => Math.round(p.avg_glucose * 10) / 10);
    } else {
        if (!legacyPatterns || !legacyPatterns.length) return null;
        const timePatterns = legacyPatterns.filter(p => p.type === 'time_of_day');
        if (!timePatterns.length) return null;
        timePatterns.sort((a, b) => (parseInt(a.time_period) || 0) - (parseInt(b.time_period) || 0));
        labels = timePatterns.map(p => p.time_period);
        values = timePatterns.map(p => p.avg_glucose);
    }

    const colors = values.map(glucoseBarColor);

    if (!hasWeekdaySplit) {
        const filter = document.getElementById('todDayTypeFilter');
        if (filter) { filter.disabled = true; filter.title = 'Weekday/weekend split requires at least 5 days of data'; }
    }

    todChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{ label: 'Average Glucose (mg/dL)', data: values, backgroundColor: colors, borderWidth: 0, borderRadius: 4 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: true,
                    title: { display: true, text: 'Hour' },
                    grid: { display: false },
                    ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 24 }
                },
                y: {
                    min: 0, max: 300,
                    title: { display: true, text: 'Average Glucose (mg/dL)' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (ctx) => [`Average: ${ctx.raw} mg/dL`] } }
            }
        }
    });
    return todChart;
}

// ─── Behavioral Patterns: diurnal line chart ──────────────────────────────────

/**
 * Draw target-range band (70-180) behind the behavioral patterns chart.
 */
const targetBandPlugin = {
    id: 'targetBand',
    beforeDatasetsDraw(chart) {
        const { ctx: c, scales: { y }, chartArea: { left, right } } = chart;
        if (!y) return;
        const y70 = y.getPixelForValue(70);
        const y180 = y.getPixelForValue(180);
        c.save();
        c.fillStyle = 'rgba(34,197,94,0.08)';
        c.fillRect(left, y180, right - left, y70 - y180);
        c.restore();
    }
};

function createBehavioralPatternsLineChart(canvasId, bp) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    if (!bp || bp.insufficient_data || !bp.patterns) return null;

    const hourly = bp.patterns
        .filter(p => p.window_size_min === 60 && p.bucket_start_minute % 60 === 0)
        .sort((a, b) => a.bucket_start_minute - b.bucket_start_minute);

    if (!hourly.length) return null;

    // x-axis labels: short hour labels ("12am", "6am", etc.)
    const labels = hourly.map(p => {
        const h = Math.floor(p.bucket_start_minute / 60);
        if (h === 0) return '12am';
        if (h < 12) return `${h}am`;
        if (h === 12) return '12pm';
        return `${h - 12}pm`;
    });

    const allValues = hourly.map(p => Math.round(p.avg_glucose * 10) / 10);
    const hasWeekdaySplit = hourly.some(p => p.weekday_avg_glucose !== null && p.weekend_avg_glucose !== null);

    const datasets = [
        {
            label: 'All Days',
            data: allValues,
            borderColor: 'rgba(99,102,241,0.9)',
            backgroundColor: 'transparent',
            borderWidth: 2.5,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 5,
            order: 1
        }
    ];

    if (hasWeekdaySplit) {
        datasets.push({
            label: 'Weekdays',
            data: hourly.map(p => p.weekday_avg_glucose !== null ? Math.round(p.weekday_avg_glucose * 10) / 10 : null),
            borderColor: 'rgba(59,130,246,0.75)',
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            borderDash: [4, 3],
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 4,
            order: 2
        });
        datasets.push({
            label: 'Weekends',
            data: hourly.map(p => p.weekend_avg_glucose !== null ? Math.round(p.weekend_avg_glucose * 10) / 10 : null),
            borderColor: 'rgba(245,158,11,0.8)',
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            borderDash: [4, 3],
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 4,
            order: 3
        });
    }

    return new Chart(ctx, {
        type: 'line',
        plugins: [targetBandPlugin],
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                x: {
                    display: true,
                    title: { display: true, text: 'Time of Day' },
                    grid: { display: false }
                },
                y: {
                    display: true,
                    min: 40, max: 350,
                    title: { display: true, text: 'Average Glucose (mg/dL)' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { boxWidth: 20, padding: 12 }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ctx.raw !== null ? `${ctx.dataset.label}: ${ctx.raw} mg/dL` : null
                    }
                }
            }
        }
    });
}

// ─── Per-date window detail (for expandable Time Windows rows) ─────────────────

/**
 * Compute per-date glucose stats for a specific time window from raw readings.
 * Called by Alpine.js on row expand.
 *
 * @param {number} bucketStart - minutes from midnight (e.g. 480 for 8:00am)
 * @param {number} windowMin   - window duration in minutes (e.g. 60)
 * @returns {Array} sorted array of {date, avgGlucose, readings, min, max, pctInRange}
 */
function computeWindowDetails(bucketStart, windowMin) {
    const readings = typeof glucoseReadings !== 'undefined' ? glucoseReadings : [];
    if (!readings.length) return [];

    const bucketEnd = bucketStart + windowMin;
    const byDate = {};

    for (const r of readings) {
        const ts = new Date(r.timestamp);
        const mod = ts.getHours() * 60 + ts.getMinutes();
        const inBucket = bucketEnd <= 1440
            ? mod >= bucketStart && mod < bucketEnd
            : mod >= bucketStart || mod < (bucketEnd - 1440);
        if (!inBucket) continue;

        // Key by full date for sorting; display as short label
        const isoDate = ts.toISOString().slice(0, 10);
        const dispDate = ts.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        if (!byDate[isoDate]) byDate[isoDate] = { dispDate, values: [] };
        byDate[isoDate].values.push(r.glucose);
    }

    return Object.entries(byDate)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([, { dispDate, values }]) => {
            const avg = Math.round(values.reduce((s, v) => s + v, 0) / values.length);
            const inRange = values.filter(v => v >= 70 && v <= 180).length;
            return {
                date: dispDate,
                avgGlucose: avg,
                readings: values.length,
                min: Math.round(Math.min(...values)),
                max: Math.round(Math.max(...values)),
                pctInRange: Math.round(inRange / values.length * 100)
            };
        });
}

// ─── Init ─────────────────────────────────────────────────────────────────────

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
    createBehavioralPatternsLineChart('behavioralPatternsChart', bp);
}

document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});
