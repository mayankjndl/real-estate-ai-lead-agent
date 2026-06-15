import { ArrowRight, Bot, Target, Zap, Building2, Smartphone, BarChart3, ChevronRight } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-white selection:bg-emerald-500/30 font-sans">


      {/* Hero Section */}
      <main className="pt-32 pb-20 px-6 max-w-7xl mx-auto flex flex-col items-center text-center relative">
        <div className="absolute inset-0 z-[-1] bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(52,211,153,0.15),transparent_100%)]"></div>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 dark:bg-emerald-400/10 text-emerald-600 dark:text-emerald-400 text-xs font-medium mb-8 border border-emerald-500/20 dark:border-emerald-400/20 shadow-[0_0_15px_rgba(52,211,153,0.1)] transition-transform hover:scale-105 duration-300 cursor-default">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse"></span>
          Revenue OS 2.0 is now live
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tighter mb-8 bg-gradient-to-br from-slate-900 via-slate-700 to-slate-500 dark:from-white dark:via-zinc-200 dark:to-zinc-500 bg-clip-text text-transparent max-w-5xl leading-tight animate-in fade-in slide-in-from-bottom-4 duration-1000">
          The autonomous lead engine <br className="hidden md:block"/> for modern real estate.
        </h1>
        
        <p className="text-lg md:text-xl text-slate-600 dark:text-zinc-400 max-w-2xl mb-12 leading-relaxed font-light animate-in fade-in slide-in-from-bottom-6 duration-1000 delay-150">
          Stop losing prospects to slow follow-ups. Our AI qualifies leads instantly via WhatsApp, scores them, and routes them to your CRM while you sleep.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
          <a href="/login" className="w-full sm:w-auto px-8 py-4 bg-slate-900 text-white dark:bg-white dark:text-zinc-950 rounded-full font-medium flex items-center justify-center hover:bg-slate-800 dark:hover:bg-zinc-200 transition-all hover:scale-[1.02] active:scale-[0.98] group shadow-xl dark:shadow-[0_0_30px_rgba(255,255,255,0.2)]">
            Start free trial
            <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </a>
          <a href="/demo" className="w-full sm:w-auto px-8 py-4 bg-white/50 dark:bg-zinc-900/50 backdrop-blur-md border border-slate-200 dark:border-zinc-800 text-slate-700 dark:text-white rounded-full font-medium flex items-center justify-center hover:bg-slate-100 dark:hover:bg-zinc-800 transition-all hover:scale-[1.02] active:scale-[0.98]">
            View Live Demo
          </a>
        </div>
      </main>

      {/* Trusted By Banner */}
      <section className="border-y border-slate-200 dark:border-zinc-900 bg-white/50 dark:bg-zinc-950/50 py-10 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-sm font-medium text-slate-500 dark:text-zinc-500 mb-6 uppercase tracking-widest">Trusted by leading developers globally</p>
          <div className="flex flex-wrap justify-center gap-8 md:gap-16 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
            {['Acme Corp', 'Global Estates', 'Stellar Homes', 'Apex Properties', 'Vanguard Realty'].map((brand) => (
              <span key={brand} className="text-xl font-bold text-slate-400 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition-colors cursor-default">{brand}</span>
            ))}
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section className="py-24 px-6 relative border-t border-slate-200 dark:border-zinc-900 bg-white/50 dark:bg-zinc-950/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 dark:text-white mb-4">How it works</h2>
            <p className="text-slate-500 dark:text-zinc-400 text-lg max-w-2xl mx-auto font-light">Three simple steps to putting your real estate sales on autopilot.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="bg-white/80 dark:bg-zinc-900/40 p-8 rounded-3xl border border-slate-200 dark:border-zinc-800/80 backdrop-blur-sm relative overflow-hidden group shadow-lg dark:shadow-none">
              <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                <Smartphone className="w-32 h-32 text-emerald-500 dark:text-emerald-400" />
              </div>
              <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-zinc-800 flex items-center justify-center mb-6 border border-slate-200 dark:border-zinc-700">
                <span className="text-xl font-bold text-emerald-600 dark:text-emerald-400">1</span>
              </div>
              <h3 className="text-xl font-medium text-slate-900 dark:text-white mb-3">Instant Capture</h3>
              <p className="text-slate-600 dark:text-zinc-400 leading-relaxed text-sm">Leads flow in from Magicbricks, Facebook, or your website. Our system captures them instantly with zero latency.</p>
            </div>

            {/* Step 2 */}
            <div className="bg-white/80 dark:bg-zinc-900/40 p-8 rounded-3xl border border-slate-200 dark:border-zinc-800/80 backdrop-blur-sm relative overflow-hidden group shadow-lg dark:shadow-none">
              <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                <Bot className="w-32 h-32 text-emerald-500 dark:text-emerald-400" />
              </div>
              <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-zinc-800 flex items-center justify-center mb-6 border border-slate-200 dark:border-zinc-700">
                <span className="text-xl font-bold text-emerald-600 dark:text-emerald-400">2</span>
              </div>
              <h3 className="text-xl font-medium text-slate-900 dark:text-white mb-3">AI Qualification</h3>
              <p className="text-slate-600 dark:text-zinc-400 leading-relaxed text-sm">Our conversational AI engages via WhatsApp, asking budget, intent, and timeframe questions to score the lead.</p>
            </div>

            {/* Step 3 */}
            <div className="bg-white/80 dark:bg-zinc-900/40 p-8 rounded-3xl border border-slate-200 dark:border-zinc-800/80 backdrop-blur-sm relative overflow-hidden group shadow-lg dark:shadow-none">
              <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                <Target className="w-32 h-32 text-emerald-500 dark:text-emerald-400" />
              </div>
              <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-zinc-800 flex items-center justify-center mb-6 border border-slate-200 dark:border-zinc-700">
                <span className="text-xl font-bold text-emerald-600 dark:text-emerald-400">3</span>
              </div>
              <h3 className="text-xl font-medium text-slate-900 dark:text-white mb-3">CRM Sync & Closing</h3>
              <p className="text-slate-600 dark:text-zinc-400 leading-relaxed text-sm">Hot leads are pushed directly to your Kanban dashboard and assigned to human agents for the final close.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-32 px-6">
        <div className="max-w-4xl mx-auto bg-gradient-to-br from-slate-100 to-white dark:from-zinc-900 dark:to-zinc-950 p-12 rounded-[2.5rem] border border-slate-200 dark:border-zinc-800 text-center relative overflow-hidden shadow-2xl">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-1/2 bg-emerald-500/10 blur-[100px] rounded-full"></div>
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white mb-6 relative z-10">Ready to scale your pipeline?</h2>
          <p className="text-slate-600 dark:text-zinc-400 text-lg mb-10 max-w-xl mx-auto relative z-10">Join top real estate developers who have doubled their appointment rates using autonomous AI.</p>
          <a href="/login" className="inline-flex items-center justify-center px-8 py-4 bg-slate-900 text-white dark:bg-white dark:text-zinc-950 rounded-full font-medium hover:bg-slate-800 dark:hover:bg-zinc-200 transition-all hover:scale-[1.02] relative z-10 shadow-lg">
            Get Started Today
          </a>
        </div>
      </section>

      {/* Background grid */}
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#0f172a0a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a0a_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
