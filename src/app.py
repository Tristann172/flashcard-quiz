"""Entry point for card management and the two practice modes."""

import streamlit as st

from manager_ui import render_manager


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


def render_quiz_tab() -> None:
    """Render the group's Flashcard review when its dependencies are ready."""
    try:
        from core.storage import load_cards
        from models.card import review_questions
        from quiz_ui import render_quiz
    except ImportError:
        st.info("Quiz đang chờ nhóm hoàn thiện Storage, Card và Review.")
        return
    try:
        cards = [] if st.session_state.get("tab2_review_session") is not None else load_cards()[0]
    except (ValueError, OSError) as error:
        st.error(f"Không thể đọc data/cards.json: {error}")
        return
    render_quiz(review_questions(cards))


def render_game_tab() -> None:
    """Render the group's Minigame when its dependencies are ready."""
    try:
        from minigame_ui import render_minigame
    except ImportError:
        st.info("Game đang chờ nhóm hoàn thiện Game Storage và Game Session.")
        return
    render_minigame()


def main() -> None:
    st.set_page_config(page_title="Flashcard Quiz Engine", layout="wide")
    styles()
    st.title("📚 Flashcard Quiz Engine")
    manager_tab, quiz_tab, game_tab = st.tabs(["Manager", "Quiz", "Game"])
    with manager_tab:
        render_manager()
    with quiz_tab:
        render_quiz_tab()
    with game_tab:
        render_game_tab()


if __name__ == "__main__":
    main()
