'use client'
import { useState } from 'react'
import { Building2, Check } from 'lucide-react'

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(true)

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-white selection:bg-emerald-500/30 pb-24 font-sans">


      <header className="pt-24 pb-12 px-6 max-w-7xl mx-auto text-center animate-in fade-in slide-in-from-bottom-4 duration-1000">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-slate-900 to-slate-500 dark:from-white dark:to-zinc-500 bg-clip-text text-transparent">
          Simple, transparent pricing.
        </h1>
        <p className="text-lg text-slate-600 dark:text-zinc-400 max-w-2xl mx-auto font-light mb-10">
          Choose the plan that fits your volume. No hidden fees.
        </p>

        <div className="inline-flex items-center p-1 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-full relative isolate shadow-sm">
          {/* Animated Background Pill */}
          <div className={`absolute top-1 bottom-1 w-[110px] sm:w-[120px] bg-slate-100 dark:bg-zinc-800 rounded-full -z-10 transition-transform duration-300 ease-out ${isAnnual ? 'translate-x-[100%]' : 'translate-x-0'}`} />
          
          <button 
            onClick={() => setIsAnnual(false)}
            className={`w-[110px] sm:w-[120px] px-4 py-2.5 rounded-full text-sm font-medium transition-colors duration-300 ${!isAnnual ? 'text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white'}`}
          >
            Monthly
          </button>
          <button 
            onClick={() => setIsAnnual(true)}
            className={`w-[110px] sm:w-[120px] px-4 py-2.5 rounded-full text-sm font-medium transition-colors duration-300 ${isAnnual ? 'text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white'}`}
          >
            Annually <span className="text-emerald-600 dark:text-emerald-400 ml-1 text-xs">-20%</span>
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          
          <div className="bg-white/80 dark:bg-zinc-900/30 border border-slate-200 dark:border-zinc-800 rounded-3xl p-8 backdrop-blur-xl flex flex-col hover:border-slate-300 dark:hover:border-zinc-600 transition-all duration-500 hover:scale-105 group shadow-lg dark:shadow-none">
            <h3 className="text-xl font-medium text-slate-900 dark:text-white mb-2">Starter</h3>
            <p className="text-slate-600 dark:text-zinc-400 text-sm mb-6">Perfect for small agencies and boutique developers.</p>
            <div className="mb-6 flex items-baseline gap-1 relative overflow-hidden h-12">
              <span className={`text-4xl font-bold text-slate-900 dark:text-white absolute transition-transform duration-500 ${isAnnual ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0'}`}>$299</span>
              <span className={`text-4xl font-bold text-slate-900 dark:text-white absolute transition-transform duration-500 ${!isAnnual ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0'}`}>$349</span>
              <span className="text-slate-500 dark:text-zinc-500 text-sm absolute bottom-0 left-[80px]">/mo</span>
            </div>
            <a href="/login" className="w-full py-3 px-4 rounded-full border border-slate-200 dark:border-zinc-700 text-slate-900 dark:text-white text-center font-medium hover:bg-slate-50 dark:group-hover:bg-zinc-800 transition-colors mb-8">
              Start Free Trial
            </a>
            <div className="space-y-4 flex-1">
              {['Up to 500 leads/mo', 'Basic AI Qualification', 'Email Support', '1 Seat'].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
                  <span className="text-sm text-slate-700 dark:text-zinc-300">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gradient-to-b from-slate-50 to-white dark:from-zinc-900 dark:to-zinc-950 border border-emerald-500/50 rounded-3xl p-8 backdrop-blur-xl flex flex-col relative transform md:-translate-y-4 shadow-[0_0_40px_rgba(52,211,153,0.15)] hover:shadow-[0_0_60px_rgba(52,211,153,0.25)] transition-all duration-500 hover:scale-105 group z-10">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-emerald-500 dark:bg-emerald-400 text-white dark:text-zinc-950 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow-lg">
              Most Popular
            </div>
            <h3 className="text-xl font-medium text-slate-900 dark:text-white mb-2">Professional</h3>
            <p className="text-slate-600 dark:text-zinc-400 text-sm mb-6">For high-volume builders managing multiple sites.</p>
            <div className="mb-6 flex items-baseline gap-1 relative overflow-hidden h-12">
              <span className={`text-4xl font-bold text-slate-900 dark:text-white absolute transition-transform duration-500 ${isAnnual ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0'}`}>$799</span>
              <span className={`text-4xl font-bold text-slate-900 dark:text-white absolute transition-transform duration-500 ${!isAnnual ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0'}`}>$899</span>
              <span className="text-slate-500 dark:text-zinc-500 text-sm absolute bottom-0 left-[80px]">/mo</span>
            </div>
            <a href="/login" className="w-full py-3 px-4 rounded-full bg-slate-900 text-white dark:bg-white dark:text-zinc-950 text-center font-medium hover:bg-slate-800 dark:hover:bg-zinc-200 transition-colors mb-8 shadow-lg shadow-emerald-500/10 group-hover:shadow-emerald-500/20">
              Start Free Trial
            </a>
            <div className="space-y-4 flex-1">
              {['Up to 5,000 leads/mo', 'Advanced NLP Scoring', 'Kanban CRM Sync', 'Priority Support', '5 Seats'].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
                  <span className="text-sm text-slate-700 dark:text-zinc-300">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white/80 dark:bg-zinc-900/30 border border-slate-200 dark:border-zinc-800 rounded-3xl p-8 backdrop-blur-xl flex flex-col hover:border-slate-300 dark:hover:border-zinc-600 transition-all duration-500 hover:scale-105 group shadow-lg dark:shadow-none">
            <h3 className="text-xl font-medium text-slate-900 dark:text-white mb-2">Enterprise</h3>
            <p className="text-slate-600 dark:text-zinc-400 text-sm mb-6">Custom limits and tailored integrations for top-tier firms.</p>
            <div className="mb-6 flex items-baseline gap-1 h-12 items-end">
              <span className="text-4xl font-bold text-slate-900 dark:text-white leading-none">Custom</span>
            </div>
            <a href="/contact" className="w-full py-3 px-4 rounded-full border border-slate-200 dark:border-zinc-700 text-slate-900 dark:text-white text-center font-medium hover:bg-slate-50 dark:group-hover:bg-zinc-800 transition-colors mb-8">
              Contact Sales
            </a>
            <div className="space-y-4 flex-1">
              {['Unlimited leads', 'Custom AI Models', 'Dedicated Account Manager', 'Custom API Integrations', 'Unlimited Seats'].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
                  <span className="text-sm text-slate-700 dark:text-zinc-300">{feature}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </main>
      
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
