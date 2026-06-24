'use client'

import { useState } from 'react'
import { Building2, LayoutDashboard, Inbox, Users, Settings, LogOut, Menu, X } from 'lucide-react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { logoutClient } from '@/lib/auth'
import { ThemeToggle } from '@/components/ThemeToggle'

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const currentRole = searchParams.get('role') || 'Owner'

  const handleRoleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newRole = e.target.value
    const params = new URLSearchParams(searchParams.toString())
    params.set('role', newRole)
    router.push(`${pathname}?${params.toString()}`)
  }

  const handleRestartTour = () => {
    const userEmail = localStorage.getItem('revenue_os_user_email') || 'default'
    localStorage.removeItem(`revenue_os_onboarding_${userEmail}`)
    window.location.reload()
  }

  return (
    <>
      {/* Mobile Top Bar */}
      <div className="md:hidden flex items-center justify-between p-4 border-b border-slate-200 dark:border-zinc-900 bg-white dark:bg-zinc-950">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-cyan-500 dark:from-emerald-400 dark:to-cyan-500 flex items-center justify-center">
            <Building2 className="text-white dark:text-zinc-950 w-4 h-4" />
          </div>
          <span className="font-semibold text-slate-900 dark:text-white tracking-tight">Revenue OS</span>
        </div>
        <button 
          onClick={() => setIsOpen(!isOpen)}
          className="p-2 bg-slate-100 dark:bg-zinc-900 rounded-md text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white transition-colors"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar Content */}
      <aside className={`
        ${isOpen ? 'translate-x-0' : '-translate-x-full'} 
        md:translate-x-0
        fixed md:static inset-y-0 left-0 z-50
        w-64 border-r border-slate-200 dark:border-zinc-900 bg-white/95 dark:bg-zinc-950/95 md:bg-white/50 md:dark:bg-zinc-950/50 flex flex-col
        transition-transform duration-300 ease-in-out
      `}>
        <div className="h-16 hidden md:flex items-center px-6 border-b border-slate-200 dark:border-zinc-900">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-cyan-500 dark:from-emerald-400 dark:to-cyan-500 flex items-center justify-center">
              <Building2 className="text-white dark:text-zinc-950 w-4 h-4" />
            </div>
            <span className="font-semibold text-slate-900 dark:text-white tracking-tight">Revenue OS</span>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-2 mt-16 md:mt-0 relative">
          <a href="/dashboard" onClick={() => setIsOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-300 relative ${pathname === '/dashboard' ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-400/10' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-900'}`}>
            <LayoutDashboard className={`w-4 h-4 transition-transform duration-300 ${pathname === '/dashboard' ? 'scale-110' : ''}`} /> Dashboard
          </a>
          <a href="/leads" onClick={() => setIsOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-300 relative ${pathname === '/leads' ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-400/10' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-900'}`}>
            <Inbox className={`w-4 h-4 transition-transform duration-300 ${pathname === '/leads' ? 'scale-110' : ''}`} /> Lead Inbox
          </a>
          <a href="/crm" onClick={() => setIsOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-300 relative ${pathname === '/crm' ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-400/10' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-900'}`}>
            <Users className={`w-4 h-4 transition-transform duration-300 ${pathname === '/crm' ? 'scale-110' : ''}`} /> CRM View
          </a>
        </nav>

        <div className="p-4 border-t border-slate-200 dark:border-zinc-900 space-y-2">
          {/* Simulated RBAC Switcher for Demo */}
          <div className="px-3 py-2 mb-2 bg-slate-50 dark:bg-zinc-900/50 rounded-lg border border-slate-200 dark:border-zinc-800">
            <label className="text-xs font-semibold text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-1 block">Simulate Role</label>
            <select 
              value={currentRole}
              onChange={handleRoleChange}
              className="w-full bg-transparent text-sm font-medium text-slate-700 dark:text-zinc-300 focus:outline-none"
            >
              <option value="Owner">Owner</option>
              <option value="Sales Manager">Sales Manager</option>
              <option value="Sales Agent">Sales Agent</option>
              <option value="Agency Partner">Agency Partner</option>
            </select>
          </div>

          <div className="flex items-center justify-between px-3 py-2 mb-2">
            <span className="text-sm font-medium text-slate-500 dark:text-zinc-400">Theme</span>
            <ThemeToggle />
          </div>
          
          <button 
            onClick={handleRestartTour}
            className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-500/10 rounded-lg transition-colors text-left"
          >
            <Settings className="w-4 h-4" /> Restart Product Tour
          </button>
          <a href="/settings" onClick={() => setIsOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-300 ${pathname === '/settings' ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-400/10' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-white dark:hover:bg-zinc-900'}`}>
            <Settings className={`w-4 h-4 transition-transform duration-300 ${pathname === '/settings' ? 'scale-110' : ''}`} /> Settings
          </a>
          <form action={logoutClient}>
            <button className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-slate-500 hover:text-red-600 hover:bg-red-50 dark:text-zinc-400 dark:hover:text-red-400 dark:hover:bg-red-400/10 rounded-lg transition-colors">
              <LogOut className="w-4 h-4" /> Sign Out
            </button>
          </form>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
