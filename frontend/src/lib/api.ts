import { cookies } from 'next/headers'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL;
if (!BACKEND_URL) {
  throw new Error("CRITICAL: NEXT_PUBLIC_API_URL is not set in environment variables.");
}

async function authFetch(url: string, options?: RequestInit) {
  return fetch(url, options)
}

export interface Lead {
  id: number
  session_id: string
  name: string | null
  phone: string | null
  budget: string | null
  location: string | null
  property_type: string | null
  intent: string | null
  score: string | null
  visit_date: string | null
  source: string
  whatsapp_opt_in: boolean
  updated_at: string
  conversion_probability: number
  expected_closure_days: number
  lead_temperature: string
  engagement_score: number
  urgency_level: string
  budget_alignment_status: string
  assigned_agent: string | null
  conversion_status: string
  followup_stage: string
  funnel_stage: string
  is_negotiating: boolean
}

export interface LeadsResponse {
  status: string
  total_returned: number
  leads: Lead[]
}

export interface AnalyticsData {
  total_sessions: number;
  total_leads_captured: number;
  conversion_rate: number;
  intent_breakdown: Record<string, number>;
}

export interface AnalyticsResponse {
  status: string;
  client_id: string;
  data: AnalyticsData;
}

export async function fetchLeads(): Promise<LeadsResponse | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt')?.value

  if (!token) return null

  try {
    const res = await authFetch(`${BACKEND_URL}/api/v1/leads`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store' 
    })

    if (!res.ok) {
      console.error(`Failed to fetch leads: ${res.status}`)
      return null
    }

    return await res.json()
  } catch (err) {
    console.error('Error connecting to backend:', err)
    return null
  }
}

export async function fetchAnalytics(): Promise<AnalyticsResponse | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt')?.value

  if (!token) return null

  try {
    const res = await authFetch(`${BACKEND_URL}/api/v1/analytics`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store'
    })

    if (!res.ok) return null
    return await res.json()
  } catch (err) {
    console.error('Error fetching analytics:', err)
    return null
  }
}

async function fetchPrediction(path: string) {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt')?.value
  if (!token) return null
  try {
    const res = await authFetch(`${BACKEND_URL}/api/v1/predictions/${path}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store'
    })
    if (!res.ok) return null
    return await res.json()
  } catch (err) {
    console.error(`Error fetching prediction ${path}:`, err)
    return null
  }
}

export async function fetchPredictionsRevenue() {
  return fetchPrediction('revenue')
}

export async function fetchPredictionsCashflow() {
  return fetchPrediction('cashflow')
}

export async function fetchPredictionsInventory() {
  return fetchPrediction('inventory')
}

export async function fetchPredictionsCancellationRisk() {
  return fetchPrediction('cancellation-risk')
}

export async function fetchAllPredictions() {
  const [revenue, cashflow, inventory, cancellation] = await Promise.all([
    fetchPredictionsRevenue(),
    fetchPredictionsCashflow(),
    fetchPredictionsInventory(),
    fetchPredictionsCancellationRisk(),
  ])
  return { revenue, cashflow, inventory, cancellation }
}
