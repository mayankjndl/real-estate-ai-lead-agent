This is a complete, production-grade **QA & Testing Runbook** designed for your teammate. It outlines the entire end-to-end setup, environment configuration, database manipulation, and testing workflows to verify the **Email Fallback** and **10m/30m Escalation** engines.

---

# 🚀 RUNBOOK: Email Fallback & Multi-Stage Escalation Testing
**System:** Revenue OS — Real Estate Lead Agent (Backend Service)  
**Author:** Imperion Data Systems  
**Target Audience:** Engineering Team / QA

---

## Phase 1: Sender Email Setup (Gmail SMTP with 2FA)
The Email Fallback engine uses Python’s built-in `smtplib` to authenticate with Gmail [1.3]. Because Google has blocked basic password logins, you must generate a secure **16-character App Password**.

### 1.1 Enable 2-Step Verification (Sender Account)
1. Log into **Email A** (the account you want the system to send alerts *from*) [1.3].
2. Go to **Manage your Google Account** -> **Security** -> **How you sign in to Google**.
3. Ensure **2-Step Verification** is turned **ON** (this is a mandatory prerequisite) [1.3].

### 1.2 Generate the Google App Password
1. In the search bar at the top of your Google Account settings, search for **"App passwords"**.
2. Select **App Passwords** from the dropdown.
3. Under **App name**, enter a custom name (e.g., `Revenue OS Local Dev`) [1.3].
4. Click **Create**.
5. Copy the generated **16-character yellow code**.
6. **CRITICAL:** Remove any spaces from the code (e.g., `abcd efgh ijkl mnop` becomes `abcdefghijklmnop`) [1.3].

---

## Phase 2: Environment Configuration (`.env`)
Copy the new variables from `.env.example` to the bottom of your local `.env` file [1.1].

```env
# ==========================================
# Notification & Escalation Variables
# ==========================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Sender Account Credentials (Email A)
SMTP_USER=your_sender_email_A@gmail.com
SMTP_PASS=your16characterapppasswordwithnospaces

# Default Fallback Recipient (Email B - No 2FA required to receive)
ADMIN_EMAIL=your_receiver_email_B@gmail.com

# Twilio Status Callback Tracking
# For local testing, use your active Ngrok URL (e.g., https://doorbell-jawed-recoup.ngrok-free.dev)
WEBHOOK_BASE_URL=https://your-active-ngrok-url-here.ngrok-free.app

# System Modes
TEST_MODE=false
```

---

## Phase 3: Database & Twilio Setup
Because we modified the table schema of `NotificationLog` (adding `twilio_message_sid` and `twilio_delivery_status`), you must force SQLAlchemy to recreate the database with the new columns.

### 3.1 Hard Reset the Postgres Container
To completely clear the database volume and apply the new schema, run:
```powershell
# Stop and destroy the database volume
docker compose down -v

# Start the clean Postgres & Redis containers
docker compose up -d
```

### 3.2 Seed the Database
Run the seed script to generate the default clients and human agent directory [1.1]:
```powershell
python seed.py
```
*(This creates your first Client with `api_key="secret-client-key-123"`, a standard Sales Agent "Sneha Patil", and a Team Manager "System Admin" in the database) [1.3].*

### 3.3 Redirect Agent Alerts to Email B
By default, the seed script populates agents with fake emails (like `sneha@revenueos.com`). To actually receive the fallback emails in your inbox, you must update the database manually [1.3]:
1. Open your database GUI (TablePlus, DBeaver, or pgAdmin) [1.3].
2. Open the `agents` table.
3. Change the `email` column for **both** `Sneha Patil` and `System Admin` to **Email B** (your personal receiving email) [1.3].
4. Save/Commit the changes to the database [1.3].

### 3.4 Configure the Twilio Sandbox Webhook
1. Go to your **Twilio Console** -> **Messaging** -> **Try it out** -> **Send a WhatsApp message** [1.1].
2. Under **"When a message comes in"**, update the URL to your *current* live Ngrok forwarding address, appending your seeded client API key [1.1]:
   ```text
   https://your-active-ngrok-url.ngrok-free.app/api/v1/whatsapp?api_key=secret-client-key-123
   ```
3. Set the method to **HTTP POST** and click **Save** [1.1].

---

## Phase 4: Executing the Tests

### Test 1: Immediate Email Fallback (Twilio Crash Test)
This test verifies that if the Twilio API fails to dispatch a WhatsApp alert, the system automatically redirects the alert as an email to the agent instead of throwing an error or halting the server [1.3].

#### 1. Simulate a Twilio Outage
In your `.env` file, temporarily break your Twilio Account SID [1.3]:
```env
TWILIO_ACCOUNT_SID=FAKE_AC81b804ea9b136940a9...
```
*(Keep your real `TWILIO_AUTH_TOKEN` intact so the incoming signature validator in `main.py` passes security) [1.3].*

#### 2. Start the FastAPI Server
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Send a Hot Lead Message
Send a message to your Twilio Sandbox number to trigger a human handoff [1.1]:
> *"I want to buy a 2BHK in Baner. My budget is 80L and my name is Mayank. Connect me to an agent."* [1.3]

#### 4. Expected Output
*   **WhatsApp Chat:** The bot responds instantly: *"I completely understand. I have paused my automated responses and alerted our human team..."* [1.3]
*   **Terminal Logs:**
    ```text
    INFO:agent: 🚨 HUMAN HANDOFF TRIGGERED: Lead +91... requested an agent!
    ERROR:notification_service: WhatsApp Alert failed: Unable to create record: Authentication Error... Triggering Email Fallback.
    INFO:notification_service: Fallback email successfully sent to your_receiver_email_B@gmail.com
    ```
*   **Email B Inbox:** You receive a structured HTML email from your sender address (Email A) containing the lead's extraction details [1.3].

---

### Test 2: The 10-Minute Escalation
This test verifies that if a sales agent ignores a priority notification, the system automatically escalates the alert to their Team Manager [1.3].

#### 1. Locate the Notification Log
1. Open your database and navigate to the `notification_logs` table.
2. Locate the row created by your previous test (where `status = "pending_ack"`).

#### 2. Fast-Forward Time
To simulate the passage of 10 minutes, execute a quick SQL query (or double-click and update manually via your DB GUI):
```sql
UPDATE notification_logs 
SET sent_at = NOW() - INTERVAL '11 minutes' 
WHERE status = 'pending_ack';
```

#### 3. Expected Output
Within 60 seconds, the background scheduler runs the `escalation_cron_job`. Watch your terminal logs:
*   The console outputs: `⚠️ 10M ESCALATION TRIGGERED: Lead X ignored by Sneha Patil.` [1.3]
*   The system queries for the client manager (`System Admin`) and triggers a WhatsApp dispatch to their phone number (`+919163962356`) [1.3].
*   The log's `status` in the database changes to `"escalated_10m"`.

---

### Test 3: The 30-Minute Escalation
This test verifies that if a manager *also* ignores the 10-minute escalation alert, the system escalates it further to the Director [1.3].

#### 1. Setup the Database State
Execute the following query to simulate the manager ignoring the 10-minute alert:
```sql
UPDATE notification_logs 
SET status = 'escalated_10m', 
    sent_at = NOW() - INTERVAL '31 minutes';
```

#### 2. Expected Output
Within 60 seconds, the background scheduler runs. Watch your terminal logs:
*   The console outputs: `🚨 30M CRITICAL ESCALATION TRIGGERED: Lead X still unacknowledged! Alerting Director.` [1.3]
*   The system dispatches a critical WhatsApp message to the Director's phone number [1.3].
*   The log's `status` in the database changes to `"escalated_30m"`.

---

### Test 4: Implicit Auto-Acknowledge Integration (UX Test)
This test verifies that when an agent actually takes action in the CRM (drags a lead to "Contacted"), the system automatically clears the pending alerts, halting any further escalations [2.4].

1. Make sure your database has an active log with `status = "pending_ack"`.
2. Open your Next.js SaaS dashboard (`http://localhost:3000`) and navigate to the **CRM View** [1.1].
3. Locate your lead's card under the **"New"** column [2.4].
4. Drag and drop the card to **"Contacted"** [2.4].
5. **Expected Output:** 
   - A success toast is displayed on the UI: *"Successfully moved to Contacted"* [2.4].
   - Open your database and inspect the `notification_logs` table. The `status` has been automatically updated to **`"acknowledged"`**! Any further escalations are now canceled [2.4].