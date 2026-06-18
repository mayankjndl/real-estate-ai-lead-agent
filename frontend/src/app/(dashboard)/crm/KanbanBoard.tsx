'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Lead } from '@/lib/api'
import { updateLeadStageAction } from './actions'

const STAGES = ["New", "Contacted", "Appointment Scheduled", "Closed Won", "Lost"]

export default function KanbanBoard({ initialLeads }: { initialLeads: Lead[] }) {
  const [leads, setLeads] = useState<Lead[]>(initialLeads)
  const [toast, setToast] = useState<{message: string, type: 'success'|'error'} | null>(null)
  const router = useRouter()

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  // Group leads strictly by their current funnel stage
  const columns = STAGES.map(stage => ({
    name: stage,
    items: leads.filter((l: Lead) => (l.funnel_stage === stage) || (stage === "New" && !STAGES.includes(l.funnel_stage)))
  }))

  const handleDragStart = (e: React.DragEvent, leadId: number) => {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', leadId.toString())
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDrop = async (e: React.DragEvent, targetStage: string) => {
    e.preventDefault()
    const leadIdStr = e.dataTransfer.getData('text/plain')
    if (!leadIdStr) return
    const leadId = parseInt(leadIdStr)

    const leadToMove = leads.find(l => l.id === leadId)
    if (!leadToMove || leadToMove.funnel_stage === targetStage) return

    // Optimistically update UI
    setLeads(prev => prev.map(lead => 
      lead.id === leadId ? { ...lead, funnel_stage: targetStage } : lead
    ))

    try {
      await updateLeadStageAction(leadId, targetStage)
      setToast({ message: `Successfully moved to ${targetStage}`, type: 'success' })
      router.refresh()
    } catch (error) {
      console.error('Failed to update lead stage:', error)
      setToast({ message: 'Failed to update stage. Please try again.', type: 'error' })
      // Revert if failed
      setLeads(initialLeads)
    }
  }

  return (
    <>
      {/* Toast Notification Layer */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5 fade-in duration-300">
          <div className={`px-4 py-3 rounded-xl shadow-lg backdrop-blur-md border flex items-center gap-3 ${
            toast.type === 'success' 
              ? 'bg-emerald-50/90 dark:bg-emerald-900/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200' 
              : 'bg-rose-50/90 dark:bg-rose-900/40 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200'
          }`}>
            <div className={`w-2 h-2 rounded-full ${toast.type === 'success' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            <span className="text-sm font-medium">{toast.message}</span>
          </div>
        </div>
      )}

      <div className="flex-1 flex gap-6 overflow-x-auto pb-4 snap-x snap-mandatory scroll-smooth touch-pan-x">
        {columns.map(col => (
          <div key={col.name} className="flex-shrink-0 w-[320px] sm:w-[350px] flex flex-col snap-center">
            <div className="flex items-center justify-between mb-4 px-1">
              <h3 className="text-sm font-medium text-slate-700 dark:text-zinc-300">{col.name}</h3>
              <span className="text-xs font-medium text-slate-500 dark:text-zinc-500 bg-slate-100 dark:bg-zinc-900/80 px-2.5 py-1 rounded-full border border-slate-200 dark:border-zinc-800">
                {col.items.length}
              </span>
            </div>
            
            <div 
              className="flex-1 bg-slate-50/50 dark:bg-zinc-900/30 rounded-3xl p-3 border border-slate-200 dark:border-zinc-800/40 flex flex-col gap-3 min-h-[500px]"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, col.name)}
            >
              {col.items.map((lead: Lead) => (
                <div 
                  key={lead.id} 
                  draggable={true}
                  onDragStart={(e) => handleDragStart(e, lead.id)}
                  className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl p-4 rounded-2xl border border-slate-200 dark:border-zinc-800/80 shadow-sm dark:shadow-lg dark:shadow-black/20 hover:border-slate-300 dark:hover:border-zinc-700/80 transition-all cursor-grab active:cursor-grabbing group relative"
                >
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="text-sm font-medium text-slate-900 dark:text-zinc-200 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                      {lead.name || 'Anonymous User'}
                    </h4>
                    {lead.lead_temperature?.toLowerCase() === 'hot' && (
                      <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] animate-pulse"></span>
                    )}
                  </div>
                  <div className="flex flex-col gap-1 mb-4">
                    <p className="text-xs text-slate-500 dark:text-zinc-400 line-clamp-1">
                      {lead.intent ? `${lead.intent} · ${lead.budget || 'Open Budget'}` : 'Exploring options'}
                    </p>
                    {lead.budget_alignment_status && lead.budget_alignment_status !== 'unknown' && (
                      <span className="inline-flex self-start px-2 py-0.5 rounded-full text-[9px] font-medium bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400 border border-slate-200 dark:border-zinc-700 capitalize">
                        {lead.budget_alignment_status} Match
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center justify-between border-t border-slate-100 dark:border-zinc-800/50 pt-3 mt-1">
                    <span className="text-[10px] uppercase font-semibold text-slate-500 dark:text-zinc-500 tracking-wider flex items-center gap-1.5">
                      <div className="w-12 bg-slate-200 dark:bg-zinc-800 rounded-full h-1 overflow-hidden">
                        <div className="bg-emerald-500 dark:bg-emerald-400 h-1 rounded-full" style={{ width: `${lead.conversion_probability || 0}%` }}></div>
                      </div>
                      {lead.conversion_probability || 0}%
                    </span>
                    <span className="text-[10px] text-slate-500 dark:text-zinc-500 font-medium">
                      {lead.expected_closure_days ? `${lead.expected_closure_days}d close` : 'Unknown'}
                    </span>
                  </div>
                </div>
              ))}
              {col.items.length === 0 && (
                <div className="h-full flex items-center justify-center border-2 border-dashed border-slate-200 dark:border-zinc-800/50 rounded-2xl">
                  <span className="text-xs text-slate-400 dark:text-zinc-600 font-medium">No leads in stage</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
