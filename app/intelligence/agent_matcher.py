# app/intelligence/agent_matcher.py

from app.intelligence.feedback_loop import (
    get_agent_success_rate
)

from app.intelligence.learning_engine import (
    learning_engine
)

# ==========================================
# AGENT DATABASE
# ==========================================

AGENTS = [

    {
        "name": "Rahul Sharma",

        "locations": [
            "Baner",
            "Balewadi",
            "Aundh",
            "Pashan"
        ],

        "speciality": "luxury",

        "deal_size": "high",

        "lead_type": "buyer",

        "conversion_rate": 41,

        "response_speed_score": 82,

        "active_leads": 11,

        "specializations": [
            "luxury",
            "premium",
            "high_budget"
        ]
    },

    {
        "name": "Sneha Patil",

        "locations": [
            "Wakad",
            "Hinjewadi",
            "Tathawade",
            "Punawale"
        ],

        "speciality": "mid_range",

        "deal_size": "medium",

        "lead_type": "buyer",

        "conversion_rate": 38,

        "response_speed_score": 76,

        "active_leads": 8,

        "specializations": [
            "family",
            "mid_budget",
            "residential"
        ]
    },

    {
        "name": "Aman Deshmukh",

        "locations": [
            "Kharadi",
            "Magarpatta",
            "Hadapsar",
            "Mundhwa",
            "Viman Nagar"
        ],

        "speciality": "investment",

        "deal_size": "high",

        "lead_type": "investor",

        "conversion_rate": 44,

        "response_speed_score": 88,

        "active_leads": 9,

        "specializations": [
            "investment",
            "roi",
            "rental_yield"
        ]
    },

    {
        "name": "Priya Joshi",

        "locations": [
            "Ravet",
            "Kondhwa",
            "Undri",
            "Bavdhan"
        ],

        "speciality": "rental",

        "deal_size": "low",

        "lead_type": "tenant",

        "conversion_rate": 35,

        "response_speed_score": 74,

        "active_leads": 6,

        "specializations": [
            "rental",
            "budget",
            "tenant"
        ]
    }
]

# ==========================================
# LEAD TYPE CLASSIFICATION
# ==========================================

def classify_lead_type(query):

    text = query.lower()

    investor_keywords = [

        "investment",
        "roi",
        "returns",
        "yield",
        "appreciation",
        "rental yield"
    ]

    tenant_keywords = [

        "rent",
        "lease",
        "rental"
    ]

    luxury_keywords = [

        "luxury",
        "premium",
        "villa",
        "penthouse"
    ]

    for word in investor_keywords:

        if word in text:

            return "investor"

    for word in tenant_keywords:

        if word in text:

            return "tenant"

    for word in luxury_keywords:

        if word in text:

            return "luxury"

    return "buyer"

# ==========================================
# DEAL SIZE DETECTION
# ==========================================

def detect_deal_size(query):

    text = query.lower()

    if (
        "cr" in text
        or "crore" in text
    ):

        return "high"

    if (
        "lakh" in text
        or "lac" in text
    ):

        return "medium"

    return "low"

# ==========================================
# URGENCY DETECTION
# ==========================================

def detect_urgency(query):

    text = query.lower()

    high_urgency = [

        "urgent",
        "immediately",
        "asap",
        "this week",
        "closing soon",
        "deal closure",
        "token amount",
        "loan approved"
    ]

    for word in high_urgency:

        if word in text:

            return "high"

    return "medium"

# ==========================================
# SPECIALIZATION MATCH
# ==========================================

def detect_specialization(query):

    text = query.lower()

    if any(
        word in text
        for word in [
            "investment",
            "roi",
            "yield",
            "returns"
        ]
    ):

        return "investment"

    if any(
        word in text
        for word in [
            "luxury",
            "premium",
            "villa",
            "penthouse"
        ]
    ):

        return "luxury"

    if any(
        word in text
        for word in [
            "rent",
            "rental",
            "lease"
        ]
    ):

        return "rental"

    return "family"

# ==========================================
# DYNAMIC AGENT SCORE
# ==========================================

def calculate_dynamic_agent_score(

    base_score,

    learned_rate,

    lead_type,

    urgency,

    response_speed_score=50,

    active_leads=0
):

    score = base_score

    # ==========================================
    # HISTORICAL CONVERSION BOOST
    # ==========================================

    score += int(
        learned_rate / 4
    )

    # ==========================================
    # RESPONSE SPEED BOOST
    # ==========================================

    score += int(
        response_speed_score / 5
    )

    # ==========================================
    # INVESTOR PRIORITY
    # ==========================================

    if (
        lead_type == "investor"
        and learned_rate >= 60
    ):

        score += 18

    # ==========================================
    # HIGH URGENCY BOOST
    # ==========================================

    if urgency == "high":

        score += 12

    # ==========================================
    # LOAD BALANCING
    # ==========================================

    score -= int(
        active_leads * 1.8
    )

    return score

# ==========================================
# MAIN MATCH ENGINE
# ==========================================

def match_best_agent(

    location,

    query
):

    lead_type = classify_lead_type(
        query
    )

    deal_size = detect_deal_size(
        query
    )

    urgency = detect_urgency(
        query
    )

    specialization = detect_specialization(
        query
    )

    best_agent = None

    best_score = -1

    for agent in AGENTS:

        score = 0

        # ==========================================
        # LOCATION MATCH
        # ==========================================

        if (
            location
            and location in agent["locations"]
        ):

            score += 40

        # ==========================================
        # DEAL SIZE MATCH
        # ==========================================

        if (
            deal_size
            == agent["deal_size"]
        ):

            score += 20

        # ==========================================
        # LEAD TYPE MATCH
        # ==========================================

        if (
            lead_type
            == agent["lead_type"]
        ):

            score += 25

        # ==========================================
        # SPECIALIZATION MATCH
        # ==========================================

        if (
            specialization
            in agent["specializations"]
        ):

            score += 30

        # ==========================================
        # BASE CONVERSION
        # ==========================================

        score += int(
            agent[
                "conversion_rate"
            ] / 5
        )

        # ==========================================
        # LEARNING ENGINE
        # ==========================================

        learning_data = (

            learning_engine
            .agent_performance
            .get(
                agent["name"],
                {}
            )
        )

        live_conversion = (

            learning_data.get(
                "conversion_rate",
                agent[
                    "conversion_rate"
                ]
            )
        )

        reply_rate = (

            learning_data.get(
                "reply_rate",
                50
            )
        )

        learned_rate = max(
            live_conversion,
            get_agent_success_rate(
                agent["name"]
            )
        )

        response_speed_score = (
            agent[
                "response_speed_score"
            ]
        )

        # ==========================================
        # DYNAMIC SCORING
        # ==========================================

        score = calculate_dynamic_agent_score(

            score,

            learned_rate,

            lead_type,

            urgency,

            response_speed_score,

            agent["active_leads"]
        )

        # ==========================================
        # REPLY RATE BOOST
        # ==========================================

        score += int(
            reply_rate / 10
        )

        # ==========================================
        # OVERLOAD PROTECTION
        # ==========================================

        if agent["active_leads"] > 18:

            score -= 25

        # ==========================================
        # BEST AGENT
        # ==========================================

        if score > best_score:

            best_score = score

            best_agent = agent

    # ==========================================
    # FALLBACK
    # ==========================================

    if not best_agent:

        return {

            "assigned_agent": None,

            "agent_name": None,

            "match_score": 0,

            "specialization": None,

            "agent_data": None
        }

    # ==========================================
    # UPDATE ACTIVE LEADS
    # ==========================================

    best_agent[
        "active_leads"
    ] += 1

    # ==========================================
    # FINAL RESPONSE
    # ==========================================

    return {

        "assigned_agent":
            best_agent["name"],

        "agent_name":
            best_agent["name"],

        "match_score":
            best_score,

        "specialization":
            best_agent[
                "speciality"
            ],

        "lead_type":
            lead_type,

        "deal_size":
            deal_size,

        "urgency":
            urgency,

        "routing_reason":
            (
                f"Matched using "
                f"{specialization} specialization, "
                f"response speed, "
                f"conversion history, "
                f"and workload balancing."
            ),

        "agent_data":
            best_agent
    }