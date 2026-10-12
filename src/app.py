"""Flashcard Quiz Engine. Tab 1 uses session-only demo data until Manager is ready."""

from __future__ import annotations

from copy import deepcopy

import streamlit as st


TAB1_STATE_KEY = "tab1_card_management"
TAB1_DIFFICULTIES = {"Easy": "Dễ", "Medium": "Vừa", "Hard": "Khó"}
TAB1_SAMPLE_CARDS = [
    {"id": "c1", "question": "Tính bao đóng trong OOP là gì?",
     "answer": "Gom dữ liệu và phương thức vào một lớp, kiểm soát truy cập từ bên ngoài.",
     "category": "OOP", "difficulty": "Easy", "hint": "Encapsulation", "image": None},
    {"id": "c2", "question": "Cấu trúc nào hoạt động theo FIFO?",
     "answer": "Queue (hàng đợi).", "category": "DSA", "difficulty": "Easy",
     "hint": "First In, First Out", "image": None},
    {"id": "c3", "question": "append() của collections.deque có độ phức tạp bao nhiêu?",
     "answer": "O(1).", "category": "Python", "difficulty": "Medium",
     "hint": "Thao tác ở cuối deque", "image": None},
]


def tab1_state() -> dict:
    """Create demo cards once per browser session, not once per rerun."""
    if TAB1_STATE_KEY not in st.session_state:
        st.session_state[TAB1_STATE_KEY] = {
            "cards": deepcopy(TAB1_SAMPLE_CARDS), "history": [],
            "editing_id": None, "form_version": 0,
            "notice": None, "show_form": False,
        }
    state = st.session_state[TAB1_STATE_KEY]
    state.setdefault("show_form", False)
    return state


def tab1_cards(state: dict) -> list[dict]:
    return deepcopy(state["cards"])


def tab1_next_id(state: dict) -> str:
    used = {card["id"] for card in state["cards"]}
    for snapshot in state["history"]:
        used.update(card["id"] for card in snapshot)
    number = 1
    while f"c{number}" in used:
        number += 1
    return f"c{number}"


def tab1_commit(state: dict, cards: list[dict]) -> None:
    """Push old cards onto the undo stack, then change session memory."""
    state["history"].append(tab1_cards(state))
    state["cards"] = deepcopy(cards)


def tab1_save_card(state: dict, values: dict, card_id: str | None = None) -> dict:
    """Demo data operation. Replace here with Manager calls at integration time."""
    cleaned = {}
    for field in ("question", "answer", "category"):
        value = values.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Hãy nhập câu hỏi, đáp án và chủ đề.")
        cleaned[field] = value.strip()
    if values.get("difficulty") not in TAB1_DIFFICULTIES:
        raise ValueError("Độ khó không hợp lệ.")
    cleaned["difficulty"] = values["difficulty"]
    cleaned["hint"] = (values.get("hint") or "").strip()
    cleaned["image"] = values.get("image")
    cards = tab1_cards(state)
    if card_id is None:
        card = {"id": tab1_next_id(state), **cleaned}
        cards.append(card)
    else:
        index = next((i for i, item in enumerate(cards) if item["id"] == card_id), None)
        if index is None:
            raise ValueError("Thẻ cần sửa không còn tồn tại.")
        card = {**cards[index], **cleaned}
        cards[index] = card
    tab1_commit(state, cards)
    return deepcopy(card)


def tab1_delete_card(state: dict, card_id: str) -> None:
    cards = tab1_cards(state)
    remaining = [card for card in cards if card["id"] != card_id]
    if len(remaining) == len(cards):
        raise ValueError("Thẻ cần xóa không còn tồn tại.")
    tab1_commit(state, remaining)


def tab1_undo(state: dict) -> bool:
    if not state["history"]:
        return False
    state["cards"] = state["history"].pop()
    return True


def tab1_reset_form(state: dict) -> None:
    state["editing_id"] = None
    state["show_form"] = False
    state["form_version"] += 1


def tab1_notice(state: dict, message: str) -> None:
    state["notice"] = message
    st.rerun()


def tab1_styles() -> None:
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
      .st-key-tab1_library input,
      .st-key-tab1_editor [data-baseweb="select"] > div,
      .st-key-tab1_library [data-baseweb="select"] > div {
        background: #ffffff !important; color: #111827 !important;
        border-color: #d6dee6 !important; border-radius: 8px;
      }
      .st-key-tab1_editor textarea::placeholder,
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


def tab1_render_form(state: dict, cards: list[dict]) -> None:
    editing = next((card for card in cards if card["id"] == state["editing_id"]), None)
    initial = editing or {"question": "", "answer": "", "hint": "", "category": "OOP",
                          "difficulty": "Easy", "image": None}
    categories = sorted({"OOP", "DSA", "Python"} | {card["category"] for card in cards})
    version = state["form_version"]
    with st.container(key="tab1_editor"):
        st.markdown("### ✏️ Chỉnh sửa thẻ" if editing else "### ✏️ Tạo thẻ mới")
        if editing:
            st.caption(f"Đang sửa thẻ {editing['id']}")
        with st.form(f"tab1_form_{version}"):
            question = st.text_area("Câu hỏi (mặt trước) *", value=initial["question"],
                                    placeholder="Nhập câu hỏi...", height=90,
                                    key=f"tab1_question_{version}")
            answer = st.text_area("Đáp án (mặt sau) *", value=initial["answer"],
                                  placeholder="Nhập câu trả lời...", height=90,
                                  key=f"tab1_answer_{version}")
            hint = st.text_area("Gợi ý (không bắt buộc)", value=initial.get("hint", ""),
                                placeholder="Thêm gợi ý nếu cần...", height=72,
                                key=f"tab1_hint_{version}")
            category_col, difficulty_col = st.columns(2)
            with category_col:
                category = st.selectbox("Chủ đề *", categories,
                                        index=categories.index(initial["category"]),
                                        accept_new_options=True,
                                        key=f"tab1_category_{version}")
            with difficulty_col:
                difficulty = st.selectbox("Độ khó *", list(TAB1_DIFFICULTIES),
                                          index=list(TAB1_DIFFICULTIES).index(initial["difficulty"]),
                                          format_func=TAB1_DIFFICULTIES.get,
                                          key=f"tab1_difficulty_{version}")
            add_image = st.checkbox("Thêm ảnh (không bắt buộc)",
                                    value=initial.get("image") is not None,
                                    key=f"tab1_add_image_{version}")
            upload = None
            if add_image:
                upload = st.file_uploader("Chọn ảnh PNG, JPG hoặc WEBP (tối đa 2 MB)",
                                          type=["png", "jpg", "jpeg", "webp"],
                                          max_upload_size=2, key=f"tab1_image_{version}")
                if initial.get("image") and upload is None:
                    st.caption("Ảnh hiện tại được giữ nếu không chọn ảnh mới.")
            save_col, reset_col = st.columns(2)
            save = save_col.form_submit_button("Cập nhật thẻ" if editing else "Thêm thẻ",
                                               type="primary", width="stretch")
            reset = reset_col.form_submit_button("Hủy chỉnh sửa" if editing else "Nhập lại",
                                                 width="stretch")
        if reset:
            tab1_reset_form(state)
            st.rerun()
        if save:
            image = (upload.getvalue() if upload is not None else initial.get("image")) if add_image else None
            try:
                card = tab1_save_card(state, {
                    "question": question, "answer": answer, "hint": hint,
                    "category": category, "difficulty": difficulty, "image": image,
                }, card_id=editing["id"] if editing else None)
            except ValueError as error:
                st.error(str(error))
            else:
                tab1_reset_form(state)
                tab1_notice(state, f"Đã {'cập nhật' if editing else 'thêm'} thẻ {card['id']}.")


def tab1_render_library(state: dict, cards: list[dict]) -> None:
    with st.container(key="tab1_library"):
        title_col, count_col = st.columns([3, 1], vertical_alignment="center")
        title_col.markdown("### Bộ câu hỏi")
        count_col.markdown(f"**{len(cards)} câu**")
        categories = sorted({card["category"] for card in cards})
        if st.session_state.get("tab1_filter") not in ["Tất cả", *categories]:
            st.session_state["tab1_filter"] = "Tất cả"
        search_col, category_col = st.columns([3, 1])
        with search_col:
            search = st.text_input("Tìm câu hỏi", placeholder="🔍 Nhập từ khóa...",
                                   key="tab1_search").strip().casefold()
        with category_col:
            selected = st.selectbox("Chủ đề", ["Tất cả", *categories], key="tab1_filter")
        visible = [card for card in cards if search in card["question"].casefold()
                   and (selected == "Tất cả" or card["category"] == selected)]
        if not cards:
            st.info("Chưa có câu hỏi trong phiên này.")
        elif not visible:
            st.info("Không tìm thấy thẻ phù hợp.")
        else:
            with st.container(height=430, border=False):
                for card in visible:
                    with st.container(border=True, key=f"tab1_card_{card['id']}"):
                        st.markdown(f"**{card['question']}**")
                        st.caption(f"{card['id']} · {card['category']} · "
                                   f"{TAB1_DIFFICULTIES[card['difficulty']]}")
                        with st.expander("Xem đáp án"):
                            st.write(card["answer"])
                            if card.get("hint"):
                                st.caption(f"Gợi ý: {card['hint']}")
                            if card.get("image"):
                                st.image(card["image"])
                        edit_col, delete_col = st.columns(2)
                        if edit_col.button("✏️ Sửa", key=f"tab1_edit_{card['id']}", width="stretch"):
                            state["editing_id"] = card["id"]
                            state["show_form"] = True
                            state["form_version"] += 1
                            st.rerun()
                        if delete_col.button("🗑️ Xóa", key=f"tab1_delete_{card['id']}", width="stretch"):
                            tab1_delete_card(state, card["id"])
                            if state["editing_id"] == card["id"]:
                                tab1_reset_form(state)
                            tab1_notice(state, f"Đã xóa thẻ {card['id']}. Có thể hoàn tác.")


def render_tab1() -> None:
    state = tab1_state()
    cards = tab1_cards(state)
    if state["notice"]:
        st.toast(state["notice"])
        st.success(state["notice"])
        state["notice"] = None
    heading_col, add_col, reload_col, undo_col = st.columns(
        [3.8, 1.5, 1.3, 1.2], vertical_alignment="center"
    )
    heading_col.markdown("#### Quản lý bộ câu hỏi")
    if add_col.button("＋ Thêm câu hỏi", key="tab1_add", width="stretch"):
        state["editing_id"] = None
        state["show_form"] = True
        state["form_version"] += 1
        st.rerun()
    reload_col.button(
        "↻ Nạp lại", key="tab1_reload", width="stretch", disabled=True,
        help="Chờ Storage của nhóm cung cấp chức năng nạp lại từ data/cards.json.",
    )
    if undo_col.button("↩ Hoàn tác", key="tab1_undo",
                       disabled=not state["history"], width="stretch"):
        if tab1_undo(state):
            tab1_reset_form(state)
            tab1_notice(state, "Đã hoàn tác thao tác gần nhất.")
    st.info(
        "Hiện chỉ có 3 câu hỏi mẫu để thử giao diện. "
        "Kho dữ liệu của nhóm sẽ hiển thị ở đây sau khi tích hợp Manager và Storage."
    )
    if state["show_form"]:
        tab1_render_form(state, cards)
    tab1_render_library(state, cards)


def render_quiz() -> None:
    st.subheader("Quiz · Ôn tập Flashcard")
    st.info("Tính năng hàng đợi ôn tập & làm bài quiz đang được phát triển..")


def render_minigame() -> None:
    st.subheader("Minigame")
    st.info("Tính năng thử thách tốc độ và bảng xếp hạng đang được phát triển.")


def main() -> None:
    st.set_page_config(page_title="Flashcard Quiz Engine", layout="wide")
    tab1_styles()
    st.title("📚 Flashcard Quiz Engine")
    manager_tab, quiz_tab, minigame_tab = st.tabs(["Manager", "Quiz", "Minigame"])
    with manager_tab:
        render_tab1()
    with quiz_tab:
        render_quiz()
    with minigame_tab:
        render_minigame()


if __name__ == "__main__":
    main()
