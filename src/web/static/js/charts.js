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
function computeDailyTIR(readings, dateRange) {
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

    const sorted = Object.entries(byDate).sort(([a], [b]) => a.localeCompare(b));
    if (sorted.length === 0) return [];

    // Use server-supplied date range when available so the chart fills the full
    // analysis period even when the sensor was inactive at the start or end.
    const firstKey = (dateRange && dateRange.start) ? dateRange.start : sorted[0][0];
    const lastKey  = (dateRange && dateRange.end)   ? dateRange.end   : sorted[sorted.length - 1][0];

    const result = [];
    const cursor = new Date(firstKey + 'T00:00:00');
    const end    = new Date(lastKey  + 'T00:00:00');

    while (cursor <= end) {
        const isoKey  = `${cursor.getFullYear()}-${String(cursor.getMonth()+1).padStart(2,'0')}-${String(cursor.getDate()).padStart(2,'0')}`;
        const dateStr = cursor.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        const v = byDate[isoKey];
        result.push(v
            ? { date: v.dateStr, pctInRange: Math.round(v.inRange / v.total * 100), total: v.total, inRange: v.inRange, hasData: true }
            : { date: dateStr, pctInRange: 0, total: 0, inRange: 0, hasData: false }
        );
        cursor.setDate(cursor.getDate() + 1);
    }
    return result;
}

function _enableDragScroll(el) {
    let isDown = false, startX, scrollLeft;
    el.addEventListener('mousedown', e => { isDown = true; startX = e.pageX - el.offsetLeft; scrollLeft = el.scrollLeft; el.style.cursor = 'grabbing'; });
    el.addEventListener('mouseleave', () => { isDown = false; el.style.cursor = 'grab'; });
    el.addEventListener('mouseup', () => { isDown = false; el.style.cursor = 'grab'; });
    el.addEventListener('mousemove', e => { if (!isDown) return; e.preventDefault(); el.scrollLeft = scrollLeft - (e.pageX - el.offsetLeft - startX); });
}

function createGlucoseTrendChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    if (!data || data.length === 0) return null;

    const dateRange = typeof glucoseDateRange !== 'undefined' ? glucoseDateRange : null;
    const daily = computeDailyTIR(data, dateRange);
    if (daily.length === 0) return null;

    // Each bar gets a fixed pixel budget so the chart grows beyond the viewport and becomes scrollable
    const BAR_PX = 32;
    const scroll = document.getElementById('glucoseTrendScroll');
    const wrapper = document.getElementById('glucoseTrendOuter');
    if (wrapper) {
        const needed = daily.length * BAR_PX;
        if (needed > wrapper.offsetWidth) {
            wrapper.style.width = needed + 'px';
            // Show scroll hint and enable drag-to-scroll
            const hint = document.getElementById('glucoseTrendScrollHint');
            if (hint) hint.classList.remove('hidden');
            if (scroll) _enableDragScroll(scroll);
        }
    }

    const labels = daily.map(d => d.date);
    const values = daily.map(d => d.pctInRange);

    // Color each bar: grey for no-data days, then green/yellow/red by TIR
    const colors = daily.map(d =>
        !d.hasData         ? 'rgba(156,163,175,0.35)' :
        d.pctInRange >= 70 ? 'rgba(34,197,94,0.8)'    :
        d.pctInRange >= 50 ? 'rgba(250,204,21,0.85)'   :
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
                    ticks: { maxRotation: 45, autoSkip: false }
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
                            if (!d.hasData) return ['No readings recorded'];
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

// ─── Time-of-Day patterns: three inline box-plot charts (All / Weekdays / Weekends) ──

function extractHourlyPatterns(bp) {
    if (!bp || bp.insufficient_data || !bp.patterns) return { hourly: [], hasWeekdaySplit: false };
    const hourly = bp.patterns.filter(p => p.window_size_min === 60 && p.bucket_start_minute % 60 === 0);
    const hasWeekdaySplit = hourly.some(p => p.weekday_avg_glucose !== null && p.weekend_avg_glucose !== null);
    return { hourly, hasWeekdaySplit };
}

// Shared target-band plugin (70–180 green fill) used by ToD charts
const _todTargetBandPlugin = {
    id: 'todTargetBand',
    beforeDatasetsDraw(chart) {
        const { ctx: c, scales: { y }, chartArea: { left, right } } = chart;
        if (!y) return;
        const y70 = y.getPixelForValue(70);
        const y180 = y.getPixelForValue(180);
        c.save();
        c.fillStyle = 'rgba(34,197,94,0.07)';
        c.fillRect(left, y180, right - left, y70 - y180);
        c.restore();
    }
};

function _makeTodBoxChart(canvasId, labels, pts) {
    // pts: array of {avg, p25, p50, p75} — any field may be null
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const hasPercentiles = pts.some(d => d.p25 !== null && d.p75 !== null);

    // Build datasets. IQR band uses fill-between-lines:
    //   datasets[0] = p75 upper boundary, fill: '+1' → fills down to datasets[1]
    //   datasets[1] = p25 lower boundary, fill: false (floor of the filled area)
    // Both boundary lines are invisible (no border); only the fill shows.
    const datasets = [];

    if (hasPercentiles) {
        datasets.push({
            label: 'IQR (25th–75th %ile)',
            data: pts.map(d => d.p75 !== null ? Math.round(d.p75 * 10) / 10 : null),
            backgroundColor: 'rgba(99,102,241,0.22)',
            borderColor: 'transparent',
            borderWidth: 0,
            pointRadius: 0,
            fill: '+1',
            tension: 0.3,
        });
        datasets.push({
            label: '',
            data: pts.map(d => d.p25 !== null ? Math.round(d.p25 * 10) / 10 : null),
            backgroundColor: 'transparent',
            borderColor: 'transparent',
            borderWidth: 0,
            pointRadius: 0,
            fill: false,
            tension: 0.3,
        });
    }

    datasets.push({
        label: 'Median (50th %ile)',
        data: pts.map(d => d.p50 !== null ? Math.round(d.p50 * 10) / 10 : null),
        borderColor: 'rgba(99,102,241,1)',
        backgroundColor: 'transparent',
        borderWidth: 2.5,
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.3,
        fill: false,
    });

    datasets.push({
        label: 'Mean',
        data: pts.map(d => d.avg !== null ? Math.round(d.avg * 10) / 10 : null),
        borderColor: 'rgba(239,68,68,0.75)',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        borderDash: [5, 3],
        pointRadius: 2,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: false,
    });

    return new Chart(ctx, {
        type: 'line',
        plugins: [_todTargetBandPlugin],
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 12 }
                },
                y: {
                    min: 40, max: 350,
                    title: { display: true, text: 'Glucose (mg/dL)' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 16,
                        padding: 10,
                        font: { size: 11 },
                        filter: item => item.text !== ''
                    }
                },
                tooltip: {
                    callbacks: {
                        label: item => {
                            if (item.raw === null || item.dataset.label === '') return null;
                            return `${item.dataset.label}: ${item.raw} mg/dL`;
                        }
                    }
                }
            }
        }
    });
}

function createDailyPatternCharts(legacyPatterns, bp) {
    const { hourly, hasWeekdaySplit } = extractHourlyPatterns(bp);
    const useBehavioral = hourly.length > 0;

    let labels, allPts, wdPts, wePts;
    if (useBehavioral) {
        labels = hourly.map(p => p.bucket_label);
        allPts = hourly.map(p => ({
            avg: p.avg_glucose,
            p25: p.p25_glucose ?? null,
            p50: p.p50_glucose ?? null,
            p75: p.p75_glucose ?? null,
        }));
        wdPts = hourly.map(p => ({
            avg: p.weekday_avg_glucose,
            p25: p.weekday_p25_glucose ?? null,
            p50: p.weekday_p50_glucose ?? null,
            p75: p.weekday_p75_glucose ?? null,
        }));
        wePts = hourly.map(p => ({
            avg: p.weekend_avg_glucose,
            p25: p.weekend_p25_glucose ?? null,
            p50: p.weekend_p50_glucose ?? null,
            p75: p.weekend_p75_glucose ?? null,
        }));
    } else {
        if (!legacyPatterns || !legacyPatterns.length) return;
        const timePatterns = legacyPatterns.filter(p => p.type === 'time_of_day');
        if (!timePatterns.length) return;
        timePatterns.sort((a, b) => (parseInt(a.time_period) || 0) - (parseInt(b.time_period) || 0));
        labels = timePatterns.map(p => p.time_period);
        allPts = timePatterns.map(p => ({ avg: p.avg_glucose, p25: null, p50: null, p75: null }));
        wdPts = null;
        wePts = null;
    }

    _makeTodBoxChart('dailyPatternsChartAll', labels, allPts);

    const hasWdData = wdPts && wdPts.some(d => d.avg !== null);
    const hasWeData = wePts && wePts.some(d => d.avg !== null);

    if (!hasWeekdaySplit || !hasWdData || !hasWeData) {
        const weekdaysCol = document.getElementById('todWeekdaysCol');
        const weekendsCol = document.getElementById('todWeekendsCol');
        if (weekdaysCol) weekdaysCol.style.display = 'none';
        if (weekendsCol) weekendsCol.style.display = 'none';
        return;
    }

    _makeTodBoxChart('dailyPatternsChartWeekdays', labels, wdPts);
    _makeTodBoxChart('dailyPatternsChartWeekends', labels, wePts);
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

// ─── Recurring Trend IQR chart ────────────────────────────────────────────────

/**
 * Render a single recurring trend as a line chart with IQR shading.
 *
 * @param {string} canvasId - id of the <canvas> element
 * @param {Object} trend    - RecurringTrend object from recurringTrends.trends[]
 */
function createRecurringTrendChart(canvasId, trend) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const slots   = trend.slots;
    const labels  = slots.map(s => s.label);
    const q1      = slots.map(s => s.q1);
    const medians = slots.map(s => s.median);
    const q3      = slots.map(s => s.q3);

    const isRising = trend.direction === 'rising';
    const rgb   = isRising ? '245,158,11' : '99,102,241';
    const solid = isRising ? '#f59e0b'    : '#6366f1';

    const allVals = [...q1, ...medians, ...q3].filter(v => v != null);
    const yMin = allVals.length ? Math.max(40,  Math.floor(Math.min(...allVals) - 15)) : 40;
    const yMax = allVals.length ? Math.min(400, Math.ceil(Math.max(...allVals)  + 15)) : 300;

    new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [
                // Q3 fills toward dataset[+1] (Q1), creating the IQR band
                {
                    label: 'Q3',
                    data: q3,
                    fill: '+1',
                    backgroundColor: `rgba(${rgb},0.15)`,
                    borderColor: `rgba(${rgb},0.25)`,
                    borderWidth: 1,
                    borderDash: [3, 3],
                    pointRadius: 0,
                    tension: 0.35,
                },
                {
                    label: 'Q1',
                    data: q1,
                    fill: false,
                    borderColor: `rgba(${rgb},0.25)`,
                    borderWidth: 1,
                    borderDash: [3, 3],
                    pointRadius: 0,
                    tension: 0.35,
                },
                {
                    label: 'Median',
                    data: medians,
                    fill: false,
                    borderColor: solid,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: solid,
                    tension: 0.35,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    filter: item => item.datasetIndex === 2,
                    callbacks: {
                        label: ctx => {
                            const s = slots[ctx.dataIndex];
                            return [
                                `Median: ${ctx.parsed.y} mg/dL`,
                                `IQR: ${s.q1}–${s.q3} mg/dL`,
                                `${s.day_count} day${s.day_count !== 1 ? 's' : ''}`,
                            ];
                        },
                    },
                },
            },
            scales: {
                x: { ticks: { maxTicksLimit: 8, maxRotation: 0 } },
                y: {
                    min: yMin,
                    max: yMax,
                    title: { display: true, text: 'mg/dL', font: { size: 11 } },
                    ticks: { stepSize: 20 },
                },
            },
        },
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
function computeWindowDetails(bucketStart, windowMin, dayType) {
    const readings = typeof glucoseReadings !== 'undefined' ? glucoseReadings : [];
    if (!readings.length) return [];

    const bucketEnd = bucketStart + windowMin;
    const byDate = {};

    for (const r of readings) {
        const ts = new Date(r.timestamp);

        // Filter by day type before anything else
        const dow = ts.getDay(); // 0=Sun, 6=Sat
        const isWeekend = dow === 0 || dow === 6;
        if (dayType === 'weekday' && isWeekend) continue;
        if (dayType === 'weekend' && !isWeekend) continue;

        const mod = ts.getHours() * 60 + ts.getMinutes();
        const inBucket = bucketEnd <= 1440
            ? mod >= bucketStart && mod < bucketEnd
            : mod >= bucketStart || mod < (bucketEnd - 1440);
        if (!inBucket) continue;

        // Use local calendar date as key (toISOString uses UTC and misgroups late-night readings)
        const localKey = `${ts.getFullYear()}-${String(ts.getMonth()+1).padStart(2,'0')}-${String(ts.getDate()).padStart(2,'0')}`;
        const dispDate = ts.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        if (!byDate[localKey]) byDate[localKey] = { dispDate, values: [] };
        byDate[localKey].values.push(r.glucose);
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
    createDailyPatternCharts(legacyPatterns, bp);
    createBehavioralPatternsLineChart('behavioralPatternsChart', bp);

    const rt = typeof recurringTrends !== 'undefined' ? recurringTrends : null;
    if (rt && !rt.insufficient_data && Array.isArray(rt.trends)) {
        rt.trends.forEach((trend, i) => {
            createRecurringTrendChart(`recurringTrendChart_${i + 1}`, trend);
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});
