'use server';

import { cookies } from 'next/headers';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function authHeaders() {
  const cookieStore = await cookies();
  const token = cookieStore.get('jwt')?.value;
  if (!token) throw new Error('Unauthorized');
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

export type SalesAiMode = 'preview' | 'execute';

export async function runSalesAi(leadId: string | number, mode: SalesAiMode = 'preview') {
  const headers = await authHeaders();
  const res = await fetch(`${BACKEND_URL}/api/v1/leads/${leadId}/sales-ai`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ mode }),
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`Sales AI ${mode} failed: ${res.status}`);
  }
  return await res.json();
}

/** @deprecated use runSalesAi(id, 'preview') */
export async function getNextBestAction(leadId: string) {
  return runSalesAi(leadId, 'preview');
}

export async function fetchLeadOptions() {
  const headers = await authHeaders();
  const res = await fetch(`${BACKEND_URL}/api/v1/leads`, {
    method: 'GET',
    headers,
    cache: 'no-store',
  });
  if (!res.ok) return [];
  const data = await res.json();
  return (data.leads || []).map(
    (l: {
      id: number;
      name?: string;
      phone?: string;
      lead_temperature?: string;
      funnel_stage?: string;
    }) => ({
      id: String(l.id),
      label: l.name || l.phone || `Lead ${l.id}`,
      temperature: l.lead_temperature || 'cold',
      stage: l.funnel_stage || '',
    })
  );
}

export async function fetchNeighborhood(leadId: string | number) {
  const headers = await authHeaders();
  const res = await fetch(
    `${BACKEND_URL}/api/v1/graph/neighborhood?lead_id=${leadId}&limit=25`,
    { method: 'GET', headers, cache: 'no-store' }
  );
  if (!res.ok) {
    return { status: 'error', available: false, data: { nodes: [], edges: [] }, ai_summary: '' };
  }
  return await res.json();
}
