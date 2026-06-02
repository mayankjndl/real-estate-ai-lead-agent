import { Play, Calendar, CheckCircle2 } from 'lucide-react'

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white selection:bg-emerald-500/30 pb-24 font-sans relative overflow-hidden">
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-emerald-500/10 blur-[120px] rounded-full z-[-1] translate-x-1/3 -translate-y-1/3"></div>
      
      <header className="pt-24 pb-12 px-6 max-w-7xl mx-auto text-center animate-in fade-in slide-in-from-bottom-4 duration-1000">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent">
          See Revenue OS in action.
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto font-light mb-8">
          Watch a quick 2-minute overview or book a personalized walkthrough with our product experts.
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-6">
        {/* Video Mockup */}
        <div className="max-w-4xl mx-auto mb-20 animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-150">
          <div className="relative aspect-video bg-zinc-900 rounded-3xl border border-zinc-800 shadow-2xl overflow-hidden group cursor-pointer">
            <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-900/20 to-transparent z-10"></div>
            
            {/* Play Button Overlay */}
            <div className="absolute inset-0 flex items-center justify-center z-20">
              <div className="w-20 h-20 bg-emerald-500 rounded-full flex items-center justify-center shadow-[0_0_40px_rgba(52,211,153,0.4)] group-hover:scale-110 group-hover:bg-emerald-400 transition-all duration-300">
                <Play className="w-8 h-8 text-zinc-950 ml-1" fill="currentColor" />
              </div>
            </div>

            {/* Mock UI Background */}
            <div className="absolute inset-0 opacity-50 grayscale group-hover:grayscale-0 transition-all duration-700 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PHBhdGggZD0iTTIwIDIwTDIwIDQwTDAgNDBMMCAyMFoiIGZpbGw9IiMzMzMiIGZpbGwtb3BhY2l0eT0iMC4wNSIvPjwvc3ZnPg==')] bg-repeat z-0">
               {/* Abstract mock UI elements */}
               <div className="absolute top-8 left-8 w-64 h-8 bg-zinc-800/80 rounded-md"></div>
               <div className="absolute top-24 left-8 right-8 h-64 bg-zinc-800/50 rounded-xl"></div>
               <div className="absolute bottom-8 left-8 w-32 h-8 bg-emerald-500/20 rounded-full"></div>
            </div>
          </div>
        </div>

        {/* Booking Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-5xl mx-auto items-center animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
          <div className="space-y-8">
            <h2 className="text-3xl font-bold tracking-tight">Book a personalized 1:1 onboarding call.</h2>
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

          {/* Calendar Embed Mockup */}
          <div className="bg-white p-6 rounded-3xl shadow-xl shadow-white/5 relative overflow-hidden group">
            <div className="flex items-center justify-between mb-8 pb-4 border-b border-zinc-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-zinc-100 rounded-full flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-zinc-900" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-zinc-900">30 Minute Walkthrough</h4>
                  <p className="text-xs text-zinc-500">Revenue OS Team</p>
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-7 gap-2 text-center mb-4">
              {['Mo','Tu','We','Th','Fr','Sa','Su'].map(day => (
                <div key={day} className="text-xs font-semibold text-zinc-400">{day}</div>
              ))}
              {Array.from({length: 31}).map((_, i) => (
                <div key={i} className={`p-2 text-sm font-medium rounded-full cursor-pointer transition-colors ${i === 14 ? 'bg-emerald-500 text-white' : 'text-zinc-700 hover:bg-zinc-100'}`}>
                  {i + 1}
                </div>
              ))}
            </div>
            <button className="w-full py-3 bg-zinc-950 text-white rounded-xl font-medium hover:bg-zinc-800 transition-colors mt-4">
              View Available Times
            </button>
          </div>
        </div>

      </main>
      
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
