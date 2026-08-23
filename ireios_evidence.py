"""IREIOS 3.0 — Phase 10.4: Evidence pack generator.

Produces a machine-readable evidence summary for the program final gate (G2):
  * IREIOS 3.0 agent registry (active + placeholders)
  * Knowledge-graph availability
  * Event-bus backend (Redis Streams)
  * OpenAPI export of the running app

Run:  python ireios_evidence.py            # prints summary
      python ireios_evidence.py --openapi out.json   # also dumps OpenAPI spec

See plans/phase3/IREIOS_3.0_STEP_BY_STEP_EXPANSION.md (Phase 10) and
plans/phase3/IREIOS_3.0_EXPANSION_CHANGELOG.md.
"""
from __future__ import annotations

import argparse
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ireios_evidence")


def _register_all_agents(ceo) -> None:
    """Register every active agent/workflow + placeholders on the CEO.

    Mirrors main.py lifespan so the evidence pack reflects the full runtime
    registry even when generated from this standalone script.
    """
    from app.workflows.followup_arm import on_lead_created
    from app.agents.lead_scoring_handler import register_lead_scoring
    from app.workflows.crm_automation import register_crm_automation
    from app.agents.marketing_agent import register_marketing_agent
    from app.agents.customer_success_agent import register_customer_success
    from app.knowledge_graph.event_writers import register_graph_writers
    from app.agents.placeholders import register_placeholders

    ceo.register_agent("followup_arm", on_lead_created,
                       ["lead.created", "conversation.updated"], status="active")
    register_lead_scoring(ceo)
    register_crm_automation(ceo)
    register_marketing_agent(ceo)
    register_customer_success(ceo)
    register_graph_writers(ceo)
    register_placeholders(ceo)


def build_evidence() -> dict:
    from app.agents.placeholders import PLACEHOLDER_AGENTS
    from app.knowledge_graph.neo4j_kg import knowledge_graph
    from app.orchestrator.ceo_orchestrator import ceo
    from config import settings

    if not ceo.registry.list_agents():
        _register_all_agents(ceo)
    agents = ceo.registry.list_agents()
    evidence = {
        "ireios_version": "3.0",
        "event_bus_backend": "redis_streams",
        "event_bus_key": settings.EVENT_STREAM_KEY,
        "knowledge_graph_available": bool(knowledge_graph.available),
        "feature_flags": {
            "FEATURE_WHATSAPP_V3": bool(getattr(settings, "FEATURE_WHATSAPP_V3", False)),
            "FOLLOWUP_ENGINE": getattr(settings, "FOLLOWUP_ENGINE", "legacy"),
        },
        "registered_agents": [
            {"agent_id": a.agent_id, "status": a.status, "subscriptions": a.subscriptions}
            for a in agents
        ],
        "placeholder_agents_declared": PLACEHOLDER_AGENTS,
        "runtime_path": "Event -> CEO -> Agent/Workflow -> AutomationEngine -> ExecutionEngine -> Event",
    }
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="IREIOS 3.0 evidence pack")
    parser.add_argument("--openapi", default=None, help="Path to write OpenAPI JSON")
    args = parser.parse_args()

    evidence = build_evidence()
    print(json.dumps(evidence, indent=2, default=str))

    if args.openapi:
        try:
            from main import app
            with open(args.openapi, "w") as f:
                json.dump(app.openapi(), f, indent=2, default=str)
            logger.info("OpenAPI written to %s", args.openapi)
        except Exception as e:  # pragma: no cover
            logger.warning("OpenAPI export failed: %s", e)

    active = [a for a in evidence["registered_agents"] if a["status"] == "active"]
    placeholders = [a for a in evidence["registered_agents"] if a["status"] == "placeholder"]
    logger.info("Evidence: %d active agents, %d placeholders, KG=%s",
                len(active), len(placeholders), evidence["knowledge_graph_available"])


if __name__ == "__main__":
    main()
