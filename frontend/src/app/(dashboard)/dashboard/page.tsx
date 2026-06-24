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

type Props = {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function DashboardPage(props: Props) {
  const searchParams = await props.searchParams;
  const analyticsData = await fetchAnalytics()
  const leadsData = await fetchLeads()
  
  let rawLeads = leadsData?.leads || []
  let leads = [...rawLeads]

  // --- RBAC Implementation (Simulated for Demo) ---
  const role = (searchParams?.role as string) || 'Owner'
  const isSalesAgent = role === 'Sales Agent'
  const isAgencyPartner = role === 'Agency Partner'

  if (isSalesAgent) {
    // Sales Agents only see leads assigned to them (mocked here as 'Jane Doe' or a subset)
    leads = leads.filter(l => l.assigned_agent === 'Jane Doe' || (l.id % 2 === 0))
  }

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
    if (isAgencyPartner) return 'RESTRICTED'; // Agency Partners cannot see Revenue
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
  
  // Follow-Up Metrics
  const engagedLeads = leads.filter(l => (l.engagement_score || 0) > 50).length;
  const followUpSuccessRate = totalLeads > 0 ? Math.round((engagedLeads / totalLeads) * 100) : 0;
  
  const overdueLeadsList = leads.filter(l => (l.engagement_score || 100) < 40 && l.urgency_level === 'High');
  const overdueFollowUps = overdueLeadsList.length;

  // Temperatures
  const hotCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'hot').length
  const warmCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'warm').length

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
          <p className="text-slate-500 dark:text-zinc-400 mt-1">
            Live AI Intelligence & Pipeline Performance 
            <span className="ml-2 px-2 py-0.5 bg-slate-200 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 rounded text-xs font-semibold uppercase tracking-wider">Role: {role}</span>
          </p>
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
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-8 sm:p-12 rounded-3xl backdrop-blur-xl max-w-3xl mx-auto mt-10 shadow-sm animate-in zoom-in-95 duration-500">
          <div className="flex flex-col items-center text-center mb-10">
            <div className="h-24 w-24 bg-emerald-100 dark:bg-emerald-500/20 rounded-full flex items-center justify-center mb-6">
              <Inbox className="w-12 h-12 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-3">Welcome to Revenue OS</h2>
            <p className="text-slate-500 dark:text-zinc-400 max-w-md text-lg">Your CRM pipeline is ready. Complete these 4 steps to activate your AI agent and start generating leads.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { title: "Connect Lead Source", desc: "Link WhatsApp or Facebook to the AI engine." },
              { title: "Send a Test Inquiry", desc: "Message the AI to see how it qualifies leads in real-time." },
              { title: "Invite Sales Agents", desc: "Add your team so the AI can route hot leads to them." },
              { title: "Configure Settings", desc: "Upload your property brochures and pricing rules." },
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-4 p-5 border border-slate-200 dark:border-zinc-800 rounded-2xl hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors cursor-pointer group">
                <div className="h-8 w-8 rounded-full border-2 border-slate-300 dark:border-zinc-700 flex items-center justify-center flex-shrink-0 group-hover:border-emerald-500 transition-colors"></div>
                <div>
                  <h4 className="font-semibold text-slate-900 dark:text-white mb-1">{step.title}</h4>
                  <p className="text-sm text-slate-500 dark:text-zinc-400">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
          {rawLeads.length > 0 && (
             <div className="mt-10 text-center">
               <Link href="/dashboard" className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors shadow-md">Clear Active Filters</Link>
             </div>
          )}
        </div>
      ) : (
        <>
          {/* Top KPIs Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <KPICard badge="live" title="Total Leads" value={totalLeads} icon={Users} color="text-slate-500" bg="bg-slate-500/10" border="border-slate-500/20" tooltip="Total number of people who interacted with your AI assistant. (Calculated by counting all unique lead profiles)" />
            <KPICard badge="live" title="Hot Leads" value={hotCount} icon={Flame} color="text-emerald-500" bg="bg-emerald-500/10" border="border-emerald-500/20" tooltip="Ready to buy! Call these people immediately. (Calculated by AI based on high purchase intent & budget match)" />
            <KPICard badge="live" title="Warm Leads" value={warmCount} icon={Target} color="text-amber-500" bg="bg-amber-500/10" border="border-amber-500/20" tooltip="Interested but still thinking. (Calculated by AI based on medium intent and positive engagement)" />
            <KPICard badge="live" title="Est. Pipeline Value" value={formatCurrency(activePipelineValue)} icon={Briefcase} color="text-indigo-500" bg="bg-indigo-500/10" border="border-indigo-500/20" tooltip="The total combined budget of everyone looking to buy. (Calculated by summing budgets of all non-Lost leads)" />
            <KPICard badge="live" title="Closed Revenue" value={formatCurrency(closedRevenue)} icon={Banknote} color="text-emerald-600" bg="bg-emerald-600/10" border="border-emerald-600/20" tooltip="Total money made. (Calculated by summing budgets of leads strictly in the 'Closed Won' stage)" />
            
            <KPICard badge="live" title="Conversion Rate" value={`${conversionRate}%`} icon={ArrowUpRight} color="text-blue-500" bg="bg-blue-500/10" border="border-blue-500/20" tooltip="Percentage of people who actually bought. (Calculated as Closed Won divided by Total Leads)" />
            <KPICard badge="live" title="Stage Conversion" value={`${stageConversion}%`} icon={Target} color="text-teal-500" bg="bg-teal-500/10" border="border-teal-500/20" tooltip="How many people had a meaningful conversation. (Calculated by percentage of leads advancing past the 'New' stage)" />
            <KPICard badge="sample" title="Response Time" value="5m" icon={Clock} color="text-purple-500" bg="bg-purple-500/10" border="border-purple-500/20" tooltip="How quickly the AI replies to a new inquiry. (Metric not yet tracked in DB)" />
            <KPICard badge="live" title="Follow-Up Success" value={`${followUpSuccessRate}%`} icon={Activity} color="text-orange-500" bg="bg-orange-500/10" border="border-orange-500/20" tooltip="How well AI keeps people interested. (Percentage of leads maintaining an engagement score > 50)" />
            <KPICard badge="live" title="Overdue Follow-ups" value={overdueFollowUps} icon={AlertCircle} color="text-rose-500" bg="bg-rose-500/10" border="border-rose-500/20" tooltip="Important leads that have gone quiet. (Calculated by engagement < 40 and high urgency)" />
          </div>

          {/* Action Queues Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                  <Link href={`/crm?leadId=${l.id}`} key={l.id} className="bg-white dark:bg-zinc-950/50 border border-slate-200 dark:border-white/5 p-3 rounded-xl flex justify-between items-center shadow-sm hover:border-emerald-300 dark:hover:border-emerald-500/50 transition-colors group">
                    <div className="min-w-0 flex-1 pr-4">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{l.name || l.phone}</p>
                        <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[10px] rounded-full font-bold uppercase whitespace-nowrap">Call Now</span>
                      </div>
                      <p className="text-xs text-slate-500 dark:text-zinc-400 truncate">{l.budget || 'Budget unknown'} • {l.location || 'Unknown loc'}</p>
                    </div>
                    <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-500 transition-colors flex-shrink-0" />
                  </Link>
                ))}
                {priorityLeads.length === 0 && <p className="text-slate-500 dark:text-zinc-500 text-sm">No critical alerts currently.</p>}
              </div>
            </div>

            {/* Overdue Action Queue */}
            <div className="bg-gradient-to-br from-rose-50 to-white dark:from-rose-900/20 dark:to-zinc-900/40 border border-rose-200 dark:border-rose-500/20 p-6 rounded-3xl backdrop-blur-xl shadow-sm">
              <div className="flex items-center gap-3 mb-6">
                <Clock className="text-rose-600 dark:text-rose-400 w-5 h-5" />
                <h3 className="text-sm font-medium text-rose-600 dark:text-rose-400 uppercase tracking-wider">Overdue Action Queue</h3>
              </div>
              <p className="text-sm text-slate-700 dark:text-zinc-300 mb-6 leading-relaxed">
                <span className="font-bold text-slate-900 dark:text-white">{overdueLeadsList.length} leads</span> have dropped below the engagement threshold and require a manual touchpoint.
              </p>
              <div className="space-y-3">
                {overdueLeadsList.slice(0,3).map(l => (
                  <Link href={`/crm?leadId=${l.id}`} key={l.id} className="bg-white dark:bg-zinc-950/50 border border-slate-200 dark:border-white/5 p-3 rounded-xl flex justify-between items-center shadow-sm hover:border-rose-300 dark:hover:border-rose-500/50 transition-colors group">
                    <div className="min-w-0 flex-1 pr-4">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{l.name || l.phone}</p>
                        <span className="px-2 py-0.5 bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 text-[10px] rounded-full font-bold uppercase whitespace-nowrap">Message</span>
                      </div>
                      <p className="text-xs text-slate-500 dark:text-zinc-400 truncate">Engagement Drop: {l.engagement_score}%</p>
                    </div>
                    <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-rose-500 transition-colors flex-shrink-0" />
                  </Link>
                ))}
                {overdueLeadsList.length === 0 && <p className="text-slate-500 dark:text-zinc-500 text-sm">No overdue follow-ups! You are caught up.</p>}
              </div>
            </div>
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

          {/* Inbox Snapshot (Full Width) */}
          <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Recent Inbox Activity</h3>
              <Link href="/crm" className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 transition-colors">View All Pipeline &rarr;</Link>
            </div>
            
            <div className="w-full overflow-x-auto">
              <table className="w-full text-sm text-left min-w-[600px]">
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
                      <td className="px-4 py-3 max-w-[200px]">
                        <div className="font-medium text-slate-900 dark:text-white truncate">{lead.name || 'Anonymous'}</div>
                        <div className="text-slate-500 dark:text-zinc-500 text-xs truncate">{lead.phone}</div>
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-zinc-300 capitalize max-w-[150px] truncate">{lead.intent || 'Unknown'}</td>
                      <td className="px-4 py-3 max-w-[150px]">
                        <span className="px-2 py-1 bg-slate-100 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 text-slate-600 dark:text-zinc-300 text-xs rounded-md truncate inline-block max-w-full">{lead.funnel_stage}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium inline-block truncate ${
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

        </>
      )}

    </div>
  )
}

function KPICard({ title, value, icon: Icon, color, bg, border, trend, tooltip, badge }: any) {
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
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider line-clamp-1">{title}</h3>
          {badge === 'live' && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 uppercase">Live</span>}
          {badge === 'sample' && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 uppercase">Sample</span>}
        </div>
        <p className="text-2xl lg:text-3xl font-bold text-slate-900 dark:text-white tracking-tight truncate">{value}</p>
      </div>
    </Link>
  )
}
