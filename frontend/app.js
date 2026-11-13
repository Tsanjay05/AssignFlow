/**
 * AssignFlow Dashboard Application Script
 * Dynamically connects to FastAPI backend on http://localhost:8000
 * Handles health checking, metric aggregation, and live anomaly queue rendering.
 */

const BACKEND_URL = 'http://localhost:8000';

// DOM Elements
const apiStatusEl = document.getElementById('api-status');
const errorBannerEl = document.getElementById('error-banner');
const errorMessageEl = document.getElementById('error-message');
const refreshBtn = document.getElementById('refresh-btn');
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
            apiStatusEl.textContent = 'Connected (Status: OK)';
            apiStatusEl.className = 'px-2.5 py-1 rounded-full text-xs font-semibold status-ok transition-colors';
            hideError();
            return true;
        } else {
            throw new Error('Backend returned non-OK status');
        }
    } catch (error) {
        apiStatusEl.textContent = 'Disconnected';
        apiStatusEl.className = 'px-2.5 py-1 rounded-full text-xs font-semibold status-error transition-colors';
        showError('Unable to connect to AssignFlow Backend (http://localhost:8000). Ensure the backend service is running.');
        console.error('Health check failed:', error);
        return false;
    }
}

/**
 * Fetches and displays system KPI metrics
 */
async function loadMetrics() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/dashboard/metrics`);
        if (!response.ok) {
            throw new Error(`Metrics endpoint returned HTTP ${response.status}`);
        }
        const data = await response.json();

        metricCoursesEl.textContent = Number(data.total_courses || 0).toLocaleString();
        metricLearnersEl.textContent = Number(data.total_learners || 0).toLocaleString();
        metricAssignmentsEl.textContent = Number(data.total_assignments || 0).toLocaleString();
        metricSubmissionsEl.textContent = Number(data.total_submissions || 0).toLocaleString();
        metricAvgScoreEl.textContent = `${Number(data.average_score || 0).toFixed(2)}`;

        const now = new Date();
        lastUpdatedTimeEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (error) {
        console.error('Failed to load metrics:', error);
        metricCoursesEl.textContent = '--';
        metricLearnersEl.textContent = '--';
        metricAssignmentsEl.textContent = '--';
        metricSubmissionsEl.textContent = '--';
        metricAvgScoreEl.textContent = '--';
    }
}

/**
 * Fetches and renders the live anomaly/exception queue
 */
async function loadAnomalies() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/dashboard/anomalies`);
        if (!response.ok) {
            throw new Error(`Anomalies endpoint returned HTTP ${response.status}`);
        }
        const anomalies = await response.json();

        renderAnomalies(anomalies);
    } catch (error) {
        console.error('Failed to load anomalies:', error);
        anomalyBadgeEl.textContent = 'Error Loading';
        anomalyBadgeEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-200';
        anomaliesTableBodyEl.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-8 text-center text-red-600 font-medium">
                    Failed to fetch anomaly queue from backend.
                </td>
            </tr>
        `;
    }
}

/**
 * Renders anomalies list into table DOM
 */
function renderAnomalies(anomalies) {
    if (!anomalies || anomalies.length === 0) {
        anomalyBadgeEl.textContent = '0 Detected (Clean)';
        anomalyBadgeEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200';
        anomaliesTableBodyEl.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-10 text-center text-slate-500">
                    <div class="flex flex-col items-center justify-center gap-1">
                        <svg class="w-8 h-8 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <span class="font-semibold text-slate-700">No anomalies detected</span>
                        <span class="text-xs text-slate-400">All student submissions, grades, and enrollments conform to system policy.</span>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    anomalyBadgeEl.textContent = `${anomalies.length} Detected`;
    anomalyBadgeEl.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200';

    const rowsHtml = anomalies.map(anomaly => {
        const severity = (anomaly.severity || 'HIGH').toUpperCase();
        let badgeClass = 'badge-high';
        if (severity === 'CRITICAL') badgeClass = 'badge-critical';
        else if (severity === 'MEDIUM') badgeClass = 'badge-medium';

        return `
            <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider ${badgeClass}">
                        ${escapeHtml(severity)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap font-medium text-slate-900">
                    ${escapeHtml(anomaly.type)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <code class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-xs border border-slate-200">
                        ${escapeHtml(anomaly.entity_id || '--')}
                    </code>
                </td>
                <td class="px-6 py-4 text-slate-600 text-xs leading-relaxed max-w-md">
                    ${escapeHtml(anomaly.details)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                    <span class="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200">
                        <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                        Action Required
                    </span>
                </td>
            </tr>
        `;
    }).join('');

    anomaliesTableBodyEl.innerHTML = rowsHtml;
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
 * Refreshes dashboard metrics and anomalies
 */
async function refreshDashboard() {
    refreshBtn.classList.add('opacity-75', 'cursor-not-allowed');
    const isHealthy = await checkBackendHealth();
    if (isHealthy) {
        await Promise.all([loadMetrics(), loadAnomalies()]);
    }
    refreshBtn.classList.remove('opacity-75', 'cursor-not-allowed');
}

// Event Listeners
refreshBtn.addEventListener('click', refreshDashboard);
document.addEventListener('DOMContentLoaded', refreshDashboard);
