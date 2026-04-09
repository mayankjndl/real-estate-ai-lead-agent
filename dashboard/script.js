const API_KEY = "secret-client-key-123";
const API_BASE = "http://127.0.0.1:8000/api/v1";

const headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
};

async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE}/analytics`, { headers });
        const result = await response.json();
        
        if (result.status === "success") {
            const data = result.data;
            document.getElementById('total-sessions').textContent = data.total_sessions;
            document.getElementById('total-leads').textContent = data.total_leads_captured;
            document.getElementById('conversion-rate').textContent = `${data.conversion_rate}%`;
        }
    } catch (error) {
        console.error("Error fetching stats:", error);
    }
}

async function fetchLeads() {
    const intent = document.getElementById('intent-filter').value;
    const score = document.getElementById('score-filter').value;
    
    let url = `${API_BASE}/leads?`;
    if (intent) url += `intent=${intent}&`;
    if (score) url += `score=${score}`;

    try {
        const response = await fetch(url, { headers });
        const result = await response.json();
        
        if (result.status === "success") {
            renderTable(result.leads);
        }
    } catch (error) {
        console.error("Error fetching leads:", error);
    }
}

function renderTable(leads) {
    const tbody = document.getElementById('leads-body');
    tbody.innerHTML = '';

    leads.reverse().forEach(lead => {
        const row = document.createElement('tr');
        
        let dateStr = lead.updated_at;
        if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
            dateStr += 'Z'; // Append UTC timezone marker so JS correctly offsets it to IST
        }
        
        const date = new Date(dateStr).toLocaleString('en-US', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        row.innerHTML = `
            <td><strong>${lead.name || 'Unknown'}</strong></td>
            <td>${lead.phone || 'N/A'}</td>
            <td>${lead.location || 'N/A'}</td>
            <td>${lead.budget || 'N/A'}</td>
            <td><span class="badge intent">${lead.intent || 'Unknown'}</span></td>
            <td><span class="badge score-${(lead.score || 'low').toLowerCase()}">${lead.score || 'Low'}</span></td>
            <td style="color: var(--text-muted)">${date}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function exportLeads() {
    window.open(`${API_BASE}/leads/export?X-API-Key=${API_KEY}`, '_blank');
}

// Initial load
fetchStats();
fetchLeads();

// Refresh every 30 seconds
setInterval(() => {
    fetchStats();
    fetchLeads();
}, 30000);
