'use client'

import { Info } from 'lucide-react'

export default function TooltipInfo({ text }: { text: string }) {
  return (
    <div className="group relative inline-flex items-center justify-center ml-1.5 cursor-help">
      <Info className="w-3.5 h-3.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors" />
      
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-800 dark:bg-zinc-800 text-white dark:text-zinc-200 text-xs font-medium rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 w-[200px] text-center z-50 pointer-events-none">
        {text}
        <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-slate-800 dark:border-t-zinc-800"></div>
      </div>
    </div>
  )
}
