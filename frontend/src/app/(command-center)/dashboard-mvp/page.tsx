'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useCommandCenterStore } from '@/lib/store/useCommandCenterStore';
import { mockChartData } from '@/lib/api/mockService';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, Users, DollarSign, Activity, AlertTriangle, Info, BellRing, Bot } from 'lucide-react';
import { formatInrCr, HEURISTIC_DISCLAIMER } from '@/lib/format';

type Predictions = {
  revenue: { total_expected_revenue?: number; open_lead_count?: number } | null;
  cashflow: { expected_30pct_cashflow?: number; open_lead_count?: number } | null;
  inventory: Record<string, number> | null;
  cancellation: { length?: number } | unknown[] | null;
};

export default function ExecutiveDashboardPage() {
  const { activeProjectId } = useCommandCenterStore();

  const [kpis, setKpis] = useState({
    totalRevenue: 0,
    pipelineValue: 0,
    activeAgents: 0,
    leadVelocity: 0,
    atRisk: 0,
  });
  const [alerts, setAlerts] = useState<
    { id: string; type: string; message: string; timestamp: string }[]
  >([]);
  const [preds, setPreds] = useState<Predictions>({
    revenue: null,
    cashflow: null,
    inventory: null,
    cancellation: null,
  });
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadPredictions = useCallback(async () => {
    try {
      const [rev, cash, inv, cancel] = await Promise.all([
        fetch('/api/v1/predictions/revenue', { credentials: 'include' }).then((r) =>
          r.ok ? r.json() : null
        ),
        fetch('/api/v1/predictions/cashflow', { credentials: 'include' }).then((r) =>
          r.ok ? r.json() : null
        ),
        fetch('/api/v1/predictions/inventory', { credentials: 'include' }).then((r) =>
          r.ok ? r.json() : null
        ),
        fetch('/api/v1/predictions/cancellation-risk', { credentials: 'include' }).then((r) =>
          r.ok ? r.json() : null
        ),
      ]);
      setPreds({ revenue: rev, cashflow: cash, inventory: inv, cancellation: cancel });
      const atRisk = Array.isArray(cancel)
        ? cancel.length
        : cancel && typeof cancel === 'object' && Array.isArray((cancel as { items?: unknown[] }).items)
          ? (cancel as { items: unknown[] }).items.length
          : 0;
      setKpis((prev) => ({
        ...prev,
        totalRevenue: Number(rev?.total_expected_revenue || 0),
        pipelineValue: Number(rev?.total_expected_revenue || 0),
        leadVelocity: Number(rev?.open_lead_count || 0),
        atRisk,
      }));
      setLoadError(null);
    } catch {
      setLoadError('Failed to load predictions');
    }
  }, []);

  useEffect(() => {
    const t = window.setTimeout(() => {
      void loadPredictions();
    }, 0);

    const eventSource = new EventSource('/api/v1/events/stream', { withCredentials: true });

    eventSource.onmessage = (event) => {
      if (!event.data || String(event.data).startsWith(':')) return;
      try {
        const data = JSON.parse(event.data);
        const t = data.event_type as string;
        const pushAlert = (type: string, message: string) => {
          setAlerts((prev) =>
            [
              {
                id: data.event_id || String(Date.now()),
                type,
                message,
                timestamp: new Date().toLocaleTimeString(),
              },
              ...prev,
            ].slice(0, 5)
          );
        };

        if (t === 'lead.created') {
          setKpis((prev) => ({ ...prev, leadVelocity: prev.leadVelocity + 1 }));
          pushAlert('info', `New Lead Created (${data.entity_id})`);
        } else if (t === 'approval.requested') {
          pushAlert('warning', 'Approval Requested');
        } else if (t === 'lead.scored') {
          pushAlert('info', 'Lead Scored');
        } else if (t === 'lead.hot' || t === 'lead.escalated') {
          pushAlert('critical', `Hot lead ${data.entity_id || ''}`);
        } else if (t === 'lead.assigned') {
          pushAlert('info', 'Lead Assigned');
        } else if (t === 'site_visit.scheduled') {
          pushAlert('info', 'Site visit scheduled');
        } else if (t === 'marketing.report.generated') {
          pushAlert('info', 'Marketing Report Generated');
          loadPredictions();
        } else if (t) {
          pushAlert('info', `Event: ${t}`);
        }
      } catch {
        /* ignore */
      }
    };

    eventSource.onerror = () => {
      /* reconnect handled by browser */
    };

    return () => {
      window.clearTimeout(t);
      eventSource.close();
    };
  }, [activeProjectId, loadPredictions]);

  const inv = preds.inventory || {};
  const invAvailable = Number(inv.available || inv.Available || 0);
  const invHold = Number(inv.hold || inv.Hold || 0);
  const invSold = Number(inv.sold || inv.Sold || 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
          {HEURISTIC_DISCLAIMER}
        </span>
        {loadError && <span className="text-xs text-red-400">{loadError}</span>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#13131a] border border-gray-800/60 rounded-2xl p-5 shadow-lg">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <DollarSign className="w-5 h-5 text-blue-400" />
            </div>
            <span className="text-[10px] font-bold uppercase text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded-full">
              Heuristic
            </span>
          </div>
          <p className="text-sm text-gray-400 font-medium mb-1">Expected revenue</p>
          <h3 className="text-2xl font-bold text-white tracking-tight">
            {formatInrCr(kpis.totalRevenue)}
          </h3>
        </div>

        <div className="bg-[#13131a] border border-gray-800/60 rounded-2xl p-5 shadow-lg">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Activity className="w-5 h-5 text-purple-400" />
            </div>
            <span className="text-xs font-medium text-gray-400 bg-gray-800 px-2 py-1 rounded-full">
              Live SSE
            </span>
          </div>
          <p className="text-sm text-gray-400 font-medium mb-1">30% cashflow slice</p>
          <h3 className="text-2xl font-bold text-white tracking-tight">
            {formatInrCr(preds.cashflow?.expected_30pct_cashflow)}
          </h3>
        </div>

        <div className="bg-[#13131a] border border-gray-800/60 rounded-2xl p-5 shadow-lg">
          <div className="p-2 bg-emerald-500/10 rounded-lg w-fit mb-4">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
          </div>
          <p className="text-sm text-gray-400 font-medium mb-1">Open leads</p>
          <h3 className="text-2xl font-bold text-white tracking-tight">
            {kpis.leadVelocity}{' '}
            <span className="text-sm font-normal text-gray-500">in pipeline</span>
          </h3>
        </div>

        <div className="bg-[#13131a] border border-gray-800/60 rounded-2xl p-5 shadow-lg">
          <div className="p-2 bg-orange-500/10 rounded-lg w-fit mb-4">
            <Users className="w-5 h-5 text-orange-400" />
          </div>
          <p className="text-sm text-gray-400 font-medium mb-1">At-risk / cancel proxy</p>
          <h3 className="text-2xl font-bold text-white tracking-tight">{kpis.atRisk}</h3>
          <p className="text-xs text-gray-500 mt-2">
            Inv: {invAvailable} avail · {invHold} hold · {invSold} sold
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-[#13131a] border border-gray-800/60 rounded-2xl p-6 shadow-lg">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">Revenue trend (illustrative)</h3>
              <p className="text-sm text-gray-400 mt-1">
                Chart shape is illustrative; KPI totals come from live `/predictions/*`.
              </p>
            </div>
            <div className="text-right hidden sm:block">
              <p className="text-xs text-gray-400 uppercase font-semibold tracking-wider">
                Heuristic EOM
              </p>
              <p className="text-lg font-bold text-blue-400">{formatInrCr(kpis.totalRevenue)}</p>
            </div>
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis
                  dataKey="name"
                  stroke="#52525b"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#52525b"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `₹${(Number(value) / 1e7).toFixed(1)}Cr`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#18181b',
                    borderColor: '#27272a',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                  formatter={(value) => formatInrCr(Number(value ?? 0))}
                />
                <Area
                  type="monotone"
                  dataKey="actual"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorActual)"
                />
                <Area
                  type="monotone"
                  dataKey="forecast"
                  stroke="#8b5cf6"
                  strokeWidth={3}
                  strokeDasharray="5 5"
                  fillOpacity={1}
                  fill="url(#colorForecast)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-gradient-to-b from-[#1a1a2e] to-[#13131a] border border-blue-900/30 rounded-2xl p-6 shadow-lg flex flex-col">
          <div className="flex items-center gap-2 mb-6">
            <Bot className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">Forecast notes</h3>
          </div>
          <div className="space-y-4 flex-1 text-sm text-blue-100/90">
            <p className="p-4 rounded-xl bg-blue-950/20 border border-blue-900/40 leading-relaxed">
              Totals are heuristic expected revenue from open-lead budgets × conversion
              probability — not a trained ML model.
            </p>
            <p className="p-4 rounded-xl bg-blue-950/20 border border-blue-900/40 leading-relaxed">
              Cashflow card uses the 30% expected cashflow slice from the same engine.
            </p>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BellRing className="w-5 h-5 text-gray-400" />
          Attention Required
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {alerts.length === 0 && (
            <p className="text-sm text-gray-500 col-span-3">Waiting for live bus events…</p>
          )}
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 rounded-xl border flex items-start gap-3 ${
                alert.type === 'critical'
                  ? 'bg-red-950/20 border-red-900/50'
                  : alert.type === 'warning'
                    ? 'bg-amber-950/20 border-amber-900/50'
                    : 'bg-blue-950/20 border-blue-900/50'
              }`}
            >
              <div className="mt-0.5">
                {alert.type === 'critical' && <AlertTriangle className="w-5 h-5 text-red-500" />}
                {alert.type === 'warning' && <AlertTriangle className="w-5 h-5 text-amber-500" />}
                {alert.type === 'info' && <Info className="w-5 h-5 text-blue-500" />}
              </div>
              <div>
                <p
                  className={`text-sm font-medium ${
                    alert.type === 'critical'
                      ? 'text-red-200'
                      : alert.type === 'warning'
                        ? 'text-amber-200'
                        : 'text-blue-200'
                  }`}
                >
                  {alert.message}
                </p>
                <p className="text-xs mt-1.5 text-gray-500">{alert.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
