import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export default function middleware(request: NextRequest) {
  // --- FIX FOR NEXT.JS SERVER ACTION WEBHOOK BUG ---
  // If the request is a Server Action, bypass middleware processing
  // to prevent response header corruption
  const isServerAction = request.headers.has('next-action') || request.headers.has('x-action');
  if (isServerAction) {
    return NextResponse.next();
  }
  // -------------------------------------------------

  // Extract the JWT securely from HttpOnly cookie
  const token = request.cookies.get('jwt')?.value;

  // Define the protected route boundaries
  const isProtectedRoute =
    request.nextUrl.pathname.startsWith('/dashboard') ||
    request.nextUrl.pathname.startsWith('/leads') ||
    request.nextUrl.pathname.startsWith('/crm') ||
    request.nextUrl.pathname.startsWith('/settings');

  // Guard: Redirect unauthenticated users back to login
  if (isProtectedRoute && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Guard: Prevent authenticated users from seeing the login page
  if (request.nextUrl.pathname === '/login' && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

// Optimization: Exclude static files and Next.js internals from middleware
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)',
  ],
};