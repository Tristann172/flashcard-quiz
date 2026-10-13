"""Tab 1: manage both sides of a Card in the shared JSON repository."""

import base64
from copy import deepcopy
from uuid import uuid4

import streamlit as st

from core.storage import load_cards, save_cards, StaleCardsError
from models.card import Card, CHOICE_IDS


STATE_KEY = "tab1_card_management"
DIFFICULTIES = {"Easy": "Dễ", "Medium": "Vừa", "Hard": "Khó"}


def manager_state() -> dict:
    if STATE_KEY not in st.session_state:
        cards, revision = load_cards()
        st.session_state[STATE_KEY] = {
            "cards": cards, "revision": revision, "history": [],
            "editing_id": None, "form_version": 0, "show_form": False,
            "notice": None,
        }
    return st.session_state[STATE_KEY]


def reload_cards(state: dict) -> None:
    cards, revision = load_cards()
    state.update(cards=cards, revision=revision, history=[], editing_id=None,
                 show_form=False, form_version=state["form_version"] + 1)


def commit(state: dict, cards: list[dict], *, remember: bool = True) -> None:
    previous = deepcopy(state["cards"])
    new_revision = save_cards(cards, state["revision"])
    if remember:
        state["history"].append(previous)
    state["cards"] = deepcopy(cards)
    state["revision"] = new_revision


def save_card(state: dict, values: dict, card_id: str | None = None) -> dict:
    card = Card.from_dict({"id": card_id or "c" + uuid4().hex[:12], **values}).to_dict()
    cards = deepcopy(state["cards"])
    if card_id is None:
        cards.append(card)
    else:
        index = next((i for i, item in enumerate(cards) if item["id"] == card_id), None)
        if index is None:
            raise ValueError("Thẻ cần sửa không còn tồn tại.")
        cards[index] = card
    commit(state, cards)
    return card


def delete_card(state: dict, card_id: str) -> None:
    cards = [c for c in state["cards"] if c["id"] != card_id]
    if len(cards) == len(state["cards"]):
        raise ValueError("Thẻ cần xóa không còn tồn tại.")
    commit(state, cards)


def undo(state: dict) -> bool:
    if not state["history"]:
        return False
    previous = state["history"][-1]
    commit(state, previous, remember=False)
    state["history"].pop()
    return True


def reset_form(state: dict) -> None:
    state["editing_id"] = None
    state["show_form"] = False
    state["form_version"] += 1


def image_bytes(image: dict | None) -> bytes | None:
    return base64.b64decode(image["data"]) if image else None


def render_form(state: dict) -> None:
    cards = state["cards"]
    editing = next((c for c in cards if c["id"] == state["editing_id"]), None)
    flash = editing["flashcard"] if editing else {}
    game = editing["minigame"] if editing else {}
    options = game.get("options", {})
    categories = sorted({"OOP", "DSA", "Python"} | {c["category"] for c in cards})
    version = state["form_version"]
    with st.container(key="tab1_editor"):
        st.markdown("### ✏️ Chỉnh sửa thẻ" if editing else "### ✏️ Tạo thẻ mới")
        if editing:
            st.caption(f"Đang sửa thẻ {editing['id']}")
        with st.form(f"tab1_form_{version}"):
            question = st.text_area("Câu hỏi (mặt trước) *", value=flash.get("question", ""),
                                    placeholder="Nhập câu hỏi...", height=90,
                                    key=f"tab1_question_{version}")
            answer = st.text_area("Đáp án (mặt sau) *", value=flash.get("answer", ""),
                                  placeholder="Nhập câu trả lời...", height=90,
                                  key=f"tab1_answer_{version}")
            hint = st.text_area("Gợi ý (không bắt buộc)", value=flash.get("hint", ""),
                                placeholder="Thêm gợi ý nếu cần...", height=72,
                                key=f"tab1_hint_{version}")
            category_col, difficulty_col = st.columns(2)
            with category_col:
                category = st.selectbox("Chủ đề *", categories,
                                        index=categories.index(editing["category"] if editing else "OOP"),
                                        accept_new_options=True, key=f"tab1_category_{version}")
            with difficulty_col:
                difficulty = st.selectbox("Độ khó *", list(DIFFICULTIES),
                                          index=list(DIFFICULTIES).index(editing["difficulty"] if editing else "Easy"),
                                          format_func=DIFFICULTIES.get,
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
            st.divider()
            st.markdown("#### Câu hỏi Minigame vận dụng")
            game_question = st.text_area("Câu hỏi Minigame *", value=game.get("question", ""),
                                         height=90, key=f"tab1_game_question_{version}")
            game_options = {}
            for left, right in (("A", "B"), ("C", "D")):
                columns = st.columns(2)
                for column, key in zip(columns, (left, right)):
                    game_options[key] = column.text_input(f"Đáp án {key} *", value=options.get(key, ""),
                                                          key=f"tab1_option_{key}_{version}")
            correct = st.multiselect("Đáp án đúng * (chọn một hoặc nhiều)", CHOICE_IDS,
                                     default=game.get("correct_ids", []),
                                     key=f"tab1_correct_{version}")
            explanation = st.text_area("Lời giải Minigame *", value=game.get("explanation", ""),
                                       height=80, key=f"tab1_explanation_{version}")
            save_col, cancel_col = st.columns(2)
            save = save_col.form_submit_button("Cập nhật thẻ" if editing else "Thêm thẻ",
                                               type="primary", width="stretch")
            cancel = cancel_col.form_submit_button("Hủy chỉnh sửa" if editing else "Nhập lại",
                                                   width="stretch")
        if cancel:
            reset_form(state)
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
                                    "hint": hint, "image": image},
                      "minigame": {"question": game_question,
                                   "options": game_options, "correct_ids": correct,
                                   "explanation": explanation}}
            try:
                result = save_card(state, values, editing["id"] if editing else None)
            except (ValueError, OSError) as error:
                st.error(str(error))
            else:
                reset_form(state)
                state["notice"] = f"Đã {'cập nhật' if editing else 'thêm'} thẻ {result['id']} cho cả hai chế độ."
                st.rerun()


def render_library(state: dict) -> None:
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
                        or search in c["minigame"]["question"].casefold())]
        if not cards:
            st.info("Chưa có câu hỏi trong bộ thẻ.")
        elif not visible:
            st.info("Không tìm thấy thẻ phù hợp.")
        else:
            with st.container(height=430, border=False):
                for card in visible:
                    with st.container(border=True, key=f"tab1_card_{card['id']}"):
                        st.markdown(f"**{card['flashcard']['question']}**")
                        st.caption(f"{card['id']} · {card['category']} · {DIFFICULTIES[card['difficulty']]}")
                        with st.expander("Xem đáp án"):
                            st.write(card["flashcard"]["answer"])
                            if card["flashcard"].get("hint"):
                                st.caption("Gợi ý: " + card["flashcard"]["hint"])
                            if card["flashcard"].get("image"):
                                st.image(image_bytes(card["flashcard"]["image"]))
                            st.divider()
                            st.write("**Minigame:**", card["minigame"]["question"])
                            for key, option in card["minigame"]["options"].items():
                                st.write(f"{key}. {option}")
                            st.caption("Đáp án đúng: " + ", ".join(card["minigame"]["correct_ids"]))
                        edit_col, delete_col = st.columns(2)
                        if edit_col.button("✏️ Sửa", key=f"tab1_edit_{card['id']}", width="stretch"):
                            state["editing_id"] = card["id"]
                            state["show_form"] = True
                            state["form_version"] += 1
                            st.rerun()
                        if delete_col.button("🗑️ Xóa", key=f"tab1_delete_{card['id']}", width="stretch"):
                            try:
                                delete_card(state, card["id"])
                            except (ValueError, OSError) as error:
                                st.error(str(error))
                            else:
                                if state["editing_id"] == card["id"]:
                                    reset_form(state)
                                state["notice"] = f"Đã xóa thẻ {card['id']} khỏi cả hai chế độ. Có thể hoàn tác."
                                st.rerun()


def render_manager() -> None:
    try:
        state = manager_state()
    except (ValueError, OSError) as error:
        st.error(f"Không thể đọc data/cards.json: {error}")
        return
    if state["notice"]:
        st.toast(state["notice"])
        st.success(state["notice"])
        state["notice"] = None
    title, add_col, reload_col, undo_col = st.columns([3.8, 1.5, 1.3, 1.2], vertical_alignment="center")
    title.markdown("#### Quản lý bộ câu hỏi")
    if add_col.button("＋ Thêm câu hỏi", key="tab1_add", width="stretch"):
        state["editing_id"] = None
        state["show_form"] = True
        state["form_version"] += 1
        st.rerun()
    if reload_col.button("↻ Nạp lại", key="tab1_reload", width="stretch"):
        try:
            reload_cards(state)
        except (ValueError, OSError) as error:
            st.error(str(error))
        else:
            state["notice"] = "Đã nạp lại bộ thẻ từ data/cards.json."
            st.rerun()
    if undo_col.button("↩ Hoàn tác", key="tab1_undo",
                       disabled=not state["history"], width="stretch"):
        try:
            if undo(state):
                reset_form(state)
                state["notice"] = "Đã hoàn tác và lưu bộ thẻ."
                st.rerun()
        except (StaleCardsError, ValueError, OSError) as error:
            st.error(str(error))
    st.info("Mỗi thẻ gồm câu hỏi Flashcard và một câu hỏi Minigame vận dụng, cùng lưu trong data/cards.json.")
    if state["show_form"]:
        render_form(state)
    render_library(state)
