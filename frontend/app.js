/**
 * AssignFlow Dashboard Application Script
 * Dynamically connects to FastAPI backend on http://localhost:8000
 * Handles health checking, metric aggregation, Chart.js visualizations, and live anomaly queue rendering.
 */

const BACKEND_URL = 'http://localhost:8000';

// Global Chart Instances for safe lifecycle cleanup
let severityChartInstance = null;
let platformChartInstance = null;

// DOM Elements
const apiStatusEl = document.getElementById('api-status');
const errorBannerEl = document.getElementById('error-banner');
const errorMessageEl = document.getElementById('error-message');
const refreshBtn = document.getElementById('refresh-btn');
const refreshIcon = document.getElementById('refresh-icon');
const lastUpdatedTimeEl = document.getElementById('last-updated-time');

// Metric Elements
const metricCoursesEl = document.getElementById('metric-courses');
const metricLearnersEl = document.getElementById('metric-learners');
const metricAssignmentsEl = document.getElementById('metric-assignments');
const metricSubmissionsEl = document.getElementById('metric-submissions');
const metricAvgScoreEl = document.getElementById('metric-avg-score');

// Anomaly Elements
const anomalyBadgeEl = document.getElementById('anomaly-badge');
const anomaliesTableBodyEl = document.getElementById('anomalies-table-body');

/**
 * Checks backend health endpoint
 */
async function checkBackendHealth() {
    try {
        const response = await fetch(`${BACKEND_URL}/health`);
        const data = await response.json();

        if (data.status === 'ok') {
            apiStatusEl.innerHTML = `
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Connected (OK)</span>
            `;
            apiStatusEl.className = 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 transition-all';
            hideError();
            return true;
        } else {
            throw new Error('Backend returned non-OK status');
        }
    } catch (error) {
        apiStatusEl.innerHTML = `
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            <span>Disconnected</span>
        `;
        apiStatusEl.className = 'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 transition-all';
        showError('Unable to connect to AssignFlow Backend (http://localhost:8000). Ensure FastAPI is running on port 8000.');
        console.error('Health check failed:', error);
        return false;
    }
}

/**
 * Shows skeleton loading states
 */
function showLoadingSkeletons() {
    const skeletonBox = '<div class="h-8 w-20 bg-slate-100 animate-pulse rounded-lg my-1"></div>';
    metricCoursesEl.innerHTML = skeletonBox;
    metricLearnersEl.innerHTML = skeletonBox;
    metricAssignmentsEl.innerHTML = skeletonBox;
    metricSubmissionsEl.innerHTML = skeletonBox;
    metricAvgScoreEl.innerHTML = skeletonBox;

    anomaliesTableBodyEl.innerHTML = `
        <tr class="animate-pulse">
            <td class="px-6 py-4"><div class="h-6 w-20 bg-slate-100 rounded-md"></div></td>
            <td class="px-6 py-4"><div class="h-4 w-48 bg-slate-100 rounded"></div></td>
            <td class="px-6 py-4"><div class="h-5 w-32 bg-slate-100 rounded"></div></td>
            <td class="px-6 py-4"><div class="h-4 w-72 bg-slate-100 rounded"></div></td>
            <td class="px-6 py-4"><div class="h-6 w-28 bg-slate-100 rounded-full ml-auto"></div></td>
        </tr>
        <tr class="animate-pulse">
            <td class="px-6 py-4"><div class="h-6 w-20 bg-slate-100 rounded-md"></div></td>
            <td class="px-6 py-4"><div class="h-4 w-40 bg-slate-100 rounded"></div></td>
            <td class="px-6 py-4"><div class="h-5 w-32 bg-slate-100 rounded"></div></td>
            <td class="px-6 py-4"><div class="h-4 w-64 bg-slate-100 rounded"></div></td>
            <td class="px-6 py-4"><div class="h-6 w-28 bg-slate-100 rounded-full ml-auto"></div></td>
        </tr>
    `;
}

/**
 * Fetches system KPI metrics
 */
async function loadMetrics() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/dashboard/metrics`);
        if (!response.ok) {
            throw new Error(`Metrics endpoint returned HTTP ${response.status}`);
        }
        const data = await response.json();

        renderMetricValue(metricCoursesEl, Number(data.total_courses || 0).toLocaleString());
        renderMetricValue(metricLearnersEl, Number(data.total_learners || 0).toLocaleString());
        renderMetricValue(metricAssignmentsEl, Number(data.total_assignments || 0).toLocaleString());
        renderMetricValue(metricSubmissionsEl, Number(data.total_submissions || 0).toLocaleString());
        renderMetricValue(metricAvgScoreEl, `${Number(data.average_score || 0).toFixed(2)}`);

        const now = new Date();
        lastUpdatedTimeEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        return data;
    } catch (error) {
        console.error('Failed to load metrics:', error);
        metricCoursesEl.textContent = '--';
        metricLearnersEl.textContent = '--';
        metricAssignmentsEl.textContent = '--';
        metricSubmissionsEl.textContent = '--';
        metricAvgScoreEl.textContent = '--';
        return null;
    }
}

/**
 * Animates text insertion with fade-in
 */
function renderMetricValue(el, text) {
    el.innerHTML = `<span class="inline-block fade-in">${escapeHtml(text)}</span>`;
}

/**
 * Fetches anomaly queue
 */
async function loadAnomalies() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/dashboard/anomalies`);
        if (!response.ok) {
            throw new Error(`Anomalies endpoint returned HTTP ${response.status}`);
        }
        const anomalies = await response.json();
        renderAnomalies(anomalies);
        return anomalies;
    } catch (error) {
        console.error('Failed to load anomalies:', error);
        anomalyBadgeEl.textContent = 'Error Loading';
        anomalyBadgeEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200';
        anomaliesTableBodyEl.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-8 text-center text-rose-600 font-medium">
                    Failed to fetch anomaly queue from backend.
                </td>
            </tr>
        `;
        return [];
    }
}

/**
 * Renders anomalies list into table DOM
 */
function renderAnomalies(anomalies) {
    if (!anomalies || anomalies.length === 0) {
        anomalyBadgeEl.textContent = '0 Detected (Clean)';
        anomalyBadgeEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200';
        anomaliesTableBodyEl.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-12 text-center text-slate-500 fade-in">
                    <div class="flex flex-col items-center justify-center gap-2">
                        <div class="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl shadow-xs">
                            <i class="fa-solid fa-circle-check"></i>
                        </div>
                        <span class="font-bold text-slate-800 text-base">No policy violations detected</span>
                        <span class="text-xs text-slate-400 max-w-sm">All submissions, grading entries, and course enrollments adhere to institutional compliance rules.</span>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    anomalyBadgeEl.textContent = `${anomalies.length} Detected`;
    anomalyBadgeEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200';

    const rowsHtml = anomalies.map(anomaly => {
        const severity = (anomaly.severity || 'HIGH').toUpperCase();
        let badgeHtml = '';

        if (severity === 'CRITICAL') {
            badgeHtml = `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-extrabold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200/90 shadow-2xs">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-600 animate-pulse"></span>
                    Critical
                </span>
            `;
        } else if (severity === 'HIGH') {
            badgeHtml = `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-extrabold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200/90 shadow-2xs">
                    <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                    High
                </span>
            `;
        } else {
            badgeHtml = `
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-extrabold uppercase tracking-wider bg-sky-50 text-sky-700 border border-sky-200/90 shadow-2xs">
                    <span class="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
                    Medium
                </span>
            `;
        }

        return `
            <tr class="hover:bg-slate-50/90 transition-colors duration-150 fade-in">
                <td class="px-6 py-4 whitespace-nowrap">
                    ${badgeHtml}
                </td>
                <td class="px-6 py-4 whitespace-nowrap font-semibold text-slate-900 text-sm">
                    ${escapeHtml(anomaly.type)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <code class="px-2.5 py-1 rounded-md bg-slate-100 text-indigo-700 font-mono text-xs border border-slate-200/80 font-semibold tracking-tight">
                        ${escapeHtml(anomaly.entity_id || '--')}
                    </code>
                </td>
                <td class="px-6 py-4 text-slate-600 text-xs leading-relaxed max-w-md">
                    ${escapeHtml(anomaly.details)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                    <span class="inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 bg-rose-50 px-3 py-1 rounded-full border border-rose-200/80 shadow-2xs">
                        <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
                        Investigation Required
                    </span>
                </td>
            </tr>
        `;
    }).join('');

    anomaliesTableBodyEl.innerHTML = rowsHtml;
}

/**
 * Renders Chart.js data visualizations
 */
function renderCharts(metrics, anomalies) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js library is not loaded');
        return;
    }

    // Common Chart.js Defaults
    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.color = '#64748b';

    // 1. Anomaly Severity Breakdown (Doughnut Chart)
    const severityCounts = {
        CRITICAL: 0,
        HIGH: 0,
        MEDIUM: 0
    };

    if (anomalies && anomalies.length > 0) {
        anomalies.forEach(a => {
            const sev = (a.severity || 'HIGH').toUpperCase();
            if (severityCounts[sev] !== undefined) {
                severityCounts[sev]++;
            } else {
                severityCounts.HIGH++;
            }
        });
    }

    const severityCanvas = document.getElementById('anomalySeverityChart');
    if (severityCanvas) {
        if (severityChartInstance) {
            severityChartInstance.destroy();
        }

        const totalAnomalies = (anomalies && anomalies.length) || 0;

        severityChartInstance = new Chart(severityCanvas, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium'],
                datasets: [{
                    data: totalAnomalies === 0 ? [0, 0, 1] : [severityCounts.CRITICAL, severityCounts.HIGH, severityCounts.MEDIUM],
                    backgroundColor: totalAnomalies === 0 ? ['#f1f5f9', '#f1f5f9', '#10b981'] : ['#f43f5e', '#f59e0b', '#0ea5e9'],
                    borderColor: '#ffffff',
                    borderWidth: 3,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        padding: 10,
                        cornerRadius: 8,
                        boxPadding: 4,
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw} records`;
                            }
                        }
                    }
                }
            }
        });
    }

    // 2. Platform Scale & Activity Distribution (Bar Chart)
    const platformCanvas = document.getElementById('platformMetricsChart');
    if (platformCanvas && metrics) {
        if (platformChartInstance) {
            platformChartInstance.destroy();
        }

        platformChartInstance = new Chart(platformCanvas, {
            type: 'bar',
            data: {
                labels: ['Courses', 'Learners', 'Assignments', 'Submissions'],
                datasets: [{
                    label: 'Total Volume',
                    data: [
                        metrics.total_courses || 0,
                        metrics.total_learners || 0,
                        metrics.total_assignments || 0,
                        metrics.total_submissions || 0
                    ],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.85)',
                        'rgba(16, 185, 129, 0.85)',
                        'rgba(139, 92, 246, 0.85)',
                        'rgba(245, 158, 11, 0.85)'
                    ],
                    borderColor: [
                        '#3b82f6',
                        '#10b981',
                        '#8b5cf6',
                        '#f59e0b'
                    ],
                    borderWidth: 1.5,
                    borderRadius: 8,
                    borderSkipped: false,
                    barPercentage: 0.55
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        padding: 10,
                        cornerRadius: 8,
                        boxPadding: 4,
                        callbacks: {
                            label: function(context) {
                                return ` Total Count: ${Number(context.raw).toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#94a3b8',
                            font: { size: 11 },
                            callback: function(val) {
                                return Number(val).toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#475569',
                            font: { size: 11, weight: '600' }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Utility to escape raw HTML text
 */
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function showError(msg) {
    errorMessageEl.textContent = msg;
    errorBannerEl.classList.remove('hidden');
}

function hideError() {
    errorBannerEl.classList.add('hidden');
}

/**
 * Refreshes dashboard metrics, anomalies, and charts
 */
async function refreshDashboard() {
    refreshBtn.classList.add('opacity-75', 'cursor-not-allowed');
    if (refreshIcon) {
        refreshIcon.classList.add('animate-spin');
    }

    showLoadingSkeletons();

    const isHealthy = await checkBackendHealth();
    if (isHealthy) {
        const [metrics, anomalies] = await Promise.all([loadMetrics(), loadAnomalies()]);
        renderCharts(metrics, anomalies);
    }

    refreshBtn.classList.remove('opacity-75', 'cursor-not-allowed');
    if (refreshIcon) {
        refreshIcon.classList.remove('animate-spin');
    }
}

// Event Listeners
refreshBtn.addEventListener('click', refreshDashboard);
document.addEventListener('DOMContentLoaded', refreshDashboard);
