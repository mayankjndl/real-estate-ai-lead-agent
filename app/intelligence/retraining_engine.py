from datetime import datetime

from app.intelligence.conversion_learning import (
    get_learning_summary
)
from app.intelligence.live_model_evaluator import (
    should_trigger_live_retraining,
    calculate_live_model_metrics
)
from app.intelligence.refresh_dataset_predictions import (
    refresh_predictions
)


# ==========================================
# RETRAINING ENGINE
# ==========================================

def run_retraining_cycle():

    trigger_data = (
        should_trigger_live_retraining()
    )

    metrics = (
        calculate_live_model_metrics()
    )

    if not trigger_data["trigger"]:

        return {

            "retraining_triggered":
                False,

            "message":
                "Retraining not required.",

            "metrics":
                metrics,

            "recommendations":
                trigger_data.get(
                    "recommendations",
                    []
                ),

            "generated_at":
                str(datetime.utcnow())
        }

    # ==========================================
    # REFRESH LIVE PREDICTIONS
    # ==========================================

    refresh_predictions()

    learning_summary = (
        get_learning_summary()
    )

    return {

        "retraining_triggered":
            True,

        "message":
            "Model recalibration completed successfully.",

        "metrics":
            metrics,

        "recommendations":
            trigger_data.get(
                "recommendations",
                []
            ),

        "learning_summary":
            learning_summary,

        "generated_at":
            str(datetime.utcnow())
    }