from collections import defaultdict


FEEDBACK_STATS = {

    "total_leads": 0,

    "converted_leads": 0,

    "failed_leads": 0,

    "high_score_conversions": 0,

    "low_score_failures": 0,

    "agent_performance": defaultdict(
        lambda: {
            "wins": 0,
            "losses": 0
        }
    ),

    "message_performance": defaultdict(
        lambda: {
            "wins": 0,
            "losses": 0
        }
    )
}


# ==========================================
# RECORD FEEDBACK
# ==========================================

def record_feedback(
    converted,
    lead_score,
    agent_name=None,
    message_type=None
):

    FEEDBACK_STATS[
        "total_leads"
    ] += 1

    if converted:

        FEEDBACK_STATS[
            "converted_leads"
        ] += 1

        if lead_score >= 70:

            FEEDBACK_STATS[
                "high_score_conversions"
            ] += 1

        if agent_name:

            FEEDBACK_STATS[
                "agent_performance"
            ][agent_name]["wins"] += 1

        if message_type:

            FEEDBACK_STATS[
                "message_performance"
            ][message_type]["wins"] += 1

    else:

        FEEDBACK_STATS[
            "failed_leads"
        ] += 1

        if lead_score < 40:

            FEEDBACK_STATS[
                "low_score_failures"
            ] += 1

        if agent_name:

            FEEDBACK_STATS[
                "agent_performance"
            ][agent_name]["losses"] += 1

        if message_type:

            FEEDBACK_STATS[
                "message_performance"
            ][message_type]["losses"] += 1


# ==========================================
# SCORE ACCURACY
# ==========================================

def calculate_score_accuracy():

    total = FEEDBACK_STATS[
        "total_leads"
    ]

    if total == 0:
        return 0

    correct_predictions = (

        FEEDBACK_STATS[
            "high_score_conversions"
        ]

        +

        FEEDBACK_STATS[
            "low_score_failures"
        ]
    )

    return round(
        (
            correct_predictions / total
        ) * 100,
        2
    )


# ==========================================
# AGENT SUCCESS RATE
# ==========================================

def get_agent_success_rate(agent_name):

    data = FEEDBACK_STATS[
        "agent_performance"
    ].get(agent_name)

    if not data:
        return 0

    total = (
        data["wins"]
        +
        data["losses"]
    )

    if total == 0:
        return 0

    return round(
        (
            data["wins"] / total
        ) * 100,
        2
    )


# ==========================================
# MESSAGE PERFORMANCE
# ==========================================

def get_best_message_type():

    best = None

    best_rate = -1

    for message_type, stats in (
        FEEDBACK_STATS[
            "message_performance"
        ].items()
    ):

        total = (
            stats["wins"]
            +
            stats["losses"]
        )

        if total == 0:
            continue

        rate = (
            stats["wins"] / total
        ) * 100

        if rate > best_rate:

            best_rate = rate

            best = message_type

    return best


# ==========================================
# SUMMARY REPORT
# ==========================================

def get_feedback_summary():

    return {

        "total_leads":
            FEEDBACK_STATS[
                "total_leads"
            ],

        "converted_leads":
            FEEDBACK_STATS[
                "converted_leads"
            ],

        "failed_leads":
            FEEDBACK_STATS[
                "failed_leads"
            ],

        "score_accuracy":
            calculate_score_accuracy(),

        "best_message_type":
            get_best_message_type()
    }