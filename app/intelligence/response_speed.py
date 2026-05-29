from datetime import datetime


def calculate_response_speed_score(memory):

    if not memory:
        return {
            "speed_score": 50,
            "response_pattern": "unknown"
        }

    total_gap = 0
    count = 0

    for item in memory:

        timestamp = item.get("timestamp")

        if not timestamp:
            continue

        try:
            ts = datetime.fromisoformat(timestamp)
            gap = (datetime.utcnow() - ts).total_seconds()

            total_gap += gap
            count += 1

        except Exception:
            continue

    if count == 0:
        return {
            "speed_score": 50,
            "response_pattern": "unknown"
        }

    avg_gap = total_gap / count

    # ==========================================
    # FAST ENGAGEMENT
    # ==========================================

    if avg_gap < 1800:
        return {
            "speed_score": 95,
            "response_pattern": "very_fast"
        }

    if avg_gap < 7200:
        return {
            "speed_score": 75,
            "response_pattern": "fast"
        }

    if avg_gap < 86400:
        return {
            "speed_score": 55,
            "response_pattern": "moderate"
        }

    return {
        "speed_score": 25,
        "response_pattern": "slow"
    }