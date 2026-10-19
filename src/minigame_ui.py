"""Lobby, timed play and persisted results for Minigame mode in tab 2."""

import streamlit as st

from core.game_storage import load_questions, load_leaderboard, save_result, ranked_results
from models.game_session import MinigameSession, BASE_POINTS, SECONDS_PER_QUESTION

STATE = "minigame_session"
LEVELS = {"Easy": "Dễ", "Medium": "Vừa", "Hard": "Khó"}


def lobby():
    try:
        questions = load_questions()
    except (OSError, ValueError) as error:
        st.error(f"Không thể đọc bộ câu hỏi Minigame: {error}")
        st.caption("Kiểm tra file data/cards.json rồi tải lại ứng dụng.")
        return
    with st.container(key="game_lobby"):
        st.markdown("### 🔥 Thử thách kiến thức")
        st.write("Trả lời chính xác, giữ chuỗi đúng và ghi điểm trước khi hết giờ.")
        name = st.text_input("Tên người chơi", max_chars=40, key="game_name",
                             placeholder="Nhập tên của bạn")
        categories = [None, *sorted({q["category"] for q in questions})]
        if st.session_state.get("game_category") not in categories:
            st.session_state["game_category"] = None
        category = st.selectbox("Chủ đề", categories, key="game_category",
                                format_func=lambda c: c if c is not None else "Tất cả chủ đề")
        available = sum(category is None or q["category"] == category for q in questions)
        if not available:
            st.info("Chưa có câu hỏi cho chủ đề này.")
            return
        counts = list(range(1, available + 1))
        if st.session_state.get("game_count") not in counts:
            st.session_state["game_count"] = min(5, available)
        count = st.selectbox("Số câu", counts, key="game_count")
        shuffle = st.checkbox("Xáo trộn thứ tự câu hỏi", value=True, key="game_shuffle")
        st.caption(f"{available} câu có sẵn · {SECONDS_PER_QUESTION} giây/câu · A–D cố định")
        with st.expander("Luật chơi và cách tính điểm"):
            st.write("Dễ 10 · Vừa 20 · Khó 30 điểm. Mỗi 2 giây còn lại thưởng 1 điểm, tối đa 10.")
            st.write("Chuỗi đúng: 1 câu ×1; 2 câu ×1,5; từ 3 câu ×2. "
                     "Điểm = phần nguyên của (điểm cơ bản + thưởng tốc độ) × combo.")
            st.write("Câu nhiều đáp án phải chọn đủ và không chọn sai. Sai hoặc hết giờ: 0 điểm, mất chuỗi.")
            st.write("Thời gian xếp hạng chỉ tính lúc trả lời, không tính lúc đọc giải thích. "
                     "Nộp sớm giữ điểm hiện có; câu còn lại tính là chưa trả lời.")
            st.write("Cùng chủ đề và số câu sẽ dùng cùng một bộ câu hỏi. Xáo trộn chỉ đổi thứ tự câu; A–D giữ nguyên.")
        if st.button("🚀 Bắt đầu Minigame", key="game_start", type="primary",
                     disabled=not name.strip(), width="stretch"):
            st.session_state[STATE] = MinigameSession(questions, name, category, count, shuffle)
            st.rerun()
    st.caption("Câu hỏi được lấy từ phần Minigame của các thẻ trong data/cards.json.")


@st.fragment(run_every=1)
def active():
    game = st.session_state.get(STATE)
    if game is None or game.phase != "question":
        return
    if game.expire():
        st.rerun()
    q = game.question
    with st.container(key="game_tracker"):
        timer, score, streak, combo = st.columns(4)
        timer.metric("⏳ Còn lại", f"{game.time_left} giây")
        score.metric("🏆 Điểm", game.total_score)
        streak.metric("🔥 Chuỗi đúng", game.streak)
        combo.metric("⚡ Combo hiện tại", f"×{game.multiplier:g}")
        st.progress(game.index / len(game.questions), text=f"Câu {game.index + 1}/{len(game.questions)}")
        if game.time_left <= 5:
            st.warning("Sắp hết giờ! Hãy xác nhận câu trả lời.")
    with st.container(key="game_question"):
        st.caption(f"{q['category']} · {LEVELS[q['difficulty']]} · {BASE_POINTS[q['difficulty']]} điểm cơ bản")
        st.markdown("#### " + q["question"])
        prefix = f"game_choice_{game.session_id}_{game.index}"
        if len(q["correct_ids"]) == 1:
            labels = {o["id"]: o["text"] for o in q["options"]}
            choice = st.radio("Chọn một đáp án", list(labels), index=None,
                              format_func=lambda key: f"{key}. {labels[key]}", key=prefix)
            choices = [choice] if choice is not None else []
        else:
            st.caption("Chọn tất cả đáp án đúng.")
            choices = [o["id"] for o in q["options"]
                       if st.checkbox(f"{o['id']}. {o['text']}", key=f"{prefix}_{o['id']}")]
        if st.button("✓ Xác nhận câu trả lời", key="game_answer", type="primary", width="stretch"):
            try:
                game.answer(choices, q["id"])
            except ValueError as error:
                st.warning(str(error))
            else:
                st.rerun()
        if st.button("🏁 Nộp bài ngay", key="game_submit"):
            game.submit()
            st.rerun()
        st.caption("Chuyển tab không dừng đồng hồ. Lựa chọn chỉ được chấm khi bấm Xác nhận.")


def feedback(game):
    item = game.history[-1]
    with st.container(key="game_feedback"):
        if item["timed_out"]:
            st.warning("Hết giờ · 0 điểm · Chuỗi đúng đã đặt lại.")
        elif item["correct"]:
            st.success(f"Chính xác! +{item['points']} điểm · Combo ×{item['multiplier']:g}")
        else:
            st.error("Chưa chính xác · 0 điểm · Chuỗi đúng đã đặt lại.")
        st.markdown("#### " + game.question["question"])
        for option in game.question["options"]:
            correct = option["id"] in game.question["correct_ids"]
            selected = option["id"] in item["selected"]
            st.write(f"{'✅' if correct else '▫️'} {option['id']}. {option['text']}" + (" — Bạn chọn" if selected else ""))
        st.info(game.question["explanation"])
        st.write(f"Tổng điểm: **{game.total_score}** · Chuỗi đúng cao nhất: **{game.max_streak}**")
        st.caption("Đồng hồ câu tiếp theo chỉ bắt đầu khi bạn bấm Tiếp tục.")
        if st.button("🏆 Xem kết quả" if game.index + 1 == len(game.questions) else "Tiếp tục →",
                     key="game_next", type="primary", width="stretch"):
            game.next_question()
            st.rerun()
        if game.index + 1 < len(game.questions) and st.button("🏁 Nộp bài ngay", key="game_submit_feedback"):
            game.submit()
            st.rerun()


def result(game):
    record = game.submit()
    saved_key = f"game_saved_{game.session_id}"
    attempted_key = f"game_save_attempted_{game.session_id}"
    if not st.session_state.get(attempted_key):
        st.session_state[attempted_key] = True
        try:
            save_result(record)
        except (OSError, ValueError) as error:
            st.session_state[f"game_save_error_{game.session_id}"] = str(error)
        else:
            st.session_state[saved_key] = True
    with st.container(key="game_result"):
        st.markdown("### 🏁 Kết quả Minigame")
        st.write(f"Người chơi: **{record['player_name']}**")
        score, correct, streak, duration = st.columns(4)
        score.metric("Tổng điểm", record["total_score"])
        correct.metric("Đúng / Tổng", f"{record['correct_count']}/{record['total_questions']}")
        streak.metric("Chuỗi cao nhất", record["max_streak"])
        duration.metric("Thời gian làm bài", f"{record['elapsed_seconds']:.1f}s")
        unanswered = record["total_questions"] - record["answered_count"]
        st.caption(f"{unanswered} câu chưa trả lời · Thời gian không bao gồm lúc đọc giải thích.")
        if st.session_state.get(saved_key):
            st.success("Đã lưu kết quả vào bảng xếp hạng.")
        else:
            st.error("Chưa lưu được kết quả. " + st.session_state.get(f"game_save_error_{game.session_id}", ""))
            if st.button("Thử lưu lại", key="game_retry_save"):
                st.session_state[attempted_key] = False
                st.rerun()
        with st.expander("Xem lại toàn bộ câu hỏi"):
            answers = {a["question_id"]: a for a in game.history}
            for index, q in enumerate(game.questions, 1):
                item = answers.get(q["id"])
                status = "Chưa trả lời" if item is None else "Hết giờ" if item["timed_out"] else "Đúng" if item["correct"] else "Sai"
                st.markdown(f"**{index}. {q['question']}**")
                st.caption(status)
                if item:
                    st.write("Bạn chọn: " + ("; ".join(f"{o['id']}. {o['text']}" for o in q["options"] if o["id"] in item["selected"]) or "Không chọn"))
                st.write("Đáp án: " + "; ".join(f"{o['id']}. {o['text']}" for o in q["options"] if o["id"] in q["correct_ids"]))
                st.write(q["explanation"])
    st.markdown("### 🏆 Bảng xếp hạng")
    st.caption(f"Cùng bộ {record['total_questions']} câu · {record['category']} · 20 giây/câu. "
               "Điểm cao hơn xếp trước; bằng điểm ưu tiên thời gian ngắn hơn.")
    try:
        ranked = ranked_results(load_leaderboard(), game.config_id)
    except (OSError, ValueError) as error:
        st.error(f"Không thể đọc bảng xếp hạng: {error}")
    else:
        if ranked:
            for i, r in enumerate(ranked, 1):
                current = " (Bạn)" if r["session_id"] == game.session_id else ""
                st.write(f"**{i}. {r['player_name']}{current}** · {r['total_score']} điểm · "
                         f"{r['correct_count']}/{r['total_questions']} đúng · "
                         f"{r['elapsed_seconds']:.1f}s · {r['played_at']}")
        else:
            st.info("Chưa có kết quả được lưu cho bộ câu hỏi này.")
    if not st.session_state.get(saved_key):
        discard = st.checkbox("Tôi đồng ý quay về khi kết quả chưa được lưu", key="game_discard_unsaved")
    else:
        discard = True
    if st.button("🔄 Về màn hình chờ", key="game_lobby_return", disabled=not discard):
        for key in list(st.session_state):
            if key.startswith(("game_choice_", "game_saved_", "game_save_attempted_", "game_save_error_")) or key == "game_discard_unsaved":
                del st.session_state[key]
        del st.session_state[STATE]
        st.rerun()


def render_minigame():
    st.subheader("Minigame · Thử thách tốc độ")
    st.markdown("""
    <style>
    .st-key-game_lobby, .st-key-game_tracker, .st-key-game_question,
    .st-key-game_feedback, .st-key-game_result {
      background: #fff; color: #111827; border: 1px solid #d6dee6;
      border-radius: 14px; padding: 18px 20px; margin-bottom: 16px;
      box-shadow: 0 4px 14px rgba(29,38,50,.08);
    }
    [class*="st-key-game_"] button[kind="primary"] {
      background: #c7eee6 !important; color: #111827 !important; border-color: #9edbce !important;
    }
    [class*="st-key-game_"] label { color: #111827 !important; }
    [class*="st-key-game_"] input, [class*="st-key-game_"] [data-baseweb="select"] > div {
      background: #fff !important; color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    game = st.session_state.get(STATE)
    if game is None:
        lobby()
    elif game.phase == "question":
        active()
    elif game.phase == "feedback":
        feedback(game)
    else:
        result(game)
