# app/intelligence/analytics_engine.py

from datetime import datetime


# ==========================================
# BUILD ANALYTICS SNAPSHOT
# ==========================================

def build_analytics_snapshot(
    session_id,
    query,
    response,
    lead_data,
    assigned_agent=None,
    followup_plan=None
):

    analytics = {

        # ==========================================
        # CORE SESSION INFO
        # ==========================================

        "session_id": session_id,

        "timestamp": datetime.utcnow().isoformat(),

        # ==========================================
        # CONVERSATION
        # ==========================================

        "query": query,

        "response": response,

        # ==========================================
        # LEAD INTELLIGENCE
        # ==========================================

        "intent": lead_data.get(
            "intent",
            "Unknown"
        ),

        "conversion_probability": lead_data.get(
            "conversion_probability",
            0
        ),

        "expected_closure_days": lead_data.get(
            "expected_closure_days",
            60
        ),

        "urgency_level": lead_data.get(
            "urgency_level",
            "low"
        ),

        "engagement_score": lead_data.get(
            "engagement_score",
            0
        ),

        "budget_alignment_status": lead_data.get(
            "budget_alignment_status",
            "unknown"
        ),

        "response_speed_score": lead_data.get(
            "response_speed_score",
            0
        ),

        # ==========================================
        # PROPERTY CONTEXT
        # ==========================================

        "location": lead_data.get(
            "location"
        ),

        "budget": lead_data.get(
            "budget"
        ),

        "property_type": lead_data.get(
            "property_type"
        ),

        # ==========================================
        # AGENT MATCHING
        # ==========================================

        "assigned_agent": (
            assigned_agent.get(
                "assigned_agent"
            )
            if assigned_agent
            else None
        ),

        "agent_match_score": (
            assigned_agent.get(
                "match_score"
            )
            if assigned_agent
            else None
        ),

        "agent_specialization": (
            assigned_agent.get(
                "specialization"
            )
            if assigned_agent
            else None
        ),

        # ==========================================
        # FOLLOWUP ENGINE
        # ==========================================

        "followup_stage": (
            followup_plan.get(
                "stage"
            )
            if followup_plan
            else None
        ),

        "followup_message": (
            followup_plan.get(
                "message"
            )
            if followup_plan
            else None
        ),

        "followup_delay_days": (
            followup_plan.get(
                "delay_days"
            )
            if followup_plan
            else None
        ),

        "engagement_strategy": (
            followup_plan.get(
                "engagement_strategy"
            )
            if followup_plan
            else None
        ),

        "recommended_tone": (
            followup_plan.get(
                "recommended_tone"
            )
            if followup_plan
            else None
        )
    }

    return analytics


# ==========================================
# PRINT ANALYTICS CLEANLY
# ==========================================

def print_analytics_snapshot(analytics):

    print("\n" + "=" * 60)
    print("AI CRM ANALYTICS SNAPSHOT")
    print("=" * 60)

    print(f"Session ID              : {analytics['session_id']}")
    print(f"Timestamp               : {analytics['timestamp']}")

    print("-" * 60)

    print(f"Intent                  : {analytics['intent']}")
    print(f"Conversion Probability  : {analytics['conversion_probability']}%")
    print(f"Expected Closure Days   : {analytics['expected_closure_days']}")
    print(f"Urgency Level           : {analytics['urgency_level']}")
    print(f"Engagement Score        : {analytics['engagement_score']}")
    print(f"Budget Alignment        : {analytics['budget_alignment_status']}")
    print(f"Response Speed Score    : {analytics['response_speed_score']}")

    print("-" * 60)

    print(f"Location                : {analytics['location']}")
    print(f"Budget                  : {analytics['budget']}")
    print(f"Property Type           : {analytics['property_type']}")

    print("-" * 60)

    print(f"Assigned Agent          : {analytics['assigned_agent']}")
    print(f"Agent Match Score       : {analytics['agent_match_score']}")
    print(f"Agent Specialization    : {analytics['agent_specialization']}")

    print("-" * 60)

    print(f"Followup Stage          : {analytics['followup_stage']}")
    print(f"Followup Delay          : {analytics['followup_delay_days']}")
    print(f"Engagement Strategy     : {analytics['engagement_strategy']}")
    print(f"Recommended Tone        : {analytics['recommended_tone']}")
    print(f"Followup Message        : {analytics['followup_message']}")

    print("=" * 60 + "\n")


# ==========================================
# PERFORMANCE METRICS
# ==========================================

def generate_performance_metrics(analytics):

    metrics = {}

    probability = analytics.get(
        "conversion_probability",
        0
    )

    urgency = analytics.get(
        "urgency_level",
        "low"
    )

    engagement = analytics.get(
        "engagement_score",
        0
    )

    # ==========================================
    # PRIORITY
    # ==========================================

    if probability >= 85:

        metrics["priority"] = "critical"

    elif probability >= 70:

        metrics["priority"] = "high"

    elif probability >= 45:

        metrics["priority"] = "medium"

    else:

        metrics["priority"] = "low"

    # ==========================================
    # ACTION ENGINE
    # ==========================================

    if urgency == "high":

        metrics["recommended_action"] = (
            "Immediate human follow-up recommended."
        )

    elif engagement >= 75:

        metrics["recommended_action"] = (
            "Highly engaged lead. Push site visit."
        )

    elif probability >= 70:

        metrics["recommended_action"] = (
            "Strong nurture sequence recommended."
        )

    elif probability >= 45:

        metrics["recommended_action"] = (
            "Continue consultative nurturing."
        )

    else:

        metrics["recommended_action"] = (
            "Long-term nurture workflow advised."
        )

    return metrics