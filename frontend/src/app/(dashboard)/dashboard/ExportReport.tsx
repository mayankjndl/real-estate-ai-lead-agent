'use client'

import { Download } from 'lucide-react'
import { Lead } from '@/lib/api'

export default function ExportReport({ leads }: { leads: Lead[] }) {
  const handleExport = () => {
    if (!leads || leads.length === 0) {
      alert("No data available to export based on current filters.");
      return;
    }

    const headers = ["ID", "Name", "Phone", "Funnel Stage", "Temperature", "Budget", "Location", "Source", "Updated At"]
    
    const csvContent = [
      headers.join(","),
      ...leads.map(l => [
        l.id,
        `"${l.name || 'Unknown'}"`,
        l.phone || 'N/A',
        l.funnel_stage || 'New',
        l.lead_temperature || 'N/A',
        `"${l.budget || '0'}"`,
        `"${l.location || 'Unknown'}"`,
        l.source || 'Direct',
        new Date(l.updated_at).toLocaleDateString()
      ].join(","))
    ].join("\n")

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", `revenue_os_report_${new Date().toISOString().split('T')[0]}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <button 
      onClick={handleExport}
      className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-xl transition-colors shadow-sm shadow-indigo-600/20"
    >
      <Download className="w-4 h-4" />
      <span>Export Weekly Report</span>
    </button>
  )
}
