import { fetchLeads } from '@/lib/api'
import LeadsTable from './LeadsTable'

export default async function LeadsPage() {
  const data = await fetchLeads()
  const leads = data?.leads || []

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Lead Inbox</h1>
        <p className="text-slate-500 dark:text-zinc-400 mt-1">Manage, filter, and track your autonomous AI leads.</p>
      </div>
      
      <LeadsTable initialLeads={leads} />
    </div>
  )
}
