import streamlit as st
import pandas as pd
import random

# CSV読み込み
df = pd.read_csv("tango.csv")

st.title("📘 単語クイズアプリ（午前・午後対応）")

# --- セッションステート初期化 ---
for key, default in {
    "total": 0,
    "correct": 0,
    "answered_words": set(),
    "latest_result": "",
    "current_quiz": None,
    "quiz_answered": False,
    "quiz_choice": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- フィルター ---
field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(df["分野"].unique()))
period = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(df["試験区分"].unique()))

filtered_df = df.copy()
if field != "すべて":
    filtered_df = filtered_df[filtered_df["分野"] == field]
if period != "すべて":
    filtered_df = filtered_df[filtered_df["試験区分"] == period]

remaining_df = filtered_df[~filtered_df["用語"].isin(st.session_state.answered_words)]

# --- 進捗表示 ---
st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)}中 {len(filtered_df)} 語学習済み**")
st.markdown(f"🔁 **これまで {st.session_state.total} 回回答 / 🎯 正解数：{st.session_state.correct} 回**")

# --- 新しいクイズをセット ---
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

# 初回または「次へ」でクイズをロード
if st.session_state.current_quiz is None:
    load_new_quiz()

# --- 全問完了した場合 ---
if len(filtered_df) == 0:
    st.warning("その条件の問題はありません。")
elif st.session_state.current_quiz is None:
    st.success("🎉 全問解答済み！お疲れさまでした！")
    if st.button("🔁 セッションをリセットする"):
        for key in ["total", "correct", "answered_words", "latest_result", "current_quiz", "quiz_answered", "quiz_choice"]:
            st.session_state[key] = 0 if isinstance(st.session_state[key], int) else set() if isinstance(st.session_state[key], set) else ""
        st.experimental_rerun()
else:
    quiz = st.session_state.current_quiz
    st.subheader(f"この用語の説明は？：**{quiz['word']}**")
    st.session_state.quiz_choice = st.radio("選択肢を選んでください", quiz["options"], index=0 if st.session_state.quiz_choice is None else quiz["options"].index(st.session_state.quiz_choice))

    if not st.session_state.quiz_answered:
        if st.button("✅ 答え合わせ"):
            st.session_state.total += 1
            st.session_state.answered_words.add(quiz["word"])
            if st.session_state.quiz_choice == quiz["correct"]:
                st.session_state.correct += 1
                st.session_state.latest_result = "✅ 正解！🎉"
            else:
                st.session_state.latest_result = f"❌ 不正解… 正解は「{quiz['correct']}」でした。"
            st.session_state.quiz_answered = True
            st.experimental_rerun()
    else:
        st.info(st.session_state.latest_result)
        if st.button("➡️ 次の問題へ"):
            st.session_state.current_quiz = None
            st.experimental_rerun()