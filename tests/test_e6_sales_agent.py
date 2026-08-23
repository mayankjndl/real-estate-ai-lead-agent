"""Expansion Phase 6 — Sales AI agent + CRM automation (Tasks 6.1–6.4).

Tracks Step 15 (Expansion Phase 6). Exercises the Sales AI recommendation
policy, deal-stage progression, assignment integration, and AE-routed CRM sync.

See plans/IREIOS_3.0_EXPANSION_CHANGELOG.md (Phase 6 status).
"""
import asyncio

from app.agents.sales_agent import SalesAgent, progress_deal_stage, recommend_next_action
from app.agents.whatsapp_agent import score_lead
from models import Agent, Lead, Session


def _clean(db, sid):
    db.query(Lead).filter(Lead.session_id == sid).delete()
    db.query(Session).filter(Session.id == sid).delete()
    db.commit()


def test_recommend_request_info():
    lead = Lead(lead_temperature="cold")
    rec = recommend_next_action(lead)
    assert rec["action"] == "request_info"
    assert "budget" in rec["missing_fields"]


def test_recommend_escalate_hot():
    lead = Lead(lead_temperature="hot", name="A", phone="+919999999999",
                location="Wakad", budget="80L", property_type="2BHK")
    assert recommend_next_action(lead)["action"] == "escalate_hot"


def test_recommend_schedule_site_visit():
    lead = Lead(lead_temperature="warm", name="A", phone="+919999999999",
                location="Wakad", budget="80L", property_type="2BHK",
                visit_date="2026-08-01", assigned_agent="Raj")
    assert recommend_next_action(lead)["action"] == "schedule_site_visit"


def test_recommend_terminal_closed_won_no_outbound():
    """Closed Won must not schedule visits or send brochures."""
    lead = Lead(
        funnel_stage="Closed Won",
        lead_temperature="hot",
        name="A",
        phone="+919999999999",
        location="Wakad",
        budget="80L",
        property_type="2BHK",
        visit_date="2026-08-01",
        assigned_agent="Raj",
    )
    rec = recommend_next_action(lead)
    assert rec["action"] == "deal_closed"
    lead2 = Lead(
        funnel_stage="Closed Won",
        lead_temperature="warm",
        name="B",
        phone="+919999999998",
        location="Baner",
        budget="70L",
        property_type="2BHK",
        assigned_agent="Raj",
    )
    assert recommend_next_action(lead2)["action"] == "deal_closed"


def test_recommend_nurture_when_cold_unassigned():
    lead = Lead(lead_temperature="cold", name="A", phone="+919999999999",
                location="Wakad", budget="80L", property_type="2BHK")
    assert recommend_next_action(lead)["action"] == "nurture_followup"


def test_progress_deal_stage():
    lead = Lead(funnel_stage="New", assigned_agent="Raj")
    assert progress_deal_stage(lead) == "Contacted"
    # No blind +1 every confirm
    lead_mid = Lead(funnel_stage="Contacted", assigned_agent="Raj", name="A",
                    phone="+91", location="W", budget="80L", property_type="2BHK")
    assert progress_deal_stage(lead_mid) is None
    lead2 = Lead(funnel_stage="Closed Won")
    assert progress_deal_stage(lead2) is None
    lead3 = Lead(funnel_stage="Qualified", name="A", phone="+919999999999",
                 location="W", budget="80L", property_type="2BHK", visit_date="2026-08-01")
    assert progress_deal_stage(lead3) == "Site Visit Booked"
    lead4 = Lead(funnel_stage="Qualified", name="A", phone="+91", location="W",
                 budget="80L", property_type="2BHK", visit_date="2026-08-01")
    assert progress_deal_stage(lead4, {"action": "schedule_site_visit"}) == "Site Visit Booked"


def test_sales_ai_run_assigns_and_scores():
    with __import__("database").SessionLocal() as db:
        _clean(db, "sess_sales_1")
        # Seed an agent for the tenant so assignment has a candidate.
        if not db.query(Agent).filter(Agent.client_id == 1, Agent.name == "SalesTestAgent").first():
            db.add(Agent(client_id=1, name="SalesTestAgent", phone="+919999999998",
                         email="sales@test.com", locations="Wakad", lead_type="buyer",
                         deal_size="medium", speciality="buyer", conversion_rate=40))
            db.commit()
        db.add(Session(id="sess_sales_1", client_id=1, status="active"))
        lead = Lead(session_id="sess_sales_1", client_id=1, name="Buyer", phone="+919999999999",
                    location="Wakad", budget="80L", property_type="2BHK", lead_temperature="warm")
        db.add(lead)
        db.commit()

        async def run():
            agent = SalesAgent()
            return await agent.run_sales_ai(db, lead, 1, sync_crm=False)

        res = asyncio.run(run())
        assert res["recommendation"]["action"] in ("send_brochure", "assign_agent", "nurture_followup")
        assert res["assigned_agent"] in ("SalesTestAgent", None)
        assert res["scores"]["lead_temperature"] == "warm"
        _clean(db, "sess_sales_1")


def test_sync_crm_via_ae_returns_dict(monkeypatch):
    captured = {}

    async def fake_submit(action_request):
        captured.update(action_request)
        return {"status": "success", "crm_sync_status": "success"}

    import app.agents.sales_agent as sa
    monkeypatch.setattr(sa, "ae_submit", fake_submit)
    agent = SalesAgent()
    out = asyncio.run(agent.sync_crm_via_ae(123, 1))
    assert out["status"] == "success"
    assert captured["action_type"] == "update_crm"
    assert captured["parameters"]["lead_id"] == 123
