'use client'

import { useState } from 'react'
import { Lead } from '@/lib/api'
import { Flame, ThermometerSnowflake, AlertCircle, Clock, Zap, ArrowUpDown, Filter } from 'lucide-react'

function getTempBadge(temp: string) {
  const t = temp?.toLowerCase() || 'cold'
  if (t === 'hot') return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-rose-100 text-rose-600 border border-rose-200 dark:bg-red-400/10 dark:text-red-400 dark:border-red-400/20"><Flame className="w-3 h-3" /> Hot</span>
  if (t === 'warm') return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-orange-100 text-orange-600 border border-orange-200 dark:bg-orange-400/10 dark:text-orange-400 dark:border-orange-400/20"><Zap className="w-3 h-3" /> Warm</span>
  return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-600 border border-blue-200 dark:bg-blue-400/10 dark:text-blue-400 dark:border-blue-400/20"><ThermometerSnowflake className="w-3 h-3" /> Cold</span>
}

function getUrgencyBadge(urgency: string) {
  const u = urgency?.toLowerCase() || 'low'
  if (u === 'high') return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-rose-600 dark:text-red-400"><AlertCircle className="w-3 h-3" /> High</span>
  if (u === 'medium') return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-amber-500 dark:text-yellow-400"><Clock className="w-3 h-3" /> Medium</span>
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-slate-500 dark:text-zinc-500">Low</span>
}

type SortField = 'name' | 'score' | 'probability'
type SortOrder = 'asc' | 'desc'

export default function LeadsTable({ initialLeads }: { initialLeads: Lead[] }) {
  const [leads, setLeads] = useState<Lead[]>(initialLeads)
  const [sortField, setSortField] = useState<SortField>('probability')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  
  const [filterStage, setFilterStage] = useState<string>('All')
  const [filterTemp, setFilterTemp] = useState<string>('All')

  const handleSort = (field: SortField) => {
    const isAsc = sortField === field && sortOrder === 'asc'
    setSortOrder(isAsc ? 'desc' : 'asc')
    setSortField(field)
  }

  // Filter and Sort
  const filteredAndSortedLeads = leads
    .filter(lead => {
      if (filterStage !== 'All' && lead.funnel_stage !== filterStage) return false
      if (filterTemp !== 'All' && (lead.lead_temperature?.toLowerCase() || 'cold') !== filterTemp.toLowerCase()) return false
      return true
    })
    .sort((a, b) => {
      let valA: any = 0;
      let valB: any = 0;

      if (sortField === 'name') {
        valA = a.name?.toLowerCase() || ''
        valB = b.name?.toLowerCase() || ''
      } else if (sortField === 'score') {
        valA = a.engagement_score || 0
        valB = b.engagement_score || 0
      } else if (sortField === 'probability') {
        valA = a.conversion_probability || 0
        valB = b.conversion_probability || 0
      }

      if (valA < valB) return sortOrder === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

  const stages = ['All', 'New', 'Contacted', 'Qualified', 'Appointment Scheduled', 'Closed Won']
  const temps = ['All', 'Hot', 'Warm', 'Cold']

  return (
    <div className="space-y-6">
      
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-center bg-white/80 dark:bg-zinc-900/40 p-4 rounded-xl border border-slate-200 dark:border-zinc-800 shadow-sm dark:shadow-none backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500 dark:text-zinc-400" />
          <span className="text-sm font-medium text-slate-700 dark:text-zinc-300">Filters:</span>
        </div>
        
        <select 
          className="bg-slate-50 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 text-slate-700 dark:text-zinc-300 text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block px-3 py-2"
          value={filterStage}
          onChange={(e) => setFilterStage(e.target.value)}
        >
          {stages.map(s => <option key={s} value={s}>Stage: {s}</option>)}
        </select>

        <select 
          className="bg-slate-50 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 text-slate-700 dark:text-zinc-300 text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block px-3 py-2"
          value={filterTemp}
          onChange={(e) => setFilterTemp(e.target.value)}
        >
          {temps.map(t => <option key={t} value={t}>Temp: {t}</option>)}
        </select>
        
        <div className="ml-auto text-xs text-slate-500 dark:text-zinc-500">
          Showing {filteredAndSortedLeads.length} leads
        </div>
      </div>

      <div className="bg-white/80 dark:bg-zinc-900/40 border border-slate-200 dark:border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl dark:shadow-2xl backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-zinc-800/80 bg-slate-50/50 dark:bg-zinc-900/50">
                <th 
                  className="px-6 py-4 text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
                  onClick={() => handleSort('name')}
                >
                  <div className="flex items-center gap-1">Lead <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th className="px-6 py-4 text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Intent & Budget</th>
                <th 
                  className="px-6 py-4 text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
                  onClick={() => handleSort('score')}
                >
                  <div className="flex items-center gap-1">Intelligence <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th 
                  className="px-6 py-4 text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors"
                  onClick={() => handleSort('probability')}
                >
                  <div className="flex items-center gap-1">Probability <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th className="px-6 py-4 text-xs font-medium text-slate-500 dark:text-zinc-400 uppercase tracking-wider">Stage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-zinc-800/50">
              {filteredAndSortedLeads.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-sm text-slate-500 dark:text-zinc-500">
                    No leads found matching criteria.
                  </td>
                </tr>
              ) : filteredAndSortedLeads.map((lead: Lead) => (
                <tr key={lead.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/30 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-slate-900 dark:text-zinc-200">{lead.name || 'Anonymous User'}</span>
                      <span className="text-xs text-slate-500 dark:text-zinc-500">{lead.phone || lead.session_id}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-sm text-slate-700 dark:text-zinc-300 capitalize">{lead.intent || 'Exploring'}</span>
                      <span className="text-xs text-slate-500 dark:text-zinc-500">{lead.budget || 'Undisclosed'}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        {getTempBadge(lead.lead_temperature)}
                        {getUrgencyBadge(lead.urgency_level)}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-zinc-400">
                        <span title="Engagement Score">Eng: {lead.engagement_score || 0}/100</span>
                        <span>•</span>
                        <span title="Expected Closure">Close: {lead.expected_closure_days || 60}d</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-3">
                      <div className="w-full max-w-[100px] bg-slate-200 dark:bg-zinc-800 rounded-full h-1.5">
                        <div 
                          className="bg-emerald-500 dark:bg-emerald-400 h-1.5 rounded-full" 
                          style={{ width: `${lead.conversion_probability || 0}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-medium text-slate-600 dark:text-zinc-400">{lead.conversion_probability || 0}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 border border-slate-200 dark:border-zinc-700">
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
