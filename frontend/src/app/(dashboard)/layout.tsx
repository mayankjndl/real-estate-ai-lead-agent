import { Building2, LayoutDashboard, Inbox, Users, Settings, LogOut } from 'lucide-react'
import { logoutClient } from '@/lib/auth'

import Sidebar from './Sidebar'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-white flex flex-col md:flex-row transition-colors duration-300">
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50 dark:bg-zinc-950 transition-colors duration-300">
        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
