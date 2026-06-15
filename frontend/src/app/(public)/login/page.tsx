'use client'

import { useActionState } from 'react'
import { loginClient } from '@/lib/auth'
import { Building2, ArrowRight, Lock } from 'lucide-react'

export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(loginClient, null)

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950 p-4">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a0a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a0a_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:14px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
      
      <div className="w-full max-w-md relative z-10">
        <div className="flex justify-center mb-8">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Building2 className="text-white dark:text-zinc-950 w-7 h-7" />
          </div>
        </div>
        
        <div className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-slate-200 dark:border-zinc-800 p-8 rounded-3xl shadow-xl dark:shadow-2xl">
          <h1 className="text-3xl font-semibold text-slate-900 dark:text-white tracking-tight mb-2">Welcome back</h1>
          <p className="text-slate-500 dark:text-zinc-400 text-sm mb-8">Sign in to your Revenue OS dashboard.</p>
          
          <form action={formAction} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-500 dark:text-zinc-300 uppercase tracking-wider">Email Address</label>
              <input 
                type="email" 
                name="email"
                required
                className="w-full bg-slate-50 dark:bg-zinc-950/50 border border-slate-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                placeholder="agent@abcproperties.com"
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between">
                <label className="text-xs font-medium text-slate-500 dark:text-zinc-300 uppercase tracking-wider">Password</label>
                <a href="#" className="text-xs text-emerald-600 dark:text-emerald-400 hover:text-emerald-500 dark:hover:text-emerald-300 transition-colors">Forgot?</a>
              </div>
              <div className="relative">
                <input 
                  type="password" 
                  name="password"
                  required
                  className="w-full bg-slate-50 dark:bg-zinc-950/50 border border-slate-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                  placeholder="••••••••"
                />
                <Lock className="absolute right-4 top-3.5 w-5 h-5 text-slate-400 dark:text-zinc-600" />
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
              className="w-full bg-slate-900 text-white dark:bg-white dark:text-zinc-950 font-medium py-3 px-4 rounded-xl hover:bg-slate-800 dark:hover:bg-zinc-200 transition-all flex items-center justify-center group disabled:opacity-70 shadow-md"
            >
              {isPending ? 'Signing in...' : 'Sign In'}
              {!isPending && <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />}
            </button>
          </form>
        </div>
        
        <p className="text-center text-slate-500 dark:text-zinc-500 text-sm mt-8">
          Don't have an account? <a href="/contact" className="text-slate-900 dark:text-white hover:underline">Request access</a>
        </p>
      </div>
    </div>
  )
}
