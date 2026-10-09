import streamlit as st

st.set_page_config(page_title="Flashcard Quiz Engine", layout="wide")

st.title("📚 Flashcard Quiz Engine")
st.success("Khởi tạo môi trường uv và Streamlit thành công!")

tab1, tab2 = st.tabs(["Quản lý thẻ", "Phòng thi & Ôn tập"])

with tab1:
    st.subheader("Kho dữ liệu thẻ Flashcard")
    st.info("Tính năng quản lý thẻ đang được phát triển...")

with tab2:
    st.subheader("Không gian tương tác ôn tập")
    st.info("Tính năng hàng đợi ôn tập & làm bài quiz đang được phát triển..")