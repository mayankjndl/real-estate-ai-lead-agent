'use client'

import { useEffect } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Optionally log the error to an error reporting service
    console.error(error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-10rem)] bg-zinc-900/20 border border-zinc-800/50 rounded-3xl p-8 text-center">
      <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-6 border border-red-500/20">
        <AlertCircle className="w-8 h-8 text-red-400" />
      </div>
      <h2 className="text-2xl font-semibold text-white mb-2">Something went wrong!</h2>
      <p className="text-zinc-400 mb-8 max-w-md">
        We encountered an error while loading your dashboard data. The connection to the database might have timed out.
      </p>
      <button
        onClick={() => reset()}
        className="flex items-center gap-2 bg-zinc-100 hover:bg-white text-zinc-900 px-6 py-2.5 rounded-full font-medium transition-colors"
      >
        <RefreshCw className="w-4 h-4" /> Try again
      </button>
    </div>
  )
}
