'use server'

import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export async function loginClient(prevState: any, formData: FormData) {
  const email = formData.get('email')
  const password = formData.get('password')

  if (!email || !password) {
    return { error: 'Email and password are required.' }
  }

  try {
    // FastAPI's OAuth2PasswordRequestForm expects form-urlencoded data
    const params = new URLSearchParams()
    params.append('username', email.toString())
    params.append('password', password.toString())

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login`, {
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
    
    // Store token securely in an HttpOnly cookie to prevent XSS
    const cookieStore = await cookies()
    cookieStore.set('jwt', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    })

  } catch (err) {
    return { error: 'Failed to connect to the authentication server.' }
  }

  // Redirect to dashboard on success (must be called outside try/catch block for Next.js)
  redirect('/dashboard')
}

export async function logoutClient() {
  const cookieStore = await cookies()
  cookieStore.delete('jwt')
  redirect('/login')
}
