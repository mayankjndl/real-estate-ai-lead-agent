# app/intelligence/live_model_evaluator.py

import json
from datetime import datetime
from pathlib import Path

from sklearn.metrics import (

    precision_score,

    recall_score,

    f1_score,

    confusion_matrix,

    accuracy_score
)

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

EVENT_LOG_PATH = (

    DATA_DIR
    / "live_model_events.json"
)

# ==========================================
# LOAD EVENTS
# ==========================================

def load_events():

    if not EVENT_LOG_PATH.exists():

        return []

    try:

        with open(

            EVENT_LOG_PATH,

            "r",

            encoding="utf-8"

        ) as f:

            data = json.load(f)

            if isinstance(data, list):

                return data

            return []

    except Exception:

        return []

# ==========================================
# SAVE EVENTS
# ==========================================

def save_events(events):

    try:

        with open(

            EVENT_LOG_PATH,

            "w",

            encoding="utf-8"

        ) as f:

            json.dump(

                events,

                f,

                indent=4
            )

    except Exception as e:

        print(
            f"Failed to save live events: {e}"
        )

# ==========================================
# TRACK LIVE EVENT
# ==========================================

def track_live_event(

    session_id,

    lead_score,

    assigned_agent,

    followup_variant,

    timing_strategy,

    replied=False,

    appointment_booked=False,

    converted=False
):

    events = load_events()

    event = {

        "session_id":
            session_id,

        "lead_score":
            lead_score,

        "assigned_agent":
            assigned_agent,

        "followup_variant":
            followup_variant,

        "timing_strategy":
            timing_strategy,

        "replied":
            replied,

        "appointment_booked":
            appointment_booked,

        "converted":
            converted,

        "timestamp":
            str(datetime.utcnow())
    }

    events.append(event)

    save_events(events)

# ==========================================
# FOLLOWUP ANALYTICS
# ==========================================

def calculate_followup_analytics():

    events = load_events()

    variants = {}

    for event in events:

        variant = event.get(
            "followup_variant",
            "A"
        )

        if variant not in variants:

            variants[variant] = {

                "sent": 0,

                "replied": 0,

                "appointments": 0,

                "converted": 0
            }

        variants[variant]["sent"] += 1

        if event.get("replied"):

            variants[variant]["replied"] += 1

        if event.get(
            "appointment_booked"
        ):

            variants[variant][
                "appointments"
            ] += 1

        if event.get("converted"):

            variants[variant][
                "converted"
            ] += 1

    analytics = {}

    for variant, stats in variants.items():

        sent = stats["sent"]

        if sent == 0:

            continue

        analytics[variant] = {

            "reply_rate":

                round(

                    (
                        stats["replied"]
                        / sent
                    ) * 100,

                    2
                ),

            "appointment_rate":

                round(

                    (
                        stats["appointments"]
                        / sent
                    ) * 100,

                    2
                ),

            "conversion_rate":

                round(

                    (
                        stats["converted"]
                        / sent
                    ) * 100,

                    2
                ),

            "total_sent":
                sent
        }

    return analytics

# ==========================================
# TIMING ANALYTICS
# ==========================================

def calculate_timing_analytics():

    events = load_events()

    strategies = {}

    for event in events:

        strategy = event.get(
            "timing_strategy",
            "A"
        )

        if strategy not in strategies:

            strategies[strategy] = {

                "sent": 0,

                "converted": 0
            }

        strategies[strategy][
            "sent"
        ] += 1

        if event.get("converted"):

            strategies[strategy][
                "converted"
            ] += 1

    output = {}

    for strategy, stats in strategies.items():

        sent = stats["sent"]

        if sent == 0:

            continue

        output[strategy] = {

            "conversion_rate":

                round(

                    (
                        stats["converted"]
                        / sent
                    ) * 100,

                    2
                ),

            "total_sent":
                sent
        }

    return output

# ==========================================
# AGENT PERFORMANCE ANALYTICS
# ==========================================

def calculate_agent_performance():

    events = load_events()

    agents = {}

    for event in events:

        agent = event.get(
            "assigned_agent",
            "Unknown"
        )

        if agent not in agents:

            agents[agent] = {

                "assigned": 0,

                "converted": 0,

                "replied": 0
            }

        agents[agent][
            "assigned"
        ] += 1

        if event.get("converted"):

            agents[agent][
                "converted"
            ] += 1

        if event.get("replied"):

            agents[agent][
                "replied"
            ] += 1

    results = {}

    for agent, stats in agents.items():

        assigned = stats["assigned"]

        if assigned == 0:

            continue

        results[agent] = {

            "conversion_rate":

                round(

                    (
                        stats["converted"]
                        / assigned
                    ) * 100,

                    2
                ),

            "reply_rate":

                round(

                    (
                        stats["replied"]
                        / assigned
                    ) * 100,

                    2
                ),

            "assigned_leads":
                assigned
        }

    return results

# ==========================================
# LIVE MODEL METRICS
# ==========================================

def calculate_live_model_metrics():

    events = load_events()

    if not events:

        return {

            "total_events": 0
        }

    y_true = []
    y_pred = []

    replies = 0
    appointments = 0
    conversions = 0

    for e in events:

        actual = (
            1 if e["converted"]
            else 0
        )

        predicted = (

            1
            if e["lead_score"] >= 82
            else 0
        )

        y_true.append(actual)
        y_pred.append(predicted)

        if e["replied"]:

            replies += 1

        if e[
            "appointment_booked"
        ]:

            appointments += 1

        if e["converted"]:

            conversions += 1

    precision = precision_score(

        y_true,

        y_pred,

        zero_division=0
    )

    recall = recall_score(

        y_true,

        y_pred,

        zero_division=0
    )

    f1 = f1_score(

        y_true,

        y_pred,

        zero_division=0
    )

    accuracy = accuracy_score(

        y_true,

        y_pred
    )

    matrix = confusion_matrix(

        y_true,

        y_pred

    ).tolist()

    total = len(events)

    health_score = round(

        (
            (precision * 0.30)
            + (recall * 0.30)
            + (f1 * 0.25)
            + (accuracy * 0.15)
        ) * 100,

        2
    )

    return {

        "total_events":
            total,

        "reply_rate":

            round(
                (
                    replies
                    / total
                ) * 100,
                2
            ),

        "appointment_rate":

            round(
                (
                    appointments
                    / total
                ) * 100,
                2
            ),

        "conversion_rate":

            round(
                (
                    conversions
                    / total
                ) * 100,
                2
            ),

        "precision":
            round(
                precision * 100,
                2
            ),

        "recall":
            round(
                recall * 100,
                2
            ),

        "accuracy":
            round(
                accuracy * 100,
                2
            ),

        "f1_score":
            round(
                f1 * 100,
                2
            ),

        "health_score":
            health_score,

        "confusion_matrix":
            matrix
    }

# ==========================================
# RETRAINING CHECK
# ==========================================

def should_trigger_live_retraining():

    metrics = (
        calculate_live_model_metrics()
    )

    total = metrics.get(
        "total_events",
        0
    )

    f1 = metrics.get(
        "f1_score",
        0
    )

    precision = metrics.get(
        "precision",
        0
    )

    recall = metrics.get(
        "recall",
        0
    )

    health_score = metrics.get(
        "health_score",
        0
    )

    recommendations = []

    # ==========================================
    # PRECISION CHECK
    # ==========================================

    if precision < 55:

        recommendations.append(

            "Reduce false positives by tightening hot lead threshold."
        )

    # ==========================================
    # RECALL CHECK
    # ==========================================

    if recall < 55:

        recommendations.append(

            "Improve recall by reducing over-penalization."
        )

    # ==========================================
    # F1 CHECK
    # ==========================================

    if f1 < 60:

        recommendations.append(

            "Retraining recommended using latest conversion data."
        )

    # ==========================================
    # HEALTH CHECK
    # ==========================================

    if health_score < 65:

        recommendations.append(

            "Model health degraded. Trigger recalibration."
        )

    # ==========================================
    # MINIMUM SAMPLE CHECK
    # ==========================================

    if total < 50:

        return {

            "trigger": False,

            "reason":
                "Insufficient live samples.",

            "recommendations":
                recommendations
        }

    # ==========================================
    # FINAL TRIGGER
    # ==========================================

    trigger = (

        f1 < 60
        or health_score < 65
    )

    return {

        "trigger":
            trigger,

        "reason":

            (
                "Low model performance."
                if trigger
                else "Model healthy."
            ),

        "recommendations":
            recommendations,

        "metrics":
            metrics,

        "followup_analytics":
            calculate_followup_analytics(),

        "timing_analytics":
            calculate_timing_analytics(),

        "agent_performance":
            calculate_agent_performance()
    }