# Production Deployment Checklist

This is the definitive checklist for deploying the Real Estate Revenue OS Next.js frontend to Vercel.

## 1. Pre-Deployment Preparation
- [ ] **Verify Next.js Configuration:** Ensure `next.config.ts` has `reactStrictMode: true` and `trailingSlash: false` set correctly.
- [ ] **Lint and Type Check:** Run `npm run lint` and `npm run tsc` locally to ensure there are no build errors or TypeScript warnings.
- [ ] **Verify Routing:** Double-check that `middleware.ts` is correctly protecting the `/dashboard`, `/leads`, `/crm`, and `/settings` routes.
- [ ] **Verify API Base URL:** Ensure the frontend is configured to point to Aritro's production FastAPI backend URL (not `localhost`).

## 2. Vercel Configuration
- [ ] **Import Project:** Connect your GitHub repository to Vercel and select the `frontend/` directory as the Root Directory.
- [ ] **Framework Preset:** Ensure "Next.js" is automatically selected as the framework preset.
- [ ] **Environment Variables:** Add the required production environment variables in the Vercel dashboard:
  - `NEXT_PUBLIC_API_URL`: The production URL of the FastAPI backend.
  - *(Any other frontend-specific keys, e.g., analytics trackers or external UI service keys).*

## 3. Deployment
- [ ] **Trigger Build:** Click "Deploy" and monitor the build logs on Vercel.
- [ ] **Check Build Success:** Ensure the build step completes without errors and the serverless functions (like Edge Middleware) are deployed successfully.

## 4. Post-Deployment Smoke Testing
Perform these manual tests on the live Vercel URL to ensure a stable deployment:

- [ ] **Authentication:** 
  - Attempt to access `/dashboard` while logged out. Verify it redirects to `/login`.
  - Log in successfully and verify redirection to `/dashboard`.
- [ ] **UI Responsiveness:**
  - Access the application on a mobile device (or use browser DevTools).
  - Verify the navigation collapses into a hamburger menu.
  - Verify the `/leads` table scrolls horizontally without breaking the screen layout.
  - Verify the `/crm` Kanban board swiping functions smoothly via `snap-x` CSS properties.
- [ ] **Error Handling:**
  - Simulate a data fetch failure (e.g., block the API request in DevTools) and verify the `error.tsx` "Something went wrong" boundary appears gracefully.
- [ ] **Loading States:**
  - Refresh the page and observe the `loading.tsx` skeleton pulse animation to ensure smooth visual transitions.
