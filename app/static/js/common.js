/* ── Common JS Utilities ── */

// Toast notifications
const toastContainer = document.createElement('div');
toastContainer.className = 'toast-container';
document.body.appendChild(toastContainer);

function showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Fetch helpers
async function api(url, options = {}) {
    const defaults = {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
    };
    const opts = { ...defaults, ...options };
    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
        opts.body = JSON.stringify(opts.body);
    }
    if (opts.body instanceof FormData) {
        delete opts.headers['Content-Type'];
    }
    const resp = await fetch(url, opts);
    if (resp.status === 401) {
        window.location.href = '/login';
        return null;
    }
    if (resp.status === 429) {
        showToast('Quota exhausted. Please wait for refresh.', 'warning');
        return null;
    }
    return resp;
}

async function apiJson(url, options = {}) {
    const resp = await api(url, options);
    if (!resp) return null;
    return resp.json();
}

// Loading overlay
function showLoading(message = 'Processing...') {
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div class="spinner" style="margin: 0 auto 16px;"></div>
                <div id="loading-message" style="color: var(--text-secondary); font-size: 0.9rem;">${message}</div>
            </div>
        `;
        document.body.appendChild(overlay);
    } else {
        document.getElementById('loading-message').textContent = message;
        overlay.classList.remove('hidden');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
}

// Check for quota warnings on page load
async function checkQuotaWarnings() {
    const data = await apiJson('/auth/me');
    if (data && data.warnings) {
        data.warnings.forEach(w => showToast(w, 'warning', 6000));
    }
    return data;
}

// Format date
function formatDate(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

function formatDateTime(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleString('zh-CN');
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// Copy to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied!', 'success', 2000);
    } catch {
        showToast('Copy failed', 'error');
    }
}

// Debounce
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// Confirm dialog
function confirmAction(message) {
    return confirm(message);
}

// Init on page load
document.addEventListener('DOMContentLoaded', () => {
    // Set active nav link
    const path = window.location.pathname;
    document.querySelectorAll('.navbar-nav a').forEach(a => {
        if (a.getAttribute('href') === path) {
            a.classList.add('active');
        }
    });
});
