# app/intelligence/followup_ab_testing.py

import json
import random
from datetime import datetime
from pathlib import Path

# ==========================================
# STORAGE
# ==========================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent.parent.parent
)

DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(
    exist_ok=True
)

AB_RESULTS_PATH = (
    DATA_DIR
    / "followup_ab_results.json"
)

# ==========================================
# FOLLOWUP VARIANTS
# ==========================================

FOLLOWUP_VARIANTS = {

    "A": (
        "Hi! Found a few 2BHK options "
        "matching your budget."
    ),

    "B": (
        "Hi! Based on your Baner interest, "
        "I shortlisted 3 options."
    )
}

# ==========================================
# TIMING STRATEGIES
# ==========================================

TIMING_STRATEGIES = {

    "A": [
        0,
        24,
        72,
        168
    ],

    "B": [
        0,
        6,
        48,
        120
    ]
}

# ==========================================
# LOAD RESULTS
# ==========================================

def load_ab_results():

    if not AB_RESULTS_PATH.exists():

        return []

    try:

        with open(
            AB_RESULTS_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return []

# ==========================================
# SAVE RESULTS
# ==========================================

def save_ab_results(
    results
):

    with open(
        AB_RESULTS_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=4
        )

# ==========================================
# ASSIGN VARIANT
# ==========================================

def assign_followup_variant():

    return random.choice(
        list(
            FOLLOWUP_VARIANTS.keys()
        )
    )

# ==========================================
# ASSIGN TIMING STRATEGY
# ==========================================

def assign_timing_strategy():

    return random.choice(
        list(
            TIMING_STRATEGIES.keys()
        )
    )

# ==========================================
# GET FOLLOWUP MESSAGE
# ==========================================

def get_followup_message(
    variant
):

    return FOLLOWUP_VARIANTS.get(
        variant,
        FOLLOWUP_VARIANTS["A"]
    )

# ==========================================
# GET TIMING SCHEDULE
# ==========================================

def get_timing_schedule(
    strategy
):

    return TIMING_STRATEGIES.get(
        strategy,
        TIMING_STRATEGIES["A"]
    )

# ==========================================
# LOG RESULT
# ==========================================

def log_followup_result(

    session_id,

    variant,

    timing_strategy,

    replied=False,

    appointment_booked=False,

    converted=False
):

    results = load_ab_results()

    results.append({

        "session_id":
            session_id,

        "variant":
            variant,

        "timing_strategy":
            timing_strategy,

        "replied":
            replied,

        "appointment_booked":
            appointment_booked,

        "converted":
            converted,

        "timestamp":
            str(
                datetime.utcnow()
            )
    })

    save_ab_results(results)

# ==========================================
# CALCULATE PERFORMANCE
# ==========================================

def calculate_ab_performance():

    results = load_ab_results()

    variant_metrics = {}

    timing_metrics = {}

    # ==========================================
    # VARIANT ANALYTICS
    # ==========================================

    for variant in FOLLOWUP_VARIANTS:

        variant_rows = [

            r for r in results

            if r["variant"] == variant
        ]

        total = len(variant_rows)

        replies = sum(

            1 for r in variant_rows

            if r["replied"]
        )

        appointments = sum(

            1 for r in variant_rows

            if r["appointment_booked"]
        )

        conversions = sum(

            1 for r in variant_rows

            if r["converted"]
        )

        variant_metrics[variant] = {

            "total_sent":
                total,

            "reply_rate":
                round(
                    replies / total,
                    2
                ) if total else 0,

            "appointment_rate":
                round(
                    appointments / total,
                    2
                ) if total else 0,

            "conversion_rate":
                round(
                    conversions / total,
                    2
                ) if total else 0
        }

    # ==========================================
    # TIMING ANALYTICS
    # ==========================================

    for strategy in TIMING_STRATEGIES:

        strategy_rows = [

            r for r in results

            if (
                r["timing_strategy"]
                == strategy
            )
        ]

        total = len(strategy_rows)

        replies = sum(

            1 for r in strategy_rows

            if r["replied"]
        )

        appointments = sum(

            1 for r in strategy_rows

            if r["appointment_booked"]
        )

        conversions = sum(

            1 for r in strategy_rows

            if r["converted"]
        )

        timing_metrics[strategy] = {

            "total_sent":
                total,

            "reply_rate":
                round(
                    replies / total,
                    2
                ) if total else 0,

            "appointment_rate":
                round(
                    appointments / total,
                    2
                ) if total else 0,

            "conversion_rate":
                round(
                    conversions / total,
                    2
                ) if total else 0
        }

    # ==========================================
    # WINNER SELECTION
    # ==========================================

    best_variant = max(

        variant_metrics,

        key=lambda x:

        (
            variant_metrics[x][
                "conversion_rate"
            ] * 0.5

            +

            variant_metrics[x][
                "appointment_rate"
            ] * 0.3

            +

            variant_metrics[x][
                "reply_rate"
            ] * 0.2
        )
    )

    best_timing = max(

        timing_metrics,

        key=lambda x:

        (
            timing_metrics[x][
                "conversion_rate"
            ] * 0.5

            +

            timing_metrics[x][
                "appointment_rate"
            ] * 0.3

            +

            timing_metrics[x][
                "reply_rate"
            ] * 0.2
        )
    )

    return {

        "variant_performance":
            variant_metrics,

        "timing_performance":
            timing_metrics,

        "winning_variant":
            best_variant,

        "winning_timing":
            best_timing
    }

# ==========================================
# GET BEST CONFIG
# ==========================================

def get_best_followup_config():

    performance = (
        calculate_ab_performance()
    )

    return {

        "best_variant":
            performance[
                "winning_variant"
            ],

        "best_timing":
            performance[
                "winning_timing"
            ]
    }