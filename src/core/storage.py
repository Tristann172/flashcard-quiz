import json
import os
from pathlib import Path
from typing import Any

class StaleCardsError(Exception):
    """Ngoại lệ văng ra khi dữ liệu thẻ bị cũ hoặc không đồng bộ."""
    pass

# Khởi tạo đường dẫn tuyệt đối đến thư mục data/ để đảm bảo không bị lỗi path khi chạy từ các thư mục khác nhau
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
CARDS_FILE = DATA_DIR / 'cards.json'
LEADERBOARD_FILE = DATA_DIR / 'leaderboard.json'

# Dữ liệu 10 thẻ mẫu (Demo data) chuẩn kỹ thuật theo mục 2.3
DEMO_CARDS = [
    {
        "id": "c1",
        "question": "Tính bao đóng (Encapsulation) trong OOP là gì?",
        "answer": "Là cơ chế che giấu dữ liệu bên trong lớp và chỉ cho phép truy xuất qua các phương thức (getter/setter).",
        "category": "OOP",
        "difficulty": "Easy",
        "quiz_question": "Mục đích chính của tính bao đóng trong OOP là gì?",
        "options": [
            {"id": "A", "text": "Che giấu trạng thái nội tại của đối tượng"},
            {"id": "B", "text": "Kế thừa các thuộc tính từ lớp cha"},
            {"id": "C", "text": "Nạp chồng phương thức"},
            {"id": "D", "text": "Bảo vệ dữ liệu khỏi việc sửa đổi tùy tiện từ bên ngoài"}
        ],
        "correct_option_ids": ["A", "D"]
    },
    {
        "id": "c2",
        "question": "Độ phức tạp thời gian khi tra cứu một khóa (key) trong Hash Map (dict) của Python là bao nhiêu?",
        "answer": "Thời gian trung bình là O(1) nhờ cơ chế băm (hashing).",
        "category": "Python",
        "difficulty": "Easy",
        "quiz_question": "Cấu trúc dữ liệu nào trong Python cung cấp thời gian tra cứu trung bình là O(1)?",
        "options": [
            {"id": "A", "text": "List"},
            {"id": "B", "text": "Dictionary (Dict)"},
            {"id": "C", "text": "Tuple"},
            {"id": "D", "text": "Set"}
        ],
        "correct_option_ids": ["B", "D"]
    },
    {
        "id": "c3",
        "question": "deque dùng làm hàng đợi như thế nào?",
        "answer": "append ở cuối, popleft ở đầu.",
        "category": "DSA",
        "difficulty": "Medium",
        "quiz_question": "Chọn thao tác để ôn thẻ theo chuẩn FIFO bằng deque.",
        "options": [
            {"id": "A", "text": "popleft() lấy phần tử đầu"},
            {"id": "B", "text": "pop() lấy phần tử cuối"},
            {"id": "C", "text": "append() thêm vào cuối"},
            {"id": "D", "text": "insert() chèn vào giữa"}
        ],
        "correct_option_ids": ["A", "C"]
    },
    {
        "id": "c4",
        "question": "Stack (Ngăn xếp) hoạt động theo nguyên tắc nào?",
        "answer": "LIFO (Last-In, First-Out) - Vào sau ra trước.",
        "category": "DSA",
        "difficulty": "Easy",
        "quiz_question": "Khi áp dụng Stack cho tính năng Undo (Hoàn tác), phần tử nào sẽ được lấy ra đầu tiên?",
        "options": [
            {"id": "A", "text": "Phần tử được thêm vào đầu tiên"},
            {"id": "B", "text": "Phần tử được thêm vào cuối cùng (gần nhất)"},
            {"id": "C", "text": "Phần tử ở giữa"},
            {"id": "D", "text": "Phần tử có giá trị lớn nhất"}
        ],
        "correct_option_ids": ["B"]
    },
    {
        "id": "c5",
        "question": "Sự khác biệt chính giữa List và Tuple trong Python là gì?",
        "answer": "List có thể thay đổi (mutable), còn Tuple thì không thể thay đổi (immutable) sau khi khởi tạo.",
        "category": "Python",
        "difficulty": "Medium",
        "quiz_question": "Đặc điểm nào dưới đây đúng với Tuple trong Python?",
        "options": [
            {"id": "A", "text": "Có thể thêm phần tử bằng hàm append()"},
            {"id": "B", "text": "Không thể thay đổi nội dung (immutable)"},
            {"id": "C", "text": "Dùng ngoặc vuông [] để khởi tạo"},
            {"id": "D", "text": "Thường dùng làm Key trong Dictionary"}
        ],
        "correct_option_ids": ["B", "D"]
    },
    {
        "id": "c6",
        "question": "Tính đa hình (Polymorphism) là gì?",
        "answer": "Là khả năng các đối tượng thuộc các lớp khác nhau có thể phản hồi cùng một lời gọi phương thức theo những cách riêng biệt.",
        "category": "OOP",
        "difficulty": "Hard",
        "quiz_question": "Tính đa hình trong Python thường được thể hiện qua khái niệm nào?",
        "options": [
            {"id": "A", "text": "Duck typing (phương thức giống nhau thì coi là giống nhau)"},
            {"id": "B", "text": "Overriding (Ghi đè phương thức)"},
            {"id": "C", "text": "Private attributes (Thuộc tính riêng tư)"},
            {"id": "D", "text": "Constructors (Hàm khởi tạo)"}
        ],
        "correct_option_ids": ["A", "B"]
    },
    {
        "id": "c7",
        "question": "Tại sao lại dùng Queue cho tính năng ôn tập Flashcard thay vì Stack?",
        "answer": "Queue giúp các thẻ xếp hàng theo thứ tự (FIFO), đảm bảo thẻ nào tới lượt trước sẽ được học trước.",
        "category": "DSA",
        "difficulty": "Medium",
        "quiz_question": "Cấu trúc dữ liệu nào phù hợp nhất để xây dựng một hàng đợi (Queue) xử lý tác vụ tuần tự?",
        "options": [
            {"id": "A", "text": "Hash Map"},
            {"id": "B", "text": "Ngăn xếp (Stack)"},
            {"id": "C", "text": "collections.deque"},
            {"id": "D", "text": "Mảng 2 chiều (2D Array)"}
        ],
        "correct_option_ids": ["C"]
    },
    {
        "id": "c8",
        "question": "Khối try...except trong Python dùng để làm gì?",
        "answer": "Dùng để bắt và xử lý các ngoại lệ (exceptions) có thể xảy ra trong lúc chạy chương trình, giúp app không bị crash.",
        "category": "Python",
        "difficulty": "Easy",
        "quiz_question": "Từ khóa nào được sử dụng để định nghĩa khối mã luôn luôn được thực thi bất kể có ngoại lệ hay không?",
        "options": [
            {"id": "A", "text": "catch"},
            {"id": "B", "text": "finally"},
            {"id": "C", "text": "else"},
            {"id": "D", "text": "continue"}
        ],
        "correct_option_ids": ["B"]
    },
    {
        "id": "c9",
        "question": "Phương pháp Active Recall trong học tập là gì?",
        "answer": "Là phương pháp chủ động nhớ lại thông tin từ não bộ thay vì đọc thụ động, giúp củng cố liên kết thần kinh mạnh mẽ hơn.",
        "category": "Methodology",
        "difficulty": "Easy",
        "quiz_question": "Đâu là một ví dụ của việc áp dụng Active Recall?",
        "options": [
            {"id": "A", "text": "Đọc đi đọc lại cuốn sách giáo khoa nhiều lần"},
            {"id": "B", "text": "Tự làm bài kiểm tra trắc nghiệm không nhìn tài liệu"},
            {"id": "C", "text": "Dùng Flashcard lật mặt trước và tự nhẩm mặt sau"},
            {"id": "D", "text": "Highlight (bôi màu) các dòng chữ quan trọng"}
        ],
        "correct_option_ids": ["B", "C"]
    },
    {
        "id": "c10",
        "question": "Git Flow thường chia ra các nhánh (branch) cơ bản nào?",
        "answer": "Thường có nhánh main (production), nhánh develop, và các nhánh tính năng (feature branches).",
        "category": "Tools",
        "difficulty": "Medium",
        "quiz_question": "Lệnh nào sau đây dùng để tạo và chuyển sang một nhánh tính năng mới trong Git?",
        "options": [
            {"id": "A", "text": "git branch feat/new"},
            {"id": "B", "text": "git checkout -b feat/new"},
            {"id": "C", "text": "git switch -c feat/new"},
            {"id": "D", "text": "git merge feat/new"}
        ],
        "correct_option_ids": ["B", "C"]
    }
]

def initialize_data() -> None:
    """Kiểm tra và tự động tạo thư mục, nạp dữ liệu mẫu nếu file chưa tồn tại."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not CARDS_FILE.exists():
        save_cards(DEMO_CARDS)
        
    if not LEADERBOARD_FILE.exists():
        save_leaderboard([])

def load_cards() -> tuple[list[dict[str, Any]], Any]:
    """Đọc file cards.json an toàn với cơ chế bắt ngoại lệ.
    Trả về tuple (cards, revision) để khớp với giao diện UI.
    """
    try:
        with open(CARDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except FileNotFoundError:
        print("Cảnh báo: Không tìm thấy cards.json. Khởi tạo file mới cùng dữ liệu mẫu.")
        initialize_data()
        return DEMO_CARDS, None
    except json.JSONDecodeError:
        print("Lỗi nghiêm trọng: File cards.json bị hỏng định dạng (JSONDecodeError).")
        return [], None

def save_cards(cards_data: list[dict[str, Any]], revision: Any = None) -> Any:
    """Ghi đè toàn bộ danh sách thẻ xuống file cards.json.
    Nhận thêm tham số revision và trả về revision mới để khớp với UI.
    """
    try:
        with open(CARDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=4)
        return None
    except Exception as e:
        print(f"Lỗi ghi file cards.json: {e}")
        return None

def load_leaderboard() -> list[dict[str, Any]]:
    """Đọc dữ liệu lịch sử thi Minigame từ leaderboard.json."""
    try:
        with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Trả về mảng rỗng nếu chưa có file hoặc file lỗi để không crash app
        return []

def save_leaderboard(leaderboard_data: list[dict[str, Any]]) -> bool:
    """
    Ghi dữ liệu xuống leaderboard.json.
    Sắp xếp theo tổng điểm giảm dần trước khi lưu, không thêm trường rank.
    Thứ hạng được tính khi hiển thị trên giao diện.
    
    Lưu ý cho Models & UI: Các bản ghi trong `leaderboard_data` 
    cần đảm bảo có chứa các key như 'player_name', 'total_score', 'elapsed_seconds'
    để việc lưu trữ và hiển thị được đầy đủ thông tin.
    """
    # Sắp xếp mảng điểm giảm dần
    leaderboard_data.sort(key=lambda x: x.get('total_score', 0), reverse=True)
    
    try:
        with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
            json.dump(leaderboard_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Lỗi ghi file leaderboard.json: {e}")
        return False

def reload_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Hàm nạp lại toàn bộ dữ liệu (Phục vụ cho nút Reload trên UI Streamlit)."""
    # Gọi khởi tạo đảm bảo file luôn có sẵn trước khi nạp
    initialize_data()
    return load_cards(), load_leaderboard()

# Kích hoạt khởi tạo dữ liệu ngay khi import module này
initialize_data()
