"""Quiz views sharing Tab 1's palette and session-only card source."""

import streamlit as st

from core.review import ReviewSession


STATE_KEY = "tab2_review_session"
DIFFICULTIES = {"Easy": "Dễ", "Medium": "Vừa", "Hard": "Khó"}


def reset_review() -> None:
    session = st.session_state.pop(STATE_KEY, None)
    if session is not None:
        session.cancel()
    st.rerun()


def render_lobby(cards: list[dict]) -> None:
    with st.container(key="quiz_lobby"):
        st.markdown("### 🎯 Bắt đầu phiên ôn tập")
        st.write("Lật thẻ, tự đánh giá mức độ ghi nhớ và học lại những câu chưa nhớ.")
        categories = [None, *sorted({card["category"] for card in cards})]
        if st.session_state.get("quiz_category") not in categories:
            st.session_state["quiz_category"] = None
        category = st.selectbox("Chủ đề ôn tập", categories,
                                format_func=lambda item: "Tất cả chủ đề" if item is None else item,
                                key="quiz_category")
        shuffle = st.checkbox("Xáo trộn thứ tự câu hỏi", value=True, key="quiz_shuffle")
        count = sum(category is None or card["category"] == category for card in cards)
        st.caption(f"{count} thẻ sẵn sàng · Không giới hạn thời gian")
        if not count:
            st.info("Chưa có thẻ để ôn tập. Hãy thêm câu hỏi ở tab Manager.")
        if st.button("🚀 Bắt đầu ôn tập", key="quiz_start", type="primary",
                     disabled=count == 0, width="stretch"):
            try:
                st.session_state[STATE_KEY] = ReviewSession(cards, category, shuffle)
            except ValueError as error:
                st.error(str(error))
            else:
                st.rerun()
    st.caption("Dữ liệu lấy từ bộ thẻ ở tab Manager trong phiên hiện tại. "
               "Thay đổi bộ thẻ sẽ được áp dụng ở lượt ôn tập tiếp theo.")


def render_active(session: ReviewSession) -> None:
    stats = session.stats
    with st.container(key="quiz_tracker"):
        remaining, correct, wrong, accuracy = st.columns(4)
        remaining.metric("Thẻ còn lại", session.remaining)
        correct.metric("Đã nhớ", stats.correct_count)
        wrong.metric("Lượt chưa nhớ", len(stats.history) - stats.correct_count)
        accuracy.metric("Tỷ lệ chính xác", f"{stats.get_accuracy_percentage():.1f}%")
        progress = stats.correct_count / stats.total_questions
        st.progress(progress, text=f"Đã ghi nhớ {stats.correct_count}/{stats.total_questions} thẻ")
        st.caption("Tỷ lệ chính xác = số lượt Đã nhớ / tổng lượt tự đánh giá. "
                   "Thẻ Chưa nhớ được đưa về cuối hàng đợi.")
    card = session.current_card
    with st.container(key="quiz_card"):
        st.caption(f"{card['id']} · {card['category']} · "
                   f"{DIFFICULTIES.get(card['difficulty'], card['difficulty'])}")
        st.markdown("#### ❓ Câu hỏi")
        st.write(card["question"])
        if card.get("image"):
            st.image(card["image"])
        if card.get("hint"):
            with st.expander("💡 Xem gợi ý"):
                st.write(card["hint"])
        if not session.revealed:
            if st.button("🔄 Lật xem đáp án", key="quiz_flip", type="primary",
                         width="stretch"):
                session.reveal()
                st.rerun()
        else:
            st.divider()
            st.markdown("#### 💡 Đáp án")
            st.write(card["answer"])
            st.write("Bạn đã nhớ câu trả lời chưa?")
            yes, no = st.columns(2)
            if yes.button("✅ Đã nhớ", key="quiz_remembered", type="primary", width="stretch"):
                session.answer(True)
                st.rerun()
            if no.button("↩ Chưa nhớ · Học lại", key="quiz_retry", width="stretch"):
                session.answer(False)
                st.rerun()
    if st.button("✕ Hủy ôn tập", key="quiz_cancel"):
        reset_review()


def render_result(session: ReviewSession) -> None:
    stats = session.stats
    with st.container(key="quiz_result"):
        st.markdown("### 🎉 Hoàn thành phiên ôn tập!")
        st.success(f"Bạn đã ghi nhớ toàn bộ {stats.total_questions} thẻ.")
        remembered, attempts, accuracy = st.columns(3)
        remembered.metric("Thẻ đã nhớ", stats.correct_count)
        attempts.metric("Tổng lượt ôn", len(stats.history))
        accuracy.metric("Tỷ lệ chính xác", f"{stats.get_accuracy_percentage():.1f}%")
        st.markdown(f"#### Xếp loại: {stats.get_performance_rating()}")
        st.caption("Xuất sắc ≥90% · Tốt ≥75% · Khá ≥50% · Cần cải thiện <50%")
        st.caption("Tỷ lệ tính trên tất cả lượt tự đánh giá, bao gồm các lượt học lại.")
        with st.expander("Xem lịch sử ôn tập"):
            st.dataframe([
                {"Lượt": index + 1,
                 "Câu hỏi": session.cards[item["card_id"]]["question"],
                 "Kết quả": "Đã nhớ" if item["is_correct"] else "Chưa nhớ"}
                for index, item in enumerate(stats.history)
            ], hide_index=True, width="stretch")
        if st.button("🔄 Ôn tập phiên mới", key="quiz_new", type="primary", width="stretch"):
            reset_review()


def render_quiz(cards: list[dict]) -> None:
    st.subheader("Quiz · Ôn tập Flashcard")
    st.markdown("""
    <style>
    .st-key-quiz_lobby, .st-key-quiz_tracker, .st-key-quiz_card, .st-key-quiz_result {
      background: #ffffff; color: #111827; border: 1px solid #d6dee6;
      border-radius: 14px; padding: 18px 20px;
      box-shadow: 0 4px 14px rgba(29,38,50,.08); margin-bottom: 16px;
    }
    [class*="st-key-quiz_"] button[kind="primary"] {
      background: #c7eee6 !important; color: #111827 !important;
      border-color: #9edbce !important;
    }
    [class*="st-key-quiz_"] button[kind="secondary"] {
      background: #f1f5f9 !important; color: #111827 !important;
      border-color: #d6dee6 !important;
    }
    [class*="st-key-quiz_"] [data-baseweb="select"] > div {
      background: #ffffff !important; color: #111827 !important;
      border-color: #d6dee6 !important;
    }
    [class*="st-key-quiz_"] label { color: #111827 !important; }
    </style>
    """, unsafe_allow_html=True)
    session = st.session_state.get(STATE_KEY)
    if session is None:
        render_lobby(cards)
    elif session.finished:
        render_result(session)
    else:
        render_active(session)
