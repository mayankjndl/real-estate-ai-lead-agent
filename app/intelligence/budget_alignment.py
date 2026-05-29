# app/intelligence/budget_alignment.py

import re

from app.data_manager import PUNE_LOCATIONS

# ==========================================
# PREMIUM LOCATIONS
# ==========================================

PREMIUM_LOCATIONS = [

    "baner",
    "kharadi",
    "aundh",
    "balewadi",
    "koregaon park",
    "viman nagar",
    "kalyani nagar",
    "magarpatta",
    "bavdhan",
    "wakad",
    "hinjewadi",
    "pashan",
    "boat club road",
    "model colony",
    "shivaji nagar",
    "hadapsar",
    "nibm",
    "undri",
    "tathawade",
    "punawale"
]

# ==========================================
# PARSE USER BUDGET
# ==========================================

def parse_budget_to_lakhs(text):

    text = text.lower()

    match = re.search(
        r'(\d+(?:\.\d+)?)\s*(cr|crore|l|lac|lakh)',
        text
    )

    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit in ["cr", "crore"]:
        return value * 100

    return value

# ==========================================
# EXTRACT AVG LOCATION PRICE
# ==========================================

def get_average_price(
    location,
    property_type
):

    if not location or not property_type:
        return None

    location = location.lower()

    location_data = PUNE_LOCATIONS.get(location)

    if not location_data:
        return None

    buy_data = location_data.get("buy")

    if not buy_data:
        return None

    property_data = buy_data.get(property_type)

    if not property_data:
        return None

    values = re.findall(
        r'(\d+(?:\.\d+)?)',
        property_data
    )

    if not values:
        return None

    numbers = [float(v) for v in values]

    avg = sum(numbers) / len(numbers)

    if "cr" in property_data.lower():
        avg *= 100

    return avg

# ==========================================
# BUDGET ALIGNMENT SCORING
# ==========================================

def evaluate_budget_alignment(
    budget_text,
    location,
    property_type
):

    user_budget = parse_budget_to_lakhs(
        budget_text or ""
    )

    avg_price = get_average_price(
        location,
        property_type
    )

    if not user_budget or not avg_price:

        return {
            "alignment_score": 50,
            "alignment_status": "unknown"
        }

    ratio = user_budget / avg_price

    alignment_score = 0

    alignment_status = "weak"

    # ==========================================
    # BASE ALIGNMENT
    # ==========================================

    if ratio >= 1.0:

        alignment_score = 92
        alignment_status = "excellent"

    elif ratio >= 0.85:

        alignment_score = 78
        alignment_status = "strong"

    elif ratio >= 0.65:

        alignment_score = 58
        alignment_status = "moderate"

    elif ratio >= 0.45:

        alignment_score = 35
        alignment_status = "weak"

    else:

        alignment_score = 12
        alignment_status = "very_low"

    # ==========================================
    # PREMIUM LOCATION BOOST
    # ==========================================

    if (
        location
        and location.lower() in PREMIUM_LOCATIONS
    ):

        if user_budget >= 150:

            alignment_score += 20

        elif user_budget < 70:

            alignment_score -= 18

    # ==========================================
    # LUXURY PROPERTY BOOST
    # ==========================================

    if property_type:

        property_type_lower = (
            property_type.lower()
        )

        if any(

            x in property_type_lower

            for x in [
                "villa",
                "penthouse",
                "luxury"
            ]
        ):

            if user_budget >= 250:

                alignment_score += 15

            elif user_budget < 120:

                alignment_score -= 20

    # ==========================================
    # NORMALIZATION
    # ==========================================

    alignment_score = max(
        0,
        min(100, alignment_score)
    )

    return {

        "alignment_score":
            round(alignment_score),

        "alignment_status":
            alignment_status
    }