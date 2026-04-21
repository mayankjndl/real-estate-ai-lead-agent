/* ==============================================
   ABC Properties — AI CRM Dashboard Script
   ============================================== */

const API_KEY  = "secret-client-key-123";
const API_BASE = "https://real-estate-ai-lead-agent-1.onrender.com/api/v1";
const HEADERS  = { "X-API-Key": API_KEY, "Content-Type": "application/json" };

/* ---- Theme Toggle ---- */
function toggleTheme() {
    const html  = document.documentElement;
    const icon  = document.getElementById("theme-icon");
    const isDark = html.getAttribute("data-theme") === "dark";
    html.setAttribute("data-theme", isDark ? "light" : "dark");
    icon.setAttribute("data-lucide", isDark ? "moon" : "sun");
    lucide.createIcons();
    localStorage.setItem("crm-theme", isDark ? "light" : "dark");
}

// Restore saved theme on load
(function() {
    const saved = localStorage.getItem("crm-theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    window.addEventListener("DOMContentLoaded", () => {
        const icon = document.getElementById("theme-icon");
        if (icon) {
            icon.setAttribute("data-lucide", saved === "dark" ? "sun" : "moon");
            lucide.createIcons();
        }
    });
})();

/* ---- Helpers ---- */
function fmtDate(raw) {
    if (!raw) return "—";
    const str = raw.endsWith("Z") || raw.includes("+") ? raw : raw + "Z";
    return new Date(str).toLocaleString("en-IN", {
        month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    });
}

function setEl(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

/* ---- Fetch Analytics ---- */
async function fetchStats() {
    try {
        const res  = await fetch(`${API_BASE}/analytics`, { headers: HEADERS });
        const json = await res.json();
        if (json.status !== "success") return;

        const d = json.data;
        setEl("total-sessions",  d.total_sessions   ?? "--");
        setEl("total-leads",     d.total_leads_captured ?? "--");
        setEl("conversion-rate", `${d.conversion_rate ?? "--"}%`);

        // Intent counts
        const breakdown = d.intent_breakdown || {};
        setEl("count-buy",        breakdown.buy        ?? 0);
        setEl("count-rent",       breakdown.rent       ?? 0);
        setEl("count-investment",  breakdown.investment ?? 0);
        setEl("count-browsing",   breakdown.browsing   ?? 0);
    } catch (e) {
        console.error("fetchStats:", e);
    }
}

/* ---- Fetch Leads & Visits Booked ---- */
async function fetchLeads() {
    const intent = document.getElementById("intent-filter")?.value ?? "";
    const score  = document.getElementById("score-filter")?.value  ?? "";

    let url = `${API_BASE}/leads?`;
    if (intent) url += `intent=${encodeURIComponent(intent)}&`;
    if (score)  url += `score=${encodeURIComponent(score)}`;

    try {
        const res  = await fetch(url, { headers: HEADERS });
        const json = await res.json();
        if (json.status !== "success") return;

        renderTable(json.leads || []);

        // Count visits booked from the full unfiltered leads for the stat card
        const visitsCount = (json.leads || []).filter(l => l.visit_date).length;
        setEl("visits-booked", visitsCount);
    } catch (e) {
        console.error("fetchLeads:", e);
    }
}

/* ---- Render Table ---- */
function renderTable(leads) {
    const tbody = document.getElementById("leads-body");
    if (!tbody) return;

    if (!leads.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No leads found matching the selected filters.</td></tr>';
        return;
    }

    const sorted = [...leads].reverse();
    tbody.innerHTML = sorted.map(lead => {
        const intent = (lead.intent || "unknown").toLowerCase();
        const score  = (lead.score  || "low").toLowerCase();

        const visitCell = lead.visit_date
            ? `<span class="visit-chip">📅 ${lead.visit_date}</span>`
            : `<span style="color:var(--text-muted)">—</span>`;

        return `
        <tr>
            <td><strong>${lead.name || "—"}</strong></td>
            <td style="color:var(--text-secondary)">${lead.phone || "—"}</td>
            <td>${lead.location || "—"}</td>
            <td style="font-weight:600">${lead.budget || "—"}</td>
            <td><span class="badge badge-intent ${intent}">${lead.intent || "unknown"}</span></td>
            <td><span class="badge score-${score}">${lead.score || "Low"}</span></td>
            <td>${visitCell}</td>
            <td style="color:var(--text-muted);font-size:0.78rem">${fmtDate(lead.updated_at)}</td>
        </tr>`;
    }).join("");
}

/* ---- Export ---- */
function exportLeads() {
    window.open(`${API_BASE}/leads/export?X-API-Key=${API_KEY}`, "_blank");
}

/* ---- System Health ---- */
async function openHealth() {
    try {
        const res  = await fetch("https://real-estate-ai-lead-agent-1.onrender.com/health");
        const json = await res.json();
        const dot  = document.getElementById("health-dot");
        if (dot) {
            dot.style.background = json.status === "healthy" ? "var(--neon-green)" : "var(--neon-red)";
        }
        alert(
            `System Health\n\n` +
            `Status:    ${json.status}\n` +
            `DB:        ${json.database}\n` +
            `Scheduler: ${json.scheduler}\n` +
            `Uptime:    ${Math.floor(json.uptime_seconds / 3600)}h ${Math.floor((json.uptime_seconds % 3600)/60)}m\n` +
            `Version:   ${json.version}\n` +
            `Workers:   ${json.worker_mode}`
        );
    } catch (e) {
        alert("Could not reach health endpoint. Server may be offline.");
    }
}

/* ---- Last Updated ---- */
function updateTimestamp() {
    const el = document.getElementById("last-updated");
    if (el) el.textContent = "Updated " + new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

/* ---- Initial Load & Auto-Refresh ---- */
async function refresh() {
    await Promise.all([fetchStats(), fetchLeads()]);
    updateTimestamp();
}

refresh();
setInterval(refresh, 30_000);
