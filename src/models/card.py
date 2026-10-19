
class Card:
    def __init__(self, id, question, answer, category="General",
                 difficulty="Easy", quiz_question="",
                 options=None, correct_option_ids=None):
        self.id = str(id).strip()
        self.question = str(question).strip()
        self.answer = str(answer).strip()
        self.category = str(category).strip() or "General"
        self.difficulty = str(difficulty).strip().capitalize()
        self.quiz_question = str(quiz_question).strip()
        self.options = options if options is not None else []
        self.correct_option_ids = [
            str(x) for x in (correct_option_ids if correct_option_ids is not None else [])
        ]

        if not self.id:
            raise ValueError("Card id không được để trống.")
        if not self.question:
            raise ValueError("Câu hỏi flashcard không được để trống.")
        if self.difficulty not in {"Easy", "Medium", "Hard"}:
            raise ValueError("difficulty phải là Easy, Medium hoặc Hard.")

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
            "difficulty": self.difficulty,
            "quiz_question": self.quiz_question,
            "options": self.options,
            "correct_option_ids": self.correct_option_ids
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise TypeError("Dữ liệu tạo Card phải là dictionary.")

        return cls(
            id=data.get("id", ""),
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            category=data.get("category", "General"),
            difficulty=data.get("difficulty", "Easy"),
            quiz_question=data.get("quiz_question", ""),
            options=data.get("options", []),
            correct_option_ids=data.get("correct_option_ids", [])
        )

    def is_correct(self, user_answer):
        if isinstance(user_answer, str):
            return user_answer.strip().casefold() == self.answer.casefold()

        selected = {str(x) for x in user_answer}
        correct = set(self.correct_option_ids)

        return bool(correct) and selected == correct

    def get_base_points(self):
        return {"Easy": 10, "Medium": 20, "Hard": 30}[self.difficulty]
