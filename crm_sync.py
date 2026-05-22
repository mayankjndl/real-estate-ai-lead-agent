import os
import logging
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from database import SessionLocal
from models import Lead, DLQEvent

logger = logging.getLogger("crm_sync")
logging.basicConfig(level=logging.INFO)

# Dummy HubSpot CRM API settings (Using a generic placeholder URL for demo)
CRM_API_URL = os.getenv("CRM_API_URL", "https://api.hubapi.com/crm/v3/objects/contacts")
CRM_API_KEY = os.getenv("CRM_API_KEY", "demo-hubspot-key")

class CRMAPIError(Exception):
    """Custom exception to trigger retries for transient HTTP errors."""
    pass

def should_retry(exception):
    """Determine if we should retry based on the exception."""
    if isinstance(exception, httpx.HTTPStatusError):
        # Retry on Rate Limit (429) or Server Errors (5xx)
        return exception.response.status_code == 429 or exception.response.status_code >= 500
    return isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout, CRMAPIError))

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.RequestError, CRMAPIError)),
    reraise=True
)
async def _push_to_hubspot(payload: dict) -> dict:
    """Makes the actual HTTP request to HubSpot with tenacity backoff logic."""
    headers = {
        "Authorization": f"Bearer {CRM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        logger.info(f"Syncing to CRM: {payload}")
        # In a real scenario, this would be a POST to HubSpot
        # For demonstration without an actual API, we will simulate a success response
        # or mock an endpoint. We will use a mock block if CRM_API_URL is the demo string.
        
        if CRM_API_URL == "https://api.hubapi.com/crm/v3/objects/contacts" and CRM_API_KEY == "demo-hubspot-key":
            # Simulate a successful CRM response with a fake ID
            import uuid
            return {"id": str(uuid.uuid4())}

        response = await client.post(CRM_API_URL, json=payload, headers=headers, timeout=10.0)
        
        if response.status_code in [429, 500, 502, 503, 504]:
            raise CRMAPIError(f"CRM returned transient error {response.status_code}")
        
        response.raise_for_status()
        return response.json()

async def sync_lead_to_crm(lead_id: int):
    """
    Background task wrapper to extract lead data, format it, 
    push to the CRM, and update the Lead table with the external CRM ID.
    """
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.error(f"CRM Sync failed: Lead ID {lead_id} not found.")
            return

        # Prepare HubSpot contact properties
        # HubSpot expects properties inside a 'properties' object
        payload = {
            "properties": {
                "firstname": lead.name or "Unknown",
                "phone": lead.phone or "",
                "budget": lead.budget or "",
                "lifecyclestage": "lead"
            }
        }

        # Attempt to push to CRM
        try:
            response_data = await _push_to_hubspot(payload)
            
            external_id = response_data.get("id")
            if external_id:
                lead.external_crm_id = external_id
                lead.crm_sync_status = "success"
                db.commit()
                logger.info(f"Successfully synced Lead {lead_id} to CRM. External ID: {external_id}")
            else:
                lead.crm_sync_status = "failed"
                db.commit()
                logger.error(f"CRM Sync succeeded but no ID returned for Lead {lead_id}: {response_data}")

        except Exception as e:
            logger.error(f"CRM Sync permanently failed for Lead {lead_id} after retries: {e}")
            lead.crm_sync_status = "failed"
            
            # Phase 2 Hardening: Dead-Letter Queue integration
            dlq_entry = DLQEvent(
                target_endpoint="hubspot_crm",
                payload=payload,
                error_trace=str(e),
                status="pending"
            )
            db.add(dlq_entry)
            db.commit()

    finally:
        db.close()
