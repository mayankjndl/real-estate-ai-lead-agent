import { fetchLeads, Lead } from '@/lib/api'
import { Flame, ThermometerSnowflake, AlertCircle, Clock, Zap } from 'lucide-react'

function getTempBadge(temp: string) {
  const t = temp?.toLowerCase() || 'cold'
  if (t === 'hot') return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-red-400/10 text-red-400 border border-red-400/20"><Flame className="w-3 h-3" /> Hot</span>
  if (t === 'warm') return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-orange-400/10 text-orange-400 border border-orange-400/20"><Zap className="w-3 h-3" /> Warm</span>
  return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-400/10 text-blue-400 border border-blue-400/20"><ThermometerSnowflake className="w-3 h-3" /> Cold</span>
}

function getUrgencyBadge(urgency: string) {
  const u = urgency?.toLowerCase() || 'low'
  if (u === 'high') return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-red-400"><AlertCircle className="w-3 h-3" /> High</span>
  if (u === 'medium') return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-yellow-400"><Clock className="w-3 h-3" /> Medium</span>
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-zinc-500">Low</span>
}

export default async function LeadsPage() {
  const data = await fetchLeads()
  const leads = data?.leads || []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-medium text-white tracking-tight">Lead Inbox</h1>
        <p className="text-sm text-zinc-400 mt-1">Manage and track your autonomous AI leads.</p>
      </div>
      
      <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-zinc-800/80 bg-zinc-900/50">
                <th className="px-6 py-4 text-xs font-medium text-zinc-400 uppercase tracking-wider">Lead</th>
                <th className="px-6 py-4 text-xs font-medium text-zinc-400 uppercase tracking-wider">Intent & Budget</th>
                <th className="px-6 py-4 text-xs font-medium text-zinc-400 uppercase tracking-wider">Intelligence</th>
                <th className="px-6 py-4 text-xs font-medium text-zinc-400 uppercase tracking-wider">Probability</th>
                <th className="px-6 py-4 text-xs font-medium text-zinc-400 uppercase tracking-wider">Stage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {leads.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-sm text-zinc-500">
                    No leads found. Waiting for AI interactions...
                  </td>
                </tr>
              ) : leads.map((lead: Lead) => (
                <tr key={lead.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-zinc-200">{lead.name || 'Anonymous User'}</span>
                      <span className="text-xs text-zinc-500">{lead.phone || lead.session_id}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-sm text-zinc-300 capitalize">{lead.intent || 'Exploring'}</span>
                      <span className="text-xs text-zinc-500">{lead.budget || 'Undisclosed'}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        {getTempBadge(lead.lead_temperature)}
                        {getUrgencyBadge(lead.urgency_level)}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <span title="Engagement Score">Eng: {lead.engagement_score || 0}/100</span>
                        <span>•</span>
                        <span title="Expected Closure">Close: {lead.expected_closure_days || 60}d</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-3">
                      <div className="w-full max-w-[100px] bg-zinc-800 rounded-full h-1.5">
                        <div 
                          className="bg-emerald-400 h-1.5 rounded-full" 
                          style={{ width: `${lead.conversion_probability || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-medium text-zinc-400">{lead.conversion_probability || 0}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                      {lead.funnel_stage}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
