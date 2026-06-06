'use server'

import { cookies } from 'next/headers'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function updateLeadStageAction(leadId: number, stage: string) {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt')?.value

  if (!token) throw new Error('Unauthorized')

  const res = await fetch(`${BACKEND_URL}/api/v1/leads/${leadId}/stage`, {
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
