import os

base_dir = "src/app/(dashboard)/dashboard"
os.makedirs(base_dir, exist_ok=True)

charts_code = """'use client'

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'

export function FunnelChart({ data }: { data: any[] }) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" horizontal={false} opacity={0.5} />
          <XAxis type="number" stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis dataKey="name" type="category" stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '12px' }}
            itemStyle={{ color: '#fff' }}
            cursor={{ fill: '#27272a', opacity: 0.4 }}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={32}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={['#34d399', '#2dd4bf', '#38bdf8', '#818cf8', '#c084fc'][index % 5]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function SourceChart({ data }: { data: any[] }) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} opacity={0.5} />
          <XAxis dataKey="name" stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '12px' }}
            itemStyle={{ color: '#fff' }}
            cursor={{ fill: '#27272a', opacity: 0.4 }}
          />
          <Bar dataKey="value" fill="#38bdf8" radius={[6, 6, 0, 0]} barSize={40} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
"""

with open(f"{base_dir}/Charts.tsx", "w", encoding="utf-8") as f:
    f.write(charts_code)

page_code = """import { fetchAnalytics, fetchLeads } from '@/lib/api'
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
"""

with open(f"{base_dir}/page.tsx", "w", encoding="utf-8") as f:
    f.write(page_code)
print("ROI Dashboard created successfully.")
