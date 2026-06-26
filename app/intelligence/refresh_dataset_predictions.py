import json
from pathlib import Path

from app.intelligence.lead_scoring import (
    calculate_lead_score
)

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent.parent.parent
)

DATASET_PATH = (
    BASE_DIR
    / "data"
    / "sample_100_leads_dataset_v2.json"
)

def refresh_predictions():

    if not DATASET_PATH.exists():

        return False

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        leads = json.load(f)

    for lead in leads:

        query = lead.get(
            "query",
            ""
        )

        result = calculate_lead_score(
            query=query,
            memory=[],
            intent="high"
        )

        lead[
            "predicted_conversion_probability"
        ] = result.get(
            "conversion_probability",
            0
        )

    with open(
        DATASET_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            leads,
            f,
            indent=4
        )

    return True