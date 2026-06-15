import { CheckCircle2 } from 'lucide-react'
import Script from 'next/script'

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white selection:bg-emerald-500/30 pb-24 font-sans relative overflow-hidden">
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-emerald-500/10 blur-[120px] rounded-full z-[-1] translate-x-1/3 -translate-y-1/3"></div>
      
      <header className="pt-24 pb-12 px-6 max-w-7xl mx-auto text-center animate-in fade-in slide-in-from-bottom-4 duration-1000">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent">
          Book a walkthrough.
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto font-light mb-8">
          See exactly how Revenue OS integrates with your workflow and scales your lead qualification autonomously.
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-6xl mx-auto items-start animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
          
          <div className="space-y-8 lg:sticky lg:top-32">
            <h2 className="text-3xl font-bold tracking-tight">Your personalized 1:1 session.</h2>
            <p className="text-zinc-400 leading-relaxed">
              Skip the generic tour. We'll show you exactly how Revenue OS integrates with your current CRM and how our AI will specifically qualify your leads based on your unique criteria.
            </p>
            <ul className="space-y-4">
              {['Live WhatsApp AI demonstration', 'CRM integration strategy', 'Custom workflow mapping', 'Pricing tailored to your volume'].map((item, i) => (
                <li key={i} className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span className="text-zinc-300">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Real Calendly Embed */}
          <div className="bg-white/5 border border-zinc-800 p-2 rounded-3xl shadow-xl backdrop-blur-md relative overflow-hidden">
            <div 
              className="calendly-inline-widget w-full rounded-2xl overflow-hidden" 
              data-url="https://calendly.com/info-imperiondatasystem/discovery-call?hide_event_type_details=1&hide_gdpr_banner=1&background_color=09090b&text_color=ffffff&primary_color=34d399" 
              style={{ minWidth: '320px', height: '700px' }}
            ></div>
            <Script type="text/javascript" src="https://assets.calendly.com/assets/external/widget.js" async />
          </div>

        </div>
      </main>
      
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
