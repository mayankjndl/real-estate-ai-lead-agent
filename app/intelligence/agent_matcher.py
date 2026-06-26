from sqlalchemy.orm import Session
from models import Agent
from app.intelligence.feedback_loop import get_agent_success_rate

def classify_lead_type(query: str) -> str:
    text = query.lower()
    if any(w in text for w in ["investment", "roi", "returns", "yield", "appreciation"]):
        return "investor"
    if any(w in text for w in ["rent", "lease", "rental"]):
        return "tenant"
    if any(w in text for w in ["luxury", "premium", "villa", "penthouse"]):
        return "luxury"
    return "buyer"

def detect_deal_size(query: str) -> str:
    text = query.lower()
    if "cr" in text or "crore" in text:
        return "high"
    if "lakh" in text or "lac" in text:
        return "medium"
    return "low"

def detect_urgency(query: str) -> str:
    text = query.lower()
    high_urgency = ["urgent", "immediately", "asap", "this week", "closing soon", "loan approved"]
    return "high" if any(w in text for w in high_urgency) else "medium"

def calculate_dynamic_agent_score(base_score, learned_rate, lead_type, urgency, response_speed_score=50, active_leads=0):
    score = base_score
    score += int(learned_rate / 4)
    score += int(response_speed_score / 5)
    if lead_type == "investor" and learned_rate >= 60:
        score += 18
    if urgency == "high":
        score += 12
    score -= int(active_leads * 1.8)
    return score

def match_best_agent(db: Session, client_id: int, location: str, query: str):
    """
    Dynamically routes a lead to the best agent for this specific tenant (client_id).
    Queries the database instead of hardcoded lists.
    """
    agents = db.query(Agent).filter(Agent.client_id == client_id).all()
    if not agents:
        return {"assigned_agent": None, "agent_name": None, "match_score": 0}

    lead_type = classify_lead_type(query)
    deal_size = detect_deal_size(query)
    urgency = detect_urgency(query)

    best_agent = None
    best_score = -1

    for agent in agents:
        score = 0

        # --- DYNAMIC LOCATION MATCHING ---
        if location and agent.locations:
            lead_locs = [l.strip().lower() for l in location.split(",") if l.strip()]
            agent_locs = [l.strip().lower() for l in agent.locations.split(",") if l.strip()]
            if any(loc in agent_locs for loc in lead_locs):
                score += 40

        if deal_size == agent.deal_size:
            score += 20
        if lead_type == agent.lead_type:
            score += 25
        if agent.speciality == lead_type:
            score += 30

        score += int((agent.conversion_rate or 30) / 5)
        try:
            learned_rate = max(agent.conversion_rate or 30, get_agent_success_rate(agent.name))
        except Exception:
            learned_rate = agent.conversion_rate or 30

        score = calculate_dynamic_agent_score(
            score, learned_rate, lead_type, urgency, agent.response_speed_score or 50, agent.active_leads or 0
        )

        if (agent.active_leads or 0) > 18:
            score -= 25

        if score > best_score:
            best_score = score
            best_agent = agent

    if not best_agent:
        return {"assigned_agent": None, "agent_name": None, "match_score": 0}

    best_agent.active_leads = (best_agent.active_leads or 0) + 1
    db.commit()

    return {
        "assigned_agent": best_agent.name,
        "agent_name": best_agent.name,
        "match_score": best_score,
        "agent_data": {"name": best_agent.name, "phone": best_agent.phone, "email": best_agent.email}
    }