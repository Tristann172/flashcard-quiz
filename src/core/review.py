"""FIFO review over a snapshot of the cards supplied by the UI.

Independent of Streamlit and storage; does not replace the team's Manager.
"""

from collections import deque
from copy import deepcopy
from random import shuffle as shuffle_cards

from models.session import FlashcardSession


class ReviewSession:
    def __init__(self, cards: list[dict], category: str | None = None,
                 shuffle: bool = False):
        selected = [deepcopy(card) for card in cards
                    if category is None or card["category"] == category]
        if not selected:
            raise ValueError("Chủ đề này chưa có thẻ để ôn tập.")
        self.cards = {card["id"]: card for card in selected}
        if len(self.cards) != len(selected):
            raise ValueError("Bộ thẻ có mã trùng nhau. Hãy kiểm tra lại dữ liệu.")
        ids = list(self.cards)
        if shuffle:
            shuffle_cards(ids)
        self.queue = deque(ids)
        self.stats = FlashcardSession(total_questions=len(ids))
        self.current_id = self.queue.popleft()
        self.revealed = False
        self.cancelled = False

    @property
    def current_card(self) -> dict | None:
        return self.cards.get(self.current_id)

    @property
    def remaining(self) -> int:
        return len(self.queue) + int(self.current_id is not None)

    @property
    def finished(self) -> bool:
        return not self.cancelled and self.remaining == 0

    def reveal(self) -> None:
        if self.current_id is not None:
            self.revealed = True

    def answer(self, remembered: bool) -> None:
        if self.current_id is None or not self.revealed:
            raise ValueError("Hãy lật thẻ trước khi tự đánh giá.")
        self.stats.record_answer(self.current_id, remembered)
        if not remembered:
            self.queue.append(self.current_id)
        self.current_id = self.queue.popleft() if self.queue else None
        self.revealed = False

    def cancel(self) -> None:
        self.queue.clear()
        self.current_id = None
        self.revealed = False
        self.cancelled = True
