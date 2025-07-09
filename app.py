import streamlit as st
import pandas as pd
import random

class QuizApp:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.kana_labels = ["ア", "イ", "ウ", "エ", "オ"]
        self.defaults = {
            "total": 0,
            "correct": 0,
            "answered_words": set(),
            "latest_result": "",
            "current_quiz": None,
            "quiz_answered": False,
            "quiz_choice": None,
            "history": []
        }
        self.initialize_session()

    def initialize_session(self):
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val if not isinstance(val, set) else set()

    def filter_data(self):
        field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(self.df["分野"].dropna().unique()))
        period = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(self.df["試験区分"].dropna().unique()))
        df_filtered = self.df.copy()
        if field != "すべて":
            df_filtered = df_filtered[df_filtered["分野"] == field]
        if period != "すべて":
            df_filtered = df_filtered[df_filtered["試験区分"] == period]
        remaining = df_filtered[~df_filtered["用語"].isin(st.session_state.answered_words)]
        return df_filtered, remaining

    def show_progress(self, df_filtered):
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答数：{st.session_state.total} 回 / 🎯 正解数：{st.session_state.correct} 回**")

    def load_quiz(self, df_filtered, remaining_df):
        if len(remaining_df) > 0:
            q = remaining_df.sample(1).iloc[0]
            correct = q["説明"]
            wrongs = (
                df_filtered[df_filtered["用語"] != q["用語"]]["説明"]
                .drop_duplicates()
                .sample(min(3, len(df_filtered) - 1))
                .tolist()
            )
            options = wrongs + [correct]
            random.shuffle(options)
            st.session_state.current_quiz = {
                "word": q["用語"],
                "correct": correct,
                "options": options
            }
            st.session_state.quiz_answered = False
            st.session_state.quiz_choice = None

    def display_quiz(self, df_filtered, remaining_df):
        q = st.session_state.current_quiz
        if not q:
            st.warning("⚠️ クイズが読み込まれていません。")
            return

        st.subheader(f"この用語の説明は？：**{q['word']}**")
        labeled = [f"{self.kana_labels[i]}：{txt}" for i, txt in enumerate(q["options"])
