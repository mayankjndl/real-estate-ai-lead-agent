'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Lead } from '@/lib/api'
import { updateLeadStageAction } from './actions'

const STAGES = ["New", "Contacted", "Appointment Scheduled", "Closed Won", "Lost"]

export default function KanbanBoard({ initialLeads }: { initialLeads: Lead[] }) {
  const [leads, setLeads] = useState<Lead[]>(initialLeads)
  const router = useRouter()

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
    const leadId = parseInt(e.dataTransfer.getData('text/plain'))
    if (!leadId) return

    // Optimistically update UI
    setLeads(prev => prev.map(lead => 
      lead.id === leadId ? { ...lead, funnel_stage: targetStage } : lead
    ))

    try {
      await updateLeadStageAction(leadId, targetStage)
      router.refresh()
    } catch (error) {
      console.error('Failed to update lead stage:', error)
      // Revert if failed
      setLeads(initialLeads)
    }
  }

  return (
    <div className="flex-1 flex gap-6 overflow-x-auto pb-4 snap-x snap-mandatory">
      {columns.map(col => (
        <div key={col.name} className="flex-shrink-0 w-[320px] flex flex-col snap-center">
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
                className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl p-4 rounded-2xl border border-slate-200 dark:border-zinc-800/80 shadow-sm dark:shadow-lg dark:shadow-black/20 hover:border-slate-300 dark:hover:border-zinc-700/80 transition-all cursor-grab active:cursor-grabbing group"
              >
                <div className="flex justify-between items-start mb-3">
                  <h4 className="text-sm font-medium text-slate-900 dark:text-zinc-200 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                    {lead.name || 'Anonymous User'}
                  </h4>
                  {lead.lead_temperature === 'hot' && (
                    <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] animate-pulse"></span>
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
  )
}
