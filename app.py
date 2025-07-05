import streamlit as st
import pandas as pd
import random

# CSV 読み込み
df = pd.read_csv("tango.csv")

st.title("📘 単語クイズアプリ（午前・午後対応）")

# --- セッションステート初期化 ---
if "total" not in st.session_state:
    st.session_state.total = 0
if "correct" not in st.session_state:
    st.session_state.correct = 0
if "answered_words" not in st.session_state:
    st.session_state.answered_words = set()
if "latest_result" not in st.session_state:
    st.session_state.latest_result = ""
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None

# --- フィルタ選択 ---
field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(df["分野"].unique()))
period = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(df["試験区分"].unique()))

# --- フィルタリング処理 ---
filtered_df = df.copy()
if field != "すべて":
    filtered_df = filtered_df[filtered_df["分野"] == field]
if period != "すべて":
    filtered_df = filtered_df[filtered_df["試験区分"] == period]

# --- 出題済み単語の除外 ---
remaining_df = filtered_df[~filtered_df["用語"].isin(st.session_state.answered_words)]

# --- 進捗表示 ---
st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)}語中 {len(filtered_df)} 語学習済み**")
st.markdown(f"🔁 **これまで {st.session_state.total} 回回答 / 🎯 正解数：{st.session_state.correct} 回**")

# --- クイズの再出題処理 ---
def get_new_quiz():
    if len(remaining_df) > 0:
        quiz = remaining_df.sample(1).iloc[0]
        word = quiz["用語"]
        correct = quiz["説明"]
        wrong_choices = (
            filtered_df[filtered_df["用語"] != word]["説明"]
            .drop_duplicates()
            .sample(min(3, len(filtered_df)-1))
            .tolist()
        )
        options = wrong_choices + [correct]
        random.shuffle(options)
        st.session_state.current_quiz = {
            "word": word,
            "correct": correct,
            "options": options,
            "answered": False
        }
    else:
        st.session_state.current_quiz = None

# --- 初期化（まだ出題していないとき） ---
if st.session_state.current_quiz is None:
    get_new_quiz()

# --- 全問解答済みチェック ---
if len(filtered_df) == 0:
    st.warning("該当する問題が存在しません。")
elif st.session_state.current_quiz is None:
    st.success("🎉 すべての問題に回答しました！よく頑張りました！")
    if st.button("セッションをリセットする"):
        st.session_state.total = 0
        st.session_state.correct = 0
        st.session_state.answered_words = set()
        st.session_state.latest_result = ""
        get_new_quiz()
else:
    quiz = st.session_state.current_quiz
    st.subheader(f"この用語の説明は？：**{quiz['word']}**")
    answer = st.radio("選択肢を選んでください", quiz["options"], key=quiz["word"])

    if not quiz["answered"]:
        if st.button("答え合わせ"):
            st.session_state.total += 1
            st.session_state.answered_words.add(quiz["word"])
            if answer == quiz["correct"]:
                st.session_state.correct += 1
                st.session_state.latest_result = "✅ 正解！🎉"
            else:
                st.session_state.latest_result = f"❌ 不正解… 正解は「{quiz['correct']}」でした。"
            st.session_state.current_quiz["answered"] = True
    else:
        st.info(st.session_state.latest_result)
        if st.button("次の問題へ"):
            get_new_quiz()