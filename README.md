# Flashcard Quiz

Ứng dụng ôn tập kiến thức thông minh bằng Flashcard và Trắc nghiệm xây dựng bằng Python và Streamlit, áp dụng kiến trúc 3 tầng (Clean Architecture) và các cấu trúc dữ liệu nền tảng (Stack, Queue, Hash Map).

---

## 1. Cấu Trúc Thư Mục Dự Án

```text
flashcard-quiz/
├── data/                   # Thư mục chứa cards.json (dữ liệu lưu trữ bền vững)
│   └── .gitkeep            
├── src/
│   ├── core/
│   │   ├── manager.py      # Tầng nghiệp vụ: Xử lý Stack (Undo), Queue (Review), Dict (Hash Map)
│   │   └── storage.py      # Tầng lưu trữ: Đọc/ghi cards.json, tự khởi tạo khi chạy lần đầu
│   ├── models/
│   │   └── card.py         # Thực thể Flashcard (OOP / Pydantic)
│   └── app.py              # Tầng giao diện: Entry point Streamlit UI (chạy ứng dụng)
├── pyproject.toml  
├── run.bat                 # Script nhấp đúp để chạy nhanh ứng dụng trên Windows
└── uv.lock            
```

---

## 2. Hướng Dẫn Thiết Lập Môi Trường (Dành Cho Thành Viên Mới)

Dự án sử dụng công cụ quản lý gói siêu tốc **`uv`**.

### Bước 1: Cài đặt công cụ `uv` (nếu máy chưa có)
Mở PowerShell và chạy lệnh:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Bước 2: Clone repository và đồng bộ môi trường
```bash
# 1. Clone repository về máy
git clone https://github.com/Tristann172/flashcard-quiz
cd flashcard-quiz

# 2. Tự động khởi tạo .venv và cài đặt chính xác mọi thư viện theo uv.lock
uv sync
```

### Bước 3: Khởi chạy ứng dụng
Có thể chọn một trong hai cách sau:
* **Cách 1 (Nhanh nhất):** Nhấp đúp chuột vào tệp `run.bat` ở thư mục gốc.
* **Cách 2 (Terminal):**
  ```bash
  uv run streamlit run src/app.py
  ```

---

## 3. Quy Ước Làm Việc Nhóm Với Git (Git Flow)

Để đảm bảo điểm số rubric về quy trình nhóm, xung đột mã nguồn (merge conflict) và chất lượng code, toàn bộ thành viên bắt buộc tuân thủ quy tắc sau:

### 3.1. Phân chia nhánh (Branch Convention)
* **`main`**: Nhánh sản phẩm hoàn thiện. **Tuyệt đối KHÔNG commit trực tiếp lên `main`**.
* Mỗi tính năng lớn phải được thực hiện trên một nhánh riêng biệt tương ứng với nhiệm vụ:
  * `feat/models`: Xây dựng thực thể dữ liệu trong `src/models/card.py`
  * `feat/storage`: Xây dựng tầng lưu trữ file trong `src/core/storage.py`
  * `feat/logic`: Xây dựng cấu trúc dữ liệu và xử lý nghiệp vụ trong `src/core/manager.py`
  * `feat/ui`: Dựng giao diện web Streamlit trong `src/app.py`

---

### 3.2. Quy trình làm việc hàng ngày của mỗi thành viên

#### Bước 1: Kéo code mới nhất từ `main` về trước khi làm việc
```bash
git checkout main
git pull origin main
```

#### Bước 2: Tạo nhánh riêng theo nhiệm vụ được giao
*(Ví dụ nếu làm phần models)*:
```bash
git checkout -b feat/models
```

#### Bước 3: Viết code, kiểm tra và commit đều đặn
> **Quy định quan trọng:** Lịch sử commit phải thể hiện sự đóng góp đều đặn của tất cả thành viên trong suốt 2 tuần làm việc. Tránh dồn toàn bộ code vào 1–2 commit cuối hạn.

```bash
git add .
git commit -m "feat(models): implement Card class with validation and dictionary parsing"
```

#### Bước 4: Đẩy nhánh tính năng lên GitHub
```bash
git push -u origin feat/models
```

#### Bước 5: Tạo Pull Request (PR) & Review Code
1. Truy cập vào GitHub của dự án, mở mục **Pull Requests** và chọn **New Pull Request**.
2. Chọn gộp từ nhánh của bạn (ví dụ `feat/models`) vào nhánh `main`.
3. Điền mô tả những phần việc đã hoàn thành.
4. **Quy định merge:** Cần có **ít nhất 01 thành viên khác trong nhóm review và Approve** thì nhánh mới được phép merge vào `main`.
