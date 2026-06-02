# Backend Integration Notes

This document outlines the integration between the Next.js frontend (managed by Mayank) and the FastAPI backend (managed by Aritro) for the Revenue OS application.

## 1. API Integration Endpoints

The frontend application communicates with the FastAPI backend primarily through the following core endpoints:

### `/api/v1/leads`
- **Purpose:** Fetches, creates, and updates lead information.
- **Usage:** Used heavily in the `Leads Inbox` and the `CRM Kanban Board`.
- **Key Methods:**
  - `GET /api/v1/leads`: Retrieve a list of leads filtered by the authenticated user's `client_id`.
  - `PATCH /api/v1/leads/{id}`: Update specific fields of a lead (e.g., updating the `funnel_stage` when a lead card is dragged and dropped in the Kanban board).

### `/api/v1/analytics`
- **Purpose:** Retrieves aggregated data for the dashboard's ROI and Funnel Tracking sections.
- **Usage:** Populates the main dashboard overview, charting conversion probabilities, expected closure days, and lead source distribution.
- **Key Methods:**
  - `GET /api/v1/analytics/roi`: Fetch return on investment metrics.
  - `GET /api/v1/analytics/funnel`: Fetch conversion funnel metrics.

### `/api/v1/whatsapp`
- **Purpose:** Serves as the webhook endpoint for Twilio/WhatsApp inbound messages.
- **Usage:** While primarily a backend webhook, the frontend interacts with this to trigger or display automated outbound follow-ups orchestrated by the AI.

---

## 2. JWT Authentication Flow

The application utilizes a strict, secure JWT authentication flow to ensure multi-tenant data isolation.

1. **Login Request:** The user submits their credentials via the Next.js login page. The frontend sends a `POST` request to the backend authentication endpoint (e.g., `/api/v1/auth/login`).
2. **Token Generation:** Upon successful validation, the backend generates a JSON Web Token (JWT). The token payload includes the user's `client_id` for multi-tenant isolation.
3. **Cookie Setting:** The backend responds with a `Set-Cookie` header containing the JWT. The cookie is configured as `HttpOnly`, `Secure`, and `SameSite=Lax/Strict` to prevent XSS attacks and CSRF.
4. **Middleware Interception:** For every subsequent request to protected frontend routes (e.g., `/dashboard`, `/leads`, `/crm`, `/settings`), the Next.js Edge Middleware (`middleware.ts`) intercepts the request.
5. **Token Verification:** The middleware checks for the presence of the `jwt` HttpOnly cookie.
   - If present, the user is allowed to proceed to the requested route.
   - If absent or expired, the user is immediately redirected to `/login`.
6. **Backend Verification:** In addition to frontend middleware checks, all API requests made by the frontend automatically include the HttpOnly cookie. The FastAPI backend verifies the token and strictly filters all database queries by the `client_id` contained within it.
