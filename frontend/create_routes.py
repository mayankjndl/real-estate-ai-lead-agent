import os

# Define the base directory
base_dir = "src/app"

# Ensure directories exist
directories = [
    f"{base_dir}/(public)/login",
    f"{base_dir}/(public)/features",
    f"{base_dir}/(public)/pricing",
    f"{base_dir}/(public)/demo",
    f"{base_dir}/(public)/contact",
    f"{base_dir}/(dashboard)/dashboard",
    f"{base_dir}/(dashboard)/leads",
    f"{base_dir}/(dashboard)/crm",
    f"{base_dir}/(dashboard)/settings",
]

for d in directories:
    os.makedirs(d, exist_ok=True)

# 1. Login Page
login_code = """'use client'

import { useActionState } from 'react'
import { loginClient } from '@/lib/auth'
import { Building2, ArrowRight, Lock } from 'lucide-react'

export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(loginClient, null)

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 p-4">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:14px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
      
      <div className="w-full max-w-md relative z-10">
        <div className="flex justify-center mb-8">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Building2 className="text-zinc-950 w-7 h-7" />
          </div>
        </div>
        
        <div className="bg-zinc-900/80 backdrop-blur-xl border border-zinc-800 p-8 rounded-3xl shadow-2xl">
          <h1 className="text-3xl font-semibold text-white tracking-tight mb-2">Welcome back</h1>
          <p className="text-zinc-400 text-sm mb-8">Sign in to your Revenue OS dashboard.</p>
          
          <form action={formAction} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300 uppercase tracking-wider">Email Address</label>
              <input 
                type="email" 
                name="email"
                required
                className="w-full bg-zinc-950/50 border border-zinc-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                placeholder="agent@abcproperties.com"
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <label className="text-xs font-medium text-zinc-300 uppercase tracking-wider">Password</label>
                <a href="#" className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">Forgot?</a>
              </div>
              <div className="relative">
                <input 
                  type="password" 
                  name="password"
                  required
                  className="w-full bg-zinc-950/50 border border-zinc-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                  placeholder="••••••••"
                />
                <Lock className="absolute right-4 top-3.5 w-5 h-5 text-zinc-600" />
              </div>
            </div>

            {state?.error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                <p className="text-sm text-red-400 text-center">{state.error}</p>
              </div>
            )}

            <button 
              type="submit"
              disabled={isPending}
              className="w-full bg-white text-zinc-950 font-medium py-3 px-4 rounded-xl hover:bg-zinc-200 transition-all flex items-center justify-center group disabled:opacity-70"
            >
              {isPending ? 'Signing in...' : 'Sign In'}
              {!isPending && <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />}
            </button>
          </form>
        </div>
        
        <p className="text-center text-zinc-500 text-sm mt-8">
          Don't have an account? <a href="/contact" className="text-white hover:underline">Request access</a>
        </p>
      </div>
    </div>
  )
}
"""
with open(f"{base_dir}/(public)/login/page.tsx", "w", encoding="utf-8") as f:
    f.write(login_code)


# 2. Public Pages Stub
public_pages = ["features", "pricing", "demo", "contact"]
for page in public_pages:
    code = f"""export default function {page.capitalize()}Page() {{
  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-white">
      <h1 className="text-4xl font-bold tracking-tight">{page.capitalize()}</h1>
    </div>
  )
}}
"""
    with open(f"{base_dir}/(public)/{page}/page.tsx", "w", encoding="utf-8") as f:
        f.write(code)

# 3. Dashboard Layout
layout_code = """import { Building2, LayoutDashboard, Inbox, Users, Settings, LogOut } from 'lucide-react'
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
"""
with open(f"{base_dir}/(dashboard)/layout.tsx", "w", encoding="utf-8") as f:
    f.write(layout_code)

# 4. Dashboard Pages Stub
dashboard_pages = ["dashboard", "leads", "crm", "settings"]
for page in dashboard_pages:
    code = f"""export default function {page.capitalize()}Page() {{
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold text-white tracking-tight">{page.capitalize()}</h1>
      <div className="h-96 rounded-2xl border border-zinc-800 bg-zinc-900/50 flex items-center justify-center border-dashed">
        <p className="text-zinc-500">Content for {page} will go here.</p>
      </div>
    </div>
  )
}}
"""
    with open(f"{base_dir}/(dashboard)/{page}/page.tsx", "w", encoding="utf-8") as f:
        f.write(code)

print("Generated boilerplate routes successfully.")
