'use client';

/**
 * Ego / force graph — camera policy (vasturiano/react-force-graph):
 * - Initial fit: zoomToFit once after layout (fit-to-canvas pattern).
 * - Click: selection only — do NOT call centerAt/zoom (click-to-focus is optional
 *   and blows up small panels).
 * - minZoom/maxZoom clamp runaway zoom.
 */
import React, { useRef, useEffect, useMemo, useState } from 'react';
import ForceGraph2D, {
  type ForceGraphMethods,
  type NodeObject,
  type LinkObject,
} from 'react-force-graph-2d';

export type GraphNode = {
  id?: string | number;
  label?: string;
  color?: string;
  val?: number;
  x?: number;
  y?: number;
  properties?: Record<string, unknown>;
};

export type GraphEdge = {
  source?: string | number;
  target?: string | number;
  properties?: { strength?: number };
};

interface GraphWrapperProps {
  data: { nodes: GraphNode[]; edges: GraphEdge[] };
  onNodeClick: (node: GraphNode) => void;
}

function dataFingerprint(data: { nodes: GraphNode[]; edges: GraphEdge[] }): string {
  const n = data.nodes.map((x) => String(x.id ?? '')).join(',');
  const e = data.edges
    .map((l) => `${String(l.source)}>${String(l.target)}`)
    .join(',');
  return `${n}|${e}`;
}

export default function GraphWrapper({ data, onNodeClick }: GraphWrapperProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<
    ForceGraphMethods<NodeObject<GraphNode>, LinkObject<GraphNode, GraphEdge>> | undefined
  >(undefined);
  const fittedFor = useRef<string>('');
  const [size, setSize] = useState({ w: 0, h: 0 });

  const fp = useMemo(() => dataFingerprint(data), [data]);

  // Fresh copies so force-graph can attach x/y without mutating parent state
  const graphData = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        properties: e.properties,
      })),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fp captures structural identity
    [fp]
  );

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const apply = () => {
      const r = el.getBoundingClientRect();
      const w = Math.floor(r.width);
      const h = Math.floor(r.height);
      if (w > 8 && h > 8) setSize((s) => (s.w === w && s.h === h ? s : { w, h }));
    };
    apply();
    const ro = new ResizeObserver(() => apply());
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // One fit per graph identity after layout settles (not on every click / zoom)
  useEffect(() => {
    if (!fgRef.current || size.w < 40 || size.h < 40) return;
    if (!graphData.nodes.length) return;
    if (fittedFor.current === fp) return;

    const t = window.setTimeout(() => {
      if (!fgRef.current) return;
      try {
        fgRef.current.zoomToFit(400, 48);
        fittedFor.current = fp;
      } catch {
        /* empty */
      }
    }, 350);
    return () => window.clearTimeout(t);
  }, [fp, size.w, size.h, graphData.nodes.length]);

  return (
    <div ref={wrapRef} className="w-full h-full min-h-[180px] bg-[#0a0a0a]">
      {size.w > 0 && size.h > 0 && (
        <ForceGraph2D
          ref={fgRef}
          width={size.w}
          height={size.h}
          graphData={graphData}
          backgroundColor="#0a0a0a"
          nodeId="id"
          linkSource="source"
          linkTarget="target"
          minZoom={0.35}
          maxZoom={4}
          nodeRelSize={4}
          nodeVal={(node: GraphNode) => Math.min(Number(node.val) || 8, 14)}
          nodeLabel={(node: GraphNode) => {
            const p = node.properties || {};
            const name = String(p.name || p.unit_number || p.type || node.label || '');
            if (node.label === 'Lead') {
              return [
                name,
                p.phone ? `☎ ${p.phone}` : '',
                p.temperature ? `🌡 ${p.temperature}` : '',
                p.score != null && p.score !== '' ? `score ${p.score}` : '',
                p.location ? `📍 ${p.location}` : '',
              ]
                .filter(Boolean)
                .join('\n');
            }
            return `${node.label || 'Node'}: ${name}`;
          }}
          nodeColor={(node: GraphNode) => node.color || '#64748b'}
          linkColor={() => 'rgba(255,255,255,0.18)'}
          linkWidth={1.2}
          linkDirectionalParticles={1}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={0.004}
          cooldownTicks={100}
          warmupTicks={20}
          enableNodeDrag
          enableZoomInteraction
          enablePanInteraction
          onNodeClick={(node: GraphNode) => {
            // Selection only — no centerAt / zoom (avoids blank over-zoom in small panels)
            onNodeClick(node);
          }}
          onEngineStop={() => {
            if (fittedFor.current === fp || !fgRef.current) return;
            if (!graphData.nodes.length) return;
            try {
              fgRef.current.zoomToFit(300, 48);
              fittedFor.current = fp;
            } catch {
              /* empty */
            }
          }}
        />
      )}
    </div>
  );
}
