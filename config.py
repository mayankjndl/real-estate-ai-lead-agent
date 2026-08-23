import json
import logging

import boto3
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict

_cfg_logger = logging.getLogger("config")

class Settings(BaseSettings):
    """
    Secure configuration management using Pydantic.
    ALL secrets must be supplied via environment variables or a .env file.
    No credentials are hardcoded in this file.
    """
    GEMINI_API_KEY: str = ""

    # Client API keys — must be set in .env or Render environment variables.
    # No defaults: an empty key means the endpoint will reject all requests.
    API_AUTH_KEY: str = ""
    CLIENT_KEY_A: str = ""
    CLIENT_KEY_B: str = ""

    #NGROK ENV KEY
    NGROK_AUTHTOKEN: str = ""

    # Database Settings
    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # Model configuration — gemini-3.1-flash-lite is the current test model.
    # Supports function calling, tool use, and multi-turn context.
    # Uses the same google-generativeai SDK interface as gemini-2.5-flash.
    # To revert: set GEMINI_MODEL=gemini-2.5-flash in .env
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # Follow-up system settings
    # TEST MODE: Set FOLLOW_UP_TEST_MODE=true in .env to compress all timings.
    # Day 0 = 1 min, Day 1 = 2 min, Day 3 = 3 min, Day 7 = 4 min
    # Production values: FOLLOW_UP_DELAY_MINUTES=30, hour gaps are 24/48/96
    FOLLOW_UP_DELAY_MINUTES: int = 30
    FOLLOW_UP_MAX_COUNT: int = 2
    USE_AI_FOLLOWUPS: bool = False
    FOLLOW_UP_TEST_MODE: bool = False
    FOLLOW_UP_DLQ_TEST: bool = False  # Set true alongside TEST_MODE to force a DLQ entry for QA
    TEST_MODE: bool = False

    # Security & Encryption Keys
    JWT_SECRET_KEY: str = ""
    ADMIN_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Twilio API credentials
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # --- Notification & Escalation Variables ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 0
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    ADMIN_EMAIL: str = ""
    WEBHOOK_BASE_URL: str = ""

    # Production flag — set to true on Render
    IS_PRODUCTION: bool = False

    # P5.2: when True, sync the extended property map (location, intent,
    # property_type, visit_date, assignee, alignment, urgency, engagement,
    # temperature) to the CRM. Set False for portals that lack these custom
    # properties so the base contact (firstname/phone/budget/lifecyclestage)
    # still syncs cleanly.
    CRM_SYNC_EXTENDED_PROPERTIES: bool = True

    # P6.3: below this dynamic match score, do not assign a (poorly matched)
    # agent — leave the lead unassigned so it can be routed/reviewed manually.
    MIN_MATCH_SCORE: int = 0

    # WhatsApp webhook race window (seconds). Must stay under Twilio's ~15s HTTP
    # limit so we can return TwiML (real reply or interim) before Twilio retries.
    # On exceed: return interim "Just checking..." and await the *same* in-flight
    # turn (no cancel / no second Gemini call). See main.py _session_turn_locked.
    WHATSAPP_WEBHOOK_TIMEOUT: float = 13.0

    # Per Gemini send_message hard cap (seconds). MAY exceed WHATSAPP_WEBHOOK_TIMEOUT:
    # race only decides interim vs TwiML; the turn is not cancelled, so a slower
    # Gemini (12–20s) can still finish and EE-push. Do not retry pure TimeoutError.
    LLM_TIMEOUT_SECONDS: float = 22.0

    # Pre-LLM context budgets (seconds) — keep tight so RAG/Neo4j cannot burn the race window.
    RAG_TIMEOUT_SECONDS: float = 2.0
    GRAPH_CONTEXT_TIMEOUT_SECONDS: float = 0.5

    # Shown in WA fallback / system prompt escalate lines (E.164 or local display).
    CLIENT_SUPPORT_NUMBER: str = "+91 9876543210"

    # AWS Secrets Manager
    AWS_REGION: str = ""
    AWS_SECRET_NAME: str = ""

    # --- IREIOS 3.0 expansion env vars (wired in later phases) ---
    # Redis Streams event bus (Phase 1)
    EVENT_STREAM_KEY: str = "ireios:events"
    EVENT_CONSUMER_GROUP: str = "ireios-cg"
    # WhatsApp Agent v3 feature flag (Phase 5) — v3 is the production default;
    # set false to fall back to the legacy process_chat path (rollback).
    FEATURE_WHATSAPP_V3: bool = True
    # Follow-up engine selector (Phase 4): legacy | v3 | shadow (v3 is prod default)
    FOLLOWUP_ENGINE: str = "v3"
    # Neo4j knowledge graph (Phase 7) — empty = graceful no-op until provisioned
    NEO4J_URI: str = ""
    NEO4J_USER: str = ""
    NEO4J_PASSWORD: str = ""
    # n8n automation (Phase 2) — empty = n8n_not_configured (safe)
    N8N_BASE_URL: str = ""
    N8N_API_KEY: str = ""
    N8N_MANAGEMENT_API_KEY: str = ""
    # Bus→n8n webhook bridge (separate consumer group; stock n8n cannot XREADGROUP)
    N8N_BRIDGE_ENABLED: bool = True
    N8N_BRIDGE_GROUP: str = "ireios-n8n"
    # Optional JSON override of event_type → webhook path map (empty = defaults)
    N8N_WEBHOOK_MAP: str = ""
    # Phase 8 competitor monitor watch-list (comma-separated, no network call)
    COMPETITOR_KEYWORDS: str = ""
    # Admin API key for internal webhooks
    ADMIN_API_KEY: str = ""
    # Wave D.4: WhatsApp brochure/floor plan media URL (public HTTPS). Empty = text fallback.
    BROCHURE_MEDIA_URL: str = ""
    FLOORPLAN_MEDIA_URL: str = ""
    #CRM API Key for Hubspot
    CRM_API_KEY: str = ""
    # Google Calendar (real CalendarExecutor) — empty = stub visit_id fallback
    GOOGLE_CALENDAR_ID: str = ""
    GOOGLE_CALENDAR_CREDENTIALS_JSON: str = ""
    GOOGLE_CALENDAR_TIMEZONE: str = "Asia/Kolkata"

    # IREIOS 4.0 feature flags
    FEATURE_GRAPH_VIZ: bool = True
    FEATURE_TWIN_LIVE: bool = True
    FEATURE_HUBSPOT_LIVE: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def CLIENT_KEYS(self) -> dict:
        """
        Assembles client→key mapping at runtime from individual env vars.
        Never hardcoded — sourced from CLIENT_KEY_A and CLIENT_KEY_B in .env.
        """
        return {
            "client_A": self.CLIENT_KEY_A,
            "client_B": self.CLIENT_KEY_B,
        }

def fetch_aws_secrets(secret_name: str, region_name: str) -> dict:
    """Fetch secure variables from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in get_secret_value_response:
            return json.loads(get_secret_value_response['SecretString'])
    except ClientError as e:
        _cfg_logger.error(f"Failed to fetch AWS Secrets: {e}")
    return {}

settings = Settings()

# Populate from AWS Secrets Manager if configured
if settings.AWS_REGION and settings.AWS_SECRET_NAME:
    _cfg_logger.info(f"Loading credentials from AWS Secrets Manager: {settings.AWS_SECRET_NAME}")
    aws_secrets = fetch_aws_secrets(settings.AWS_SECRET_NAME, settings.AWS_REGION)
    for key, value in aws_secrets.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

# Startup warning so missing secrets are immediately visible in logs
if not settings.GEMINI_API_KEY:
    _cfg_logger.warning("GEMINI_API_KEY is not set — AI responses will fail.")
if not settings.CLIENT_KEY_A:
    _cfg_logger.warning("CLIENT_KEY_A is not set — /leads and /analytics will reject all requests.")

from contextvars import ContextVar
request_id_ctx = ContextVar("request_id", default="SYS")
tenant_id_ctx = ContextVar("tenant_id", default="None")