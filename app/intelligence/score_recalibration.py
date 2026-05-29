# app/intelligence/score_recalibration.py

from app.intelligence.learning_engine import (
    learning_engine
)

# ==========================================
# RECALIBRATION ENGINE
# ==========================================

def recalibrate_probability(base_score):

    accuracy = (
        learning_engine
        .get_score_accuracy()
    )

    adjusted = base_score

    # ==========================================
    # SELF CALIBRATION
    # ==========================================

    if accuracy >= 85:

        adjusted += 3

    elif accuracy >= 70:

        adjusted += 1

    elif accuracy <= 45:

        adjusted -= 12

    elif accuracy <= 60:

        adjusted -= 6

    # ==========================================
    # FINAL NORMALIZATION
    # ==========================================

    adjusted = max(
        0,
        min(100, adjusted)
    )

    return adjusted