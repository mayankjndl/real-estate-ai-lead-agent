import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export default function middleware(request: NextRequest) {
  const isServerAction = request.headers.has('next-action') || request.headers.has('x-action');
  if (isServerAction) {
    return NextResponse.next();
  }

  const token = request.cookies.get('jwt')?.value;
  const path = request.nextUrl.pathname;

  const isProtectedRoute =
    path.startsWith('/dashboard') ||
    path.startsWith('/dashboard-mvp') ||
    path.startsWith('/sales-copilot') ||
    path.startsWith('/knowledge-graph') ||
    path.startsWith('/digital-twin') ||
    path.startsWith('/ai-chat') ||
    path.startsWith('/leads') ||
    path.startsWith('/crm') ||
    path.startsWith('/settings');

  if (isProtectedRoute && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', path);
    return NextResponse.redirect(loginUrl);
  }

  if (path === '/login' && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)',
  ],
};
