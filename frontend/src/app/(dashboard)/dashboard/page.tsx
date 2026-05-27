import { fetchAnalytics, fetchLeads } from '@/lib/api'
import { FunnelChart, SourceChart } from './Charts'
import { Users, Target, Banknote } from 'lucide-react'

export default async function DashboardPage() {
  const analyticsData = await fetchAnalytics()
  const leadsData = await fetchLeads()
  
  const stats = analyticsData?.data || { total_leads_captured: 0, conversion_rate: 0 }
  const leads = leadsData?.leads || []
  
  // Aggregate Funnel (Waterfall Drop-off)
  const STAGES = ["New", "Contacted", "Appointment Scheduled", "Closed Won"]
  const funnelData = STAGES.map(stage => ({
    name: stage,
    value: leads.filter(l => l.funnel_stage === stage).length
  }))
  
  // Aggregate Lead Sources
  const sourceMap: Record<string, number> = {}
  leads.forEach(l => {
    const s = l.source || 'Unknown'
    sourceMap[s] = (sourceMap[s] || 0) + 1
  })
  
  // Convert object to array and sort descending by value
  const sourceData = Object.entries(sourceMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  // Visual placeholder for Projected Revenue
  const projectedRevenue = "$1.2M"

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-medium text-white tracking-tight">ROI Dashboard</h1>
        <p className="text-sm text-zinc-400 mt-1">High-level metrics and pipeline performance.</p>
      </div>

      {/* KPI Cards (Grid layout, fully responsive) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-zinc-900/40 border border-zinc-800/80 p-6 rounded-3xl shadow-xl backdrop-blur-xl">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-10 w-10 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
              <Users className="text-blue-400 w-5 h-5" />
            </div>
            <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Total Leads</h3>
          </div>
          <p className="text-4xl font-semibold text-white tracking-tight">{stats.total_leads_captured}</p>
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/80 p-6 rounded-3xl shadow-xl backdrop-blur-xl">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
              <Target className="text-emerald-400 w-5 h-5" />
            </div>
            <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Conversion Rate</h3>
          </div>
          <p className="text-4xl font-semibold text-white tracking-tight">{stats.conversion_rate}%</p>
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/80 p-6 rounded-3xl shadow-xl backdrop-blur-xl">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-10 w-10 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
              <Banknote className="text-purple-400 w-5 h-5" />
            </div>
            <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Projected Revenue</h3>
          </div>
          <p className="text-4xl font-semibold text-white tracking-tight">{projectedRevenue}</p>
        </div>
      </div>

      {/* Charting Integration (Grid layout, fully responsive) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/40 border border-zinc-800/80 p-6 rounded-3xl shadow-xl backdrop-blur-xl">
          <h3 className="text-base font-medium text-white mb-6">Pipeline Funnel</h3>
          <FunnelChart data={funnelData} />
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/80 p-6 rounded-3xl shadow-xl backdrop-blur-xl">
          <h3 className="text-base font-medium text-white mb-6">Lead Sources</h3>
          <SourceChart data={sourceData} />
        </div>
      </div>
    </div>
  )
}
