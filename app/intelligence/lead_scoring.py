# app/intelligence/lead_scoring.py

import re

from app.intelligence.behavior_signals import (
    extract_behavior_signals
)

from app.intelligence.urgency_detector import (
    detect_urgency
)

from app.intelligence.response_speed import (
    calculate_response_speed_score
)

from app.intelligence.inactivity_decay import (
    calculate_inactivity_penalty
)

from app.intelligence.budget_alignment import (
    evaluate_budget_alignment
)

from app.intelligence.score_recalibration import (
    recalibrate_probability
)

# ==========================================
# MAIN LEAD SCORING
# ==========================================

def calculate_lead_score(
    query,
    memory,
    intent
):

    try:

        text = query.lower()

        # ==========================================
        # BEHAVIOR SIGNALS
        # ==========================================

        signals = extract_behavior_signals(
            query=query,
            memory=memory
        )

        # ==========================================
        # URGENCY DETECTION
        # ==========================================

        urgency_data = detect_urgency(
            query=query
        )

        urgency_level = urgency_data.get(
            "urgency_level",
            "low"
        )

        # ==========================================
        # RESPONSE SPEED
        # ==========================================

        response_speed_data = (
            calculate_response_speed_score(
                memory=memory
            )
        )

        if isinstance(
            response_speed_data,
            dict
        ):

            response_speed_score = (
                response_speed_data.get(
                    "response_speed_score",
                    50
                )
            )

            response_pattern = (
                response_speed_data.get(
                    "response_pattern",
                    "normal"
                )
            )

        else:

            response_speed_score = (
                response_speed_data
            )

            response_pattern = (
                "normal"
            )

        # ==========================================
        # INACTIVITY
        # ==========================================

        inactivity_data = (
            calculate_inactivity_penalty(
                memory=memory
            )
        )

        inactivity_penalty = (
            inactivity_data.get(
                "penalty",
                0
            )
        )

        inactive_lead = (
            inactivity_data.get(
                "inactive_lead",
                False
            )
        )

        # ==========================================
        # BUDGET ALIGNMENT
        # ==========================================

        budget_alignment = (
            evaluate_budget_alignment(
                budget_text=query,

                location=signals.get(
                    "detected_location"
                ),

                property_type=signals.get(
                    "detected_property_type"
                ),
                intent=intent
            )
        )

        budget_alignment_score = (
            budget_alignment.get(
                "alignment_score",
                0
            )
        )

        budget_alignment_status = (
            budget_alignment.get(
                "alignment_status",
                "unknown"
            )
        )

        # ==========================================
        # WEIGHT CONFIGURATION
        # ==========================================

        weights = {

            "intent_high": 16,
            "intent_medium": 9,
            "intent_low": 2,

            "budget_discussed": 7,
            "location_fixed": 8,
            "property_type_fixed": 7,

            # Reduced aggressive boosting
            "high_intent_signal": 10,

            # Increased engagement importance
            "repeat_engagement": 14,

            # Reduced over-scoring
            "site_visit_interest": 8,

            "buying_signal": 12,

            # Reduced investment inflation
            "investment_interest": 4,

            "comparison_behavior": 2,

            # Reduced urgency inflation
            "urgency_high": 9,
            "urgency_medium": 5,

            "response_speed_multiplier": 0.18,

            # Increased realistic budget fit impact
            "budget_alignment_multiplier": 0.30,

            "inactive_penalty_multiplier": 2.5
        }

        # ==========================================
        # INITIAL SCORE
        # ==========================================

        score = 0

        # ==========================================
        # INTENT WEIGHT
        # ==========================================

        if intent == "high":

            score += weights[
                "intent_high"
            ]

        elif intent == "medium":

            score += weights[
                "intent_medium"
            ]

        else:

            score += weights[
                "intent_low"
            ]

        # ==========================================
        # SIGNAL SCORING
        # ==========================================

        if signals.get(
            "budget_discussed"
        ):

            score += weights[
                "budget_discussed"
            ]

        if signals.get(
            "location_fixed"
        ):

            score += weights[
                "location_fixed"
            ]

        if signals.get(
            "property_type_fixed"
        ):

            score += weights[
                "property_type_fixed"
            ]

        if signals.get(
            "high_intent_signal"
        ):

            score += weights[
                "high_intent_signal"
            ]

        if signals.get(
            "repeat_engagement"
        ):

            score += weights[
                "repeat_engagement"
            ]

        if signals.get(
            "site_visit_interest"
        ):

            score += weights[
                "site_visit_interest"
            ]

        if signals.get(
            "buying_signal"
        ):

            score += weights[
                "buying_signal"
            ]

        if signals.get(
            "investment_interest"
        ):

            score += weights[
                "investment_interest"
            ]

        if signals.get(
            "comparison_behavior"
        ):

            score += weights[
                "comparison_behavior"
            ]

        # ==========================================
        # URGENCY WEIGHTING
        # ==========================================

        if urgency_level == "high":

            score += weights[
                "urgency_high"
            ]

        elif urgency_level == "medium":

            score += weights[
                "urgency_medium"
            ]

        # ==========================================
        # RESPONSE SPEED
        # ==========================================

        score += (
            response_speed_score
            * weights[
                "response_speed_multiplier"
            ]
        )

        # ==========================================
        # BUDGET ALIGNMENT
        # ==========================================

        score += (
            budget_alignment_score
            * weights[
                "budget_alignment_multiplier"
            ]
        )

        # ==========================================
        # INACTIVITY PENALTY
        # ==========================================

        score -= (
            inactivity_penalty
            * weights[
                "inactive_penalty_multiplier"
            ]
        )

        # ==========================================
        # NEGATIVE SIGNALS
        # ==========================================

        negative_signals = {

            "just browsing": 18,
            "not sure": 12,
            "later": 14,
            "next year": 18,
            "low budget": 15,
            "cheap": 10,
            "only checking": 16,
            "not urgent": 18,
            "maybe": 10,
            "exploring": 8,
            "information only": 20,
            "brochure": 6,
            "future investment": 12,
            "researching": 10,
            "collecting info": 10
        }

        negative_penalty = 0

        for signal, penalty in negative_signals.items():

            if signal in text:

                negative_penalty += penalty

        score -= negative_penalty

        # ==========================================
        # HIGH VALUE KEYWORDS
        # ==========================================

        high_value_keywords = [

            "site visit",
            "loan approved",
            "ready to buy",
            "finalize",
            "booking",
            "token amount",
            "immediate possession",
            "urgent",
            "roi",
            "rental yield",
            "deal closure",
            "investment opportunity"
        ]

        keyword_hits = 0

        for keyword in high_value_keywords:

            if keyword in text:

                keyword_hits += 1

        # Reduced keyword inflation
        score += keyword_hits * 3

        # ==========================================
        # MEMORY ENGAGEMENT
        # ==========================================

        memory_depth = len(memory)

        if memory_depth >= 5:

            score += 10

        elif memory_depth >= 3:

            score += 6

        elif memory_depth >= 1:

            score += 3

        # ==========================================
        # NORMALIZATION
        # ==========================================

        if score > 85:

            score = (
                85
                + ((score - 85) * 0.35)
            )

        elif score < 35:

            score = score * 0.80

        # ==========================================
        # RECALIBRATION
        # ==========================================

        score = recalibrate_probability(
            score
        )

        # ==========================================
        # FINAL NORMALIZATION
        # ==========================================

        score = round(
            max(
                0,
                min(100, score)
            )
        )

        # ==========================================
        # LEAD TEMPERATURE
        # ==========================================

        if score >= 82:

            lead_temperature = "hot"

        elif score >= 45:

            lead_temperature = "warm"

        else:

            lead_temperature = "cold"

        # ==========================================
        # EXPECTED CLOSURE DAYS
        # ==========================================

        if score >= 88:

            expected_closure_days = 7

        elif score >= 72:

            expected_closure_days = 14

        elif score >= 55:

            expected_closure_days = 30

        else:

            expected_closure_days = 60

        # ==========================================
        # ENGAGEMENT SCORE
        # ==========================================

        engagement_score = min(

            100,

            (
                len(memory) * 12
            )

            + keyword_hits * 10

            + (
                20
                if signals.get(
                    "repeat_engagement"
                )
                else 0
            )

            + (
                15
                if signals.get(
                    "site_visit_interest"
                )
                else 0
            )
        )

        # ==========================================
        # SCORE EXPLANATION
        # ==========================================

        score_explanation = []

        if signals.get(
            "high_intent_signal"
        ):

            score_explanation.append(
                "Detected strong buying intent."
            )

        if signals.get(
            "site_visit_interest"
        ):

            score_explanation.append(
                "User requested site visit."
            )

        if signals.get(
            "investment_interest"
        ):

            score_explanation.append(
                "Investment-related keywords found."
            )

        if urgency_level == "high":

            score_explanation.append(
                "Urgent purchase intent detected."
            )

        if budget_alignment_status in [
            "excellent",
            "strong"
        ]:

            score_explanation.append(
                "Budget aligns well with target area."
            )

        if inactive_lead:

            score_explanation.append(
                "Lead inactivity reduced score."
            )

        # ==========================================
        # FINAL RESPONSE
        # ==========================================

        return {

            "conversion_probability":
                score,

            "lead_temperature":
                lead_temperature,

            "expected_closure_days":
                expected_closure_days,

            "urgency_level":
                urgency_level,

            "engagement_score":
                engagement_score,

            "response_speed_score":
                response_speed_score,

            "response_pattern":
                response_pattern,

            "inactivity_penalty":
                inactivity_penalty,

            "inactive_lead":
                inactive_lead,

            "budget_alignment_score":
                budget_alignment_score,

            "budget_alignment_status":
                budget_alignment_status,

            "score_explanation":
                score_explanation
        }

    except Exception as e:
        import traceback
        with open("lead_scoring_error.log", "w") as f:
            f.write(traceback.format_exc())
        print(
            "LEAD SCORING ERROR:",
            e
        )

        return {

            "conversion_probability": 0,

            "lead_temperature": "cold",

            "expected_closure_days": 60,

            "urgency_level": "low",

            "engagement_score": 0,

            "response_speed_score": 0,

            "response_pattern": "unknown",

            "inactivity_penalty": 0,

            "inactive_lead": False,

            "budget_alignment_score": 0,

            "budget_alignment_status": "unknown",

            "score_explanation": [
                str(e)
            ]
        }