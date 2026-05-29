def classify_revenue_tier(probability):

    if probability >= 85:
        return "platinum"

    if probability >= 70:
        return "gold"

    if probability >= 50:
        return "silver"

    return "bronze"


def revenue_priority(probability, urgency):

    if probability >= 80 and urgency == "high":
        return "immediate_sales_push"

    if probability >= 60:
        return "nurture_aggressively"

    if probability >= 40:
        return "soft_followup"

    return "low_priority"