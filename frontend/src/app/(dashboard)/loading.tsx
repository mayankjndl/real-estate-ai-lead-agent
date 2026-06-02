export default function DashboardLoading() {
  return (
    <div className="space-y-8 animate-pulse">
      <div>
        <div className="h-8 bg-zinc-800/50 rounded w-64 mb-2"></div>
        <div className="h-4 bg-zinc-800/50 rounded w-96"></div>
      </div>
      
      <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-xl p-6">
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-6">
              <div className="h-12 bg-zinc-800/50 rounded flex-1"></div>
              <div className="h-12 bg-zinc-800/50 rounded flex-1 hidden sm:block"></div>
              <div className="h-12 bg-zinc-800/50 rounded flex-1 hidden md:block"></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
