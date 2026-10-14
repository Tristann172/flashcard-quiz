import pytest
from src.models.card import Card
from src.models.session import FlashcardSession
from src.models.game_session import MinigameSession


#dữ liệu dùng chung cho các test case
@pytest.fixture
def sample_card():
    #thẻ mẫu : Medium(20đ)
    return Card(
        id="c1",
        question="  Queue hoạt động theo cơ chế nào?  ",
        answer="FIFO",
        category="DSA",
        difficulty="medium",  
        quiz_question="Chọn các thao tác chuẩn của Queue với deque:",
        options=[
            {"id": "A", "text": "append()"},
            {"id": "B", "text": "pop()"},
            {"id": "C", "text": "popleft()"},
            {"id": "D", "text": "insert()"}
        ],
        correct_option_ids=["A", "C"]
    )


#card 
def test_card_creation_and_normalization(sample_card):
    #test khởi tạo và chuẩn hoá dữ liệu (strip khoảng trắng và get base point )
    assert sample_card.id == "c1"
    assert sample_card.question == "Queue hoạt động theo cơ chế nào?"
    assert sample_card.difficulty == "Medium"
    assert sample_card.get_base_points() == 20


@pytest.mark.parametrize("difficulty, expected_points", [ 
    ("Easy", 10),
    ("Medium", 20),
    ("Hard", 30),
])
def test_card_base_points(difficulty, expected_points):
    #test điểm cơ bản theo từng mức độ khó
    card = Card(id="c_test", question="Q", answer="A", difficulty=difficulty)
    assert card.get_base_points() == expected_points


@pytest.mark.parametrize("invalid_id, invalid_q, invalid_diff", [
    ("   ", "Câu hỏi hợp lệ", "Easy"),      # id rỗng
    ("c1", "   ", "Easy"),                  # câu hỏi rỗng
    ("c1", "Câu hỏi hợp lệ", "SuperHard"),  # độ khó ko hợp lệ 
])
def test_card_invalid_inputs_raise_value_error(invalid_id, invalid_q, invalid_diff):
    #test truyền vào với dữ liệu không hợp lệ 
    with pytest.raises(ValueError):
        Card(id=invalid_id, question=invalid_q, answer="Đáp án", difficulty=invalid_diff)
def test_card_is_correct_multiple_choice(sample_card):
    #Kiểm tra so sánh đáp án dạng nhiều lựa chọn (list)
    assert sample_card.is_correct(["C", "A"]) is True
    assert sample_card.is_correct(["A", "C"]) is True
    assert sample_card.is_correct(["A"]) is False         #thiếu
    assert sample_card.is_correct(["A", "B", "C"]) is False #thừa
    assert sample_card.is_correct([]) is False         


def test_card_is_correct_text_answer(sample_card):
    """Kiểm tra so sánh đáp án dạng chuỗi (không phân biệt hoa thường, khoảng trắng)"""
    assert sample_card.is_correct("  fifo ") is True
    assert sample_card.is_correct("LIFO") is False


def test_card_to_dict_and_from_dict(sample_card):
    """Kiểm tra chuyển đổi qua lại giữa Object và Dictionary (để lưu JSON)"""
    data = sample_card.to_dict()
    restored_card = Card.from_dict(data)

    assert restored_card.id == sample_card.id
    assert restored_card.question == sample_card.question
    assert restored_card.correct_option_ids == ["A", "C"]


def test_card_from_dict_invalid_type():
    """Kịch bản ngoại lệ: Truyền dữ liệu không phải dict vào from_dict"""
    with pytest.raises(TypeError):
        Card.from_dict(["danh_sach_khong_phai_dict"])


# ==========================================
# 2. TEST CLASS FLASHCARD SESSION (src/models/session.py)
# ==========================================
def test_flashcard_session_initial_state():
    """Kiểm tra trạng thái ban đầu khi chưa ôn tập câu nào"""
    session = FlashcardSession()
    assert session.total_questions == 0
    assert session.correct_count == 0
    assert session.get_accuracy_percentage() == 0.0
    assert session.get_performance_rating() == "Chưa có dữ liệu"


def test_flashcard_session_record_and_rating():
    """Kiểm tra ghi nhận kết quả, tính % chính xác và xếp loại"""
    session = FlashcardSession()
    session.record_answer("c1", True)
    session.record_answer("c2", True)
    session.record_answer("c3", True)
    session.record_answer("c4", False)

    assert session.total_questions == 4
    assert session.correct_count == 3
    assert session.get_accuracy_percentage() == 75.0
    assert session.get_performance_rating() == "Tốt"


def test_flashcard_session_empty_card_id_raises_error():
    """Kịch bản ngoại lệ: card_id rỗng khi ghi nhận kết quả"""
    session = FlashcardSession()
    with pytest.raises(ValueError):
        session.record_answer("", True)


def test_flashcard_session_reset():
    """Kiểm tra hàm reset() làm mới hoàn toàn phiên học"""
    session = FlashcardSession()
    old_id = session.session_id
    session.record_answer("c1", True)
    session.reset()

    assert session.total_questions == 0
    assert session.correct_count == 0
    assert len(session.history) == 0
    assert session.session_id != old_id


# ==========================================
# 3. TEST CLASS MINIGAME SESSION (src/models/game_session.py)
# ==========================================
def test_minigame_scoring_and_streak_multiplier():
    """Kiểm tra tính điểm, thưởng thời gian và hệ số nhân chuỗi đúng (Streak Combo)"""
    game = MinigameSession()
    easy_card = Card(id="c1", question="Q", answer="A", difficulty="Easy")  # Base: 10 điểm

    # Câu 1 đúng (streak = 1 -> x1.0, time_left = 5) => 10 * 1.0 + 5 = 15 điểm
    game.record_answer(easy_card, is_correct=True, time_left=5)
    assert game.streak == 1
    assert game.multiplier == 1.0
    assert game.total_score == 15

    # Câu 2 đúng (streak = 2 -> x1.0, time_left = 15 -> giới hạn max bonus là 10) => 10 * 1.0 + 10 = 20 điểm
    game.record_answer(easy_card, is_correct=True, time_left=15)
    assert game.streak == 2
    assert game.total_score == 35

    # Câu 3 đúng (streak = 3 -> chạm mốc x1.5, time_left = 0) => 10 * 1.5 + 0 = 15 điểm
    game.record_answer(easy_card, is_correct=True, time_left=0)
    assert game.streak == 3
    assert game.multiplier == 1.5
    assert game.total_score == 50

    # Câu 4 sai -> mất chuỗi (streak = 0, multiplier = 1.0), không cộng điểm
    game.record_answer(easy_card, is_correct=False, time_left=8)
    assert game.streak == 0
    assert game.multiplier == 1.0
    assert game.total_score == 50


def test_minigame_negative_time_left_edge_case():
    """Kịch bản ngoại lệ: Thời gian còn lại bị âm phải tự động đưa về 0"""
    game = MinigameSession()
    easy_card = Card(id="c1", question="Q", answer="A", difficulty="Easy")

    game.record_answer(easy_card, is_correct=True, time_left=-10)
    assert game.total_score == 10
    assert game.history[-1]["time_left"] == 0


def test_minigame_submit_summary():
    """Kiểm tra dữ liệu tổng kết trả về khi bấm Submit"""
    game = MinigameSession()
    easy_card = Card(id="c1", question="Q", answer="A", difficulty="Easy")
    game.record_answer(easy_card, is_correct=True, time_left=2)

    result = game.submit()
    assert result["total_score"] == 12
    assert result["total_questions"] == 1
    assert result["correct_count"] == 1
    assert result["accuracy_percentage"] == 100.0