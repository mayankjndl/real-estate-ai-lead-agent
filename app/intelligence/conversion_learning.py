from collections import defaultdict
from statistics import mean


# ==========================================
# IN-MEMORY LEARNING STORE
# ==========================================

LEARNING_DB = {

    "successful_scores": [],

    "failed_scores": [],

    "successful_tones": defaultdict(int),

    "failed_tones": defaultdict(int),

    "successful_scripts": defaultdict(int),

    "failed_scripts": defaultdict(int),

    "agent_success": defaultdict(int),

    "agent_failures": defaultdict(int),

    "retraining_events": []
}


# ==========================================
# RECORD CONVERSION RESULT
# ==========================================

def record_conversion_result(

    converted,
    lead_score,
    tone=None,
    script=None,
    agent_name=None
):

    if converted:

        LEARNING_DB["successful_scores"].append(
            lead_score
        )

        if tone:

            LEARNING_DB[
                "successful_tones"
            ][tone] += 1

        if script:

            LEARNING_DB[
                "successful_scripts"
            ][script] += 1

        if agent_name:

            LEARNING_DB[
                "agent_success"
            ][agent_name] += 1

    else:

        LEARNING_DB["failed_scores"].append(
            lead_score
        )

        if tone:

            LEARNING_DB[
                "failed_tones"
            ][tone] += 1

        if script:

            LEARNING_DB[
                "failed_scripts"
            ][script] += 1

        if agent_name:

            LEARNING_DB[
                "agent_failures"
            ][agent_name] += 1


# ==========================================
# SCORE CALIBRATION
# ==========================================

def get_score_calibration():

    success = LEARNING_DB[
        "successful_scores"
    ]

    failed = LEARNING_DB[
        "failed_scores"
    ]

    return {

        "avg_success_score":
            round(mean(success), 2)
            if success else 0,

        "avg_failed_score":
            round(mean(failed), 2)
            if failed else 0,

        "successful_samples":
            len(success),

        "failed_samples":
            len(failed)
    }


# ==========================================
# BEST TONE
# ==========================================

def get_best_tone():

    if not LEARNING_DB[
        "successful_tones"
    ]:
        return "consultative"

    return max(
        LEARNING_DB[
            "successful_tones"
        ],
        key=LEARNING_DB[
            "successful_tones"
        ].get
    )


# ==========================================
# BEST SCRIPT
# ==========================================

def get_best_script():

    if not LEARNING_DB[
        "successful_scripts"
    ]:
        return "default_sales_flow"

    return max(
        LEARNING_DB[
            "successful_scripts"
        ],
        key=LEARNING_DB[
            "successful_scripts"
        ].get
    )


# ==========================================
# AGENT PERFORMANCE
# ==========================================

def get_agent_performance(agent_name):

    wins = LEARNING_DB[
        "agent_success"
    ].get(agent_name, 0)

    losses = LEARNING_DB[
        "agent_failures"
    ].get(agent_name, 0)

    total = wins + losses

    if total == 0:

        return {
            "success_rate": 0,
            "total_deals": 0
        }

    return {

        "success_rate": round(
            (wins / total) * 100,
            2
        ),

        "total_deals": total
    }


# ==========================================
# RETRAINING CHECK
# ==========================================

def should_trigger_retraining():

    total_samples = (

        len(
            LEARNING_DB[
                "successful_scores"
            ]
        )

        +

        len(
            LEARNING_DB[
                "failed_scores"
            ]
        )
    )

    if total_samples >= 50:

        LEARNING_DB[
            "retraining_events"
        ].append({
            "sample_size": total_samples
        })

        return True

    return False


# ==========================================
# LEARNING SUMMARY
# ==========================================

def get_learning_summary():

    return {

        "calibration":
            get_score_calibration(),

        "best_tone":
            get_best_tone(),

        "best_script":
            get_best_script(),

        "retraining_ready":
            should_trigger_retraining()
    }