import { Building2, Bot, MessageSquare, BarChart3, Fingerprint, Webhook } from 'lucide-react'

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-white selection:bg-emerald-500/30 pb-24">


      <header className="pt-24 pb-16 px-6 max-w-7xl mx-auto text-center animate-in fade-in slide-in-from-bottom-4 duration-1000">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-slate-900 to-slate-500 dark:from-white dark:to-zinc-500 bg-clip-text text-transparent">
          Powerful features for <br/> volume real estate.
        </h1>
        <p className="text-lg text-slate-600 dark:text-zinc-400 max-w-2xl mx-auto font-light">
          Everything you need to capture, qualify, and close leads on autopilot.
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[280px] animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-150">
          
          <div className="md:col-span-2 bg-gradient-to-br from-white to-slate-50 dark:from-zinc-900 dark:to-zinc-900/50 p-8 rounded-3xl border border-slate-200 dark:border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group overflow-hidden relative hover:border-slate-300 dark:hover:border-zinc-700 transition-all duration-500 hover:-translate-y-1 hover:shadow-xl shadow-sm dark:shadow-none">
            <div className="absolute right-0 bottom-0 opacity-10 transform translate-x-1/4 translate-y-1/4 group-hover:scale-100 transition-transform duration-700">
              <Bot className="w-64 h-64 text-emerald-500 dark:text-emerald-400" />
            </div>
            <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-zinc-800/80 flex items-center justify-center border border-slate-200 dark:border-zinc-700 shadow-inner">
              <Fingerprint className="text-emerald-600 dark:text-emerald-400 w-6 h-6" />
            </div>
            <div className="relative z-10">
              <h3 className="text-2xl font-semibold text-slate-900 dark:text-white mb-2 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors duration-300">Predictive Lead Scoring</h3>
              <p className="text-slate-600 dark:text-zinc-400 max-w-md">Our NLP engine analyzes conversational intent to instantly tag leads as Hot, Warm, or Cold, saving your agents hundreds of hours.</p>
            </div>
          </div>

          <div className="bg-white/80 dark:bg-zinc-900/40 p-8 rounded-3xl border border-slate-200 dark:border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group hover:border-slate-300 dark:hover:border-zinc-700 transition-all duration-500 hover:-translate-y-1 hover:shadow-xl shadow-sm dark:shadow-none">
            <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-zinc-800/80 flex items-center justify-center border border-slate-200 dark:border-zinc-700 shadow-inner group-hover:rotate-6 transition-transform duration-300">
              <MessageSquare className="text-blue-600 dark:text-blue-400 w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-300">Native WhatsApp</h3>
              <p className="text-sm text-slate-600 dark:text-zinc-400">Powered by Twilio to ensure 100% deliverability directly to your prospect's pocket.</p>
            </div>
          </div>

          <div className="bg-white/80 dark:bg-zinc-900/40 p-8 rounded-3xl border border-slate-200 dark:border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group hover:border-slate-300 dark:hover:border-zinc-700 transition-all duration-500 hover:-translate-y-1 hover:shadow-xl shadow-sm dark:shadow-none">
            <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-zinc-800/80 flex items-center justify-center border border-slate-200 dark:border-zinc-700 shadow-inner group-hover:-rotate-6 transition-transform duration-300">
              <Webhook className="text-purple-600 dark:text-purple-400 w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors duration-300">Universal Ingestion</h3>
              <p className="text-sm text-slate-600 dark:text-zinc-400">Connect Facebook Lead Ads, Magicbricks, 99acres, and custom web forms in seconds.</p>
            </div>
          </div>

          <div className="md:col-span-2 bg-white/80 dark:bg-zinc-900/40 p-8 rounded-3xl border border-slate-200 dark:border-zinc-800/80 backdrop-blur-xl flex flex-col justify-between group overflow-hidden relative hover:border-slate-300 dark:hover:border-zinc-700 transition-all duration-500 hover:-translate-y-1 hover:shadow-xl shadow-sm dark:shadow-none">
            <div className="absolute right-8 top-1/2 -translate-y-1/2 hidden md:flex items-end gap-2 opacity-20 group-hover:opacity-40 transition-opacity">
               <div className="w-8 h-16 bg-emerald-500 dark:bg-emerald-400 rounded-t-lg transform origin-bottom group-hover:scale-y-110 transition-transform duration-500 delay-100"></div>
               <div className="w-8 h-24 bg-emerald-500 dark:bg-emerald-400 rounded-t-lg transform origin-bottom group-hover:scale-y-110 transition-transform duration-500 delay-200"></div>
               <div className="w-8 h-32 bg-emerald-500 dark:bg-emerald-400 rounded-t-lg transform origin-bottom group-hover:scale-y-110 transition-transform duration-500 delay-300"></div>
               <div className="w-8 h-48 bg-emerald-500 dark:bg-emerald-400 rounded-t-lg transform origin-bottom group-hover:scale-y-110 transition-transform duration-500 delay-400"></div>
            </div>
            <div className="h-12 w-12 rounded-2xl bg-slate-100 dark:bg-zinc-800/80 flex items-center justify-center border border-slate-200 dark:border-zinc-700 shadow-inner">
              <BarChart3 className="text-emerald-600 dark:text-emerald-400 w-6 h-6" />
            </div>
            <div className="relative z-10">
              <h3 className="text-2xl font-semibold text-slate-900 dark:text-white mb-2 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors duration-300">Deep ROI Analytics</h3>
              <p className="text-slate-600 dark:text-zinc-400 max-w-md">Track your pipeline visually. Know exactly which lead sources drive revenue and where drop-offs occur in real-time.</p>
            </div>
          </div>

        </div>
      </main>
      
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#0f172a0a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a0a_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
