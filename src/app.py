"""Entry point for card management and Flashcard review."""

import base64
import hashlib
import json
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
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
TAB2_STATE = "tab2_controller"


@dataclass
class ReviewDeck:
    """A read-only snapshot for Tab 2; it never replaces Tab 1's repository."""

    cards: list[Card]
    extras: dict[str, dict]
    fingerprint: str
    excluded: int
    issues: list[str]

    def select(self, category: str) -> list[Card]:
        return [card for card in self.cards
                if category == "All" or card.category == category]


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








class ReviewTabView:
    """Quiz-only first increment, composed with the existing backend."""

    def __init__(self):
        self.adapter = Tab2DataAdapter()
        self.active = None

    def reset(self) -> None:
        if self.active is not None:
            self.active.cancel()
        self.active = None
        for key in list(st.session_state):
            if key.startswith(("tab2_flip_", "tab2_yes_", "tab2_no_")):
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
        </style>
        """, unsafe_allow_html=True)


    def render_lobby(self, deck: ReviewDeck) -> None:
        with st.container(border=True, key="tab2_lobby"):
            st.markdown("### 🎯 Bắt đầu phiên ôn tập")
            st.write("Lật thẻ, tự đánh giá mức độ ghi nhớ và học lại những câu chưa nhớ.")
            category = st.selectbox("Chủ đề ôn tập", ["All", *CATEGORIES], key="tab2_category",
                                    format_func=lambda value: "Tất cả chủ đề" if value == "All" else value)
            shuffle = st.checkbox("Xáo trộn thứ tự câu hỏi", value=True, key="tab2_shuffle")
            cards = deck.select(category)
            st.caption("Tắt xáo trộn: học theo độ khó Dễ → Vừa → Khó.")
            st.caption(f"{len(cards)} thẻ sẵn sàng · Không giới hạn thời gian")
            if not cards:
                st.info("Chưa có câu phù hợp. Hãy bổ sung thẻ thuộc OOP, DSA hoặc Python ở Tab 1.")
            if st.button("🚀 Bắt đầu ôn tập", key="tab2_start", type="primary",
                         width="stretch", disabled=not cards):
                self.active = FlashcardReviewView(deck, cards, shuffle)
                st.rerun()
        if deck.excluded:
            st.caption(f"Tab 2 chỉ học OOP, DSA và Python; {deck.excluded} thẻ ngoài phạm vi được giữ nguyên trong kho.")
        if deck.issues:
            with st.expander(f"Có {len(deck.issues)} thẻ cần kiểm tra"):
                for issue in deck.issues:
                    st.write(issue)
        st.caption("Dữ liệu lấy từ kho thẻ Tab 1 đã lưu. Phiên đang học giữ nguyên bộ thẻ khi bắt đầu.")

    def render(self) -> None:
        self.styles()
        with st.container(key="tab2"):
            st.subheader("Quiz · Ôn tập Flashcard")
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
            self.active.render()


def main() -> None:
    st.set_page_config(page_title="Flashcard Quiz Engine", layout="wide")
    styles()
    st.title("📚 Flashcard Quiz Engine")
    manager_tab, quiz_tab = st.tabs(["Manager", "Quiz"])
    with manager_tab:
        CardManagementView().render()
    with quiz_tab:
        if TAB2_STATE not in st.session_state:
            st.session_state[TAB2_STATE] = ReviewTabView()
        st.session_state[TAB2_STATE].render()


if __name__ == "__main__":
    main()
