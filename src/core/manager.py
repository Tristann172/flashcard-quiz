from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable

from src.models.action import DELETE_CARD, ActionRecord
from src.models.card import Card

ALL_CATEGORIES = "All"


class FlashcardManager:
    def __init__(
        self,
        cards: Iterable[Card] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._cards_dict: dict[str, Card] = {}
        self._review_queue: deque[str] = deque()
        self._history_stack: list[ActionRecord] = []
        self._rng = rng or random.Random()
        if cards is not None:
            self.load_cards(cards)

    # Kho thẻ (Hash)
    def load_cards(self, cards: Iterable[Card]) -> None:
        self._cards_dict = {}
        for card in cards:
            self._cards_dict.setdefault(card.id, card)
        self._review_queue.clear()
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

    # Xóa / Hoàn tác (Stack)
    def delete_card(self, card_id: str) -> bool:
        card = self._cards_dict.pop(card_id, None)
        if card is None:
            return False
        self._history_stack.append(ActionRecord(DELETE_CARD, card))
        return True

    def undo_last_action(self) -> bool:
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

    # Hàng đợi ôn tập (Queue)
    def init_queue(self, category: str = ALL_CATEGORIES, shuffle: bool = False) -> None:
        ids = [
            card.id
            for card in self._cards_dict.values()
            if category == ALL_CATEGORIES or card.category == category
        ]
        if shuffle:
            self._rng.shuffle(ids)
        self._review_queue = deque(ids)

    def cancel_session(self) -> None:
        self._review_queue.clear()

    def get_next_review_card(self) -> Card | None:
        while self._review_queue:
            card = self._cards_dict.get(self._review_queue.popleft())
            if card is not None:
                return card
        return None

    def requeue_card(self, card_id: str) -> None:
        if card_id in self._cards_dict:
            self._review_queue.append(card_id)

    def remaining_in_queue(self) -> int:
        return len(self._review_queue)