
from uuid import uuid4


class FlashcardSession:
    def __init__(self, total_questions=0, correct_count=0, history=None, session_id=None):
        self.total_questions = total_questions
        self.correct_count = correct_count
        self.history = history if history is not None else []
        self.session_id = session_id if session_id is not None else str(uuid4())

    def record_answer(self, card_id, is_correct):
        if not card_id:
            raise ValueError("card_id không được để trống.")

        result = bool(is_correct)
        self.total_questions += 1

        if result:
            self.correct_count += 1

        self.history.append({
            "card_id": str(card_id),
            "is_correct": result
        })

    def get_accuracy_percentage(self):
        if self.total_questions == 0:
            return 0.0

        return self.correct_count * 100.0 / self.total_questions

    def get_performance_rating(self):
        if self.total_questions == 0:
            return "Chưa có dữ liệu"

        accuracy = self.get_accuracy_percentage()

        if accuracy >= 90:
            return "Xuất sắc"
        if accuracy >= 75:
            return "Tốt"
        if accuracy >= 50:
            return "Đạt"

        return "Cần cải thiện"

    def reset(self):
        self.session_id = str(uuid4())
        self.total_questions = 0
        self.correct_count = 0
        self.history.clear()
