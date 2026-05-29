import { cookies } from 'next/headers'

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
  assigned_agent: string | null
  conversion_status: string
  followup_stage: string
  funnel_stage: string
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
    const res = await fetch('https://real-estate-ai-lead-agent-3.onrender.com/api/v1/leads', {
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
    const res = await fetch('https://real-estate-ai-lead-agent-3.onrender.com/api/v1/analytics', {
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
