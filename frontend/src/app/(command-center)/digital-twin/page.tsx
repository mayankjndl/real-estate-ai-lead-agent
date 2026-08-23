'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import type { ProjectData, UnitData } from '@/lib/api/mockTwinService';
import { Building2, X, DollarSign, Activity } from 'lucide-react';
import { formatInrCr } from '@/lib/format';

interface UnitMeshProps {
  unit: UnitData;
  position: [number, number, number];
  hideSold: boolean;
  onClick: (unit: UnitData) => void;
  selectedId: string | null;
}

/**
 * Hover label: drei Html in transform+sprite mode (billboard in 3D, locked to mesh).
 * Avoid transform={false}/portal — those float in screen space and drift off the block.
 */
const UnitMesh = ({ unit, position, hideSold, onClick, selectedId }: UnitMeshProps) => {
  const [hovered, setHovered] = useState(false);
  const isSold = unit.status === 'Sold';
  if (hideSold && isSold) return null;

  const color =
    unit.status === 'Available' ? '#10b981' : unit.status === 'Hold' ? '#f59e0b' : '#ef4444';
  const isSelected = selectedId === unit.id;
  const showTip = hovered && !isSelected;

  return (
    <group position={position}>
      <mesh
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          setHovered(false);
          document.body.style.cursor = 'auto';
        }}
        onClick={(e) => {
          e.stopPropagation();
          onClick(unit);
        }}
      >
        <boxGeometry args={[1.8, 0.8, 1.8]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected ? 0.8 : isSold ? 0.1 : 0.4}
          transparent
          opacity={isSold ? 0.4 : isSelected ? 1 : 0.8}
        />
      </mesh>
      {showTip && (
        <Html
          position={[0, 0.55, 0]}
          transform
          sprite
          distanceFactor={8}
          style={{ pointerEvents: 'none', userSelect: 'none' }}
          zIndexRange={[20, 0]}
        >
          <div
            style={{
              transform: 'scale(0.5)',
              transformOrigin: 'center bottom',
            }}
          >
            <div
              style={{
                transform: 'scale(2)',
                minWidth: 132,
                padding: '8px 12px',
                borderRadius: 8,
                border: '1px solid #4b5563',
                background: 'rgba(15,15,19,0.94)',
                boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
                whiteSpace: 'nowrap',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 16, fontWeight: 700, color: '#fff', lineHeight: 1.2 }}>
                Unit {unit.unit_number}
              </div>
              <div
                style={{
                  fontSize: 14,
                  marginTop: 3,
                  display: 'flex',
                  gap: 6,
                  justifyContent: 'center',
                  alignItems: 'center',
                }}
              >
                <span
                  style={{
                    fontWeight: 600,
                    color:
                      unit.status === 'Available'
                        ? '#34d399'
                        : unit.status === 'Hold'
                          ? '#fbbf24'
                          : '#f87171',
                  }}
                >
                  {unit.status}
                </span>
                <span style={{ color: '#6b7280' }}>|</span>
                <span style={{ fontWeight: 600, color: '#e5e7eb' }}>
                  {formatInrCr(unit.price)}
                </span>
              </div>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

function mapTwinApiToProject(payload: {
  available?: boolean;
  project?: { id?: string; name?: string } | null;
  towers?: Array<{
    id: string;
    name: string;
    floors: Array<{
      level: number;
      units: Array<{
        id: string;
        unit_number: string;
        status: string;
        price?: number | null;
        bhk?: string | null;
      }>;
    }>;
  }>;
  counts?: { available?: number; hold?: number; sold?: number };
}): { project: ProjectData; counts: { available: number; hold: number; sold: number } } | null {
  if (!payload?.towers?.length || !payload.project) return null;

  const towers = payload.towers.map((t) => {
    const maxFloor = Math.max(0, ...t.floors.map((f) => f.level));
    const floors: UnitData[][] = [];
    for (let level = 1; level <= maxFloor; level++) {
      const floor = t.floors.find((f) => f.level === level);
      const units = (floor?.units || []).map((u) => {
        const st = (u.status || 'available').toLowerCase();
        const status =
          st === 'sold' ? 'Sold' : st === 'hold' || st === 'held' ? 'Hold' : 'Available';
        return {
          id: u.id,
          unit_number: u.unit_number,
          status: status as UnitData['status'],
          price: Number(u.price || 0),
          bhk: u.bhk || '—',
          floor: level,
        } satisfies UnitData;
      });
      floors.push(units);
    }
    return { id: t.id, name: t.name, units: floors };
  });

  // Cap render at 500 units
  let total = 0;
  for (const tw of towers) {
    for (const fl of tw.units) total += fl.length;
  }
  if (total > 500) {
    // keep first towers only
    let kept = 0;
    for (const tw of towers) {
      for (let fi = 0; fi < tw.units.length; fi++) {
        if (kept >= 500) {
          tw.units[fi] = [];
          continue;
        }
        const room = 500 - kept;
        if (tw.units[fi].length > room) tw.units[fi] = tw.units[fi].slice(0, room);
        kept += tw.units[fi].length;
      }
    }
  }

  return {
    project: {
      id: payload.project.id || 'prj',
      name: payload.project.name || 'Project',
      towers,
    },
    counts: {
      available: payload.counts?.available ?? 0,
      hold: payload.counts?.hold ?? 0,
      sold: payload.counts?.sold ?? 0,
    },
  };
}

export default function DigitalTwinPage() {
  const [project, setProject] = useState<ProjectData | null>(null);
  const [counts, setCounts] = useState({ available: 0, hold: 0, sold: 0 });
  const [selectedUnit, setSelectedUnit] = useState<UnitData | null>(null);
  const [hideSold, setHideSold] = useState(false);
  const [emptyReason, setEmptyReason] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadTwin = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/inventory/twin', { credentials: 'include' });
      if (!res.ok) {
        setEmptyReason(`Twin API ${res.status}`);
        setProject(null);
        return;
      }
      const data = await res.json();
      const mapped = mapTwinApiToProject(data);
      if (!mapped) {
        setEmptyReason(
          data.disclaimer ||
            'No inventory — run: python seed_twin_demo.py --client-id 1 --clear'
        );
        setProject(null);
        setCounts({ available: 0, hold: 0, sold: 0 });
        return;
      }
      setProject(mapped.project);
      setCounts(mapped.counts);
      setEmptyReason(null);
    } catch {
      setEmptyReason('Failed to load twin layout');
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const boot = window.setTimeout(() => {
      void loadTwin();
    }, 0);
    const id = window.setInterval(() => {
      void loadTwin();
    }, 30_000);
    return () => {
      window.clearTimeout(boot);
      window.clearInterval(id);
    };
  }, [loadTwin]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-white">Loading Twin Data…</div>
    );
  }

  if (!project) {
    return (
      <div className="h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-center text-gray-400 gap-3 p-8">
        <Building2 className="w-10 h-10 text-gray-600" />
        <p className="text-white font-medium">Digital Twin empty</p>
        <p className="text-sm max-w-md">{emptyReason}</p>
      </div>
    );
  }

  const total = counts.available + counts.hold + counts.sold || 1;

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] -m-6 md:-m-8 bg-[#050505] overflow-hidden">
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-emerald-900/90 border border-emerald-500/40 text-emerald-100 px-6 py-2 rounded-full shadow-lg backdrop-blur-sm text-sm font-medium whitespace-nowrap flex items-center gap-2 pointer-events-none">
        <Activity className="w-4 h-4 text-emerald-400" />
        Live twin · read-only · refreshes every 30s
      </div>

      <Canvas camera={{ position: [20, 15, 20], fov: 45 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 20, 10]} intensity={1} />
        <OrbitControls
          makeDefault
          minPolarAngle={0}
          maxPolarAngle={Math.PI / 2 - 0.1}
          minDistance={10}
          maxDistance={60}
        />

        <group position={[0, -5, 0]}>
          {project.towers.map((tower, tIdx) => {
            const xOffset = tIdx === 0 ? -6 : 6 + (tIdx > 1 ? (tIdx - 1) * 12 : 0);
            return (
              <group key={tower.id} position={[xOffset, 0, 0]}>
                <mesh position={[0, -0.5, 0]}>
                  <boxGeometry args={[5, 1, 5]} />
                  <meshStandardMaterial color="#1a1a1a" />
                </mesh>
                {tower.units.map((floor, fIdx) => (
                  <group key={fIdx} position={[0, fIdx * 1, 0]}>
                    {floor.map((unit, uIdx) => {
                      // 2 units/floor default layout
                      const px = floor.length === 1 ? 0 : uIdx % 2 === 0 ? -1 : 1;
                      const pz = floor.length > 2 ? (uIdx < 2 ? -1 : 1) : 0;
                      return (
                        <UnitMesh
                          key={unit.id}
                          unit={unit}
                          position={[px, 0.5, pz]}
                          hideSold={hideSold}
                          onClick={(u) => setSelectedUnit(u)}
                          selectedId={selectedUnit?.id || null}
                        />
                      );
                    })}
                  </group>
                ))}
              </group>
            );
          })}
        </group>
      </Canvas>

      <div className="absolute top-6 left-6 w-64 bg-[#0f0f13]/80 backdrop-blur-xl border border-gray-800 rounded-2xl shadow-2xl overflow-hidden z-10">
        <div className="p-4 border-b border-gray-800 bg-[#15151a]/50 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-indigo-400" />
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wide">Digital Twin</h2>
            <p className="text-xs text-gray-500">{project.name}</p>
          </div>
        </div>

        <div className="p-5">
          <label className="flex items-center justify-between cursor-pointer group mb-4">
            <span className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">
              Hide Sold Units
            </span>
            <input
              type="checkbox"
              checked={hideSold}
              onChange={(e) => setHideSold(e.target.checked)}
              className="w-4 h-4 rounded bg-gray-900 border-gray-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-gray-900"
            />
          </label>

          <div className="pt-4 border-t border-gray-800">
            <p className="text-xs text-gray-500 mb-2 font-semibold uppercase">Inventory Status</p>
            <div className="space-y-2 text-xs text-gray-400 font-medium">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-emerald-500/80 border border-emerald-400" />{' '}
                  Available
                </div>
                <span>{Math.round((counts.available / total) * 100)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-amber-500/80 border border-amber-400" /> On Hold
                </div>
                <span>{Math.round((counts.hold / total) * 100)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-red-500/80 border border-red-400" /> Sold
                </div>
                <span>{Math.round((counts.sold / total) * 100)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        className={`absolute top-0 right-0 w-80 h-full bg-[#0f0f13]/95 backdrop-blur-2xl border-l border-gray-800 shadow-2xl transition-transform duration-300 ease-in-out z-20 ${selectedUnit ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {selectedUnit && (
          <div className="flex flex-col h-full">
            <div className="p-6 border-b border-gray-800 flex items-start justify-between">
              <div>
                <span
                  className={`text-xs font-bold uppercase tracking-wider mb-1 inline-block px-2 py-1 rounded-md ${
                    selectedUnit.status === 'Available'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : selectedUnit.status === 'Hold'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        : 'bg-red-500/10 text-red-400 border border-red-500/20'
                  }`}
                >
                  {selectedUnit.status}
                </span>
                <h2 className="text-2xl font-bold text-white mt-1">
                  Unit {selectedUnit.unit_number}
                </h2>
                <p className="text-sm text-gray-400 mt-1">
                  {selectedUnit.bhk} BHK · Floor {selectedUnit.floor}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedUnit(null)}
                className="p-1.5 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 flex-1 overflow-y-auto space-y-6">
              <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <DollarSign className="w-5 h-5 text-gray-400" />
                  <span className="text-sm text-gray-300">List price</span>
                </div>
                <span className="font-bold text-white">{formatInrCr(selectedUnit.price)}</span>
              </div>
              <p className="text-xs text-gray-500">
                Read-only twin — holds/writes deferred to 4.1.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
