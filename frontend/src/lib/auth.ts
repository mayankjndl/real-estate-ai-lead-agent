'use server'

import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function loginClient(prevState: any, formData: FormData) {
  const email = formData.get('email')
  const password = formData.get('password')

  if (!email || !password) {
    return { error: 'Email and password are required.' }
  }

  try {
    const params = new URLSearchParams()
    params.append('username', email.toString())
    params.append('password', password.toString())

    const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params,
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => null)
      return { error: errorData?.detail || 'Invalid email or password.' }
    }

    const data = await res.json()
    
    const cookieStore = await cookies()
    cookieStore.set('jwt', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7,
      path: '/',
    })

  } catch (err) {
    return { error: 'Failed to connect to the authentication server.' }
  }

  redirect('/dashboard')
}

export async function logoutClient() {
  const cookieStore = await cookies()
  cookieStore.delete('jwt')
  redirect('/login')
}
