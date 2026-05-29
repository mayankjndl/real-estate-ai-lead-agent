# app/intelligence/conversation_optimizer.py

from collections import defaultdict


class ConversationOptimizer:

    def __init__(self):

        self.script_data = defaultdict(
            lambda: {
                "used": 0,
                "converted": 0,
                "reply_count": 0,
                "conversion_rate": 0.0,
                "reply_rate": 0.0
            }
        )

        self.tone_data = defaultdict(
            lambda: {
                "used": 0,
                "converted": 0,
                "reply_count": 0,
                "conversion_rate": 0.0,
                "reply_rate": 0.0
            }
        )

    # ==========================================
    # TRACK SCRIPT
    # ==========================================
    def track_script(
        self,
        script_name,
        converted=False,
        replied=False
    ):

        self.script_data[script_name]["used"] += 1

        if converted:
            self.script_data[script_name]["converted"] += 1

        if replied:
            self.script_data[script_name]["reply_count"] += 1

        used = self.script_data[script_name]["used"]

        converted_count = (
            self.script_data[script_name]["converted"]
        )

        reply_count = (
            self.script_data[script_name]["reply_count"]
        )

        self.script_data[script_name][
            "conversion_rate"
        ] = round(
            (converted_count / used) * 100,
            2
        )

        self.script_data[script_name][
            "reply_rate"
        ] = round(
            (reply_count / used) * 100,
            2
        )
    # ==========================================
    # TRACK TONE
    # ==========================================

    def track_tone(
        self,
        tone,
        converted=False,
        replied=False
    ):

        self.tone_data[tone]["used"] += 1

        if converted:
            self.tone_data[tone]["converted"] += 1

        if replied:
            self.tone_data[tone]["reply_count"] += 1

        used = self.tone_data[tone]["used"]

        converted_count = (
            self.tone_data[tone]["converted"]
        )

        reply_count = (
            self.tone_data[tone]["reply_count"]
        )

        self.tone_data[tone][
            "conversion_rate"
        ] = round(
            (converted_count / used) * 100,
            2
        )

        self.tone_data[tone][
            "reply_rate"
        ] = round(
            (reply_count / used) * 100,
            2
        )
    # ==========================================
    # BEST SCRIPT
    # ==========================================

    def get_best_script(self):

        if not self.script_data:
            return "consultative_sales_flow"

        return max(
            self.script_data.items(),
            key=lambda x: (
                x[1]["conversion_rate"] * 0.7
                + x[1]["reply_rate"] * 0.3
            )
        )[0]

    # ==========================================
    # BEST TONE
    # ==========================================

    def get_best_tone(self):

        if not self.tone_data:
            return "consultative"

        return max(
            self.tone_data.items(),
            key=lambda x: (
                x[1]["conversion_rate"] * 0.7
                + x[1]["reply_rate"] * 0.3
            )
        )[0]

    # ==========================================
    # RECOMMEND STRATEGY
    # ==========================================

    def recommend_strategy(
        self,
        probability,
        urgency,
        engagement_score=0
    ):

        if probability >= 85:
            return "direct_close"

        if urgency == "high":
            return "urgency_driven"

        if engagement_score >= 70:
            return "relationship_building"

        if probability <= 40:
            return "educational"

        return "consultative"


conversation_optimizer = (
    ConversationOptimizer()
)