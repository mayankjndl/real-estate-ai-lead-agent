'use client';

import React, { useState, useEffect, Suspense } from 'react';
import dynamic from 'next/dynamic';
import { Filter, Zap, X, Network } from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { fetchNeighborhood, fetchLeadOptions } from '../sales-copilot/actions';

const GraphWrapper = dynamic(() => import('./GraphWrapper'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-[#0a0a0a]">
      <div className="animate-pulse flex flex-col items-center">
        <div className="w-12 h-12 rounded-full border-4 border-blue-500 border-t-transparent animate-spin mb-4" />
        <p className="text-blue-400 font-medium">Initializing Graph Physics…</p>
      </div>
    </div>
  ),
});

export default function KnowledgeGraphPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full h-[calc(100vh-4rem)] flex items-center justify-center bg-[#0a0a0a]">
          <div className="animate-pulse flex flex-col items-center">
            <div className="w-12 h-12 rounded-full border-4 border-blue-500 border-t-transparent animate-spin mb-4" />
            <p className="text-blue-400 font-medium">Loading graph…</p>
          </div>
        </div>
      }
    >
      <KnowledgeGraphContent />
    </Suspense>
  );
}

function KnowledgeGraphContent() {
  const searchParams = useSearchParams();
  const [leadId, setLeadId] = useState(searchParams.get('lead_id') || '');
  const [options, setOptions] = useState<{ id: string; label: string }[]>([]);
  const [data, setData] = useState<{
    nodes: Record<string, unknown>[];
    edges: Record<string, unknown>[];
  }>({ nodes: [], edges: [] });
  const [available, setAvailable] = useState(true);
  const [summary, setSummary] = useState('');
  const [selectedNode, setSelectedNode] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetchLeadOptions()
      .then((opts) => {
        setOptions(opts);
        if (!leadId && opts[0]) setLeadId(opts[0].id);
      })
      .catch(() => {});
  }, [leadId]);

  useEffect(() => {
    if (!leadId) return;
    fetchNeighborhood(leadId).then((res) => {
      setAvailable(Boolean(res.available));
      setSummary(res.ai_summary || '');
      setData({
        nodes: res.data?.nodes || [],
        edges: res.data?.edges || [],
      });
    });
  }, [leadId]);

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] -m-6 md:-m-8 bg-[#0a0a0a]">
      <div className="absolute top-4 left-4 z-20 flex flex-wrap gap-3 items-center">
        <div className="bg-[#13131a]/95 border border-gray-800 rounded-xl px-4 py-2 flex items-center gap-2">
          <Network className="w-4 h-4 text-purple-400" />
          <select
            value={leadId}
            onChange={(e) => setLeadId(e.target.value)}
            className="bg-transparent text-sm text-white outline-none"
          >
            {options.map((o) => (
              <option key={o.id} value={o.id} className="bg-[#13131a]">
                {o.label} (#{o.id})
              </option>
            ))}
          </select>
        </div>
        <a
          href={`/sales-copilot?lead_id=${leadId}`}
          className="text-xs text-indigo-300 bg-indigo-950/50 border border-indigo-800/50 px-3 py-2 rounded-xl hover:bg-indigo-900/40"
        >
          Open in Sales Copilot
        </a>
      </div>

      {!available || data.nodes.length === 0 ? (
        <div className="w-full h-full flex flex-col items-center justify-center text-gray-500 gap-2">
          <Filter className="w-8 h-8 text-gray-600" />
          <p className="text-white">Ego graph empty or unavailable</p>
          <p className="text-xs max-w-sm text-center">{summary || 'Select a lead or start Neo4j'}</p>
        </div>
      ) : (
        <GraphWrapper key={leadId || 'none'} data={data} onNodeClick={setSelectedNode} />
      )}

      {selectedNode && (
        <div className="absolute bottom-6 right-6 w-72 bg-[#13131a] border border-gray-800 rounded-2xl p-4 shadow-2xl z-20">
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-bold text-white">{String(selectedNode.label ?? '')}</span>
            </div>
            <button type="button" onClick={() => setSelectedNode(null)} className="text-gray-500">
              <X className="w-4 h-4" />
            </button>
          </div>
          {(() => {
            const p = (selectedNode.properties as Record<string, unknown>) || {};
            if (selectedNode.node_type === 'stub') {
              return (
                <div className="text-xs text-gray-500 italic mt-2">
                  No extended data for this node
                </div>
              );
            }
            if (selectedNode.node_type === 'agent') {
              return (
                <dl className="space-y-2 text-xs mt-2">
                  <div className="flex justify-between gap-3">
                    <dt className="text-gray-500 shrink-0">Name</dt>
                    <dd className="text-gray-200 text-right truncate">{String(p.name || '—')}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-gray-500 shrink-0">Role</dt>
                    <dd className="text-gray-200 text-right truncate">{String(p.role || 'Assigned Agent')}</dd>
                  </div>
                </dl>
              );
            }
            const rows: [string, string][] = [
              ['Name', String(p.name || '—')],
              ['Phone', String(p.phone || '—')],
              ['Location', String(p.location || '—')],
              ['Temperature', String(p.temperature || '—')],
              ['Score', p.score != null && p.score !== '' ? String(p.score) : '—'],
              ['Stage', String(p.funnel_stage || '—')],
              ['Type', String(p.property_type || '—')],
            ];
            return (
              <dl className="space-y-2 text-xs mt-2">
                {rows.map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3">
                    <dt className="text-gray-500 shrink-0">{k}</dt>
                    <dd className="text-gray-200 text-right truncate">{v}</dd>
                  </div>
                ))}
              </dl>
            );
          })()}
        </div>
      )}
    </div>
  );
}
