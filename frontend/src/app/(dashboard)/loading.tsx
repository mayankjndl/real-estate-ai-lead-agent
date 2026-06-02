export default function DashboardLoading() {
  return (
    <div className="space-y-8 animate-pulse">
      <div>
        <div className="h-8 bg-zinc-800 rounded w-1/4 mb-2"></div>
        <div className="h-4 bg-zinc-800/50 rounded w-1/3"></div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 bg-zinc-900/40 border border-zinc-800/80 rounded-2xl"></div>
        ))}
      </div>

      <div className="h-96 bg-zinc-900/40 border border-zinc-800/80 rounded-2xl mt-8"></div>
    </div>
  )
}
