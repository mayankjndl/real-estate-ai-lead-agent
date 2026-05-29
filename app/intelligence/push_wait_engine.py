# FULL PRODUCTION UPDATES — PRIORITY 2, 3, 4

## app/intelligence/push_wait_engine.py

# app/intelligence/push_wait_engine.py

from datetime import datetime


FOLLOWUP_COOLDOWN_HOURS = 6


# ==========================================
# PUSH / WAIT DECISION ENGINE
# ==========================================


def decide_push_vs_wait(
    probability,
    urgency,
    inactivity,
    engagement_score=0,
    response_speed_score=0,
    budget_alignment_score=0,
    replied=False,
    last_followup_hours=999
):

    # ==========================================
    # STOP-ON-REPLY
    # ==========================================

    if replied:

        return {
            "strategy": "stop_followups",
            "reason": "Lead already replied.",
            "recommended_tone": "human_assist"
        }

    # ==========================================
    # COOLDOWN PROTECTION
    # ==========================================

    if last_followup_hours < FOLLOWUP_COOLDOWN_HOURS:

        return {
            "strategy": "wait",
            "reason": "Cooldown active.",
            "recommended_tone": "patient_consultative"
        }

    # ==========================================
    # CRITICAL HOT LEADS
    # ==========================================

    if (
        probability >= 88
        and urgency == "high"
        and engagement_score >= 70
    ):

        return {
            "strategy": "aggressive_push",
            "reason": (
                "Critical high-conversion lead."
            ),
            "recommended_tone": "direct_close"
        }

    # ==========================================
    # SALES PUSH
    # ==========================================

    if (
        probability >= 72
        and urgency in ["high", "medium"]
    ):

        return {
            "strategy": "sales_push",
            "reason": (
                "Strong lead with active intent."
            ),
            "recommended_tone": "urgency_driven"
        }

    # ==========================================
    # RE-ENGAGEMENT
    # ==========================================

    if inactivity:

        return {
            "strategy": "reengage",
            "reason": "Inactive lead detected.",
            "recommended_tone": "soft_reconnect"
        }

    # ==========================================
    # LOW BUDGET FIT
    # ==========================================

    if budget_alignment_score < 35:

        return {
            "strategy": "educational_nurture",
            "reason": (
                "Budget mismatch detected."
            ),
            "recommended_tone": "educational"
        }

    # ==========================================
    # SLOW RESPONSE USER
    # ==========================================

    if response_speed_score < 40:

        return {
            "strategy": "slow_nurture",
            "reason": (
                "Lead responds slowly."
            ),
            "recommended_tone": "patient_consultative"
        }

    # ==========================================
    # LOW PROBABILITY
    # ==========================================

    if probability < 45:

        return {
            "strategy": "long_term_nurture",
            "reason": (
                "Low immediate conversion probability."
            ),
            "recommended_tone": "consultative"
        }

    # ==========================================
    # DEFAULT
    # ==========================================

    return {
        "strategy": "nurture",
        "reason": "Continue guided nurturing.",
        "recommended_tone": "consultative"
    }
