import { Mail, MapPin, Phone, ArrowRight, Link } from 'lucide-react'

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white selection:bg-emerald-500/30 pb-24 font-sans relative">
      <div className="absolute inset-0 z-[-1] bg-[radial-gradient(ellipse_60%_60%_at_50%_-20%,rgba(52,211,153,0.1),transparent_100%)]"></div>
      
      <header className="pt-24 pb-12 px-6 max-w-7xl mx-auto text-center animate-in fade-in slide-in-from-bottom-4 duration-1000">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent">
          Get in touch.
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto font-light">
          Have questions about pricing, custom integrations, or just want to chat? We'd love to hear from you.
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-5xl mx-auto items-start">
          
          {/* Contact Info */}
          <div className="space-y-8 animate-in fade-in slide-in-from-left-8 duration-1000 delay-150">
            <div className="bg-zinc-900/30 border border-zinc-800 rounded-3xl p-8 backdrop-blur-xl">
              <h3 className="text-2xl font-semibold text-white mb-8">Contact Information</h3>
              
              <div className="space-y-6">
                <div className="flex items-center gap-4 group cursor-pointer">
                  <div className="w-12 h-12 rounded-full bg-zinc-800/80 flex items-center justify-center border border-zinc-700 group-hover:border-emerald-500/50 transition-colors">
                    <Mail className="text-emerald-400 w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm text-zinc-400 font-medium">Email us at</p>
                    <p className="text-white group-hover:text-emerald-400 transition-colors">info.imperiondatasystem@gmail.com</p>
                  </div>
                </div>

                <div className="flex items-center gap-4 group cursor-pointer">
                  <div className="w-12 h-12 rounded-full bg-zinc-800/80 flex items-center justify-center border border-zinc-700 group-hover:border-emerald-500/50 transition-colors">
                    <Phone className="text-emerald-400 w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm text-zinc-400 font-medium">Call us at</p>
                    <p className="text-white group-hover:text-emerald-400 transition-colors">+91 8308755482</p>
                  </div>
                </div>

                <a href="https://www.linkedin.com/company/imperion-data-systems/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-4 group cursor-pointer">
                  <div className="w-12 h-12 rounded-full bg-zinc-800/80 flex items-center justify-center border border-zinc-700 group-hover:border-emerald-500/50 transition-colors">
                    <Link className="text-emerald-400 w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm text-zinc-400 font-medium">Connect on</p>
                    <p className="text-white group-hover:text-emerald-400 transition-colors">LinkedIn</p>
                  </div>
                </a>
              </div>
            </div>
          </div>

          {/* Contact Form */}
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 backdrop-blur-xl shadow-2xl animate-in fade-in slide-in-from-right-8 duration-1000 delay-300">
            <form className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">First Name</label>
                  <input type="text" className="w-full bg-zinc-950/50 border border-zinc-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" placeholder="John" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Last Name</label>
                  <input type="text" className="w-full bg-zinc-950/50 border border-zinc-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" placeholder="Doe" />
                </div>
              </div>
              
              <div className="space-y-2">
                <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Work Email</label>
                <input type="email" className="w-full bg-zinc-950/50 border border-zinc-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" placeholder="john@company.com" />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Message</label>
                <textarea rows={4} className="w-full bg-zinc-950/50 border border-zinc-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all resize-none" placeholder="How can we help you?"></textarea>
              </div>

              <button type="button" className="w-full bg-white text-zinc-950 font-medium py-3 px-4 rounded-xl hover:bg-zinc-200 transition-all flex items-center justify-center group shadow-[0_0_20px_rgba(255,255,255,0.1)]">
                Send Message
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </button>
            </form>
          </div>

        </div>
      </main>
      
      <div className="fixed inset-0 z-[-2] bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:32px_32px]"></div>
    </div>
  )
}
