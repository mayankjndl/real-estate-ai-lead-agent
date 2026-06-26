from datetime import datetime

from app.intelligence.feedback_loop import (
    get_feedback_summary
)
from app.intelligence.followup_ab_testing import (
    calculate_ab_performance
)
from app.intelligence.live_model_evaluator import (
    calculate_live_model_metrics
)


# ==========================================
# WEEKLY REPORT
# ==========================================

def generate_weekly_ai_report():

    metrics = (
        calculate_live_model_metrics()
    )

    ab_metrics = (
        calculate_ab_performance()
    )

    feedback = (
        get_feedback_summary()
    )

    return {

        "generated_at":
            str(datetime.utcnow()),

        "model_metrics":
            metrics,

        "ab_testing":
            ab_metrics,

        "feedback_summary":
            feedback,

        "recommendations": [

            "Review false positive hot leads.",

            "Increase followup intensity for warm leads.",

            "Retrain using latest converted sessions.",

            "Recalibrate urgency weights weekly."
        ]
    }