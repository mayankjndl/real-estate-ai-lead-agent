'use server'

import { cookies } from 'next/headers'

export async function updateLeadStageAction(leadId: number, stage: string) {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt')?.value

  if (!token) throw new Error('Unauthorized')

  const res = await fetch(`https://real-estate-ai-lead-agent-3.onrender.com/api/v1/leads/${leadId}/stage`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ stage }),
  })

  if (!res.ok) {
    throw new Error(`Failed to update stage: ${res.statusText}`)
  }

  return await res.json()
}
