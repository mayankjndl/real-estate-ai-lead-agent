import { fetchAnalytics, fetchLeads } from '@/lib/api'
import { 
  AreaTrendChart, SourcePieChart, FunnelChart, AgentPerformanceChart, FollowUpGauge 
} from './Charts'
import { 
  Users, Target, Banknote, Clock, ArrowUpRight, Flame, AlertCircle, Calendar, Briefcase, Activity
} from 'lucide-react'
import Link from 'next/link'

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

export default async function DashboardPage() {
  const analyticsData = await fetchAnalytics()
  const leadsData = await fetchLeads()
  
  const leads = leadsData?.leads || []
  const totalLeads = leads.length

  // Core KPIs & Derivations
  const closedDeals = leads.filter(l => l.funnel_stage === 'Closed Won').length
  const conversionRate = totalLeads > 0 ? Math.round((closedDeals / totalLeads) * 100) : 0
  
  // Pipeline Value (Derived from parsing budget strings)
  const parseBudget = (b: string | null) => {
    if (!b) return 0;
    if (b.includes('Cr')) return parseFloat(b) * 10000000;
    if (b.includes('L')) return parseFloat(b) * 100000;
    const num = parseFloat(b.replace(/[^0-9.]/g, ''));
    return isNaN(num) ? 0 : num;
  };
  
  const pipelineValue = leads.reduce((acc, l) => acc + parseBudget(l.budget), 0);
  const revenueForecast = leads.reduce((acc, l) => acc + (parseBudget(l.budget) * ((l.conversion_probability || 0) / 100)), 0);
  
  const formatCurrency = (val: number) => {
    if (val === 0) return '₹0';
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
    return `₹${val.toLocaleString()}`;
  }

  // Follow-Up Success Rate (Derived: engagement_score > 50)
  const engagedLeads = leads.filter(l => (l.engagement_score || 0) > 50).length;
  const followUpSuccessRate = totalLeads > 0 ? Math.round((engagedLeads / totalLeads) * 100) : 0;

  // Temperatures
  const hotCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'hot').length
  const warmCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'warm').length
  const coldCount = leads.filter(l => l.lead_temperature?.toLowerCase() === 'cold').length

  // Mock Appointments Data
  const appointmentsScheduled = leads.filter(l => l.funnel_stage === 'Appointment Scheduled').length + 1; // +1 for mock representation
  const appointmentsCompleted = 1; // derived mock metric
  const mockAppointments = [
    { id: 1, name: "Arjun Mehta", property: "3BHK Baner", date: "2026-06-19 14:00", status: "Scheduled" },
    { id: 2, name: "Sneha Patil", property: "Villa Hinjewadi", date: "2026-06-18 10:30", status: "Completed" },
    { id: 3, name: "Rahul Sharma", property: "2BHK Kharadi", date: "2026-06-20 16:00", status: "Pending" },
    { id: 4, name: "Priya Desai", property: "Penthouse Viman Nagar", date: "2026-06-21 11:00", status: "Rescheduled" },
    { id: 5, name: "Amit Singh", property: "Commercial Space", date: "2026-06-17 09:00", status: "Cancelled" },
  ];

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

      {/* Top KPIs Grid - 10 Mandatory Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <KPICard title="Total Leads" value={totalLeads} icon={Users} color="text-slate-500" bg="bg-slate-500/10" border="border-slate-500/20" />
        <KPICard title="Hot Leads" value={hotCount} icon={Flame} color="text-emerald-500" bg="bg-emerald-500/10" border="border-emerald-500/20" />
        <KPICard title="Warm Leads" value={warmCount} icon={Target} color="text-amber-500" bg="bg-amber-500/10" border="border-amber-500/20" />
        <KPICard title="Cold Leads" value={coldCount} icon={Target} color="text-rose-500" bg="bg-rose-500/10" border="border-rose-500/20" />
        <KPICard title="Conversion Rate" value={`${conversionRate}%`} icon={ArrowUpRight} color="text-blue-500" bg="bg-blue-500/10" border="border-blue-500/20" />
        
        <KPICard title="Appts Scheduled" value={appointmentsScheduled} icon={Calendar} color="text-indigo-500" bg="bg-indigo-500/10" border="border-indigo-500/20" />
        <KPICard title="Appts Completed" value={appointmentsCompleted} icon={Calendar} color="text-green-500" bg="bg-green-500/10" border="border-green-500/20" />
        <KPICard title="Follow-Up Success" value={`${followUpSuccessRate}%`} icon={Activity} color="text-teal-500" bg="bg-teal-500/10" border="border-teal-500/20" />
        <KPICard title="Pipeline Value" value={formatCurrency(pipelineValue)} icon={Banknote} color="text-purple-500" bg="bg-purple-500/10" border="border-purple-500/20" />
        <KPICard title="Revenue Forecast" value={formatCurrency(revenueForecast)} icon={Banknote} color="text-emerald-600" bg="bg-emerald-600/10" border="border-emerald-600/20" />
      </div>

      {/* Temperature Split & Conversion */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        <div className="lg:col-span-2 bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl relative overflow-hidden shadow-sm dark:shadow-none overflow-x-auto">
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl" />
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">Lead Velocity (7 Days)</h3>
          <div className="min-w-[500px]">
             <AreaTrendChart data={trendData} />
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col justify-between shadow-sm dark:shadow-none">
          <div>
            <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-4">Pipeline Temperature</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-emerald-500 font-medium">Hot</span>
                  <span className="text-slate-900 dark:text-white">{hotCount}</span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500" style={{ width: `${totalLeads ? (hotCount/totalLeads)*100 : 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-amber-500 font-medium">Warm</span>
                  <span className="text-slate-900 dark:text-white">{warmCount}</span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500" style={{ width: `${totalLeads ? (warmCount/totalLeads)*100 : 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-rose-500 font-medium">Cold</span>
                  <span className="text-slate-900 dark:text-white">{coldCount}</span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div className="h-full bg-rose-500" style={{ width: `${totalLeads ? (coldCount/totalLeads)*100 : 0}%` }} />
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
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none overflow-x-auto">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">Funnel Drop-off</h3>
          <div className="min-w-[300px]">
            <FunnelChart data={funnelData} />
          </div>
        </div>
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none overflow-x-auto">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">Source Attribution</h3>
          <div className="min-w-[250px]">
            <SourcePieChart data={sourceData} />
          </div>
        </div>
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none overflow-x-auto">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-6">AI Agent Efficiency</h3>
          <div className="min-w-[250px]">
            <AgentPerformanceChart data={agentData} />
          </div>
        </div>
        <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col justify-center shadow-sm dark:shadow-none">
          <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Automated Follow-ups</h3>
          <FollowUpGauge percentage={followUpSuccessRate} />
        </div>
      </div>

      {/* Bottom Widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        {/* Alerts / AI Summary */}
        <div className="bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-900/20 dark:to-zinc-900/40 border border-emerald-200 dark:border-emerald-500/20 p-6 rounded-3xl backdrop-blur-xl shadow-sm dark:shadow-none">
          <div className="flex items-center gap-3 mb-6">
            <AlertCircle className="text-emerald-600 dark:text-emerald-400 w-5 h-5" />
            <h3 className="text-sm font-medium text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Priority AI Alerts</h3>
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
                <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs rounded-full font-medium">Action Required</span>
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
        
        {/* Mock Appointments Table - Adding to bottom layout */}
        <div className="lg:col-span-3 bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-6 rounded-3xl backdrop-blur-xl flex flex-col shadow-sm dark:shadow-none">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Upcoming & Recent Appointments (Mocked UI)</h3>
          </div>
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-sm text-left min-w-[600px]">
              <thead className="text-xs text-slate-500 dark:text-zinc-500 uppercase border-b border-slate-200 dark:border-zinc-800">
                <tr>
                  <th className="px-4 py-3 font-medium">Client Name</th>
                  <th className="px-4 py-3 font-medium">Property Interest</th>
                  <th className="px-4 py-3 font-medium">Date & Time</th>
                  <th className="px-4 py-3 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                {mockAppointments.map((appt) => (
                  <tr key={appt.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{appt.name}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-zinc-400">{appt.property}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-zinc-300">{appt.date}</td>
                    <td className="px-4 py-3 text-right">
                      <AppointmentPill status={appt.status} />
                    </td>
                  </tr>
                ))}
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
    <div className="bg-white dark:bg-zinc-900/40 border border-slate-200 dark:border-white/5 p-4 md:p-6 rounded-3xl backdrop-blur-xl relative overflow-hidden group hover:border-slate-300 dark:hover:border-white/10 transition-colors duration-300 shadow-sm dark:shadow-none">
      <div className="flex items-center justify-between mb-4 relative z-10">
        <div className={`h-10 w-10 rounded-xl ${bg} flex items-center justify-center border ${border}`}>
          <Icon className={`${color} w-5 h-5`} />
        </div>
        {trend && <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 px-2 py-1 rounded-full">{trend}</span>}
      </div>
      <div className="relative z-10">
        <h3 className="text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-1 line-clamp-1">{title}</h3>
        <p className="text-2xl lg:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">{value}</p>
      </div>
      {/* Subtle hover glow */}
      <div className={`absolute -bottom-10 -right-10 w-32 h-32 ${bg} rounded-full blur-3xl opacity-0 group-hover:opacity-30 dark:group-hover:opacity-50 transition-opacity duration-500`} />
    </div>
  )
}
