'use client'

import * as React from 'react'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  
  // Animation state
  const [isAnimating, setIsAnimating] = React.useState(false)
  const [rippleStyle, setRippleStyle] = React.useState<React.CSSProperties>({})

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const handleToggle = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (isAnimating) return;

    const newTheme = theme === 'dark' ? 'light' : 'dark';
    const rect = e.currentTarget.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    // The color of the target theme background
    const bg = newTheme === 'dark' ? '#09090b' : '#f8fafc';

    setRippleStyle({
      left: x,
      top: y,
      backgroundColor: bg,
    });
    setIsAnimating(true);

    // The wave takes about 600-700ms to cover the screen. We switch theme at 700ms.
    setTimeout(() => {
      setTheme(newTheme);
    }, 700);

    // Total animation is 1.4s, cleanup after it finishes
    setTimeout(() => {
      setIsAnimating(false);
    }, 1400);
  }

  if (!mounted) {
    return <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-zinc-800 animate-pulse" />
  }

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes wateryExpand {
          0% {
            transform: translate(-50%, -50%) scale(1) rotate(0deg);
            border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%;
            opacity: 1;
          }
          50% {
            transform: translate(-50%, -50%) scale(1500) rotate(180deg);
            border-radius: 60% 40% 30% 70% / 50% 60% 40% 50%;
            opacity: 1;
          }
          100% {
            transform: translate(-50%, -50%) scale(2000) rotate(360deg);
            border-radius: 50%;
            opacity: 0;
          }
        }
        .animate-watery {
          animation: wateryExpand 1.4s cubic-bezier(0.5, 0, 0.2, 1) forwards;
        }
      `}} />
      <button
        onClick={handleToggle}
        className="relative p-2.5 rounded-full text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-zinc-800/50 transition-all focus:outline-none overflow-hidden group"
        aria-label="Toggle theme"
      >
        <div className="relative z-10 flex items-center justify-center transition-transform duration-500 group-hover:rotate-12 group-active:scale-90">
          {theme === 'dark' ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </div>
      </button>

      {isAnimating && (
        <div
          className="pointer-events-none fixed z-[99999] animate-watery shadow-2xl"
          style={{
            ...rippleStyle,
            width: '2px',
            height: '2px',
          }}
        />
      )}
    </>
  )
}

