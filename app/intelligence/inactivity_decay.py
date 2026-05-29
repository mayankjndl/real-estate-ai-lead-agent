# app/intelligence/inactivity_decay.py

from datetime import datetime

# ==========================================
# INACTIVITY PENALTY ENGINE
# ==========================================

def calculate_inactivity_penalty(memory):

    # ==========================================
    # EMPTY MEMORY
    # ==========================================

    if not memory:

        return {
            "penalty": 0,
            "inactive_lead": False
        }

    # ==========================================
    # MESSAGE COUNT BASED DECAY
    # ==========================================

    interaction_count = len(memory)

    # ==========================================
    # HIGHLY ACTIVE
    # ==========================================

    if interaction_count >= 8:

        return {
            "penalty": 0,
            "inactive_lead": False
        }

    # ==========================================
    # MODERATELY ACTIVE
    # ==========================================

    elif interaction_count >= 4:

        return {
            "penalty": 2,
            "inactive_lead": False
        }

    # ==========================================
    # LOW ACTIVITY
    # ==========================================

    elif interaction_count >= 2:

        return {
            "penalty": 5,
            "inactive_lead": False
        }

    # ==========================================
    # VERY LOW ACTIVITY
    # ==========================================

    else:

        return {
            "penalty": 10,
            "inactive_lead": True
        }

# ==========================================
# BACKWARD COMPATIBILITY
# ==========================================

def apply_inactivity_decay(memory):

    return calculate_inactivity_penalty(
        memory=memory
    )