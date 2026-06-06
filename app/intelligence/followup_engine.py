# app/intelligence/followup_engine.py

from datetime import datetime

from app.intelligence.push_wait_engine import (
    decide_push_vs_wait
)

from app.intelligence.conversation_optimizer import (
    conversation_optimizer
)

from app.intelligence.followup_ab_testing import (
    get_best_followup_config,
    FOLLOWUP_VARIANTS,
    TIMING_STRATEGIES
)


# ==========================================
# FOLLOW-UP AUTOMATION ENGINE
# ==========================================


def generate_followup_sequence(
    lead_name,
    location,
    budget,
    property_type,
    urgency,
    probability,
    inactivity=False,
    engagement_score=0,
    response_speed_score=0,
    budget_alignment_score=0,
    assigned_agent=None
):

    # ==========================================
    # LIVE AB OPTIMIZATION
    # ==========================================

    best_config = (
        get_best_followup_config()
    )

    best_variant = (
        best_config["best_variant"]
    )

    best_timing = (
        best_config["best_timing"]
    )

    optimized_message = (
        FOLLOWUP_VARIANTS.get(
            best_variant
        )
    )

    optimized_schedule = (
        TIMING_STRATEGIES.get(
            best_timing
        )
    )

    # ==========================================
    # PUSH / WAIT INTELLIGENCE
    # ==========================================

    strategy_data = decide_push_vs_wait(
        probability=probability,
        urgency=urgency,
        inactivity=inactivity,
        engagement_score=engagement_score,
        response_speed_score=response_speed_score,
        budget_alignment_score=budget_alignment_score
    )

    strategy = strategy_data["strategy"]

    recommended_tone = (
        strategy_data["recommended_tone"]
    )

    best_script = (
        conversation_optimizer.get_best_script()
    )

    sequence = []

    # ==========================================
    # DAY 0
    # ==========================================

    # Build Day 0 message from actual lead data instead of static variant string.
    # If fields are missing, ask for them rather than hallucinating values.
    greeting = f"Hi {lead_name}," if lead_name else "Hi,"
    if property_type and budget:
        body = f"we found some {property_type} options matching your budget of {budget}."
    elif property_type:
        body = f"we found some {property_type} options. Could you share your budget so we can shortlist better?"
    elif budget:
        body = f"we shortlisted options within your budget of {budget}. What property type are you looking for — 2BHK, 3BHK, or villa?"
    else:
        body = "we'd love to help with your property search. Could you share your budget and preferred property type?"

    day_0_message = f"{greeting} {body}"

    if assigned_agent:
        day_0_message += f" {assigned_agent} will assist you further."

    sequence.append({
        "day": 0,
        "stage": "instant_reply",
        "message": day_0_message
    })

    # ==========================================
    # DAY 1
    # ==========================================

    if budget and location:
        day_1_message = f"We shortlisted some options around {budget} in {location}. Would you like to take a look?"
    elif budget:
        day_1_message = f"We found options within {budget}. Which area in Pune are you considering?"
    elif location:
        day_1_message = f"We shortlisted options in {location}. Could you share your budget so we can narrow it down?"
    else:
        day_1_message = "We'd love to help shortlist properties for you. Could you share your preferred area and budget?"

    sequence.append({
        "day": optimized_schedule[1],
        "stage": "budget_followup",
        "message": day_1_message
    })

    # ==========================================
    # DAY 3
    # ==========================================

    if strategy in ["aggressive_push", "sales_push"]:
        if location and property_type:
            day_3_message = f"{property_type} options in {location} are moving quickly. Would you like to schedule a site visit?"
        elif location:
            day_3_message = f"Properties in {location} are moving quickly. Would you like to schedule a site visit?"
        else:
            day_3_message = "Good properties in Pune are moving quickly. Would you like to schedule a site visit?"
        stage = "urgency_push"

    elif strategy == "reengage":
        if location or budget or property_type:
            day_3_message = "Just checking in — would you like updated options based on what you shared earlier?"
        else:
            day_3_message = "Just checking in — we'd love to help with your property search. What are you looking for?"
        stage = "reengagement"

    else:
        if location:
            day_3_message = f"We found a few more options in {location} that might interest you. Want to take a look?"
        else:
            day_3_message = "We found a few more options that might interest you. Could you share your preferred area?"
        stage = "soft_nurture"

    sequence.append({
        "day": optimized_schedule[2],
        "stage": stage,
        "message": day_3_message
    })

    # ==========================================
    # DAY 7
    # ==========================================

    if probability >= 70:

        day_7_message = (
            "Inventory is becoming limited for "
            "high-demand configurations in "
            f"{location or 'your selected area'}."
        )

        stage = "sales_push"

    else:

        day_7_message = (
            "Would you like updated "
            "recommendations or alternative "
            "locations within your budget?"
        )

        stage = "reengagement"

    sequence.append({
        "day": optimized_schedule[3],
        "stage": stage,
        "message": day_7_message
    })

    # ==========================================
    # FINAL PAYLOAD
    # ==========================================

    return {

        "generated_at": str(datetime.utcnow()),

        "lead_priority": (
            "critical"
            if probability >= 85
            else "high"
            if probability >= 70
            else "medium"
            if probability >= 45
            else "low"
        ),

        "recommended_strategy": strategy,

        "recommended_tone": recommended_tone,

        "recommended_script": best_script,

        "sequence": sequence,

        # ======================================
        # BACKWARD COMPATIBILITY
        # ======================================

        "day_0": day_0_message,

        "day_1": day_1_message,

        "day_3": day_3_message,

        "day_7": day_7_message
    }