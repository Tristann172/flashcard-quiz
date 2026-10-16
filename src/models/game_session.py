
from .card import Card


class MinigameSession:
    max_id = 0

    def __init__(self, total_score=0, streak=0, multiplier=1.0,
                 total_questions=0, correct_count=0, history=None):
        MinigameSession.max_id += 1
        self.session_id = "GAME" + str(MinigameSession.max_id).zfill(3)

        self.total_score = total_score
        self.streak = streak
        self.multiplier = multiplier
        self.total_questions = total_questions
        self.correct_count = correct_count
        self.history = history if history is not None else []

    def record_answer(self, card, is_correct, time_left):
        if time_left < 0:
            time_left = 0

        self.total_questions += 1
        correct = bool(is_correct)
        points_gained = 0

        if correct:
            self.correct_count += 1
            self.streak += 1

            if self.streak >= 5:
                self.multiplier = 2.0
            elif self.streak >= 3:
                self.multiplier = 1.5
            else:
                self.multiplier = 1.0

            time_bonus = min(time_left, 10)
            points_gained = int(card.get_base_points() * self.multiplier) + time_bonus
            self.total_score += points_gained
        else:
            self.streak = 0
            self.multiplier = 1.0

        self.history.append({
            "card_id": card.id,
            "is_correct": correct,
            "time_left": time_left,
            "points_gained": points_gained,
            "streak": self.streak,
            "multiplier": self.multiplier
        })

    def submit(self):
        if self.total_questions:
            accuracy = self.correct_count * 100.0 / self.total_questions
        else:
            accuracy = 0.0

        return {
            "session_id": self.session_id,
            "total_score": self.total_score,
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "accuracy_percentage": round(accuracy, 2),
            "history": list(self.history)
        }
