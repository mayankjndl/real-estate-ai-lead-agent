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

    # FIX: Added 'k' and 'thousand' to handle rental budgets
    match = re.search(r'(\d+(?:\.\d+)?)\s*(cr|crore|l|lac|lakh|k|thousand)', text)

    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit in ["cr", "crore"]:
        return value * 100
    elif unit in ["k", "thousand"]:
        return value / 100  # Convert thousands to lakhs (e.g., 25k -> 0.25 Lakhs)

    return value

# ==========================================
# EXTRACT AVG LOCATION PRICE
# ==========================================

import re


def get_average_price(location, property_type):
    if not location or not property_type:
        return None

    location = location.lower()
    from app.data_manager import PUNE_LOCATIONS
    location_data = PUNE_LOCATIONS.get(location)

    if not location_data:
        return None

    buy_data = location_data.get("buy")
    if not buy_data:
        return None

    # Try to find an exact match in the dictionary first (e.g., "2BHK" or "3BHK")
    property_data = None
    for key, val in buy_data.items():
        if key.upper() == property_type.upper().replace(" ", ""):
            property_data = val
            break

    # --- FIX: Dynamic Fallback for 1BHK, 4BHK, 5BHK+, and Villas ---
    if not property_data:
        base_2bhk = buy_data.get("2BHK") or buy_data.get("2bhk")
        if not base_2bhk:
            return None

        values = re.findall(r'(\d+(?:\.\d+)?)', base_2bhk)
        if not values:
            return None

        base_price = sum([float(v) for v in values]) / len(values)
        if "cr" in base_2bhk.lower():
            base_price *= 100

        pt_lower = property_type.lower()

        # 1. Handle Villas / Penthouses (Assume ~3x the cost of a standard 2BHK)
        if "villa" in pt_lower or "penthouse" in pt_lower or "row house" in pt_lower:
            return base_price * 3.0

        # 2. Handle any custom number of BHKs (1BHK, 4BHK, 5BHK, 10BHK...)
        bhk_match = re.search(r'(\d+)\s*bhk', pt_lower)
        if bhk_match:
            rooms = int(bhk_match.group(1))
            if rooms == 1:
                return base_price * 0.65  # 1BHK is ~65% of a 2BHK
            elif rooms == 4:
                return base_price * 1.8  # 4BHK is ~1.8x of a 2BHK
            elif rooms == 5:
                return base_price * 2.4  # 5BHK is ~2.4x of a 2BHK
            elif rooms >= 6:
                return base_price * 3.5  # 6BHK+ mansions

        return None
    # -------------------------------------------------------------------------------

    # Parse the exact property_data found in the dictionary
    values = re.findall(r'(\d+(?:\.\d+)?)', property_data)
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