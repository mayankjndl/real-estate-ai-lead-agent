import { fetchLeads, Lead } from '@/lib/api'
import KanbanBoard from './KanbanBoard'

export default async function CRMPage() {
  const data = await fetchLeads()
  const leads = data?.leads || []

  return (
    <div className="space-y-8 h-[calc(100vh-8rem)] flex flex-col">
      <div>
        <h1 className="text-2xl font-medium text-white tracking-tight">Pipeline Board</h1>
        <p className="text-sm text-zinc-400 mt-1">Visualize your active real estate pipeline.</p>
      </div>

      <KanbanBoard initialLeads={leads} />
    </div>
  )
}
