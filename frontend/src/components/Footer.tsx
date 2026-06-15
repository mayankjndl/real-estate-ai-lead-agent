import Link from 'next/link'
import { Building2 } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="bg-slate-50 dark:bg-zinc-950 border-t border-slate-200 dark:border-zinc-900 py-12 px-6 mt-auto transition-colors duration-300">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="col-span-1 md:col-span-2">
          <Link href="/" className="flex items-center gap-3 mb-4">
            <div className="h-6 w-6 rounded-lg bg-gradient-to-tr from-emerald-500 to-cyan-500 dark:from-emerald-400 dark:to-cyan-500 flex items-center justify-center">
              <Building2 className="text-white dark:text-zinc-950 w-3 h-3" />
            </div>
            <span className="font-semibold tracking-tight text-slate-900 dark:text-white">Revenue OS</span>
          </Link>
          <p className="text-sm text-slate-500 dark:text-zinc-400 max-w-sm">
            The AI-powered lead intelligence platform built for modern real estate agencies. Capture, score, and convert leads autonomously.
          </p>
        </div>
        
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-white mb-4">Product</h4>
          <ul className="space-y-2 text-sm text-slate-500 dark:text-zinc-400">
            <li><Link href="/features" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Features</Link></li>
            <li><Link href="/pricing" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Pricing</Link></li>
            <li><Link href="/demo" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Book a Demo</Link></li>
          </ul>
        </div>
        
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-white mb-4">Legal</h4>
          <ul className="space-y-2 text-sm text-slate-500 dark:text-zinc-400">
            <li><Link href="/privacy" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Privacy Policy</Link></li>
            <li><Link href="/terms" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Terms of Service</Link></li>
            <li><Link href="/contact" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Contact Us</Link></li>
          </ul>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto mt-12 pt-8 border-t border-slate-200 dark:border-zinc-900 flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-sm text-slate-500 dark:text-zinc-500">
          &copy; {new Date().getFullYear()} Imperion Data Systems Private Limited. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
