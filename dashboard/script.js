/* ═══════════════════════════════
   ABC Properties — CRM Script
═══════════════════════════════ */

const API_KEY  = "secret-client-key-123";
const API_BASE = "https://real-estate-ai-lead-agent-1.onrender.com/api/v1";
const H        = { "X-API-Key": API_KEY, "Content-Type": "application/json" };

/* ── Theme ── */
(function initTheme() {
    const saved = localStorage.getItem("crm-theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    document.addEventListener("DOMContentLoaded", () => syncThemeIcon(saved));
})();

function syncThemeIcon(theme) {
    const el = document.getElementById("theme-icon");
    if (el) el.textContent = theme === "dark" ? "☀" : "🌙";
}

function toggleTheme() {
    const cur  = document.documentElement.getAttribute("data-theme");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("crm-theme", next);
    syncThemeIcon(next);
}

/* ── Helpers ── */
function fmtDate(raw) {
    if (!raw) return "—";
    const s = (raw.endsWith("Z") || raw.includes("+")) ? raw : raw + "Z";
    return new Date(s).toLocaleString("en-IN", {
        month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    });
}
function $id(id) { return document.getElementById(id); }
function set(id, v) { const el = $id(id); if (el) el.textContent = v; }

/* ── Badge helpers ── */
function intentBadge(intent) {
    const map = { buy:"b-buy", rent:"b-rent", investment:"b-inv", browsing:"b-br" };
    const cls = map[(intent||"").toLowerCase()] || "b-unkn";
    return `<span class="badge ${cls}">${intent || "unknown"}</span>`;
}
function scoreBadge(score) {
    const s = score || "Low";
    return `<span class="badge score-${s}">${s}</span>`;
}

/* ── Outcome cell ── */
function outcomeCell(lead) {
    if (lead.visit_date) {
        return `<span class="outcome-chip">📅 Visit: ${lead.visit_date}</span>`;
    }
    if ((lead.score || "").toLowerCase() === "high") {
        return `<span class="outcome-chip" style="background:rgba(104,211,145,.12);color:var(--green);border-color:rgba(104,211,145,.25)">✅ High intent — follow-up pending</span>`;
    }
    if (lead.phone) {
        return `<span class="outcome-chip" style="background:rgba(99,179,237,.12);color:var(--blue);border-color:rgba(99,179,237,.25)">📞 Contact captured</span>`;
    }
    return `<span class="outcome-none">—</span>`;
}

/* ── Analytics ── */
async function fetchStats() {
    try {
        const r = await fetch(`${API_BASE}/analytics`, { headers: H });
        const j = await r.json();
        if (j.status !== "success") return;
        const d = j.data;
        set("total-sessions",  d.total_sessions        ?? "—");
        set("total-leads",     d.total_leads_captured  ?? "—");
        set("conversion-rate", (d.conversion_rate ?? "—") + "%");

        const bd = d.intent_breakdown || {};
        set("count-buy",        bd.buy        ?? 0);
        set("count-rent",       bd.rent       ?? 0);
        set("count-investment", bd.investment  ?? 0);
        set("count-browsing",   bd.browsing   ?? 0);
    } catch(e) { console.error("fetchStats:", e); }
}

/* ── Leads ── */
async function fetchLeads() {
    const intent = ($id("intent-filter") || {}).value || "";
    const score  = ($id("score-filter")  || {}).value || "";

    let url = `${API_BASE}/leads?`;
    if (intent) url += `intent=${encodeURIComponent(intent)}&`;
    if (score)  url += `score=${encodeURIComponent(score)}`;

    try {
        const r = await fetch(url, { headers: H });
        const j = await r.json();
        if (j.status !== "success") return;

        const leads = j.leads || [];
        renderTable(leads);

        const visits = leads.filter(l => l.visit_date).length;
        set("visits-booked", visits);
    } catch(e) { console.error("fetchLeads:", e); }
}

function renderTable(leads) {
    const tbody = $id("leads-body");
    if (!tbody) return;

    if (!leads.length) {
        tbody.innerHTML = `<tr><td colspan="8" class="tbl-empty">No leads match the selected filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = [...leads].reverse().map(l => `
        <tr>
            <td><strong>${l.name || "—"}</strong></td>
            <td style="color:var(--c-txt2)">${l.phone || "—"}</td>
            <td>${l.location || "—"}</td>
            <td style="font-weight:600">${l.budget || "—"}</td>
            <td>${intentBadge(l.intent)}</td>
            <td>${scoreBadge(l.score)}</td>
            <td>${outcomeCell(l)}</td>
            <td style="color:var(--c-txt3);font-size:11.5px;white-space:nowrap">${fmtDate(l.updated_at)}</td>
        </tr>`).join("");
}

/* ── Export ── */
function exportLeads() {
    window.open(`${API_BASE}/leads/export?X-API-Key=${API_KEY}`, "_blank");
}

/* ── System Health ── */
async function openHealth() {
    try {
        const r = await fetch("https://real-estate-ai-lead-agent-1.onrender.com/health");
        const j = await r.json();
        const dot = $id("health-dot");
        if (dot) dot.style.background = j.status === "healthy" ? "var(--green)" : "var(--red)";
        alert(`System Health\n\nStatus:    ${j.status}\nDatabase:  ${j.database}\nScheduler: ${j.scheduler}\nUptime:    ${Math.floor(j.uptime_seconds/3600)}h ${Math.floor((j.uptime_seconds%3600)/60)}m\nVersion:   ${j.version}`);
    } catch(e) {
        alert("Could not reach health endpoint — server may be offline.");
    }
}

/* ── Refresh loop ── */
async function refresh() {
    await Promise.all([fetchStats(), fetchLeads()]);
    const el = $id("last-updated");
    if (el) el.textContent = "Updated " + new Date().toLocaleTimeString("en-IN", { hour:"2-digit", minute:"2-digit" });
}

refresh();
setInterval(refresh, 30_000);
