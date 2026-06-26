'use client'

import { useState } from 'react'
import { Download, FileText, Table } from 'lucide-react'
import { Lead } from '@/lib/api'
import jsPDF from 'jspdf'
import 'jspdf-autotable'

export default function ExportReport({ leads }: { leads: Lead[] }) {
  const [isOpen, setIsOpen] = useState(false)

  const handleExport = (format: 'csv' | 'pdf', scope: 'weekly' | 'monthly') => {
    setIsOpen(false)
    if (!leads || leads.length === 0) {
      alert("No data available to export based on current filters.");
      return;
    }

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - (scope === 'weekly' ? 7 : 30));
    
    const filteredLeads = leads.filter(l => new Date(l.updated_at) >= cutoffDate);
    
    if (filteredLeads.length === 0) {
      alert(`No data available for the past ${scope === 'weekly' ? '7' : '30'} days.`);
      return;
    }

    const headers = ["ID", "Name", "Phone", "Funnel Stage", "Temperature", "Budget", "Location", "Source", "Updated At"]
    
    const rows = filteredLeads.map(l => [
      l.id.toString(),
      l.name || 'Unknown',
      l.phone || 'N/A',
      l.funnel_stage || 'New',
      l.lead_temperature || 'N/A',
      l.budget || '0',
      l.location || 'Unknown',
      l.source || 'Direct',
      new Date(l.updated_at).toLocaleDateString()
    ])

    const fileName = `revenue_os_${scope}_report_${new Date().toISOString().split('T')[0]}`

    if (format === 'csv') {
      const csvContent = [
        headers.join(","),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
      ].join("\n")

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.setAttribute("href", url)
      link.setAttribute("download", `${fileName}.csv`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } else {
      const doc = new jsPDF('landscape')
      doc.text(`Revenue OS - ${scope.charAt(0).toUpperCase() + scope.slice(1)} Report`, 14, 15)
      doc.setFontSize(10)
      doc.text(`Generated on: ${new Date().toLocaleDateString()}`, 14, 22)
      
      // @ts-ignore
      doc.autoTable({
        startY: 25,
        head: [headers],
        body: rows,
        theme: 'grid',
        styles: { fontSize: 8 },
        headStyles: { fillColor: [79, 70, 229] } // indigo-600
      })
      
      doc.save(`${fileName}.pdf`)
    }
  }

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-xl transition-colors shadow-sm shadow-indigo-600/20"
      >
        <Download className="w-4 h-4" />
        <span>Export Report</span>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl shadow-xl overflow-hidden z-50">
            <div className="p-2 space-y-1">
              <div className="px-3 py-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Weekly (7 Days)</div>
              <button onClick={() => handleExport('csv', 'weekly')} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded-lg transition-colors">
                <Table className="w-4 h-4 text-emerald-500" /> CSV Format
              </button>
              <button onClick={() => handleExport('pdf', 'weekly')} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded-lg transition-colors">
                <FileText className="w-4 h-4 text-rose-500" /> PDF Format
              </button>
              <div className="border-t border-slate-200 dark:border-zinc-800 my-1"></div>
              <div className="px-3 py-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Monthly (30 Days)</div>
              <button onClick={() => handleExport('csv', 'monthly')} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded-lg transition-colors">
                <Table className="w-4 h-4 text-emerald-500" /> CSV Format
              </button>
              <button onClick={() => handleExport('pdf', 'monthly')} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded-lg transition-colors">
                <FileText className="w-4 h-4 text-rose-500" /> PDF Format
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
