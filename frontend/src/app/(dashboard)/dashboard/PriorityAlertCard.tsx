'use client'

import { useState } from 'react'
import { ArrowUpRight, CheckCircle2 } from 'lucide-react'
import Link from 'next/link'
import { acknowledgeLeadAlert } from '../crm/actions'

interface PriorityLead {
  id: number;
  name?: string | null;
  phone?: string | null;
  budget?: string | null;
  location?: string | null;
  assigned_agent?: string | null;
  is_negotiating?: boolean;
  conversion_status?: string;
}

export default function PriorityAlertCard({ lead }: { lead: PriorityLead }) {
  const [isClaimed, setIsClaimed] = useState(lead.conversion_status === 'claimed')
  const [isPending, setIsPending] = useState(false)

  const handleClaim = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsPending(true)
    try {
      await acknowledgeLeadAlert(lead.id)
      setIsClaimed(true)
    } catch (error) {
      console.error('Failed to claim lead', error)
    } finally {
      setIsPending(false)
    }
  }

  return (
    <Link 
      href={`/crm?leadId=${lead.id}`} 
      className={`p-3 rounded-xl flex justify-between items-center shadow-sm transition-colors group border ${
        isClaimed 
          ? 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-300 dark:border-emerald-500/50' 
          : 'bg-white dark:bg-zinc-950/50 border-slate-200 dark:border-white/5 hover:border-emerald-300 dark:hover:border-emerald-500/50'
      }`}
    >
      <div className="min-w-0 flex-1 pr-4">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{lead.name || lead.phone}</p>
          {isClaimed ? (
            <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[10px] rounded-full font-bold uppercase whitespace-nowrap flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Claimed
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[10px] rounded-full font-bold uppercase whitespace-nowrap">Call Now</span>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-zinc-400 truncate">{lead.budget || 'Budget unknown'} • {lead.location || 'Unknown loc'}</p>
        <p className="text-[10px] text-slate-400 dark:text-zinc-500 truncate mt-0.5">
          Agent: {lead.assigned_agent || 'Unassigned'}
        </p>
      </div>
      
      <div className="ml-2 flex items-center gap-2 flex-shrink-0">
        {lead.is_negotiating && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold whitespace-nowrap bg-purple-100 dark:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-800/50">
            🤝 Negotiate
          </span>
        )}
        {!isClaimed ? (
          <button 
            onClick={handleClaim}
            disabled={isPending}
            className="px-3 py-1.5 bg-rose-100 hover:bg-rose-200 text-rose-700 dark:bg-rose-500/20 dark:hover:bg-rose-500/40 dark:text-rose-400 text-xs font-bold rounded-lg transition-colors whitespace-nowrap"
          >
            {isPending ? 'Claiming...' : '🚨 Claim'}
          </button>
        ) : (
          <ArrowUpRight className="w-4 h-4 text-emerald-500" />
        )}
      </div>
    </Link>
  )
}
