'use client'
import { Building2 } from 'lucide-react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'

export default function Header() {
  const pathname = usePathname()

  const links = [
    { name: 'Features', href: '/features' },
    { name: 'Pricing', href: '/pricing' },
    { name: 'Demo', href: '/demo' },
    { name: 'Contact', href: '/contact' },
  ]

  return (
    <nav className="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-900 transition-all duration-300">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-emerald-400 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:shadow-emerald-500/40 transition-shadow duration-300">
            <Building2 className="text-zinc-950 w-4 h-4" />
          </div>
          <span className="font-semibold tracking-tight text-lg text-white">Revenue OS</span>
        </Link>
        
        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => {
            const isActive = pathname === link.href
            return (
              <Link 
                key={link.name} 
                href={link.href} 
                className={`text-sm font-medium transition-colors relative ${isActive ? 'text-white' : 'text-zinc-400 hover:text-white'}`}
              >
                {link.name}
                {isActive && (
                  <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-emerald-400" />
                )}
              </Link>
            )
          })}
        </div>
        
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm font-medium text-zinc-300 hover:text-white transition-colors hidden sm:block">
            Sign in
          </Link>
          <Link href="/dashboard" className="text-sm font-medium bg-white text-zinc-950 px-5 py-2 rounded-full hover:bg-zinc-200 transition-all hover:scale-105 active:scale-95 shadow-[0_0_20px_rgba(255,255,255,0.1)]">
            Dashboard
          </Link>
        </div>
      </div>
    </nav>
  )
}
