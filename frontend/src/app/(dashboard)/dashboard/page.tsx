import { fetchAnalytics, fetchLeads } from '@/lib/api'
import { 
  AreaTrendChart, SourcePieChart, FunnelChart, AgentPerformanceChart, FollowUpGauge 
} from './Charts'
import { 
  Users, Target, Banknote, Clock, ArrowUpRight, Flame, AlertCircle, Calendar, Briefcase, Activity, Inbox
} from 'lucide-react'
import Link from 'next/link'
import GlobalFilters from './GlobalFilters'
import ExportReport from './ExportReport'
import TooltipInfo from './TooltipInfo'
import OnboardingWalkthrough from './OnboardingWalkthrough'

// Helper for Mock Appointment Colors
function AppointmentPill({ status }: { status: string }) {
  switch (status) {
    case 'Scheduled': return <span className="px-2 py-1 bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400 text-xs rounded-full font-medium">{status}</span>;
    case 'Completed': return <span className="px-2 py-1 bg-green-100 text-green-600 dark:bg-green-500/20 dark:text-green-400 text-xs rounded-full font-medium">{status}</span>;
    case 'Pending': return <span className="px-2 py-1 bg-orange-100 text-orange-600 dark:bg-orange-500/20 dark:text-orange-400 text-xs rounded-full font-medium">{status}</span>;
    case 'Rescheduled': return <span className="px-2 py-1 bg-purple-100 text-purple-600 dark:bg-purple-500/20 dark:text-purple-400 text-xs rounded-full font-medium">{status}</span>;
    case 'Cancelled': return <span className="px-2 py-1 bg-red-100 text-red-600 dark:bg-red-500/20 dark:text-red-400 text-xs rounded-full font-medium">{status}</span>;
    default: return <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-full font-medium">{status}</span>;
  }
}

type Props = {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function DashboardPage(props: Props) {
  const searchParams = await props.searchParams;
  const analyticsData = await fetchAnalytics()
  const leadsData = await fetchLeads()
  
  let rawLeads = leadsData?.leads || []
  let leads = [...rawLeads]

  // --- Apply Global Filters ---
  if (searchParams?.days && searchParams.days !== 'all') {
    const days = parseInt(searchParams.days as string, 10);
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    leads = leads.filter(l => new Date(l.updated_at) >= cutoffDate);
  }

  if (searchParams?.source && searchParams.source !== 'all') {
    const src = searchParams.source as string;
    leads = leads.filter(l => (l.source || 'Direct').toLowerCase() === src.toLowerCase());
  }

  const totalLeads = leads.length

  // Parse Budget
  const parseBudget = (b: string | null) => {
    if (!b) return 0;
    if (b.includes('Cr')) return parseFloat(b) * 10000000;
    if (b.includes('L')) return parseFloat(b) * 100000;
    const num = parseFloat(b.replace(/[^0-9.]/g, ''));
    return isNaN(num) ? 0 : num;
  };
  
  const formatCurrency = (val: number) => {
    if (val === 0) return '₹0';
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
    return `₹${val.toLocaleString()}`;
  }

  // Core KPIs & Derivations
  const closedDeals = leads.filter(l => l.funnel_stage === 'Closed Won').length
  const conversionRate = totalLeads > 0 ? Math.round((closedDeals / totalLeads) * 100) : 0
  
  const activePipelineValue = leads.filter(l => l.funnel_stage !== 'Lost').reduce((acc, l) => acc + parseBudget(l.budget), 0);
  const closedRevenue = leads.filter(l => l.funnel_stage === 'Closed Won').reduce((acc, l) => acc + parseBudget(l.budget), 0);
  const revenueForecast = leads.reduce((acc, l) => acc + (parseBudget(l.budget) * ((l.conversion_probability || 0) / 100)), 0);
  
  // Follow-Up Metrics
  const engagedLeads = leads.filter(l => (l.engagement_score || 0) > 50).length;
  const followUpSuccessRate = totalLeads > 0 ? Math.round((engagedLeads / totalLeads) * 100) : 0;
  const overdueFollowUps = leads.filter(l => (l.engagement_score || 100) < 40 && l.urgency_level === 'High').length;

  // Temperatures
  const hotCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'hot').length
  const warmCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'warm').length
  const coldCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'cold').length

  // Funnel Data & Conversion by Stage
  const STAGES = ["New", "Contacted", "Qualified", "Appointment Scheduled", "Closed Won"]
  const funnelData = STAGES.map(stage => ({
    name: stage,
    value: leads.filter(l => l.funnel_stage === stage).length
  }))
  
  const stageConversion = totalLeads > 0 
    ? Math.round((leads.filter(l => l.funnel_stage !== 'New').length / totalLeads) * 100) 
    : 0;

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

  const priorityLeads = leads
    .filter(l => l.lead_temperature?.toLowerCase() === 'hot')
    .slice(0, 3)

  const recentLeads = [...leads].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 5)

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700 relative">
      <OnboardingWalkthrough />

      {/* Header */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Executive Overview</h1>
          <p className="text-slate-500 dark:text-zinc-400 mt-1">Live AI Intelligence & Pipeline Performance</p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <GlobalFilters />
          <ExportReport leads={leads} />
          <div className="flex items-center gap-3 bg-white dark:bg-zinc-900/50 border border-slate-200 dark:border-zinc-800 rounded-full px-4 py-2 backdrop-blur-md shadow-sm">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400 tracking-wider uppercase">Live Sync Active</span>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {leads.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 rounded-3xl backdrop-blur-xl">
          <div className="h-24 w-24 bg-slate-100 dark:bg-zinc-800 rounded-full flex items-center justify-center mb-6">
            <Inbox className="w-10 h-10 text-slate-400" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">No leads found</h2>
          <p className="text-slate-500 dark:text-zinc-400 max-w-sm text-center mb-6">
            {rawLeads.length > 0 
              ? "No leads match your current filter criteria. Try adjusting the date range or source." 
              : "Your CRM pipeline is currently empty. Connect a source to start capturing AI leads."}
          </p>
          {rawLeads.length > 0 && (
            <Link href="/dashboard" className="px-6 py-2 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors">
              Clear Filters
            </Link>
          )}
        </div>
      ) : (
        <>
          {/* Top KPIs Grid - 10 Mandatory Metrics + New Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <KPICard title="Total Leads" value={totalLeads} icon={Users} color="text-slate-500" bg="bg-slate-500/10" border="border-slate-500/20" tooltip="Total number of people who interacted with your AI assistant." />
            <KPICard title="Hot Leads" value={hotCount} icon={Flame} color="text-emerald-500" bg="bg-emerald-500/10" border="border-emerald-500/20" tooltip="Ready to buy! Call these people immediately." />
            <KPICard title="Warm Leads" value={warmCount} icon={Target} color="text-amber-500" bg="bg-amber-500/10" border="border-amber-500/20" tooltip="Interested but still thinking. They need a little more time." />
            <KPICard title="Overdue Follow-ups" value={overdueFollowUps} icon={AlertCircle} color="text-rose-500" bg="bg-rose-500/10" border="border-rose-500/20" tooltip="Important leads that have gone quiet. You should reach out to them now." />
            <KPICard title="Est. Pipeline Value" value={formatCurrency(activePipelineValue)} icon={Briefcase} color="text-indigo-500" bg="bg-indigo-500/10" border="border-indigo-500/20" tooltip="The total combined budget of everyone currently looking to buy." />
            
            <KPICard title="Closed Revenue" value={formatCurrency(closedRevenue)} icon={Banknote} color="text-emerald-600" bg="bg-emerald-600/10" border="border-emerald-600/20" tooltip="The total money made from deals you've successfully closed." />
            <KPICard title="Conversion Rate" value={`${conversionRate}%`} icon={ArrowUpRight} color="text-blue-500" bg="bg-blue-500/10" border="border-blue-500/20" tooltip="The percentage of people who actually ended up buying." />
            <KPICard title="Stage Conversion" value={`${stageConversion}%`} icon={Target} color="text-teal-500" bg="bg-teal-500/10" border="border-teal-500/20" tooltip="How many people had a meaningful conversation instead of just dropping off." />
            <KPICard title="Response Time" value="5m (Sample)" icon={Clock} color="text-purple-500" bg="bg-purple-500/10" border="border-purple-500/20" tooltip="How quickly the AI replies to a new inquiry. (Sample data)" />
            <KPICard title="Follow-Up Success" value={`${followUpSuccessRate}%`} icon={Activity} color="text-orange-500" bg="bg-orange-500/10" border="border-orange-500/20" tooltip="How well the AI's automatic follow-ups kept people interested." />
          </div>

          {/* Visual Analytics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm relative hover:z-50 transition-all">
              <div className="flex items-center gap-2 mb-6">
                <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Funnel Drop-off</h3>
                <TooltipInfo text="Shows where people drop out of the buying process." />
              </div>
              <div className="w-full overflow-x-auto">
                <div className="min-w-[300px]">
                  <FunnelChart data={funnelData} />
                </div>
              </div>
            </div>
            <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm relative hover:z-50 transition-all">
              <div className="flex items-center gap-2 mb-6">
                <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Source Attribution</h3>
                <TooltipInfo text="Shows where your leads are coming from (like Instagram or Google)." />
              </div>
              <div className="w-full overflow-x-auto">
                <div className="min-w-[250px]">
                  <SourcePieChart data={sourceData} />
                </div>
              </div>
            </div>
            <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col justify-center shadow-sm relative hover:z-50 transition-all">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Automated Follow-ups</h3>
                <TooltipInfo text="How successfully the AI is keeping conversations alive." />
              </div>
              <FollowUpGauge percentage={followUpSuccessRate} />
            </div>
          </div>

          {/* Bottom Widgets */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            
            {/* Alerts / AI Summary */}
            <div className="bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-900/20 dark:to-zinc-900/40 border border-emerald-200 dark:border-emerald-500/20 p-6 rounded-3xl backdrop-blur-xl shadow-sm">
              <div className="flex items-center gap-3 mb-6">
                <AlertCircle className="text-emerald-600 dark:text-emerald-400 w-5 h-5" />
                <h3 className="text-sm font-medium text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Priority AI Alerts</h3>
              </div>
              <p className="text-sm text-slate-700 dark:text-zinc-300 mb-6 leading-relaxed">
                AI has identified <span className="font-bold text-slate-900 dark:text-white">{hotCount} high-intent buyers</span>. The following leads require immediate human follow-up to close.
              </p>
              <div className="space-y-3">
                {priorityLeads.map(l => (
                  <div key={l.id} className="bg-white dark:bg-zinc-950/50 border border-slate-200 dark:border-white/5 p-3 rounded-xl flex justify-between items-center shadow-sm">
                    <div>
                      <p className="text-sm font-medium text-slate-900 dark:text-white">{l.name || l.phone}</p>
                      <p className="text-xs text-slate-500 dark:text-zinc-400">{l.budget || 'Budget unknown'} • {l.location}</p>
                    </div>
                    <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs rounded-full font-medium">Action Required</span>
                  </div>
                ))}
                {priorityLeads.length === 0 && <p className="text-slate-500 dark:text-zinc-500 text-sm">No critical alerts currently.</p>}
              </div>
            </div>

            {/* Inbox Snapshot */}
            <div className="lg:col-span-2 bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Recent Inbox Activity</h3>
                <Link href="/crm" className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 transition-colors">View All Pipeline &rarr;</Link>
              </div>
              
              <div className="flex-1 overflow-x-auto">
                <table className="w-full text-sm text-left min-w-[500px]">
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
                            lead.lead_temperature === 'Hot' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
                            lead.lead_temperature === 'Warm' ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400' :
                            'bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400'
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
        </>
      )}

    </div>
  )
}

function KPICard({ title, value, icon: Icon, color, bg, border, trend, tooltip }: any) {
  return (
    <Link href={`/crm?filter=${encodeURIComponent(title)}`} className={`bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-4 md:p-6 rounded-3xl backdrop-blur-xl relative group hover:z-50 hover:border-slate-300 dark:hover:border-white/10 transition-colors duration-300 shadow-sm block`}>
      {/* Background glow container */}
      <div className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none">
        <div className={`absolute -bottom-10 -right-10 w-32 h-32 ${bg} rounded-full blur-3xl opacity-0 group-hover:opacity-30 dark:group-hover:opacity-50 transition-opacity duration-500`} />
      </div>

      <div className="flex items-center justify-between mb-4 relative z-10">
        <div className={`h-10 w-10 rounded-xl ${bg} flex items-center justify-center border ${border}`}>
          <Icon className={`${color} w-5 h-5`} />
        </div>
        <div className="flex items-center">
          {trend && <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 px-2 py-1 rounded-full">{trend}</span>}
          {tooltip && <TooltipInfo text={tooltip} />}
        </div>
      </div>
      <div className="relative z-10">
        <h3 className="text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-1 line-clamp-1">{title}</h3>
        <p className="text-2xl lg:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">{value}</p>
      </div>
    </Link>
  )
}
