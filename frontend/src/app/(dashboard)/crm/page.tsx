import { fetchLeads, Lead } from '@/lib/api'

export default async function CRMPage() {
  const data = await fetchLeads()
  const leads = data?.leads || []

  const STAGES = ["New", "Contacted", "Appointment Scheduled", "Closed Won", "Lost"]
  
  // Group leads strictly by their current funnel stage
  const columns = STAGES.map(stage => ({
    name: stage,
    items: leads.filter((l: Lead) => (l.funnel_stage === stage) || (stage === "New" && !STAGES.includes(l.funnel_stage)))
  }))

  return (
    <div className="space-y-8 h-[calc(100vh-8rem)] flex flex-col">
      <div>
        <h1 className="text-2xl font-medium text-white tracking-tight">Pipeline Board</h1>
        <p className="text-sm text-zinc-400 mt-1">Visualize your active real estate pipeline.</p>
      </div>

      <div className="flex-1 flex gap-6 overflow-x-auto pb-4">
        {columns.map(col => (
          <div key={col.name} className="flex-shrink-0 w-[320px] flex flex-col">
            <div className="flex items-center justify-between mb-4 px-1">
              <h3 className="text-sm font-medium text-zinc-300">{col.name}</h3>
              <span className="text-xs font-medium text-zinc-500 bg-zinc-900/80 px-2.5 py-1 rounded-full border border-zinc-800">
                {col.items.length}
              </span>
            </div>
            
            <div className="flex-1 bg-zinc-900/30 rounded-3xl p-3 border border-zinc-800/40 flex flex-col gap-3 min-h-[500px]">
              {col.items.map((lead: Lead) => (
                <div key={lead.id} className="bg-zinc-900/80 backdrop-blur-xl p-4 rounded-2xl border border-zinc-800/80 shadow-lg shadow-black/20 hover:border-zinc-700/80 transition-all cursor-grab group">
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="text-sm font-medium text-zinc-200 group-hover:text-emerald-400 transition-colors">
                      {lead.name || 'Anonymous User'}
                    </h4>
                    {lead.lead_temperature === 'hot' && (
                      <span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] animate-pulse"></span>
                    )}
                  </div>
                  <div className="flex flex-col gap-1 mb-4">
                    <p className="text-xs text-zinc-400 line-clamp-1">
                      {lead.intent ? `${lead.intent} · ${lead.budget || 'Open Budget'}` : 'Exploring options'}
                    </p>
                    {lead.budget_alignment_status && lead.budget_alignment_status !== 'unknown' && (
                      <span className="inline-flex self-start px-2 py-0.5 rounded-full text-[9px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700 capitalize">
                        {lead.budget_alignment_status} Match
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center justify-between border-t border-zinc-800/50 pt-3 mt-1">
                    <span className="text-[10px] uppercase font-semibold text-zinc-500 tracking-wider flex items-center gap-1.5">
                      <div className="w-12 bg-zinc-800 rounded-full h-1 overflow-hidden">
                        <div className="bg-emerald-400 h-1 rounded-full" style={{ width: `${lead.conversion_probability || 0}%` }}></div>
                      </div>
                      {lead.conversion_probability || 0}%
                    </span>
                    <span className="text-[10px] text-zinc-500 font-medium">
                      {lead.expected_closure_days ? `${lead.expected_closure_days}d close` : 'Unknown'}
                    </span>
                  </div>
                </div>
              ))}
              {col.items.length === 0 && (
                <div className="h-full flex items-center justify-center border-2 border-dashed border-zinc-800/50 rounded-2xl">
                  <span className="text-xs text-zinc-600 font-medium">No leads in stage</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
