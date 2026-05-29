# app/intelligence/learning_engine.py

from collections import defaultdict

from datetime import datetime

# ==========================================
# LEARNING ENGINE
# ==========================================

class LearningEngine:

    def __init__(self):

        # ==========================================
        # SCORE FEEDBACK
        # ==========================================

        self.score_feedback = []

        # ==========================================
        # AGENT PERFORMANCE
        # ==========================================

        self.agent_performance = defaultdict(

            lambda: {

                "assigned": 0,

                "converted": 0,

                "replied": 0,

                "appointments": 0,

                "conversion_rate": 0.0,

                "reply_rate": 0.0,

                "appointment_rate": 0.0
            }
        )

        # ==========================================
        # SCRIPT PERFORMANCE
        # ==========================================

        self.script_performance = defaultdict(

            lambda: {

                "used": 0,

                "converted": 0,

                "replied": 0,

                "conversion_rate": 0.0,

                "reply_rate": 0.0
            }
        )

        # ==========================================
        # TIMING PERFORMANCE
        # ==========================================

        self.timing_performance = defaultdict(

            lambda: {

                "used": 0,

                "converted": 0,

                "conversion_rate": 0.0
            }
        )

    # ==========================================
    # SCORE FEEDBACK
    # ==========================================

    def track_score_feedback(

        self,

        session_id,

        predicted_probability,

        converted,

        confidence=1.0
    ):

        self.score_feedback.append({

            "session_id":
                session_id,

            "predicted_probability":
                predicted_probability,

            "converted":
                converted,

            "confidence":
                confidence,

            "timestamp":
                str(datetime.utcnow())
        })

    # ==========================================
    # AGENT TRACKING
    # ==========================================

    def track_agent_result(

        self,

        agent_name,

        converted=False,

        replied=False,

        appointment_booked=False
    ):

        self.agent_performance[
            agent_name
        ]["assigned"] += 1

        if converted:

            self.agent_performance[
                agent_name
            ]["converted"] += 1

        if replied:

            self.agent_performance[
                agent_name
            ]["replied"] += 1

        if appointment_booked:

            self.agent_performance[
                agent_name
            ]["appointments"] += 1

        assigned = self.agent_performance[
            agent_name
        ]["assigned"]

        converted_count = self.agent_performance[
            agent_name
        ]["converted"]

        replied_count = self.agent_performance[
            agent_name
        ]["replied"]

        appointment_count = self.agent_performance[
            agent_name
        ]["appointments"]

        # ==========================================
        # CONVERSION RATE
        # ==========================================

        self.agent_performance[
            agent_name
        ]["conversion_rate"] = round(

            (
                converted_count
                / assigned
            ) * 100,

            2
        )

        # ==========================================
        # REPLY RATE
        # ==========================================

        self.agent_performance[
            agent_name
        ]["reply_rate"] = round(

            (
                replied_count
                / assigned
            ) * 100,

            2
        )

        # ==========================================
        # APPOINTMENT RATE
        # ==========================================

        self.agent_performance[
            agent_name
        ]["appointment_rate"] = round(

            (
                appointment_count
                / assigned
            ) * 100,

            2
        )

    # ==========================================
    # SCRIPT TRACKING
    # ==========================================

    def track_script_result(

        self,

        script_name,

        converted=False,

        replied=False
    ):

        self.script_performance[
            script_name
        ]["used"] += 1

        if converted:

            self.script_performance[
                script_name
            ]["converted"] += 1

        if replied:

            self.script_performance[
                script_name
            ]["replied"] += 1

        used = self.script_performance[
            script_name
        ]["used"]

        converted_count = self.script_performance[
            script_name
        ]["converted"]

        replied_count = self.script_performance[
            script_name
        ]["replied"]

        # ==========================================
        # CONVERSION RATE
        # ==========================================

        self.script_performance[
            script_name
        ]["conversion_rate"] = round(

            (
                converted_count
                / used
            ) * 100,

            2
        )

        # ==========================================
        # REPLY RATE
        # ==========================================

        self.script_performance[
            script_name
        ]["reply_rate"] = round(

            (
                replied_count
                / used
            ) * 100,

            2
        )

    # ==========================================
    # TIMING TRACKING
    # ==========================================

    def track_timing_result(

        self,

        timing_strategy,

        converted=False
    ):

        self.timing_performance[
            timing_strategy
        ]["used"] += 1

        if converted:

            self.timing_performance[
                timing_strategy
            ]["converted"] += 1

        used = self.timing_performance[
            timing_strategy
        ]["used"]

        converted_count = self.timing_performance[
            timing_strategy
        ]["converted"]

        self.timing_performance[
            timing_strategy
        ]["conversion_rate"] = round(

            (
                converted_count
                / used
            ) * 100,

            2
        )

    # ==========================================
    # BEST AGENT
    # ==========================================

    def get_best_agent(self):

        if not self.agent_performance:

            return None

        return max(

            self.agent_performance.items(),

            key=lambda x: (
                x[1]["conversion_rate"]
                +
                (
                    x[1]["reply_rate"]
                    * 0.3
                )
            )
        )

    # ==========================================
    # BEST SCRIPT
    # ==========================================

    def get_best_script(self):

        if not self.script_performance:

            return None

        return max(

            self.script_performance.items(),

            key=lambda x: (
                x[1]["conversion_rate"]
                +
                (
                    x[1]["reply_rate"]
                    * 0.2
                )
            )
        )

    # ==========================================
    # BEST TIMING
    # ==========================================

    def get_best_timing_strategy(self):

        if not self.timing_performance:

            return None

        return max(

            self.timing_performance.items(),

            key=lambda x: x[1][
                "conversion_rate"
            ]
        )

    # ==========================================
    # SCORE ACCURACY
    # ==========================================

    def get_score_accuracy(self):

        if not self.score_feedback:

            return 0

        weighted_correct = 0

        total_weight = 0

        for item in self.score_feedback:

            predicted = item[
                "predicted_probability"
            ]

            converted = item[
                "converted"
            ]

            confidence = item.get(
                "confidence",
                1.0
            )

            is_correct = False

            # ==========================================
            # POSITIVE MATCH
            # ==========================================

            if (

                predicted >= 70
                and converted
            ):

                is_correct = True

            # ==========================================
            # NEGATIVE MATCH
            # ==========================================

            elif (

                predicted < 45
                and not converted
            ):

                is_correct = True

            if is_correct:

                weighted_correct += confidence

            total_weight += confidence

        if total_weight == 0:

            return 0

        accuracy = (

            weighted_correct
            / total_weight

        ) * 100

        return round(
            accuracy,
            2
        )

    # ==========================================
    # MODEL HEALTH
    # ==========================================

    def get_model_health(self):

        accuracy = (
            self.get_score_accuracy()
        )

        if accuracy >= 80:

            return "excellent"

        if accuracy >= 65:

            return "healthy"

        if accuracy >= 50:

            return "warning"

        return "critical"

    # ==========================================
    # PERFORMANCE SUMMARY
    # ==========================================

    def get_performance_summary(self):

        return {

            "score_accuracy":
                self.get_score_accuracy(),

            "model_health":
                self.get_model_health(),

            "best_agent":
                self.get_best_agent(),

            "best_script":
                self.get_best_script(),

            "best_timing":
                self.get_best_timing_strategy(),

            "tracked_feedback":
                len(self.score_feedback)
        }

# ==========================================
# GLOBAL INSTANCE
# ==========================================

learning_engine = LearningEngine()