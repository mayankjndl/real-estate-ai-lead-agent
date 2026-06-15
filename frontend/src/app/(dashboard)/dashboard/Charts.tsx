'use client'

import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, 
  AreaChart, Area, PieChart, Pie, Legend, RadialBarChart, RadialBar, PolarAngleAxis
} from 'recharts'

const THEME = {
  emerald: '#10b981',
  blue: '#3b82f6',
  purple: '#8b5cf6',
  orange: '#f97316',
  rose: '#f43f5e',
  zinc400: '#a1a1aa',
  zinc800: '#27272a',
  zinc900: '#18181b',
  text: '#ffffff'
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-xl shadow-2xl backdrop-blur-md">
        <p className="text-zinc-300 text-xs font-medium mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm font-bold" style={{ color: entry.color || entry.fill }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
}

export function AreaTrendChart({ data }: { data: any[] }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={THEME.emerald} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={THEME.emerald} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={THEME.zinc800} vertical={false} />
          <XAxis dataKey="date" stroke={THEME.zinc400} fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke={THEME.zinc400} fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: THEME.zinc800, strokeWidth: 2 }} />
          <Area type="monotone" dataKey="leads" stroke={THEME.emerald} strokeWidth={3} fillOpacity={1} fill="url(#colorLeads)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function SourcePieChart({ data }: { data: any[] }) {
  const COLORS = [THEME.blue, THEME.purple, THEME.emerald, THEME.orange, THEME.rose]
  
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={5}
            dataKey="value"
            stroke="none"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '12px', color: THEME.zinc400 }} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export function FunnelChart({ data }: { data: any[] }) {
  const COLORS = [THEME.emerald, THEME.blue, THEME.purple, THEME.orange]
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 30, left: 40, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={THEME.zinc800} horizontal={false} />
          <XAxis type="number" stroke={THEME.zinc400} fontSize={12} tickLine={false} axisLine={false} />
          <YAxis dataKey="name" type="category" stroke={THEME.zinc400} fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: THEME.zinc800, opacity: 0.4 }} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={24}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function AgentPerformanceChart({ data }: { data: any[] }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={THEME.zinc800} vertical={false} />
          <XAxis dataKey="name" stroke={THEME.zinc400} fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke={THEME.zinc400} fontSize={12} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: THEME.zinc800, opacity: 0.4 }} />
          <Bar dataKey="score" fill={THEME.purple} radius={[4, 4, 0, 0]} barSize={30} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function FollowUpGauge({ percentage }: { percentage: number }) {
  const data = [{ name: 'Follow-up Success', value: percentage, fill: THEME.emerald }]
  return (
    <div className="h-48 w-full flex items-center justify-center relative">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart 
          cx="50%" cy="60%" 
          innerRadius="70%" outerRadius="100%" 
          barSize={15} data={data} 
          startAngle={180} endAngle={0}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar background={{ fill: THEME.zinc800 }} dataKey="value" cornerRadius={10} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-8 pointer-events-none">
        <span className="text-3xl font-bold text-white">{percentage}%</span>
        <span className="text-xs text-zinc-400 uppercase tracking-wider mt-1">Success Rate</span>
      </div>
    </div>
  )
}
