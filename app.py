import streamlit as st
import pandas as pd
import random

# CSV読み込み（同じフォルダに tango.csv を配置してください）
df = pd.read_csv("tango.csv")

st.title("📘 単語クイズアプリ（午前・午後対応）")

# --- セッションステート初期化 ---
defaults = {
    "total": 0,
    "correct": 0,
    "answered_words": set(),
    "latest_result": "",
    "current_quiz": None,
    "quiz_answered": False,
    "quiz_choice": None
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- フィルター ---
field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(df["分野"].dropna().unique()))
period = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(df["試験区分"].dropna().unique()))

filtered_df = df.copy()
if field != "すべて":
    filtered_df = filtered_df[filtered_df["分野"] == field]
if period != "すべて":
    filtered_df = filtered_df[filtered_df["試験区分"] == period]

remaining_df = filtered_df[~filtered_df["用語"].isin(st.session_state.answered_words)]

# --- 進捗表示 ---
st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(filtered_df)} 語**")
st.markdown(f"🔁 **総回答数：{st.session_state.total} 回 / 🎯 正解数：{st.session_state.correct} 回**")

# --- 新しいクイズ出題 ---
def load_new_quiz():
    if len(remaining_df) > 0:
        quiz = remaining_df.sample(1).iloc[0]
        correct = quiz["説明"]
        wrong_choices = (
            filtered_df[filtered_df["用語"] != quiz["用語"]]["説明"]
            .drop_duplicates()
            .sample(min(3, len(filtered_df) - 1))
            .tolist()
        )
        options = wrong_choices + [correct]
        random.shuffle(options)

        st.session_state.current_quiz = {
            "word": quiz["用語"],
            "correct": correct,
            "options": options
        }
        st.session_state.quiz_answered = False
        st.session_state.quiz_choice = None
    else:
        st.session_state.current_quiz = None

# 初期ロード or「次へ」で再出題
if st.session_state.current_quiz is None and len(filtered_df) > 0:
    load_new_quiz()

# --- 全問解答済み処理 ---
if len(filtered_df) == 0:
    st.success("🎉 選択中の条件では全問解答済みです！")
    if st.button("🔁 セッションをリセットする"):
        for key in defaults:
            st.session_state[key] = defaults[key] if not isinstance(defaults[key], set) else set()
        st.rerun()

elif st.session_state.current_quiz:
    quiz = st.session_state.current_quiz
    st.subheader(f"この用語の説明は？：**{quiz['word']}**")
    choice = st.radio("選択肢を選んでください", quiz["options"], index=0 if st.session_state.quiz_choice is None else quiz["options"].index(st.session_state.quiz_choice))
    st.session_state.quiz_choice = choice

    if not st.session_state.quiz_answered:
        if st.button("✅ 答え合わせ"):
            st.session_state.total += 1
            st.session_state.answered_words.add(quiz["word"])
            if choice == quiz["correct"]:
                st.session_state.correct += 1
                st.session_state.latest_result = "✅ 正解！🎉"
            else:
                st.session_state.latest_result = f"❌ 不正解… 正解は「{quiz['correct']}」でした。"
            st.session_state.quiz_answered = True
            st.rerun()
    else:
        st.info(st.session_state.latest_result)
        if st.button("➡️ 次の問題へ"):
            st.session_state.current_quiz = None
            st.rerun()