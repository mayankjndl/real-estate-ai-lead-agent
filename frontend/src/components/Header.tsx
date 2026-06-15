'use client'
import { useState, useEffect } from 'react'
import { Building2, Menu, X } from 'lucide-react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { ThemeToggle } from './ThemeToggle'

export default function Header() {
  const pathname = usePathname()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [pathname])

  const links = [
    { name: 'Features', href: '/features' },
    { name: 'Pricing', href: '/pricing' },
    { name: 'Demo', href: '/demo' },
    { name: 'Contact', href: '/contact' },
  ]

  return (
    <nav className="fixed top-0 w-full z-50 bg-white/90 dark:bg-zinc-950/80 backdrop-blur-xl border-b border-slate-200 dark:border-zinc-900 transition-all duration-300 shadow-sm dark:shadow-none">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 dark:from-emerald-400 dark:to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:shadow-emerald-500/40 transition-shadow duration-300">
            <Building2 className="text-white dark:text-zinc-950 w-4 h-4" />
          </div>
          <span className="font-semibold tracking-tight text-lg text-slate-900 dark:text-white">Revenue OS</span>
        </Link>
        
        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => {
            const isActive = pathname === link.href
            return (
              <Link 
                key={link.name} 
                href={link.href} 
                className={`text-sm font-medium transition-colors relative ${isActive ? 'text-emerald-600 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white'}`}
              >
                {link.name}
                {isActive && (
                  <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-emerald-500 dark:bg-emerald-400" />
                )}
              </Link>
            )
          })}
        </div>
        
        <div className="hidden md:flex items-center gap-4">
          <ThemeToggle />
          <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-zinc-300 dark:hover:text-white transition-colors">
            Sign in
          </Link>
          <Link href="/dashboard" className="text-sm font-medium bg-emerald-600 text-white dark:bg-white dark:text-zinc-950 px-5 py-2 rounded-full hover:bg-emerald-700 dark:hover:bg-zinc-200 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-emerald-600/20 dark:shadow-[0_0_20px_rgba(255,255,255,0.1)]">
            Dashboard
          </Link>
        </div>

        {/* Mobile Menu Toggle Button */}
        <div className="md:hidden flex items-center gap-2">
          <ThemeToggle />
          <button 
            className="p-2 text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Dropdown */}
      <div className={`md:hidden absolute w-full bg-white dark:bg-zinc-950/95 backdrop-blur-xl border-b border-slate-200 dark:border-zinc-900 transition-all duration-300 overflow-hidden shadow-lg dark:shadow-none ${isMobileMenuOpen ? 'max-h-[400px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-6 py-4 flex flex-col gap-4">
          {links.map((link) => {
            const isActive = pathname === link.href
            return (
              <Link 
                key={link.name} 
                href={link.href} 
                className={`text-base font-medium py-2 transition-colors ${isActive ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-600 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white'}`}
              >
                {link.name}
              </Link>
            )
          })}
          <div className="h-px w-full bg-slate-200 dark:bg-zinc-800 my-2"></div>
          <Link href="/login" className="text-base font-medium text-slate-600 hover:text-slate-900 dark:text-zinc-300 dark:hover:text-white py-2">
            Sign in
          </Link>
          <Link href="/dashboard" className="text-base font-medium bg-emerald-600 text-white dark:bg-white dark:text-zinc-950 px-5 py-3 rounded-xl text-center hover:bg-emerald-700 dark:hover:bg-zinc-200 transition-colors mt-2 shadow-lg shadow-emerald-600/20">
            Dashboard
          </Link>
        </div>
      </div>
    </nav>
  )
}
