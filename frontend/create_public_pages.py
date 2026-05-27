import os

base_dir = "src/app/(public)"

home_page = """import { ArrowRight, Bot, Target, Zap, Building2, Smartphone, BarChart3, ChevronRight } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white selection:bg-emerald-500/30 font-sans">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-900">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Building2 className="text-zinc-950 w-4 h-4" />
            </div>
            <span className="font-semibold tracking-tight text-lg">Revenue OS</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
            <a href="/features" className="hover:text-white transition-colors">Features</a>
            <a href="/pricing" className="hover:text-white transition-colors">Pricing</a>
            <a href="/contact" className="hover:text-white transition-colors">Contact</a>
          </div>
          <div className="flex items-center gap-4">
            <a href="/login" className="text-sm font-medium text-zinc-300 hover:text-white transition-colors hidden md:block">Sign in</a>
            <a href="/login" className="text-sm font-medium bg-white text-zinc-950 px-4 py-2 rounded-full hover:bg-zinc-200 transition-colors">Go to Dashboard</a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="pt-40 pb-20 px-6 max-w-7xl mx-auto flex flex-col items-center text-center relative">
        <div className="absolute inset-0 z-[-1] bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(52,211,153,0.15),transparent_100%)]"></div>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-400/10 text-emerald-400 text-xs font-medium mb-8 border border-emerald-400/20">
          <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Revenue OS 2.0 is now live
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tighter mb-8 bg-gradient-to-br from-white via-zinc-200 to-zinc-500 bg-clip-text text-transparent max-w-5xl leading-tight">
          The autonomous lead engine <br className="hidden md:block"/> for modern real estate.
        </h1>
        
        <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mb-12 leading-relaxed font-light">
          Stop losing prospects to slow follow-ups. Our AI qualifies leads instantly via WhatsApp, scores them, and routes them to your CRM while you sleep.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
          <a href="/login" className="w-full sm:w-auto px-8 py-4 bg-white text-zinc-950 rounded-full font-medium flex items-center justify-center hover:bg-zinc-200 transition-all hover:scale-[1.02] active:scale-[0.98] group">
            Start free trial
            <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </a>
          <a href="/demo" className="w-full sm:w-auto px-8 py-4 bg-zinc-900/50 backdrop-blur-md border border-zinc-800 text-white rounded-full font-medium flex items-center justify-center hover:bg-zinc-800 transition-all hover:scale-[1.02] active:scale-[0.98]">
            View Live Demo
          </a>
        </div>
      </main>

      {/* How it Works Section */}
      <section className="py-24 px-6 relative border-t border-zinc-900 bg-zinc-950/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-white mb-4">How it works</h2>
            <p className="text-zinc-400 text-lg max-w-2xl mx-auto font-light">Three simple steps to putting your real estate sales on autopilot.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="bg-zinc-900/40 p-8 rounded-3xl border border-zinc-800/80 backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                <Smartphone className="w-32 h-32 text-emerald-400" />
              </div>
              <div className="h-12 w-12 rounded-2xl bg-zinc-800 flex items-center justify-center mb-6 border border-zinc-700">
                <span className="text-xl font-bold text-emerald-400">1</span>
              </div>
              <h3 className="text-xl font-medium text-white mb-3">Instant Capture</h3>
              <p className="text-zinc-400 leading-relaxed text-sm">Leads flow in from Magicbricks, Facebook, or your website. Our system captures them instantly with zero latency.</p>
            </div>

            {/* Step 2 */}
            <div className="bg-zinc-900/40 p-8 rounded-3xl border border-zinc-800/80 backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                <Bot className="w-32 h-32 text-emerald-400" />
              </div>
              <div className="h-12 w-12 rounded-2xl bg-zinc-800 flex items-center justify-center mb-6 border border-zinc-700">
                <span className="text-xl font-bold text-emerald-400">2</span>
              </div>
              <h3 className="text-xl font-medium text-white mb-3">AI Qualification</h3>
              <p className="text-zinc-400 leading-relaxed text-sm">Our conversational AI engages via WhatsApp, asking budget, intent, and timeframe questions to score the lead.</p>
            </div>

            {/* Step 3 */}
            <div className="bg-zinc-900/40 p-8 rounded-3xl border border-zinc-800/80 backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                <Target className="w-32 h-32 text-emerald-400" />
              </div>
              <div className="h-12 w-12 rounded-2xl bg-zinc-800 flex items-center justify-center mb-6 border border-zinc-700">
                <span className="text-xl font-bold text-emerald-400">3</span>
              </div>
              <h3 className="text-xl font-medium text-white mb-3">CRM Sync & Closing</h3>
              <p className="text-zinc-400 leading-relaxed text-sm">Hot leads are pushed directly to your Kanban dashboard and assigned to human agents for the final close.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-32 px-6">
        <div className="max-w-4xl mx-auto bg-gradient-to-br from-zinc-900 to-zinc-950 p-12 rounded-[2.5rem] border border-zinc-800 text-center relative overflow-hidden shadow-2xl">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-1/2 bg-emerald-500/10 blur-[100px] rounded-full"></div>
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-6 relative z-10">Ready to scale your pipeline?</h2>
          <p className="text-zinc-400 text-lg mb-10 max-w-xl mx-auto relative z-10">Join top real estate developers who have doubled their appointment rates using autonomous AI.</p>
          <a href="/login" className="inline-flex items-center justify-center px-8 py-4 bg-white text-zinc-950 rounded-full font-medium hover:bg-zinc-200 transition-all hover:scale-[1.02] relative z-10">
            Get Started Today
          </a>
        </div>
      </section>

      {/* Background grid */}
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
"""

features_page = """import { Building2, Bot, MessageSquare, BarChart3, Fingerprint, Webhook } from 'lucide-react'

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white selection:bg-emerald-500/30 pb-24">
      <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-900">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <a href="/" className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Building2 className="text-zinc-950 w-4 h-4" />
            </div>
            <span className="font-semibold tracking-tight text-lg">Revenue OS</span>
          </a>
          <div className="flex items-center gap-4">
            <a href="/" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">Home</a>
            <a href="/pricing" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">Pricing</a>
            <a href="/login" className="text-sm font-medium bg-white text-zinc-950 px-4 py-2 rounded-full hover:bg-zinc-200 transition-colors hidden sm:block">Dashboard</a>
          </div>
        </div>
      </nav>

      <header className="pt-40 pb-16 px-6 max-w-7xl mx-auto text-center">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent">
          Powerful features for <br/> volume real estate.
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto font-light">
          Everything you need to capture, qualify, and close leads on autopilot.
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[280px]">
          
          <div className="md:col-span-2 bg-gradient-to-br from-zinc-900 to-zinc-900/50 p-8 rounded-3xl border border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group overflow-hidden relative">
            <div className="absolute right-0 bottom-0 opacity-10 transform translate-x-1/4 translate-y-1/4 group-hover:scale-110 transition-transform duration-700">
              <Bot className="w-64 h-64 text-emerald-400" />
            </div>
            <div className="h-12 w-12 rounded-2xl bg-zinc-800/80 flex items-center justify-center border border-zinc-700">
              <Fingerprint className="text-emerald-400 w-6 h-6" />
            </div>
            <div className="relative z-10">
              <h3 className="text-2xl font-semibold text-white mb-2">Predictive Lead Scoring</h3>
              <p className="text-zinc-400 max-w-md">Our NLP engine analyzes conversational intent to instantly tag leads as Hot, Warm, or Cold, saving your agents hundreds of hours.</p>
            </div>
          </div>

          <div className="bg-zinc-900/40 p-8 rounded-3xl border border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group">
            <div className="h-12 w-12 rounded-2xl bg-zinc-800/80 flex items-center justify-center border border-zinc-700">
              <MessageSquare className="text-blue-400 w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">Native WhatsApp Routing</h3>
              <p className="text-sm text-zinc-400">Powered by Twilio to ensure 100% deliverability directly to your prospect's pocket.</p>
            </div>
          </div>

          <div className="bg-zinc-900/40 p-8 rounded-3xl border border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group">
            <div className="h-12 w-12 rounded-2xl bg-zinc-800/80 flex items-center justify-center border border-zinc-700">
              <Webhook className="text-purple-400 w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">Universal Ingestion</h3>
              <p className="text-sm text-zinc-400">Connect Facebook Lead Ads, Magicbricks, 99acres, and custom web forms in seconds.</p>
            </div>
          </div>

          <div className="md:col-span-2 bg-zinc-900/40 p-8 rounded-3xl border border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group overflow-hidden relative">
            <div className="absolute right-8 top-1/2 -translate-y-1/2 hidden md:flex items-end gap-2 opacity-20 group-hover:opacity-40 transition-opacity">
               <div className="w-8 h-16 bg-emerald-400 rounded-t-lg"></div>
               <div className="w-8 h-24 bg-emerald-400 rounded-t-lg"></div>
               <div className="w-8 h-32 bg-emerald-400 rounded-t-lg"></div>
               <div className="w-8 h-48 bg-emerald-400 rounded-t-lg"></div>
            </div>
            <div className="h-12 w-12 rounded-2xl bg-zinc-800/80 flex items-center justify-center border border-zinc-700">
              <BarChart3 className="text-emerald-400 w-6 h-6" />
            </div>
            <div className="relative z-10">
              <h3 className="text-2xl font-semibold text-white mb-2">Deep ROI Analytics</h3>
              <p className="text-zinc-400 max-w-md">Track your pipeline visually. Know exactly which lead sources drive revenue and where drop-offs occur in real-time.</p>
            </div>
          </div>

        </div>
      </main>
      
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
"""

pricing_page = """'use client'
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
"""

with open(f"{base_dir}/page.tsx", "w", encoding="utf-8") as f:
    f.write(home_page)
with open(f"{base_dir}/features/page.tsx", "w", encoding="utf-8") as f:
    f.write(features_page)
with open(f"{base_dir}/pricing/page.tsx", "w", encoding="utf-8") as f:
    f.write(pricing_page)

print("Public pages created successfully.")
