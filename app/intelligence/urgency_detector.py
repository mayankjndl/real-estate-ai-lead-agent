# app/intelligence/urgency_detector.py

# ==========================================
# HIGH URGENCY SIGNALS
# ==========================================

HIGH_URGENCY = [

    "urgent",
    "immediately",
    "asap",
    "this week",
    "finalize soon",
    "ready to move",
    "need quickly",
    "immediate possession",
    "site visit today",
    "book now",
    "ready to buy",
    "closing this week",
    "token amount",
    "loan approved",
    "closing soon",
    "deal closure"
]

# ==========================================
# MEDIUM URGENCY SIGNALS
# ==========================================

MEDIUM_URGENCY = [

    "this month",
    "planning to buy",
    "exploring seriously",
    "interested",
    "looking for",
    "searching for",
    "want to finalize"
]

# ==========================================
# LOW URGENCY SIGNALS
# ==========================================

LOW_URGENCY = [

    "just exploring",
    "maybe later",
    "browsing",
    "no rush",
    "still thinking",
    "checking",
    "information only",
    "future investment",
    "researching",
    "collecting info",
    "future planning"
]

# ==========================================
# DETECT URGENCY
# ==========================================

def detect_urgency(query):

    query_lower = query.lower()

    # ==========================================
    # HIGH URGENCY
    # ==========================================

    for phrase in HIGH_URGENCY:

        if phrase in query_lower:

            return {
                "urgency_level": "high",
                "matched_signal": phrase
            }

    # ==========================================
    # MEDIUM URGENCY
    # ==========================================

    for phrase in MEDIUM_URGENCY:

        if phrase in query_lower:

            return {
                "urgency_level": "medium",
                "matched_signal": phrase
            }

    # ==========================================
    # LOW URGENCY
    # ==========================================

    for phrase in LOW_URGENCY:

        if phrase in query_lower:

            return {
                "urgency_level": "low",
                "matched_signal": phrase
            }

    # ==========================================
    # DEFAULT
    # ==========================================

    return {
        "urgency_level": "medium",
        "matched_signal": None
    }