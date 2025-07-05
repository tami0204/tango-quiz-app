import streamlit as st
import pandas as pd
import random

# CSV読み込み
df = pd.read_csv("tango.csv")

st.set_page_config(page_title="単語クイズ", layout="centered")
st.title("📘 単語クイズアプリ")

# 分野と試験区分の選択
field = st.selectbox("🔍 分野を選ぶ", ["すべて"] + sorted(df["分野"].unique()))
period = st.selectbox("🕓 試験区分を選ぶ", ["すべて"] + sorted(df["試験区分"].unique()))

filtered_df = df.copy()
if field != "すべて":
    filtered_df = filtered_df[filtered_df["分野"] == field]
if period != "すべて":
    filtered_df = filtered_df[filtered_df["試験区分"] == period]

# 問題をセッションに固定
if "current_quiz" not in st.session_state or st.session_state.get("next_question"):
    if len(filtered_df) > 0:
        st.session_state.current_quiz = filtered_df.sample(1).iloc[0]
    else:
        st.warning("該当する問題がありません。")
    st.session_state.next_question = False

if len(filtered_df) > 0:
    quiz = st.session_state.current_quiz
    word = quiz["用語"]
    correct = quiz["説明"]

    # 選択肢生成
    wrong = filtered_df[filtered_df["用語"] != word]["説明"].sample(3, replace=True).tolist()
    options = wrong + [correct]
    random.shuffle(options)

    st.subheader(f"この用語の説明は？ 👉 **{word}**")
    selected = st.radio("選択肢を選んでください", options)

    if st.button("✅ 答え合わせ"):
        if selected == correct:
            st.success("🎉 正解です！")
        else:
            st.error(f"❌ 不正解... 正解は：「{correct}」")

    if st.button("🔁 次の問題へ"):
        st.session_state.next_question = True
        st.experimental_rerun()
