"""Statistics for a flashcard review; accuracy counts every attempt."""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class FlashcardSession:
    total_questions: int = 0
    session_id: str = field(default_factory=lambda: uuid4().hex)
    correct_count: int = 0
    history: list[dict] = field(default_factory=list)

    def record_answer(self, card_id: str, is_correct: bool) -> None:
        self.history.append({"card_id": card_id, "is_correct": is_correct})
        self.correct_count += int(is_correct)

    def get_accuracy_percentage(self) -> float:
        return 100 * self.correct_count / len(self.history) if self.history else 0.0

    def get_performance_rating(self) -> str:
        accuracy = self.get_accuracy_percentage()
        for threshold, label in ((90, "Xuất sắc"), (75, "Tốt"), (50, "Khá")):
            if accuracy >= threshold:
                return label
        return "Cần cải thiện"

    def reset(self) -> None:
        self.session_id = uuid4().hex
        self.correct_count = 0
        self.history.clear()
