"""Quality check script — tests response quality and lead extraction with current model."""
import requests, time

BASE = "https://real-estate-ai-lead-agent-1.onrender.com"
SID  = "quality_check_session_99"

tests = [
    "Hi, I am looking for a 2BHK flat in Pune",
    "My budget is around 70 lakhs",
    "I prefer Baner or Aundh area",
    "My name is Rahul Mehta, my phone is 9988776655",
    "Do you have any ready possession flats?",
    "Can I book a site visit this weekend?",
]

print("=" * 60)
print("QUALITY CHECK — " + __import__("requests").get(BASE + "/health").json().get("version","?"))
print("=" * 60)

for msg in tests:
    r = requests.post(f"{BASE}/api/v1/chat",
                      params={"session_id": SID, "message": msg},
                      timeout=30)
    reply = r.json().get("reply", "ERROR")
    print(f"\nUSER : {msg}")
    print(f"AI   : {reply[:200]}")
    print("-" * 60)
    time.sleep(2)

# Check lead extraction
time.sleep(5)
r = requests.get(f"{BASE}/api/v1/leads",
                 headers={"X-API-Key": "secret-client-key-123"}, timeout=10)
leads = r.json().get("leads", [])
lead = next(
    (l for l in leads if "Rahul" in str(l.get("name","")) or "9988776655" in str(l.get("phone",""))),
    None
)

print()
print("LEAD EXTRACTION CHECK:")
if lead:
    print(f"  name     = {lead.get('name')}")
    print(f"  phone    = {lead.get('phone')}")
    print(f"  budget   = {lead.get('budget')}")
    print(f"  location = {lead.get('location')}")
    print(f"  score    = {lead.get('score')}")
    print("  Function calling: WORKING ✅")
else:
    print("  Lead NOT found in CRM ⚠️")
    print("  Function calling may be broken with flash-lite — consider switching back to gemini-2.5-flash")
