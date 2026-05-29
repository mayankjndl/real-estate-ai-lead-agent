# app/intelligence/behavior_signals.py

import re

from app.data_manager import (
    PUNE_LOCATIONS
)

# ==========================================
# HIGH INTENT PHRASES
# ==========================================

HIGH_INTENT_PHRASES = [

    "schedule visit",
    "book visit",
    "site visit",
    "finalize",
    "finalise",
    "ready to buy",
    "interested",
    "move ahead",
    "connect me",
    "call me",
    "loan approved",
    "token amount",
    "ready to finalize",
    "close deal",
    "book now",
    "site visit tomorrow"
]

# ==========================================
# COMPARISON PHRASES
# ==========================================

COMPARISON_PHRASES = [

    "compare",
    "difference",
    "better",
    "vs",
    "which is better",
    "compare projects",
    "best option"
]

# ==========================================
# BUDGET PATTERNS
# ==========================================

BUDGET_PATTERNS = [

    r'\d+\s?(lakh|lac|l|cr|crore|k)'
]

# ==========================================
# MAIN SIGNAL EXTRACTION
# ==========================================

def detect_behavior_signals(
    query,
    memory
):

    query_lower = query.lower()

    signals = {

        "budget_discussed": False,

        "location_fixed": False,

        "property_type_fixed": False,

        "high_intent_signal": False,

        "comparison_behavior": False,

        "repeat_engagement": False,

        "site_visit_interest": False,

        "buying_signal": False,

        "investment_interest": False,

        "detected_location": None,

        "detected_property_type": None
    }

    # ==========================================
    # BUDGET SIGNAL
    # ==========================================

    for pattern in BUDGET_PATTERNS:

        if re.search(
            pattern,
            query_lower
        ):

            signals[
                "budget_discussed"
            ] = True

    # ==========================================
    # LOCATION SIGNAL
    # ==========================================

    known_locations = [

        location.lower()
        for location in PUNE_LOCATIONS
    ]

    for location in known_locations:

        if location in query_lower:

            signals[
                "location_fixed"
            ] = True

            signals[
                "detected_location"
            ] = location.title()

            break

    # ==========================================
    # PROPERTY TYPE SIGNAL
    # ==========================================

    property_match = re.search(

        r'([1-5]\s?bhk|villa|penthouse|luxury apartment)',

        query_lower
    )

    if property_match:

        signals[
            "property_type_fixed"
        ] = True

        signals[
            "detected_property_type"
        ] = (
            property_match
            .group(1)
            .upper()
            .replace(" ", "")
        )

    # ==========================================
    # HIGH INTENT SIGNAL
    # ==========================================

    if any(

        phrase in query_lower

        for phrase in HIGH_INTENT_PHRASES
    ):

        signals[
            "high_intent_signal"
        ] = True

    # ==========================================
    # COMPARISON BEHAVIOR
    # ==========================================

    if any(

        phrase in query_lower

        for phrase in COMPARISON_PHRASES
    ):

        signals[
            "comparison_behavior"
        ] = True

    # ==========================================
    # REPEAT ENGAGEMENT
    # ==========================================

    if len(memory) >= 4:

        signals[
            "repeat_engagement"
        ] = True

    # ==========================================
    # SITE VISIT INTEREST
    # ==========================================

    visit_keywords = [

        "visit",
        "site visit",
        "schedule visit",
        "book visit"
    ]

    if any(

        keyword in query_lower

        for keyword in visit_keywords
    ):

        signals[
            "site_visit_interest"
        ] = True

    # ==========================================
    # BUYING SIGNAL
    # ==========================================

    buying_keywords = [

        "buy",
        "purchase",
        "own house",
        "investment",
        "finalize",
        "book",
        "ready to buy",
        "close deal",
        "agreement",
        "loan approved"
    ]

    if any(

        keyword in query_lower

        for keyword in buying_keywords
    ):

        signals[
            "buying_signal"
        ] = True

    # ==========================================
    # INVESTMENT SIGNAL
    # ==========================================

    investment_keywords = [

        "investment",
        "roi",
        "rental yield",
        "appreciation",
        "high return",
        "future value"
    ]

    if any(

        keyword in query_lower

        for keyword in investment_keywords
    ):

        signals[
            "investment_interest"
        ] = True

    return signals

# ==========================================
# BACKWARD COMPATIBILITY
# ==========================================

def extract_behavior_signals(
    query,
    memory
):

    return detect_behavior_signals(
        query=query,
        memory=memory
    )