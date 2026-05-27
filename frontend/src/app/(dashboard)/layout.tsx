import { Building2, LayoutDashboard, Inbox, Users, Settings, LogOut } from 'lucide-react'
import { logoutClient } from '@/lib/auth'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-zinc-950 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-900 bg-zinc-950/50 flex flex-col hidden md:flex">
        <div className="h-16 flex items-center px-6 border-b border-zinc-900">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center">
              <Building2 className="text-zinc-950 w-4 h-4" />
            </div>
            <span className="font-semibold text-white tracking-tight">Revenue OS</span>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          <a href="/dashboard" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-emerald-400 bg-emerald-400/10 rounded-lg">
            <LayoutDashboard className="w-4 h-4" /> Dashboard
          </a>
          <a href="/leads" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors">
            <Inbox className="w-4 h-4" /> Lead Inbox
          </a>
          <a href="/crm" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors">
            <Users className="w-4 h-4" /> CRM View
          </a>
        </nav>

        <div className="p-4 border-t border-zinc-900">
          <a href="/settings" className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors">
            <Settings className="w-4 h-4" /> Settings
          </a>
          <form action={logoutClient}>
            <button className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-zinc-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors mt-1">
              <LogOut className="w-4 h-4" /> Sign Out
            </button>
          </form>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 bg-zinc-950">
        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
