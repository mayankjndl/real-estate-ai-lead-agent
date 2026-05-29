'use client'

import { useState } from 'react'
import { Building2, LayoutDashboard, Inbox, Users, Settings, LogOut, Menu, X } from 'lucide-react'
import { logoutClient } from '@/lib/auth'

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Mobile Top Bar */}
      <div className="md:hidden flex items-center justify-between p-4 border-b border-zinc-900 bg-zinc-950">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center">
            <Building2 className="text-zinc-950 w-4 h-4" />
          </div>
          <span className="font-semibold text-white tracking-tight">Revenue OS</span>
        </div>
        <button 
          onClick={() => setIsOpen(!isOpen)}
          className="p-2 bg-zinc-900 rounded-md text-zinc-400 hover:text-white"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar Content */}
      <aside className={`
        ${isOpen ? 'translate-x-0' : '-translate-x-full'} 
        md:translate-x-0
        fixed md:static inset-y-0 left-0 z-50
        w-64 border-r border-zinc-900 bg-zinc-950/95 md:bg-zinc-950/50 flex flex-col
        transition-transform duration-300 ease-in-out
      `}>
        <div className="h-16 hidden md:flex items-center px-6 border-b border-zinc-900">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center">
              <Building2 className="text-zinc-950 w-4 h-4" />
            </div>
            <span className="font-semibold text-white tracking-tight">Revenue OS</span>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1 mt-16 md:mt-0">
          <a href="/dashboard" onClick={() => setIsOpen(false)} className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-emerald-400 bg-emerald-400/10 rounded-lg">
            <LayoutDashboard className="w-4 h-4" /> Dashboard
          </a>
          <a href="/leads" onClick={() => setIsOpen(false)} className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors">
            <Inbox className="w-4 h-4" /> Lead Inbox
          </a>
          <a href="/crm" onClick={() => setIsOpen(false)} className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors">
            <Users className="w-4 h-4" /> CRM View
          </a>
        </nav>

        <div className="p-4 border-t border-zinc-900">
          <a href="/settings" onClick={() => setIsOpen(false)} className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors">
            <Settings className="w-4 h-4" /> Settings
          </a>
          <form action={logoutClient}>
            <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors mt-1">
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
