"""Entry point for card management and the two practice modes."""

import base64
import hashlib
import json
import math
import random
import sys
import time
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

# Streamlit executes this file from src; Manager imports the src package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import storage
from src.core.manager import FlashcardManager
from src.models.card import Card
from src.models.game_session import MinigameSession
from src.models.session import FlashcardSession

def styles() -> None:
    """Keep the shared interface light and readable."""
    st.markdown("""
    <style>
      .stApp { background: #f7f9fc; color: #111827; }
      .block-container { max-width: 1140px; padding-top: 2rem; }
      h1, h2, h3 { color: #111827; }
      div[data-testid="stTabs"] > div[data-baseweb="tab-list"] {
        background: #ffffff; padding: 8px; border-radius: 14px;
        box-shadow: 0 4px 14px rgba(29,38,50,.09); gap: 8px;
      }
      button[data-baseweb="tab"] { border-radius: 9px; flex: 1; font-weight: 700; color: #111827; }
      button[data-baseweb="tab"][aria-selected="true"] { background: #e2f5f1; color: #111827; }
      .st-key-tab1_editor, .st-key-tab1_library {
        background: #ffffff; border: 1px solid #d6dee6; border-radius: 14px;
        box-shadow: 0 4px 14px rgba(29,38,50,.08);
        padding: 18px 20px;
      }
      .st-key-tab1_editor [data-testid="stForm"] { border: 0; padding: 0; }
      .st-key-tab1_editor textarea,
      .st-key-tab1_editor input,
      .st-key-tab1_library input,
      .st-key-tab1_editor [data-baseweb="select"] > div,
      .st-key-tab1_library [data-baseweb="select"] > div {
        background: #ffffff !important; color: #111827 !important;
        border-color: #d6dee6 !important; border-radius: 8px;
      }
      .st-key-tab1_editor textarea::placeholder,
      .st-key-tab1_editor input::placeholder,
      .st-key-tab1_library input::placeholder { color: #64748b !important; }
      .st-key-tab1_editor label,
      .st-key-tab1_library label { color: #111827 !important; }
      .st-key-tab1_editor button[kind="primary"] {
        background: #c7eee6 !important; color: #111827 !important;
        border-color: #9edbce !important;
      }
      .st-key-tab1_editor button[kind="secondary"],
      .st-key-tab1_library button[kind="secondary"] {
        background: #f1f5f9 !important; color: #111827 !important;
        border-color: #d6dee6 !important;
      }
      .st-key-tab1_library [class*="st-key-tab1_card_"] {
        border-radius: 10px; background: #ffffff;
      }
    </style>
    """, unsafe_allow_html=True)


class CardManagementView:
    """Tab 1 moved intact into the shared UI entry point."""

    STATE_KEY = "tab1_card_management"

    DIFFICULTIES = {"Easy": "Dễ", "Medium": "Vừa", "Hard": "Khó"}

    CHOICE_IDS = ("A", "B", "C", "D")

    SAMPLE_CARDS = [
        {"id": "demo1", "category": "OOP", "difficulty": "Easy",
         "flashcard": {"question": "Tính bao đóng trong OOP là gì?",
                       "answer": "Gom dữ liệu và phương thức trong một lớp, kiểm soát truy cập.",
                       "hint": "", "image": None},
         "minigame": {"question": "Lợi ích nào thuộc về tính bao đóng?",
                      "options": {"A": "Che giấu chi tiết cài đặt", "B": "Xóa mọi thuộc tính",
                                  "C": "Kiểm soát truy cập", "D": "Không cần phương thức"},
                      "correct_ids": ["A", "C"],
                      "explanation": "Bao đóng giúp che giấu chi tiết và kiểm soát truy cập."}},
        {"id": "demo2", "category": "DSA", "difficulty": "Easy",
         "flashcard": {"question": "Cấu trúc nào hoạt động theo FIFO?",
                       "answer": "Queue (hàng đợi).", "hint": "",
                       "image": None},
         "minigame": None},
    ]

    def backend(self):
        """Use the group's Card/Storage only when their public API is available."""
        try:
            from core.storage import load_cards, save_cards, StaleCardsError
            from models.card import Card
        except ImportError:
            return None

        # --- ADAPTER: Chuyển đổi dữ liệu chuẩn của nhóm cho Hưng xài ---
        def adapted_load():
            cards, rev = load_cards()
            adapted = []
            for c in cards:
                adapted.append({
                    "id": c["id"],
                    "category": c.get("category", "OOP"),
                    "difficulty": c.get("difficulty", "Easy"),
                    "flashcard": {
                        "question": c.get("question", ""),
                        "answer": c.get("answer", ""),
                        "hint": c.get("hint", ""),
                        "image": c.get("image")
                    },
                    "minigame": {
                        "question": c.get("quiz_question", ""),
                        "options": {opt["id"]: opt["text"] for opt in c.get("options", [])},
                        "correct_ids": c.get("correct_option_ids", []),
                        "explanation": c.get("explanation", "Giải thích mặc định")
                    } if c.get("quiz_question") else None
                })
            return adapted, rev

        def adapted_save(adapted_cards, rev):
            flat_cards = []
            for c in adapted_cards:
                flat_c = {
                    "id": c["id"],
                    "category": c["category"],
                    "difficulty": c["difficulty"],
                    "question": c["flashcard"]["question"],
                    "answer": c["flashcard"]["answer"],
                    "hint": c["flashcard"].get("hint", ""),
                    "image": c["flashcard"].get("image"),
                }
                if c.get("minigame"):
                    flat_c["quiz_question"] = c["minigame"]["question"]
                    flat_c["options"] = [{"id": k, "text": v} for k, v in c["minigame"]["options"].items()]
                    flat_c["correct_option_ids"] = c["minigame"]["correct_ids"]
                    flat_c["explanation"] = c["minigame"].get("explanation", "")
                else:
                    flat_c["quiz_question"] = ""
                    flat_c["options"] = []
                    flat_c["correct_option_ids"] = []
                flat_cards.append(flat_c)
            return save_cards(flat_cards, rev)

        # Lớp Card giả để vượt qua hàm from_dict của Hưng ở line 102
        class AdapterCard:
            @classmethod
            def from_dict(cls, data):
                cls.data = data
                return cls
            def to_dict(self):
                return self.data

        return adapted_load, adapted_save, StaleCardsError, AdapterCard

    def operation_errors(self) -> tuple[type[Exception], ...]:
        api = self.backend()
        return (ValueError, OSError) if api is None else (ValueError, OSError, api[2])

    def prepare_card_values(self, values: dict) -> dict:
        """Validate required Flashcard fields and an optional, complete Minigame."""
        flash = values["flashcard"]
        game = values["minigame"]
        required = [flash["question"], flash["answer"], values["category"]]
        if any(not isinstance(value, str) or not value.strip() for value in required):
            raise ValueError("Flashcard cần câu hỏi, đáp án và chủ đề.")
        if values["difficulty"] not in self.DIFFICULTIES:
            raise ValueError("Độ khó không hợp lệ.")
        prepared = {
            "category": values["category"].strip(),
            "difficulty": values["difficulty"],
            "flashcard": {"question": flash["question"].strip(),
                          "answer": flash["answer"].strip(),
                          "hint": flash["hint"].strip(), "image": flash["image"]},
        }
        options = game["options"]
        correct = game["correct_ids"]
        has_game = any((game["question"].strip(), game["explanation"].strip(),
                        any(value.strip() for value in options.values()), bool(correct)))
        if not has_game:
            prepared["minigame"] = None
            return prepared
        if not game["question"].strip() or not game["explanation"].strip():
            raise ValueError("Khi thêm Minigame, hãy nhập câu hỏi và lời giải.")
        if set(options) != set(self.CHOICE_IDS) or any(
            not isinstance(options[key], str) or not options[key].strip() for key in self.CHOICE_IDS
        ):
            raise ValueError("Khi thêm Minigame, hãy nhập đủ bốn phương án A–D.")
        if not correct or any(key not in self.CHOICE_IDS for key in correct):
            raise ValueError("Khi thêm Minigame, hãy chọn ít nhất một đáp án đúng.")
        prepared["minigame"] = {
            "question": game["question"].strip(),
            "options": {key: options[key].strip() for key in self.CHOICE_IDS},
            "correct_ids": [key for key in self.CHOICE_IDS if key in correct],
            "explanation": game["explanation"].strip(),
        }
        return prepared

    def manager_state(self) -> dict:
        api = self.backend()
        preview = api is None
        if (self.STATE_KEY not in st.session_state
                or st.session_state[self.STATE_KEY].get("preview") != preview):
            cards, revision = (deepcopy(self.SAMPLE_CARDS), None) if preview else api[0]()
            st.session_state[self.STATE_KEY] = {
                "cards": cards, "revision": revision, "history": [],
                "editing_id": None, "form_version": 0, "show_form": False,
                "notice": None, "preview": preview,
            }
        return st.session_state[self.STATE_KEY]

    def reload_cards(self, state: dict) -> None:
        api = self.backend()
        if api is None:
            raise ValueError("Chưa thể nạp lại: Storage của nhóm chưa sẵn sàng.")
        cards, revision = api[0]()
        state.update(cards=cards, revision=revision, history=[], editing_id=None,
                     show_form=False, form_version=state["form_version"] + 1)

    def commit(self, state: dict, cards: list[dict], *, remember: bool = True) -> None:
        previous = deepcopy(state["cards"])
        api = self.backend()
        new_revision = state["revision"] if state["preview"] else api[1](cards, state["revision"])
        if remember:
            state["history"].append(previous)
        state["cards"] = deepcopy(cards)
        state["revision"] = new_revision

    def save_card(self, state: dict, values: dict, card_id: str | None = None) -> dict:
        new_id = card_id or "c" + uuid4().hex[:12]
        prepared = {"id": new_id, **self.prepare_card_values(values)}
        card = prepared if state["preview"] else self.backend()[3].from_dict(prepared).to_dict()
        cards = deepcopy(state["cards"])
        if card_id is None:
            cards.append(card)
        else:
            index = next((i for i, item in enumerate(cards) if item["id"] == card_id), None)
            if index is None:
                raise ValueError("Thẻ cần sửa không còn tồn tại.")
            cards[index] = card
        self.commit(state, cards)
        return card

    def delete_card(self, state: dict, card_id: str) -> None:
        cards = [c for c in state["cards"] if c["id"] != card_id]
        if len(cards) == len(state["cards"]):
            raise ValueError("Thẻ cần xóa không còn tồn tại.")
        self.commit(state, cards)

    def undo(self, state: dict) -> bool:
        if not state["history"]:
            return False
        previous = state["history"][-1]
        self.commit(state, previous, remember=False)
        state["history"].pop()
        return True

    def reset_form(self, state: dict) -> None:
        state["editing_id"] = None
        state["show_form"] = False
        state["form_version"] += 1

    def image_bytes(self, image: dict | None) -> bytes | None:
        return base64.b64decode(image["data"]) if image else None

    def render_form(self, state: dict) -> None:
        cards = state["cards"]
        editing = next((c for c in cards if c["id"] == state["editing_id"]), None)
        flash = editing["flashcard"] if editing else {}
        game = (editing.get("minigame") or {}) if editing else {}
        options = game.get("options", {})
        categories = sorted({"OOP", "DSA", "Python"} | {c["category"] for c in cards})
        version = state["form_version"]
        with st.container(key="tab1_editor"):
            st.markdown("### ✏️ Chỉnh sửa thẻ" if editing else "### ✏️ Tạo thẻ mới")
            if editing:
                st.caption(f"Đang sửa thẻ {editing['id']}")
            with st.form(f"tab1_form_{version}"):
                flash_col, game_col = st.columns(2, gap="large")
                with flash_col:
                    st.markdown("#### Phần Flashcard")
                    st.caption("Bắt buộc: câu hỏi, đáp án, chủ đề và độ khó.")
                    question = st.text_area("Câu hỏi (mặt trước) *", value=flash.get("question", ""),
                                            placeholder="Nhập câu hỏi...", height=90,
                                            key=f"tab1_question_{version}")
                    answer = st.text_area("Đáp án (mặt sau) *", value=flash.get("answer", ""),
                                          placeholder="Nhập câu trả lời...", height=90,
                                          key=f"tab1_answer_{version}")
                    category_col, difficulty_col = st.columns(2)
                    with category_col:
                        category = st.selectbox("Chủ đề *", categories,
                                                index=categories.index(editing["category"] if editing else "OOP"),
                                                accept_new_options=True, key=f"tab1_category_{version}")
                    with difficulty_col:
                        difficulty = st.selectbox("Độ khó *", list(self.DIFFICULTIES),
                                                  index=list(self.DIFFICULTIES).index(editing["difficulty"] if editing else "Easy"),
                                                  format_func=self.DIFFICULTIES.get,
                                                  key=f"tab1_difficulty_{version}")
                    image_enabled = st.checkbox("Thêm ảnh (không bắt buộc)",
                                                value=flash.get("image") is not None,
                                                key=f"tab1_add_image_{version}")
                    upload = None
                    if image_enabled:
                        upload = st.file_uploader("Chọn ảnh PNG, JPG hoặc WEBP (tối đa 2 MB)",
                                                  type=["png", "jpg", "jpeg", "webp"],
                                                  max_upload_size=2, key=f"tab1_image_{version}")
                        if flash.get("image") and upload is None:
                            st.caption("Ảnh hiện tại được giữ nếu không chọn ảnh mới.")
                with game_col:
                    st.markdown("#### Phần Minigame · không bắt buộc")
                    st.caption("Có thể để trống toàn bộ và bổ sung sau. Nếu thêm, cần điền đủ các mục bên dưới.")
                    game_question = st.text_area("Câu hỏi Minigame", value=game.get("question", ""),
                                                 height=90, key=f"tab1_game_question_{version}")
                    game_options = {}
                    for left, right in (("A", "B"), ("C", "D")):
                        columns = st.columns(2)
                        for column, key in zip(columns, (left, right)):
                            game_options[key] = column.text_input(f"Đáp án {key}", value=options.get(key, ""),
                                                                  key=f"tab1_option_{key}_{version}")
                    correct = st.multiselect("Đáp án đúng (chọn một hoặc nhiều)", self.CHOICE_IDS,
                                             default=game.get("correct_ids", []),
                                             key=f"tab1_correct_{version}")
                    explanation = st.text_area("Lời giải Minigame", value=game.get("explanation", ""),
                                               height=80, key=f"tab1_explanation_{version}")
                save_col, cancel_col = st.columns(2)
                save = save_col.form_submit_button("Cập nhật thẻ" if editing else "Thêm thẻ",
                                                   type="primary", width="stretch")
                cancel = cancel_col.form_submit_button("Hủy chỉnh sửa" if editing else "Nhập lại",
                                                       width="stretch")
            if cancel:
                self.reset_form(state)
                st.rerun()
            if save:
                image = None
                if image_enabled:
                    if upload is not None:
                        image = {"mime": upload.type,
                                 "data": base64.b64encode(upload.getvalue()).decode("ascii")}
                    else:
                        image = flash.get("image")
                values = {"category": category, "difficulty": difficulty,
                          "flashcard": {"question": question, "answer": answer,
                                        "hint": flash.get("hint", ""), "image": image},
                          "minigame": {"question": game_question,
                                       "options": game_options, "correct_ids": correct,
                                       "explanation": explanation}}
                try:
                    result = self.save_card(state, values, editing["id"] if editing else None)
                except self.operation_errors() as error:
                    st.error(str(error))
                else:
                    self.reset_form(state)
                    mode = "kèm Minigame" if result.get("minigame") else "chỉ gồm Flashcard"
                    state["notice"] = f"Đã {'cập nhật' if editing else 'thêm'} thẻ {result['id']} {mode}."
                    st.rerun()

    def render_library(self, state: dict) -> None:
        cards = state["cards"]
        with st.container(key="tab1_library"):
            header, count = st.columns([3, 1], vertical_alignment="center")
            header.markdown("### Bộ câu hỏi")
            count.markdown(f"**{len(cards)} câu**")
            categories = sorted({c["category"] for c in cards})
            if st.session_state.get("tab1_filter") not in ["Tất cả", *categories]:
                st.session_state["tab1_filter"] = "Tất cả"
            search_col, filter_col = st.columns([3, 1])
            search = search_col.text_input("Tìm câu hỏi", key="tab1_search",
                                           placeholder="🔍 Nhập từ khóa...").strip().casefold()
            selected = filter_col.selectbox("Chủ đề", ["Tất cả", *categories], key="tab1_filter")
            visible = [c for c in cards if (selected == "Tất cả" or c["category"] == selected)
                       and (search in c["flashcard"]["question"].casefold()
                            or search in (c.get("minigame") or {}).get("question", "").casefold())]
            if not cards:
                st.info("Chưa có câu hỏi trong bộ thẻ.")
            elif not visible:
                st.info("Không tìm thấy thẻ phù hợp.")
            else:
                with st.container(height=430, border=False):
                    for card in visible:
                        with st.container(border=True, key=f"tab1_card_{card['id']}"):
                            st.markdown(f"**{card['flashcard']['question']}**")
                            game_status = "có Minigame" if card.get("minigame") else "chưa có Minigame"
                            st.caption(f"{card['id']} · {card['category']} · "
                                       f"{self.DIFFICULTIES[card['difficulty']]} · {game_status}")
                            with st.expander("Xem đáp án"):
                                st.write(card["flashcard"]["answer"])
                                if card["flashcard"].get("image"):
                                    st.image(self.image_bytes(card["flashcard"]["image"]))
                                if card.get("minigame"):
                                    st.divider()
                                    st.write("**Minigame:**", card["minigame"]["question"])
                                    for key, option in card["minigame"]["options"].items():
                                        st.write(f"{key}. {option}")
                                    st.caption("Đáp án đúng: " + ", ".join(card["minigame"]["correct_ids"]))
                                else:
                                    st.caption("Chưa có Minigame. Chọn Sửa để bổ sung khi cần.")
                            edit_col, delete_col = st.columns(2)
                            if edit_col.button("✏️ Sửa", key=f"tab1_edit_{card['id']}", width="stretch"):
                                state["editing_id"] = card["id"]
                                state["show_form"] = True
                                state["form_version"] += 1
                                st.rerun()
                            if delete_col.button("🗑️ Xóa", key=f"tab1_delete_{card['id']}", width="stretch"):
                                try:
                                    self.delete_card(state, card["id"])
                                except self.operation_errors() as error:
                                    st.error(str(error))
                                else:
                                    if state["editing_id"] == card["id"]:
                                        self.reset_form(state)
                                    state["notice"] = f"Đã xóa thẻ {card['id']}. Có thể hoàn tác."
                                    st.rerun()

    def render(self) -> None:
        try:
            state = self.manager_state()
        except self.operation_errors() as error:
            st.error(f"Không thể đọc data/cards.json: {error}")
            return
        if state["notice"]:
            st.toast(state["notice"])
            st.success(state["notice"])
            state["notice"] = None
        title, add_col, reload_col, undo_col = st.columns([3.8, 1.5, 1.3, 1.2], vertical_alignment="center")
        title.markdown("#### Quản lý bộ câu hỏi")
        form_toggle_label = "✕ Đóng biểu mẫu" if state["show_form"] else "＋ Thêm câu hỏi"
        if add_col.button(form_toggle_label, key="tab1_add", width="stretch"):
            if state["show_form"]:
                self.reset_form(state)
            else:
                state["editing_id"] = None
                state["show_form"] = True
                state["form_version"] += 1
            st.rerun()
        if reload_col.button("↻ Nạp lại", key="tab1_reload", width="stretch",
                             disabled=state["preview"]):
            try:
                self.reload_cards(state)
            except self.operation_errors() as error:
                st.error(str(error))
            else:
                state["notice"] = "Đã nạp lại bộ thẻ từ data/cards.json."
                st.rerun()
        if undo_col.button("↩ Hoàn tác", key="tab1_undo",
                           disabled=not state["history"], width="stretch"):
            try:
                if self.undo(state):
                    self.reset_form(state)
                    state["notice"] = "Đã hoàn tác và lưu bộ thẻ."
                    st.rerun()
            except self.operation_errors() as error:
                st.error(str(error))
        if state["preview"]:
            st.info("Đang xem thử với thẻ mẫu. Thêm, sửa, xóa và hoàn tác chỉ có hiệu lực "
                    "trong phiên này; chưa lưu vào data/cards.json.")
        else:
            st.info("Flashcard là bắt buộc. Minigame có thể bổ sung sau; "
                    "thẻ được lưu qua Storage của nhóm.")
        if state["show_form"]:
            self.render_form(state)
        self.render_library(state)


CATEGORIES = ("OOP", "DSA", "Python")
LEVELS = {"Easy": "Dễ", "Medium": "Vừa", "Hard": "Khó"}
CHOICES = ("A", "B", "C", "D")
SECONDS_PER_QUESTION = 20
TAB2_STATE = "tab2_controller"


@dataclass
class ReviewDeck:
    """A read-only snapshot for Tab 2; it never replaces Tab 1's repository."""

    cards: list[Card]
    extras: dict[str, dict]
    fingerprint: str
    excluded: int
    issues: list[str]

    def select(self, category: str, minigame: bool = False) -> list[Card]:
        return [card for card in self.cards
                if (category == "All" or card.category == category)
                and (not minigame or Tab2DataAdapter.game_ready(card))]


class Tab2DataAdapter:
    """Use existing Storage/Models without touching Tab 1 or writing cards."""

    @staticmethod
    def check_json(path: Path) -> None:
        # Storage swallows JSON errors; distinguish corrupt data from an empty deck.
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, list):
                raise ValueError(f"{path.name} phải chứa một danh sách JSON.")

    def load_deck(self) -> ReviewDeck:
        self.check_json(storage.CARDS_FILE)
        rows, _ = storage.load_cards()
        if not isinstance(rows, list):
            raise ValueError("Bộ thẻ phải là một danh sách.")
        fingerprint = hashlib.sha256(json.dumps(
            rows, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        ids = Counter(str(row.get("id", "")).strip()
                      for row in rows if isinstance(row, dict))
        cards, extras, issues, excluded = [], {}, [], 0
        canonical = {name.casefold(): name for name in CATEGORIES}
        for index, row in enumerate(rows, 1):
            try:
                if not isinstance(row, dict):
                    raise ValueError("bản ghi không phải đối tượng")
                category = canonical.get(str(row.get("category", "")).strip().casefold())
                if category is None:
                    excluded += 1
                    continue
                values = deepcopy(row)
                values["category"] = category
                card = Card.from_dict(values)
                if ids[card.id] != 1:
                    raise ValueError(f"ID {card.id} bị trùng")
                if not card.answer:
                    raise ValueError("thiếu đáp án Flashcard")
                cards.append(card)
                extras[card.id] = values
            except (TypeError, ValueError, AttributeError) as error:
                issues.append(f"Thẻ {index}: {error}")
        return ReviewDeck(cards, extras, fingerprint, excluded, issues)

    @staticmethod
    def game_ready(card: Card) -> bool:
        if not card.quiz_question or not isinstance(card.options, list):
            return False
        options = card.options
        return (len(options) == 4
                and all(isinstance(option, dict) and isinstance(option.get("id"), str)
                        for option in options)
                and {option.get("id") for option in options} == set(CHOICES)
                and all(isinstance(option.get("text"), str) and option["text"].strip()
                        for option in options)
                and bool(card.correct_option_ids)
                and set(card.correct_option_ids) <= set(CHOICES)
                and len(set(card.correct_option_ids)) == len(card.correct_option_ids))

    def load_results(self) -> list[dict]:
        self.check_json(storage.LEADERBOARD_FILE)
        rows = storage.load_leaderboard()
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Bảng xếp hạng chứa bản ghi không hợp lệ.")
        for row in rows:
            score = row.get("total_score", 0)
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
                raise ValueError("Bảng xếp hạng có điểm số không hợp lệ; chưa ghi thêm kết quả.")
        return deepcopy(rows)

    def save_result(self, record: dict) -> None:
        rows = self.load_results()
        existing = next((row for row in rows if row.get("run_id") == record["run_id"]), None)
        if existing is not None:
            if any(existing.get(key) != value for key, value in record.items()):
                raise ValueError("Mã lượt chơi đã tồn tại với kết quả khác.")
            return
        if not storage.save_leaderboard([*rows, deepcopy(record)]):
            raise OSError("Storage chưa lưu được kết quả. Bạn có thể thử lại.")
        if not any(row.get("run_id") == record["run_id"] for row in self.load_results()):
            raise OSError("Chưa xác minh được kết quả đã lưu.")


class FlashcardReviewView:
    """Presentation state composed with the team's Queue and statistics."""

    def __init__(self, deck: ReviewDeck, cards: list[Card], shuffle: bool):
        ordered = deepcopy(cards)
        if not shuffle:
            ordered.sort(key=lambda card: tuple(LEVELS).index(card.difficulty))
        self.manager = FlashcardManager(ordered)
        self.manager.init_queue(shuffle=shuffle)
        self.stats = FlashcardSession()
        self.total = len(ordered)
        self.extras = deepcopy(deck.extras)
        self.source_fingerprint = deck.fingerprint
        self.current = self.manager.get_next_review_card()
        self.revealed = False
        self.run_id = uuid4().hex
        self.turn = 0

    def answer(self, remembered: bool, turn: int) -> bool:
        if self.current is None or not self.revealed or turn != self.turn:
            return False
        card_id = self.current.id
        self.revealed = False
        self.turn += 1
        self.stats.record_answer(card_id, remembered)
        if not remembered:
            self.manager.requeue_card(card_id)
        self.current = self.manager.get_next_review_card()
        return True

    def cancel(self) -> None:
        self.manager.cancel_session()
        self.current = None

    def render(self) -> None:
        if st.button("✕ Hủy phiên · Về màn hình chờ", key="tab2_review_cancel"):
            st.session_state[TAB2_STATE].reset()
            st.rerun()
        stats = self.stats
        remembered, attempts, accuracy = st.columns(3)
        remembered.metric("Thẻ đã nhớ", f"{stats.correct_count}/{self.total}")
        attempts.metric("Lượt tự đánh giá", len(stats.history))
        accuracy.metric("Tỷ lệ đã nhớ", f"{stats.get_accuracy_percentage():.1f}%")
        st.progress(stats.correct_count / self.total,
                    text=f"Đã ghi nhớ {stats.correct_count}/{self.total} thẻ")
        st.caption("Tỷ lệ đã nhớ tính trên tất cả lượt tự đánh giá, gồm các lượt học lại.")
        if self.current is None:
            st.success("Bạn đã hoàn thành phiên ôn tập!")
            self.render_rating()
            with st.expander("Lịch sử ôn tập"):
                for item in stats.history:
                    card = self.manager.get_card(item["card_id"])
                    st.write(f"{'✅' if item['is_correct'] else '↩'} {card.question}")
            if st.button("Bắt đầu phiên mới", key="tab2_review_new", type="primary", width="stretch"):
                st.session_state[TAB2_STATE].reset()
                st.rerun()
            return
        card = self.current
        with st.container(border=True, key="tab2_flashcard"):
            st.caption(f"{card.category} · {LEVELS[card.difficulty]} · Không giới hạn thời gian")
            st.markdown("#### Câu hỏi")
            st.write(card.question)
            extra = self.extras.get(card.id, {})
            if extra.get("image"):
                try:
                    st.image(base64.b64decode(extra["image"]["data"], validate=True))
                except (OSError, ValueError, TypeError, KeyError):
                    st.caption("Không thể hiển thị ảnh của thẻ này.")
            if extra.get("hint"):
                with st.expander("💡 Gợi ý"):
                    st.write(extra["hint"])
            if not self.revealed:
                if st.button("🔄 Lật thẻ xem đáp án", key=f"tab2_flip_{self.run_id}_{self.turn}",
                             type="primary", width="stretch"):
                    self.revealed = True
                    st.rerun()
            else:
                st.divider()
                st.markdown("#### Đáp án")
                st.write(card.answer)
                yes, no = st.columns(2)
                turn = self.turn
                if yes.button("✅ Đã nhớ", key=f"tab2_yes_{self.run_id}_{turn}",
                              type="primary", width="stretch"):
                    self.answer(True, turn)
                    st.rerun()
                if no.button("↩ Chưa nhớ", key=f"tab2_no_{self.run_id}_{turn}", width="stretch"):
                    self.answer(False, turn)
                    st.rerun()

    def render_rating(self) -> None:
        ratings = {"Xuất sắc": ("Xuất sắc", "excellent"), "Tốt": ("Tốt", "good"),
                   "Đạt": ("Khá", "fair"), "Cần cải thiện": ("Kém", "poor")}
        label, color = ratings.get(self.stats.get_performance_rating(), ("Chưa có dữ liệu", "fair"))
        st.markdown(f'<div class="tab2-rating tab2-{color}">Xếp loại: {label}</div>',
                    unsafe_allow_html=True)
        st.caption("Xuất sắc ≥90% · Tốt 75–<90% · Khá 50–<75% · Kém <50%")


class MinigameView:
    """UI lifecycle/timer; the existing MinigameSession owns all scoring."""

    def __init__(self, deck: ReviewDeck, cards: list[Card], player: str, category: str,
                 shuffle: bool, kind: str = "ranked", clock=None):
        if not cards:
            raise ValueError("Chưa có câu hỏi để bắt đầu Minigame.")
        self.cards = deepcopy(cards)
        self.source_fingerprint = deck.fingerprint
        self.extras = deepcopy(deck.extras)
        self.player, self.category, self.kind = player.strip(), category, kind
        config = {"cards": sorted((card.to_dict() for card in self.cards), key=lambda c: c["id"]),
                  "seconds": SECONDS_PER_QUESTION, "category": category}
        self.config_id = hashlib.sha256(json.dumps(config, sort_keys=True,
                                                  ensure_ascii=False).encode("utf-8")).hexdigest()
        if shuffle:
            random.shuffle(self.cards)
        self.shuffle = shuffle
        self.stats = MinigameSession()
        self.run_id = uuid4().hex
        self.index, self.max_streak = 0, 0
        self.elapsed = 0.0
        self.history: list[dict] = []
        self.saved, self.save_attempted, self.save_error = False, False, ""
        self.result_record = None
        self._clock = clock or time.monotonic
        self.phase = "question"
        self.started = self._clock()
        self.deadline = self.started + SECONDS_PER_QUESTION

    @property
    def question(self) -> Card:
        return self.cards[self.index]

    @property
    def time_left(self) -> int:
        return max(0, math.ceil(self.deadline - self._clock()))

    def _grade(self, selected: list[str], timed_out: bool) -> None:
        if self.phase != "question":
            return
        now = self._clock()
        remaining = 0 if timed_out else max(0, math.ceil(self.deadline - now))
        self.phase = "feedback"
        self.elapsed += min(SECONDS_PER_QUESTION, max(0, now - self.started))
        correct = not timed_out and self.question.is_correct(selected)
        self.stats.record_answer(self.question, correct, remaining)
        self.max_streak = max(self.max_streak, self.stats.streak)
        self.history.append({"card_id": self.question.id, "selected": list(selected),
                             "timed_out": timed_out, **self.stats.history[-1]})

    def expire(self) -> bool:
        if self.phase == "question" and self._clock() >= self.deadline:
            self._grade([], True)
            return True
        return False

    def answer(self, selected: list[str], card_id: str) -> None:
        if self.phase != "question" or card_id != self.question.id:
            return
        if self.expire():
            return
        if not selected or not set(selected) <= set(CHOICES):
            raise ValueError("Hãy chọn đáp án trước khi xác nhận.")
        self._grade(selected, False)

    def next_question(self) -> None:
        if self.phase != "feedback":
            return
        if self.index + 1 == len(self.cards):
            self.finish()
        else:
            self.index += 1
            self.phase = "question"
            self.started = self._clock()
            self.deadline = self.started + SECONDS_PER_QUESTION

    def finish(self) -> None:
        if self.phase == "result":
            return
        if self.phase == "question" and not self.expire():
            self.elapsed += min(SECONDS_PER_QUESTION, max(0, self._clock() - self.started))
        self.phase = "result"
        seconds = math.ceil(self.elapsed)
        summary = self.stats.submit()
        self.result_record = {**summary, "model_session_id": summary["session_id"],
                              "session_id": self.run_id, "run_id": self.run_id,
                              "player_name": self.player, "category": self.category,
                              "total_questions": len(self.cards),
                              "answered_count": self.stats.total_questions,
                              "elapsed_seconds": round(self.elapsed, 6),
                              "completion_time": f"{seconds // 60:02}:{seconds % 60:02}",
                              "max_streak": self.max_streak, "config_id": self.config_id,
                              "kind": self.kind, "seconds_per_question": SECONDS_PER_QUESTION,
                              "question_ids": [card.id for card in self.cards],
                              "played_at": datetime.now(timezone.utc).isoformat()}

    def retry(self, unanswered: bool = False):
        attempted = {item["card_id"] for item in self.history}
        wrong = {item["card_id"] for item in self.history if not item["is_correct"]}
        cards = [card for card in self.cards
                 if (card.id not in attempted if unanswered else card.id in wrong)]
        if not cards:
            return None
        deck = ReviewDeck(self.cards, self.extras, self.source_fingerprint, 0, [])
        return MinigameView(deck, cards, self.player, self.category, self.shuffle,
                            "practice_unanswered" if unanswered else "practice_wrong")

    def render_question(self) -> None:
        if self.expire():
            st.rerun()
        timer, score, streak, combo = st.columns(4)
        timer.metric("⏳ Còn lại", f"{self.time_left} giây")
        score.metric("Điểm", self.stats.total_score)
        streak.metric("Chuỗi đúng", self.stats.streak)
        combo.metric("Combo", f"×{self.stats.multiplier:g}")
        st.progress(self.index / len(self.cards), text=f"Câu {self.index + 1}/{len(self.cards)}")
        if self.time_left <= 5:
            st.warning("Sắp hết giờ! Hãy xác nhận câu trả lời.")
        card = self.question
        with st.container(border=True):
            st.caption(f"{card.category} · {LEVELS[card.difficulty]} · {card.get_base_points()} điểm cơ bản")
            st.markdown("#### Câu hỏi")
            st.write(card.quiz_question)
            options = {option["id"]: option["text"] for option in card.options}
            prefix = f"tab2_choice_{self.run_id}_{self.index}"
            if len(card.correct_option_ids) == 1:
                choice = st.radio("Chọn một đáp án", CHOICES, index=None,
                                  format_func=lambda key: f"{key}. {options[key]}", key=prefix)
                selected = [choice] if choice is not None else []
            else:
                st.caption("Chọn tất cả đáp án đúng.")
                selected = [key for key in CHOICES
                            if st.checkbox(f"{key}. {options[key]}", key=f"{prefix}_{key}")]
            if st.button("✓ Xác nhận câu trả lời", key=f"tab2_answer_{self.run_id}_{self.index}",
                         type="primary", width="stretch"):
                try:
                    self.answer(selected, card.id)
                except ValueError as error:
                    st.warning(str(error))
                else:
                    st.rerun()
        if st.button("🏁 Nộp bài", key="tab2_submit"):
            self.finish()
            st.rerun()
        st.caption("Chuyển tab không dừng đồng hồ. Nộp bài không chấm lựa chọn chưa xác nhận.")

    def render_feedback(self) -> None:
        item = self.history[-1]
        if item["timed_out"]:
            st.warning("Hết giờ · 0 điểm · Chuỗi đúng đã đặt lại.")
        elif item["is_correct"]:
            st.success(f"Chính xác! +{item['points_gained']} điểm · Combo ×{item['multiplier']:g}")
        else:
            st.error("Chưa chính xác · 0 điểm · Chuỗi đúng đã đặt lại.")
        st.write(self.question.quiz_question)
        for option in sorted(self.question.options, key=lambda value: value["id"]):
            correct = option["id"] in self.question.correct_option_ids
            chosen = option["id"] in item["selected"]
            st.write(f"{'✅' if correct else '▫️'} {option['id']}. {option['text']}"
                     + (" — Bạn chọn" if chosen else ""))
        explanation = self.extras.get(self.question.id, {}).get("explanation")
        if explanation:
            st.info(explanation)
        st.write(f"Tổng điểm: **{self.stats.total_score}** · Chuỗi cao nhất: **{self.max_streak}**")
        st.caption("Đồng hồ câu tiếp theo bắt đầu khi bạn bấm Tiếp tục.")
        if st.button("Xem kết quả" if self.index + 1 == len(self.cards) else "Tiếp tục →",
                     key="tab2_next", type="primary", width="stretch"):
            self.next_question()
            st.rerun()
        if st.button("🏁 Nộp bài", key="tab2_submit_feedback"):
            self.finish()
            st.rerun()

    def render_result(self, adapter: Tab2DataAdapter) -> None:
        if not self.save_attempted:
            self.save_attempted = True
            try:
                adapter.save_result(self.result_record)
            except (OSError, ValueError, TypeError) as error:
                self.save_error = str(error)
            else:
                self.saved, self.save_error = True, ""
        st.markdown("### 🏁 Kết quả Minigame" if self.kind == "ranked" else "### 📖 Kết quả luyện tập")
        st.write("Người chơi:", self.player)
        score, correct, streak, duration = st.columns(4)
        score.metric("Tổng điểm", self.stats.total_score)
        correct.metric("Đúng / Tổng", f"{self.stats.correct_count}/{len(self.cards)}")
        streak.metric("Chuỗi cao nhất", self.max_streak)
        duration.metric("Thời gian làm bài", f"{self.elapsed:.1f}s")
        unanswered = len(self.cards) - len(self.history)
        timed_out = sum(item["timed_out"] for item in self.history)
        wrong = sum(not item["is_correct"] for item in self.history)
        st.caption(f"{wrong - timed_out} câu sai · {timed_out} câu hết giờ · {unanswered} câu chưa trả lời. "
                   "Thời gian không tính lúc đọc phản hồi.")
        if self.saved:
            st.success("Đã lưu kết quả." if self.kind == "ranked" else "Đã lưu lượt luyện tập, tách khỏi bảng thi chính.")
        else:
            st.error("Chưa lưu được kết quả: " + self.save_error)
            if st.button("Thử lưu lại", key="tab2_retry_save"):
                self.save_attempted = False
                st.rerun()
            st.caption("Kết quả vẫn được giữ tại đây. Lưu thành công trước khi bắt đầu lượt khác.")
        with st.expander("Xem lại câu hỏi và đáp án"):
            answers = {item["card_id"]: item for item in self.history}
            for card in self.cards:
                item = answers.get(card.id)
                status = ("Chưa trả lời" if item is None else "Hết giờ" if item["timed_out"]
                          else "Đúng" if item["is_correct"] else "Sai")
                st.write(card.quiz_question)
                st.caption(status)
                if item:
                    st.write("Bạn chọn: " + (", ".join(item["selected"]) or "Không chọn"))
                labels = {option["id"]: option["text"] for option in card.options}
                st.write("Đáp án: " + "; ".join(f"{key}. {labels[key]}" for key in card.correct_option_ids))
        if st.button(f"↻ Luyện lại câu sai / hết giờ ({wrong})", key="tab2_retry_wrong",
                     disabled=wrong == 0 or not self.saved, type="primary", width="stretch"):
            st.session_state[TAB2_STATE].active = self.retry()
            st.rerun()
        if unanswered and st.button(f"Ôn các câu chưa trả lời ({unanswered})", key="tab2_retry_unanswered",
                                    disabled=not self.saved, width="stretch"):
            st.session_state[TAB2_STATE].active = self.retry(unanswered=True)
            st.rerun()
        if not wrong:
            st.caption("Không có câu sai hoặc hết giờ để luyện lại.")
        if st.button("Về màn hình chờ", key="tab2_result_lobby", disabled=not self.saved):
            st.session_state[TAB2_STATE].reset()
            st.rerun()
        if not self.saved:
            discard = st.checkbox("Rời kết quả mà không lưu", key="tab2_discard")
            if discard and st.button("Xác nhận về màn hình chờ", key="tab2_discard_confirm"):
                st.session_state[TAB2_STATE].reset()
                st.rerun()
        if self.kind == "ranked":
            LeaderboardView(adapter).render(self.config_id)


class LeaderboardView:
    """Rank copies for display; Storage's persisted ranks stay untouched."""

    def __init__(self, adapter: Tab2DataAdapter):
        self.adapter = adapter

    @staticmethod
    def duration(row: dict) -> float:
        value = row.get("elapsed_seconds")
        if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            return float(value)
        try:
            minutes, seconds = str(row["completion_time"]).split(":")
            if minutes.isdigit() and seconds.isdigit() and int(seconds) < 60:
                return int(minutes) * 60 + int(seconds)
        except (KeyError, ValueError):
            pass
        return math.inf

    @classmethod
    def ranked(cls, rows: list[dict]) -> list[dict]:
        return sorted(deepcopy(rows), key=lambda row: (-row.get("total_score", 0), cls.duration(row),
                                                       str(row.get("played_at", "")), str(row.get("run_id", ""))))

    @classmethod
    def table(cls, rows: list[dict]) -> None:
        st.dataframe([{"Hạng": index, "Người chơi": str(row.get("player_name", "")),
                       "Điểm": row.get("total_score", 0),
                       "Thời gian": (f"{cls.duration(row):.1f}s" if math.isfinite(cls.duration(row)) else "Chưa rõ")}
                      for index, row in enumerate(cls.ranked(rows), 1)], hide_index=True, width="stretch")

    def render(self, config_id: str | None = None) -> None:
        st.markdown("### 🏆 Bảng xếp hạng")
        st.caption("Cùng bộ câu và thời gian: điểm cao xếp trước; bằng điểm ưu tiên thời gian ngắn hơn.")
        try:
            rows = self.adapter.load_results()
        except (OSError, ValueError, TypeError) as error:
            st.error(f"Không thể đọc bảng xếp hạng: {error}")
            return
        competitive = [row for row in rows if row.get("kind") == "ranked" and row.get("config_id")]
        if config_id is None and competitive:
            groups = {}
            for row in sorted(competitive, key=lambda item: str(item.get("played_at", "")), reverse=True):
                groups.setdefault(row["config_id"], row)
            def label(key):
                row = groups[key]
                category = "Tất cả chủ đề" if row.get("category") == "All" else row.get("category", "")
                return f"{category} · {row.get('total_questions', 0)} câu · {row.get('played_at', '')[:10]}"
            config_id = st.selectbox("Bộ câu thi", list(groups), format_func=label, key="tab2_board_group")
        visible = [row for row in competitive if row["config_id"] == config_id]
        if visible:
            self.table(visible)
        else:
            st.info("Chưa có kết quả thi chính cho bộ câu này.")
        legacy = [row for row in rows if not row.get("config_id")]
        if legacy:
            with st.expander("Lịch sử cũ · chưa có thông tin bộ câu"):
                st.caption("Các lượt này không được xếp chung với bộ câu thi mới.")
                self.table(legacy)


@st.fragment(run_every=1)
def render_minigame_question() -> None:
    """Only the timed question refreshes; never rerun Tab 1 on every tick."""
    controller = st.session_state.get(TAB2_STATE)
    game = controller.active if controller else None
    if game is not None and game.phase == "question":
        game.render_question()


class ReviewTabView:
    def __init__(self):
        self.adapter = Tab2DataAdapter()
        self.active = None

    def reset(self) -> None:
        if self.active is not None and hasattr(self.active, "cancel"):
            self.active.cancel()
        self.active = None
        for key in list(st.session_state):
            if key.startswith(("tab2_choice_", "tab2_flip_", "tab2_yes_", "tab2_no_", "tab2_answer_")) or key == "tab2_discard":
                del st.session_state[key]

    @staticmethod
    def styles() -> None:
        st.markdown("""
        <style>
        .st-key-tab2 { color: #111827; }
        .st-key-tab2 [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
        .st-key-tab2 button[kind="primary"] {
          background: #c7eee6 !important; color: #111827 !important; border-color: #9edbce !important;
        }
        .st-key-tab2 label { color: #111827 !important; }
        .st-key-tab2 [data-baseweb="select"] > div, .st-key-tab2 input {
          background: white !important; color: #111827 !important;
        }
        .tab2-rating { border-radius: 12px; padding: 16px; font-size: 1.1rem; font-weight: 700; }
        .tab2-excellent { background: #b8ff9f; color: #153d12; }
        .tab2-good { background: #dbeafe; color: #1e40af; }
        .tab2-fair { background: #fef3c7; color: #854d0e; }
        .tab2-poor { background: #ffe4e6; color: #9f1239; }
        .tab2-landscape { height: 88px; border-radius: 14px; overflow: hidden; position: relative;
          background: linear-gradient(#9ddcff, #e8f8ff); margin-bottom: 18px; }
        .tab2-landscape:before { content: ''; position: absolute; width: 45%; height: 95px;
          background: #8bcda6; border-radius: 50%; bottom: -50px; left: -3%; box-shadow: 250px 0 #68b690; }
        .tab2-landscape:after { content: '☁  ☁'; position: absolute; top: 0; left: 12%; color: white;
          font-size: 44px; letter-spacing: 45px; }
        </style>
        """, unsafe_allow_html=True)

    def render_lobby(self, deck: ReviewDeck) -> None:
        with st.container(border=True, key="tab2_lobby"):
            st.markdown("### 🎯 Bắt đầu phiên ôn tập")
            st.write("Lật thẻ, tự đánh giá mức độ ghi nhớ và học lại những câu chưa nhớ.")
            mode = st.radio("Chọn chế độ", ["Flashcard", "Minigame"], horizontal=True, key="tab2_mode")
            category = st.selectbox("Chủ đề ôn tập", ["All", *CATEGORIES], key="tab2_category",
                                    format_func=lambda value: "Tất cả chủ đề" if value == "All" else value)
            shuffle = st.checkbox("Xáo trộn thứ tự câu hỏi", value=True, key="tab2_shuffle")
            cards = deck.select(category, minigame=mode == "Minigame")
            if mode == "Flashcard":
                st.caption("Tắt xáo trộn: học theo độ khó Dễ → Vừa → Khó.")
                st.caption(f"{len(cards)} thẻ sẵn sàng · Không giới hạn thời gian")
                player, count = "", len(cards)
            else:
                player = st.text_input("Tên người chơi", max_chars=40, key="tab2_player",
                                       placeholder="Nhập tên của bạn")
                count = 0
                if cards:
                    count = st.selectbox("Số câu", list(range(1, len(cards) + 1)),
                                         index=min(5, len(cards)) - 1, key=f"tab2_count_{category}_{len(cards)}")
                st.caption(f"{len(cards)} câu hợp lệ · {SECONDS_PER_QUESTION} giây/câu · A–D cố định")
                missing = len(deck.select(category)) - len(cards)
                if missing:
                    st.caption(f"{missing} thẻ chưa có đủ nội dung Minigame; có thể bổ sung ở Tab 1.")
                with st.expander("Luật chơi"):
                    st.write("Dễ 10 · Vừa 20 · Khó 30 điểm. Chuỗi 1–2 câu ×1; 3–4 câu ×1.5; từ 5 câu ×2.")
                    st.write("Điểm = phần nguyên của (điểm cơ bản × combo) + số giây còn lại, thưởng tối đa 10.")
                    st.write("Chọn đủ đáp án đúng, không chọn thừa. Sai hoặc hết giờ: 0 điểm, mất chuỗi; mỗi câu chấm một lần.")
                    st.write("Nộp sớm giữ điểm đã xác nhận. Luyện lại câu sai tạo lượt luyện mới, tách khỏi bảng thi chính.")
            if not cards:
                st.info("Chưa có câu phù hợp. Hãy bổ sung thẻ thuộc OOP, DSA hoặc Python ở Tab 1.")
            if st.button("🚀 Bắt đầu ôn tập" if mode == "Flashcard" else "🚀 Bắt đầu Minigame",
                         key="tab2_start", type="primary", width="stretch",
                         disabled=not cards or (mode == "Minigame" and not player.strip())):
                self.active = (FlashcardReviewView(deck, cards, shuffle) if mode == "Flashcard" else
                               MinigameView(deck, cards[:count], player, category, shuffle))
                st.rerun()
        if deck.excluded:
            st.caption(f"Tab 2 chỉ học OOP, DSA và Python; {deck.excluded} thẻ ngoài phạm vi được giữ nguyên trong kho.")
        if deck.issues:
            with st.expander(f"Có {len(deck.issues)} thẻ cần kiểm tra"):
                for issue in deck.issues:
                    st.write(issue)
        st.caption("Dữ liệu lấy từ kho thẻ Tab 1 đã lưu. Phiên đang học giữ nguyên bộ thẻ khi bắt đầu.")
        with st.expander("🏆 Xem bảng xếp hạng"):
            LeaderboardView(self.adapter).render()

    def render(self) -> None:
        self.styles()
        with st.container(key="tab2"):
            st.subheader("Ôn tập & Minigame")
            try:
                deck = self.adapter.load_deck()
            except (OSError, ValueError, TypeError) as error:
                st.error(f"Không thể đọc bộ thẻ: {error}")
                if self.active is None:
                    return
            else:
                if self.active is None:
                    self.render_lobby(deck)
                    return
                if self.active.source_fingerprint != deck.fingerprint:
                    st.info("Bộ thẻ đã thay đổi. Phiên này giữ bộ thẻ cũ; về màn hình chờ để học dữ liệu mới.")
            if hasattr(self.active, "manager"):
                self.active.render()
            else:
                st.markdown('<div class="tab2-landscape" aria-hidden="true"></div>', unsafe_allow_html=True)
                if self.active.kind != "ranked":
                    st.caption("📖 Lượt luyện tập mới · Không tính vào bảng thi chính")
                if self.active.phase == "question":
                    render_minigame_question()
                elif self.active.phase == "feedback":
                    self.active.render_feedback()
                else:
                    self.active.render_result(self.adapter)


def main() -> None:
    st.set_page_config(page_title="Flashcard Quiz Engine", layout="wide")
    styles()
    st.title("📚 Flashcard Quiz Engine")
    manager_tab, quiz_tab = st.tabs(["Manager", "Ôn tập & Minigame"])
    with manager_tab:
        CardManagementView().render()
    with quiz_tab:
        if TAB2_STATE not in st.session_state:
            st.session_state[TAB2_STATE] = ReviewTabView()
        st.session_state[TAB2_STATE].render()


if __name__ == "__main__":
    main()
