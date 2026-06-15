import { fetchAnalytics, fetchLeads } from '@/lib/api'
import { 
  AreaTrendChart, SourcePieChart, FunnelChart, AgentPerformanceChart, FollowUpGauge 
} from './Charts'
import { 
  Users, Target, Banknote, Clock, ArrowUpRight, Flame, AlertCircle, Calendar, Briefcase 
} from 'lucide-react'
import Link from 'next/link'

export default async function DashboardPage() {
  const analyticsData = await fetchAnalytics()
  const leadsData = await fetchLeads()
  
  const leads = leadsData?.leads || []
  const totalLeads = leads.length

  // Core KPIs
  const qualifiedLeads = leads.filter(l => l.funnel_stage !== 'New').length
  const closedDeals = leads.filter(l => l.funnel_stage === 'Closed Won').length
  const conversionRate = totalLeads > 0 ? Math.round((closedDeals / totalLeads) * 100) : 0
  const appointments = leads.filter(l => l.funnel_stage === 'Appointment Scheduled').length
  
  // Parse numeric budgets for revenue calculation (very basic string matching for mockup)
  const revenueGenerated = leads.filter(l => l.funnel_stage === 'Closed Won').reduce((acc, curr) => {
    if (curr.budget?.includes('Cr')) return acc + parseFloat(curr.budget) * 10000000;
    if (curr.budget?.includes('L')) return acc + parseFloat(curr.budget) * 100000;
    return acc;
  }, 0)
  
  const formatCurrency = (val: number) => {
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`
    return `₹${val}`
  }

  // Temperatures
  const hotCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'hot').length
  const warmCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'warm').length
  const coldCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'cold').length

  // Funnel Data
  const STAGES = ["New", "Contacted", "Qualified", "Appointment Scheduled", "Closed Won"]
  const funnelData = STAGES.map(stage => ({
    name: stage,
    value: leads.filter(l => l.funnel_stage === stage).length
  })).filter(d => d.value > 0)

  // Source Data
  const sourceMap: Record<string, number> = {}
  leads.forEach(l => {
    const s = l.source || 'Direct'
    sourceMap[s] = (sourceMap[s] || 0) + 1
  })
  const sourceData = Object.entries(sourceMap).map(([name, value]) => ({ name, value }))

  // Mock Trend Data for Demo (Past 7 Days)
  const trendData = Array.from({length: 7}).map((_, i) => ({
    date: new Date(Date.now() - (6 - i) * 86400000).toLocaleDateString('en-US', { weekday: 'short' }),
    leads: Math.floor(Math.random() * 20) + 5
  }))

  // Agent Performance (Mocked AI vs Human metrics)
  const agentData = [
    { name: 'AI Qualification', score: 92 },
    { name: 'Human Handoff', score: 78 },
    { name: 'Follow-ups', score: 85 }
  ]

  // Alerts / Priority Leads
  const priorityLeads = leads
    .filter(l => l.lead_temperature?.toLowerCase() === 'hot')
    .slice(0, 3)

  // Recent Inbox
  const recentLeads = [...leads].reverse().slice(0, 5)

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Executive Overview</h1>
          <p className="text-slate-500 dark:text-zinc-400 mt-1">Live AI Intelligence & Pipeline Performance</p>
        </div>
        <div className="flex items-center gap-3 bg-white dark:bg-zinc-900/50 border border-slate-200 dark:border-zinc-800 rounded-full px-4 py-2 backdrop-blur-md shadow-sm">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400 tracking-wider uppercase">Live Sync Active</span>
        </div>
      </div>

      {/* Top KPIs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="Total Leads Generated" value={totalLeads} icon={Users} color="text-blue-400" bg="bg-blue-500/10" border="border-blue-500/20" />
        <KPICard title="Qualified Leads" value={qualifiedLeads} icon={Target} color="text-emerald-400" bg="bg-emerald-500/10" border="border-emerald-500/20" trend="+12%" />
        <KPICard title="Appointments Booked" value={appointments} icon={Calendar} color="text-purple-400" bg="bg-purple-500/10" border="border-purple-500/20" />
        <KPICard title="Revenue Generated" value={revenueGenerated > 0 ? formatCurrency(revenueGenerated) : '$0'} icon={Banknote} color="text-emerald-400" bg="bg-emerald-500/10" border="border-emerald-500/20" />
      </div>

      {/* Temperature Split & Conversion */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        <div className="lg:col-span-2 bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl relative overflow-hidden shadow-sm dark:shadow-none">
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl" />
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">Lead Velocity (7 Days)</h3>
          <AreaTrendChart data={trendData} />
        </div>

        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col justify-between shadow-sm dark:shadow-none">
          <div>
            <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-4">Pipeline Temperature</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-rose-400 font-medium">Hot</span>
                  <span className="text-slate-900 dark:text-white">{hotCount}</span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-rose-500" style={{ width: `${totalLeads ? (hotCount/totalLeads)*100 : 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-orange-400 font-medium">Warm</span>
                  <span className="text-slate-900 dark:text-white">{warmCount}</span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-orange-500" style={{ width: `${totalLeads ? (warmCount/totalLeads)*100 : 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-blue-400 font-medium">Cold</span>
                  <span className="text-slate-900 dark:text-white">{coldCount}</span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500" style={{ width: `${totalLeads ? (coldCount/totalLeads)*100 : 0}%` }} />
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-8 pt-6 border-t border-slate-200 dark:border-zinc-800">
            <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Overall Conversion</h3>
            <div className="flex items-end gap-3">
              <span className="text-4xl font-bold text-slate-900 dark:text-white">{conversionRate}%</span>
              <span className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center mb-1"><ArrowUpRight className="w-4 h-4 mr-1"/> Top Tier</span>
            </div>
          </div>
        </div>
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">Funnel Drop-off</h3>
          <FunnelChart data={funnelData} />
        </div>
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">Source Attribution</h3>
          <SourcePieChart data={sourceData} />
        </div>
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">AI Agent Efficiency</h3>
          <AgentPerformanceChart data={agentData} />
        </div>
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col justify-center shadow-sm dark:shadow-none">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Automated Follow-ups</h3>
          <FollowUpGauge percentage={85} />
        </div>
      </div>

      {/* Bottom Widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        {/* Alerts / AI Summary */}
        <div className="bg-gradient-to-br from-rose-50 to-white dark:from-rose-900/20 dark:to-zinc-900/40 border border-rose-200 dark:border-rose-500/20 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none">
          <div className="flex items-center gap-3 mb-6">
            <AlertCircle className="text-rose-600 dark:text-rose-400 w-5 h-5" />
            <h3 className="text-sm font-medium text-rose-600 dark:text-rose-400 uppercase tracking-wider">Priority AI Alerts</h3>
          </div>
          <p className="text-sm text-slate-700 dark:text-zinc-300 mb-6 leading-relaxed">
            AI has identified <span className="font-bold text-slate-900 dark:text-white">{hotCount} high-intent buyers</span>. The following leads require immediate human follow-up to close.
          </p>
          <div className="space-y-3">
            {priorityLeads.map(l => (
              <div key={l.id} className="bg-white dark:bg-zinc-950/50 border border-slate-200 dark:border-white/5 p-3 rounded-xl flex justify-between items-center shadow-sm dark:shadow-none">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">{l.name || l.phone}</p>
                  <p className="text-xs text-slate-500 dark:text-zinc-400">{l.budget || 'Budget unknown'} • {l.location}</p>
                </div>
                <span className="px-2 py-1 bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 text-xs rounded-full font-medium">Action Required</span>
              </div>
            ))}
            {priorityLeads.length === 0 && <p className="text-slate-500 dark:text-zinc-500 text-sm">No critical alerts currently.</p>}
          </div>
        </div>

        {/* Inbox Snapshot */}
        <div className="lg:col-span-2 bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col shadow-sm dark:shadow-none">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Recent Inbox Activity</h3>
            <Link href="/crm" className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 transition-colors">View All Pipeline &rarr;</Link>
          </div>
          
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 dark:text-zinc-500 uppercase border-b border-slate-200 dark:border-zinc-800">
                <tr>
                  <th className="px-4 py-3 font-medium">Lead</th>
                  <th className="px-4 py-3 font-medium">Intent</th>
                  <th className="px-4 py-3 font-medium">Stage</th>
                  <th className="px-4 py-3 font-medium text-right">Temperature</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                {recentLeads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900 dark:text-white">{lead.name || 'Anonymous'}</div>
                      <div className="text-slate-500 dark:text-zinc-500 text-xs">{lead.phone}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-zinc-300 capitalize">{lead.intent || 'Unknown'}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-slate-100 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 text-slate-600 dark:text-zinc-300 text-xs rounded-md">{lead.funnel_stage}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        lead.lead_temperature === 'Hot' ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400' :
                        lead.lead_temperature === 'Warm' ? 'bg-orange-100 dark:bg-orange-500/20 text-orange-600 dark:text-orange-400' :
                        'bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400'
                      }`}>
                        {lead.lead_temperature || 'Cold'}
                      </span>
                    </td>
                  </tr>
                ))}
                {recentLeads.length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-500 dark:text-zinc-500">No recent leads found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

    </div>
  )
}

function KPICard({ title, value, icon: Icon, color, bg, border, trend }: any) {
  return (
    <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl relative overflow-hidden group hover:border-slate-300 dark:hover:border-white/10 transition-colors duration-300 shadow-sm dark:shadow-none">
      <div className="flex items-center justify-between mb-4 relative z-10">
        <div className={`h-10 w-10 rounded-xl ${bg} flex items-center justify-center border ${border}`}>
          <Icon className={`${color} w-5 h-5`} />
        </div>
        {trend && <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 px-2 py-1 rounded-full">{trend}</span>}
      </div>
      <div className="relative z-10">
        <h3 className="text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-1">{title}</h3>
        <p className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">{value}</p>
      </div>
      {/* Subtle hover glow */}
      <div className={`absolute -bottom-10 -right-10 w-32 h-32 ${bg} rounded-full blur-3xl opacity-0 group-hover:opacity-30 dark:group-hover:opacity-50 transition-opacity duration-500`} />
    </div>
  )
}
