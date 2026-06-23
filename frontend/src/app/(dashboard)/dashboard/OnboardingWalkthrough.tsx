'use client'

import { useState, useEffect } from 'react'
import { X, ChevronRight } from 'lucide-react'

export default function OnboardingWalkthrough() {
  const [isOpen, setIsOpen] = useState(false)
  const [step, setStep] = useState(0)

  useEffect(() => {
    // Only show once per browser
    const hasSeen = localStorage.getItem('revenue_os_onboarding')
    if (!hasSeen) {
      setIsOpen(true)
    }
  }, [])

  const handleClose = () => {
    setIsOpen(false)
    localStorage.setItem('revenue_os_onboarding', 'true')
  }

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(s => s + 1)
    } else {
      handleClose()
    }
  }

  if (!isOpen) return null

  const steps = [
    {
      title: "Welcome to Revenue OS! 🚀",
      desc: "This dashboard gives you a live executive overview of your real estate pipeline. Let's take a quick 3-step tour."
    },
    {
      title: "Actionable KPIs 📊",
      desc: "Every metric you see is clickable! Click any card (like 'Hot Leads' or 'Pipeline Value') to drill down into the exact leads making up that number."
    },
    {
      title: "Global Filtering 🔎",
      desc: "Use the top filters to instantly slice your data by Date Range, Lead Source, or assigned Agent. The entire dashboard will update in real-time."
    }
  ]

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-in fade-in duration-300">
      <div className="bg-white dark:bg-zinc-900 w-full max-w-md rounded-3xl shadow-2xl overflow-hidden border border-slate-200 dark:border-zinc-800">
        <div className="relative p-6 sm:p-8">
          <button 
            onClick={handleClose}
            className="absolute top-4 right-4 p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex gap-1.5 mb-6">
            {steps.map((_, i) => (
              <div 
                key={i} 
                className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${i <= step ? 'bg-indigo-600' : 'bg-slate-100 dark:bg-zinc-800'}`} 
              />
            ))}
          </div>

          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-3">
            {steps[step].title}
          </h2>
          <p className="text-slate-600 dark:text-zinc-400 leading-relaxed mb-8">
            {steps[step].desc}
          </p>

          <div className="flex justify-between items-center">
            <button 
              onClick={handleClose}
              className="text-sm font-medium text-slate-500 hover:text-slate-700 dark:hover:text-zinc-300 px-2"
            >
              Skip Tour
            </button>
            <button 
              onClick={handleNext}
              className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition-all shadow-md shadow-indigo-600/20 active:scale-95"
            >
              {step === steps.length - 1 ? "Get Started" : "Next"}
              {step < steps.length - 1 && <ChevronRight className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
