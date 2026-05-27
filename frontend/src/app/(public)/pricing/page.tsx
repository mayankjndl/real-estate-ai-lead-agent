'use client'
import { useState } from 'react'
import { Building2, Check } from 'lucide-react'

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(true)

  return (
    <div className="min-h-screen bg-zinc-950 text-white selection:bg-emerald-500/30 pb-24 font-sans">
      <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-900">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <a href="/" className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Building2 className="text-zinc-950 w-4 h-4" />
            </div>
            <span className="font-semibold tracking-tight text-lg">Revenue OS</span>
          </a>
          <div className="flex items-center gap-4">
            <a href="/features" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">Features</a>
            <a href="/login" className="text-sm font-medium bg-white text-zinc-950 px-4 py-2 rounded-full hover:bg-zinc-200 transition-colors hidden sm:block">Dashboard</a>
          </div>
        </div>
      </nav>

      <header className="pt-40 pb-12 px-6 max-w-7xl mx-auto text-center">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent">
          Simple, transparent pricing.
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto font-light mb-10">
          Choose the plan that fits your volume. No hidden fees.
        </p>

        <div className="inline-flex items-center p-1 bg-zinc-900 border border-zinc-800 rounded-full">
          <button 
            onClick={() => setIsAnnual(false)}
            className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all ${!isAnnual ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400 hover:text-white'}`}
          >
            Monthly
          </button>
          <button 
            onClick={() => setIsAnnual(true)}
            className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all ${isAnnual ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400 hover:text-white'}`}
          >
            Annually <span className="text-emerald-400 ml-1">-20%</span>
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          
          <div className="bg-zinc-900/30 border border-zinc-800 rounded-3xl p-8 backdrop-blur-xl flex flex-col">
            <h3 className="text-xl font-medium text-white mb-2">Starter</h3>
            <p className="text-zinc-400 text-sm mb-6">Perfect for small agencies and boutique developers.</p>
            <div className="mb-6 flex items-baseline gap-1">
              <span className="text-4xl font-bold text-white">${isAnnual ? '299' : '349'}</span>
              <span className="text-zinc-500 text-sm">/mo</span>
            </div>
            <a href="/login" className="w-full py-3 px-4 rounded-full border border-zinc-700 text-white text-center font-medium hover:bg-zinc-800 transition-colors mb-8">
              Start Free Trial
            </a>
            <div className="space-y-4 flex-1">
              {['Up to 500 leads/mo', 'Basic AI Qualification', 'Email Support', '1 Seat'].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span className="text-sm text-zinc-300">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gradient-to-b from-zinc-900 to-zinc-950 border border-emerald-500/30 rounded-3xl p-8 backdrop-blur-xl flex flex-col relative transform md:-translate-y-4 shadow-2xl shadow-emerald-500/10">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-emerald-400 text-zinc-950 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              Most Popular
            </div>
            <h3 className="text-xl font-medium text-white mb-2">Professional</h3>
            <p className="text-zinc-400 text-sm mb-6">For high-volume builders managing multiple sites.</p>
            <div className="mb-6 flex items-baseline gap-1">
              <span className="text-4xl font-bold text-white">${isAnnual ? '799' : '899'}</span>
              <span className="text-zinc-500 text-sm">/mo</span>
            </div>
            <a href="/login" className="w-full py-3 px-4 rounded-full bg-white text-zinc-950 text-center font-medium hover:bg-zinc-200 transition-colors mb-8">
              Start Free Trial
            </a>
            <div className="space-y-4 flex-1">
              {['Up to 5,000 leads/mo', 'Advanced NLP Scoring', 'Kanban CRM Sync', 'Priority Support', '5 Seats'].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span className="text-sm text-zinc-300">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-zinc-900/30 border border-zinc-800 rounded-3xl p-8 backdrop-blur-xl flex flex-col">
            <h3 className="text-xl font-medium text-white mb-2">Enterprise</h3>
            <p className="text-zinc-400 text-sm mb-6">Custom limits and tailored integrations for top-tier firms.</p>
            <div className="mb-6 flex items-baseline gap-1">
              <span className="text-4xl font-bold text-white">Custom</span>
            </div>
            <a href="/contact" className="w-full py-3 px-4 rounded-full border border-zinc-700 text-white text-center font-medium hover:bg-zinc-800 transition-colors mb-8">
              Contact Sales
            </a>
            <div className="space-y-4 flex-1">
              {['Unlimited leads', 'Custom AI Models', 'Dedicated Account Manager', 'Custom API Integrations', 'Unlimited Seats'].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span className="text-sm text-zinc-300">{feature}</span>
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
