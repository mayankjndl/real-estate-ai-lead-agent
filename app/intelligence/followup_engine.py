def generate_followup_sequence(lead_name, location, budget, property_type, urgency, probability, inactivity, engagement_score, response_speed_score, budget_alignment_score, assigned_agent):
    """
    Mock implementation of Anohita's ML Follow-Up Sequence Generator.
    This will be replaced by the real model on deployment.
    """
    return {
        "sequence": [
            {"day": 0, "stage": "Day 0", "message": "Just checking if you're still looking for property options."},
            {"day": 1, "stage": "Day 1", "message": "Hi again! I have some great matches for your property search."},
            {"day": 3, "stage": "Day 3", "message": "Properties in your desired area are moving fast!"},
            {"day": 7, "stage": "Day 7", "message": "Whenever you're ready to explore properties again, just reply here!"}
        ]
    }
