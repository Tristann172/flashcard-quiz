from __future__ import annotations

import random

from src.models.action import DELETE_CARD, ActionRecord
from src.models.card import Card

ALL_CATEGORIES = "All"
_COMPACT_THRESHOLD = 32  # chỉ dọn phần đã lấy ra khi hàng đợi đủ lớn


class FlashcardManager:
    def __init__(
        self,
        cards: list[Card] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._cards_dict: dict[str, Card] = {}
        self._review_queue: list[str] = [] #queue tu setup
        self._head: int = 0
        self._history_stack: list[ActionRecord] = []
        self._rng = rng or random.Random()
        if cards is not None:
            self.load_cards(cards)

    # Kho thẻ (Hash Map)
    def load_cards(self, cards: list[Card]) -> None:
        self._cards_dict = {}
        for card in cards:
            self._cards_dict.setdefault(card.id, card)
        self._reset_queue([])
        self._history_stack.clear()

    def get_card(self, card_id: str) -> Card | None:
        return self._cards_dict.get(card_id)

    def get_all_cards(self) -> list[Card]:
        return list(self._cards_dict.values())

    def add_card(self, card: Card) -> bool:
        if card.id in self._cards_dict:
            return False
        self._cards_dict[card.id] = card
        return True

    def update_card(self, card_id: str, updated_card: Card) -> bool:
        if card_id not in self._cards_dict or updated_card.id != card_id:
            return False
        self._cards_dict[card_id] = updated_card
        return True

    def get_all_categories(self) -> set[str]:
        return {card.category for card in self._cards_dict.values()}

    # Xóa / Hoàn tác (Stack LIFO)
    def delete_card(self, card_id: str) -> bool:
        """Xóa thẻ và đẩy ActionRecord vào đỉnh Undo Stack."""
        card = self._cards_dict.pop(card_id, None)
        if card is None:
            return False
        self._history_stack.append(ActionRecord(DELETE_CARD, card))
        return True

    def undo_last_action(self) -> bool:
        """Rút phần tử đỉnh Stack và khôi phục.
        """
        if not self._history_stack:
            return False
        record = self._history_stack.pop()
        if record.action_type != DELETE_CARD:
            return False
        card: Card = record.payload
        if card.id in self._cards_dict:
            return False
        self._cards_dict[card.id] = card
        return True

    def can_undo(self) -> bool:
        return bool(self._history_stack)

    # Hàng đợi ôn tập (Queue FIFO)
    def _reset_queue(self, ids: list[str]) -> None:
        self._review_queue = ids
        self._head = 0

    def init_queue(self, category: str = ALL_CATEGORIES, shuffle: bool = False) -> None:
        # Nạp card_id vào hàng đợi ôn tập, có thể lọc theo category/tráo.
        ids = [
            card.id
            for card in self._cards_dict.values()
            if category == ALL_CATEGORIES or card.category == category
        ]
        if shuffle:
            self._rng.shuffle(ids)
        self._reset_queue(ids)

    def cancel_session(self) -> None:
        """Hủy phiên ôn tập: xóa sạch hàng đợi."""
        self._reset_queue([])

    def _dequeue(self) -> str | None:
        # Lấy card_id ở đầu hàng đợi.
        if self._head >= len(self._review_queue):
            return None
        card_id = self._review_queue[self._head]
        self._head += 1
        # Dọn phần đã lấy ra để list không phình khi requeue nhiều lần
        if (
            self._head >= _COMPACT_THRESHOLD
            and self._head * 2 >= len(self._review_queue)
        ):
            self._review_queue = self._review_queue[self._head :]
            self._head = 0
        return card_id

    def get_next_review_card(self) -> Card | None:
        # Lấy thẻ ở đầu hàng đợi. None khi hết thẻ.
        while (card_id := self._dequeue()) is not None:
            card = self._cards_dict.get(card_id)
            if card is not None:
                return card
        return None

    def requeue_card(self, card_id: str) -> None:
        # Đẩy thẻ (trả lời sai / chưa nhớ) về cuối hàng đợi.
        if card_id in self._cards_dict:
            self._review_queue.append(card_id)

    def remaining_in_queue(self) -> int:
        # Số thẻ còn trong hàng đợi.
        return len(self._review_queue) - self._head