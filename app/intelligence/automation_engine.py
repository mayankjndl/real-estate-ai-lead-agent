from app.intelligence.followup_engine import (
    generate_followup_sequence
)

from app.intelligence.push_wait_engine import (
    decide_push_vs_wait
)


def build_automation_plan(lead_data):

    followups = generate_followup_sequence(
        lead_name=lead_data.get("name"),
        location=lead_data.get("location"),
        budget=lead_data.get("budget"),
        property_type=lead_data.get("property_type"),
        urgency=lead_data.get("urgency_level"),
        probability=lead_data.get(
            "conversion_probability",
            0
        )
    )

    strategy = decide_push_vs_wait(
        probability=lead_data.get(
            "conversion_probability",
            0
        ),
        urgency=lead_data.get(
            "urgency_level",
            "low"
        ),
        inactivity=(
            lead_data.get(
                "inactivity_penalty",
                0
            ) > 0
        )
    )

    return {
        "followups": followups,
        "strategy": strategy
    }