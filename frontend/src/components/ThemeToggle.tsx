'use client'

import * as React from 'react'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-zinc-800 animate-pulse" />
  }

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="relative p-2.5 rounded-full text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-zinc-800/50 transition-all duration-300 focus:outline-none overflow-hidden group shadow-sm hover:shadow-md dark:shadow-none"
      aria-label="Toggle theme"
    >
      <div className="relative z-10 flex items-center justify-center transition-all duration-500 transform group-hover:rotate-12 group-active:scale-90">
        {theme === 'dark' ? (
          <Sun className="h-5 w-5 animate-in spin-in-90 fade-in duration-500" />
        ) : (
          <Moon className="h-5 w-5 animate-in -spin-in-90 fade-in duration-500" />
        )}
      </div>
    </button>
  )
}

