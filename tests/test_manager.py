import random

import pytest

from src.core.manager import FlashcardManager
from src.models.action import DELETE_CARD, ActionRecord
from src.models.card import Card


def make_card(cid: str, category: str = "OOP", difficulty: str = "Easy") -> Card:
    return Card(cid, f"Q {cid}", f"A {cid}", category, difficulty)


@pytest.fixture
def manager() -> FlashcardManager:
    return FlashcardManager(
        [
            make_card("c1", "OOP"),
            make_card("c2", "DSA"),
            make_card("c3", "Python"),
            make_card("c4", "DSA"),
        ],
        rng=random.Random(42),
    )


def drain(m: FlashcardManager) -> list[str]:
    out = []
    while (card := m.get_next_review_card()) is not None:
        out.append(card.id)
    return out


# ---------- ActionRecord ----------
def test_action_record_fields():
    rec = ActionRecord("DELETE_CARD", {"x": 1})
    assert rec.action_type == "DELETE_CARD"
    assert rec.payload == {"x": 1}


# ---------- Hash Map: CRUD ----------
def test_add_card_ok_and_duplicate_id(manager):
    assert manager.add_card(make_card("c5")) is True
    assert manager.get_card("c5") is not None
    assert manager.add_card(make_card("c5")) is False  # trùng id
    assert len(manager.get_all_cards()) == 5


def test_update_card(manager):
    new = Card("c1", "Q mới", "A mới", "OOP", "Hard")
    assert manager.update_card("c1", new) is True
    assert manager.get_card("c1").question == "Q mới"


def test_update_card_missing_or_id_mismatch(manager):
    assert manager.update_card("zzz", make_card("zzz")) is False
    assert manager.update_card("c1", make_card("c9")) is False
    assert manager.get_card("c1").question == "Q c1"  # không đổi


def test_get_all_categories_is_unique_set(manager):
    assert manager.get_all_categories() == {"OOP", "DSA", "Python"}


def test_load_cards_ignores_duplicates_and_resets_state():
    m = FlashcardManager()
    m.load_cards([make_card("c1"), make_card("c1", "DSA")])
    assert len(m.get_all_cards()) == 1
    assert m.get_card("c1").category == "OOP"  # giữ thẻ đầu
    m.delete_card("c1")
    m.load_cards([make_card("c2")])
    assert m.can_undo() is False


def test_empty_manager():
    m = FlashcardManager()
    assert m.get_all_cards() == []
    assert m.get_all_categories() == set()
    m.init_queue()
    assert m.get_next_review_card() is None


# ---------- Stack: Delete / Undo ----------
def test_delete_pushes_record_and_removes_card(manager):
    original = manager.get_card("c2")
    assert manager.delete_card("c2") is True
    assert manager.get_card("c2") is None

    record = manager._history_stack[-1]
    assert record.action_type == DELETE_CARD
    assert record.payload is original  # đúng đối tượng thẻ vừa xóa


def test_delete_missing_card_returns_false_and_no_record(manager):
    assert manager.delete_card("nope") is False
    assert manager.can_undo() is False


def test_undo_restores_deleted_card(manager):
    manager.delete_card("c2")
    assert manager.undo_last_action() is True
    assert manager.get_card("c2") is not None
    assert manager.can_undo() is False


def test_undo_on_empty_stack_returns_false(manager):
    assert manager.undo_last_action() is False


def test_undo_is_lifo(manager):
    manager.delete_card("c1")
    manager.delete_card("c2")
    manager.delete_card("c3")
    manager.undo_last_action()
    assert manager.get_card("c3") is not None
    assert manager.get_card("c2") is None
    manager.undo_last_action()
    assert manager.get_card("c2") is not None
    assert manager.get_card("c1") is None


def test_undo_conflict_when_id_reused(manager):
    manager.delete_card("c1")
    manager.add_card(make_card("c1", "Python"))  # id c1 bị thẻ khác chiếm
    assert manager.undo_last_action() is False
    assert manager.get_card("c1").category == "Python"  # thẻ mới còn nguyên


def test_undo_unknown_action_type_returns_false(manager):
    manager._history_stack.append(ActionRecord("EDIT_CARD", None))
    assert manager.undo_last_action() is False


# ---------- Queue: FIFO ----------
def test_init_queue_all_keeps_insertion_order(manager):
    manager.init_queue()
    assert drain(manager) == ["c1", "c2", "c3", "c4"]


def test_init_queue_filters_by_category(manager):
    manager.init_queue(category="DSA")
    assert drain(manager) == ["c2", "c4"]


def test_init_queue_unknown_category_is_empty(manager):
    manager.init_queue(category="Không có")
    assert manager.get_next_review_card() is None


def test_init_queue_shuffle_keeps_same_cards(manager):
    manager.init_queue(shuffle=True)
    assert sorted(drain(manager)) == ["c1", "c2", "c3", "c4"]


def test_init_queue_shuffle_is_reproducible_with_seed():
    cards = [make_card(f"c{i}") for i in range(10)]
    m1 = FlashcardManager(cards, rng=random.Random(7))
    m2 = FlashcardManager(cards, rng=random.Random(7))
    m1.init_queue(shuffle=True)
    m2.init_queue(shuffle=True)
    assert drain(m1) == drain(m2)


def test_init_queue_resets_previous_queue(manager):
    manager.init_queue()
    manager.get_next_review_card()
    manager.init_queue(category="OOP")
    assert drain(manager) == ["c1"]


def test_requeue_sends_card_to_back(manager):
    manager.init_queue()
    first = manager.get_next_review_card()
    manager.requeue_card(first.id)
    assert drain(manager) == ["c2", "c3", "c4", "c1"]


def test_requeue_unknown_card_is_ignored(manager):
    manager.init_queue(category="OOP")
    manager.requeue_card("nope")
    assert manager.remaining_in_queue() == 1


def test_cancel_session_clears_queue(manager):
    manager.init_queue()
    manager.cancel_session()
    assert manager.remaining_in_queue() == 0
    assert manager.get_next_review_card() is None


def test_remaining_in_queue_counts_down(manager):
    manager.init_queue()
    assert manager.remaining_in_queue() == 4
    manager.get_next_review_card()
    assert manager.remaining_in_queue() == 3


def test_deleted_card_is_skipped_in_queue(manager):
    manager.init_queue()
    manager.delete_card("c1")
    assert drain(manager) == ["c2", "c3", "c4"]


def test_review_loop_until_all_remembered(manager):
    """Mô phỏng: câu c1 sai 2 lần rồi mới nhớ."""
    manager.init_queue()
    wrong_left = {"c1": 2}
    seen = []
    while (card := manager.get_next_review_card()) is not None:
        seen.append(card.id)
        if wrong_left.get(card.id, 0) > 0:
            wrong_left[card.id] -= 1
            manager.requeue_card(card.id)
    assert seen == ["c1", "c2", "c3", "c4", "c1", "c1"]


def test_queue_stays_correct_after_compaction():
    """Hàng đợi lớn + requeue nhiều lần: thứ tự FIFO vẫn đúng sau khi dọn list."""
    cards = [make_card(f"c{i}") for i in range(100)]
    m = FlashcardManager(cards)
    m.init_queue()
    expected = [f"c{i}" for i in range(100)]
    seen = []
    requeued = 0
    while (card := m.get_next_review_card()) is not None:
        seen.append(card.id)
        if requeued < 50 and int(card.id[1:]) % 2 == 0:
            requeued += 1
            m.requeue_card(card.id)
            expected.append(card.id)
    assert seen == expected
    assert m.remaining_in_queue() == 0