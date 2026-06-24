'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { Filter } from 'lucide-react'

export default function GlobalFilters() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const currentSource = searchParams.get('source') || 'all'
  const currentDays = searchParams.get('days') || 'all'

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    if (value === 'all') {
      params.delete(key)
    } else {
      params.set(key, value)
    }
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <div className="flex items-center gap-3 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 p-2 rounded-2xl shadow-sm">
      <div className="pl-2 pr-1 text-slate-400">
        <Filter className="w-4 h-4" />
      </div>
      
      <select 
        value={currentDays}
        onChange={(e) => updateFilter('days', e.target.value)}
        className="bg-transparent text-sm font-medium text-slate-700 dark:text-zinc-300 outline-none cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
      >
        <option value="all">All Time</option>
        <option value="7">Past 7 Days</option>
        <option value="30">Past 30 Days</option>
      </select>

      <div className="w-px h-4 bg-slate-200 dark:bg-zinc-800 mx-1"></div>

      <select 
        value={currentSource}
        onChange={(e) => updateFilter('source', e.target.value)}
        className="bg-transparent text-sm font-medium text-slate-700 dark:text-zinc-300 outline-none cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
      >
        <option value="all">All Sources</option>
        <option value="Direct">Direct</option>
        <option value="Instagram">Instagram</option>
        <option value="Google">Google</option>
        <option value="Facebook">Facebook</option>
        <option value="WhatsApp">WhatsApp</option>
      </select>
    </div>
  )
}
