import streamlit as st
import pandas as pd
import random

# CSVファイル読み込み
df = pd.read_csv("tango.csv")

st.title("📘 単語クイズアプリ（午前・午後対応）")

# 分野や試験区分でフィルター（任意）
field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(df["分野"].unique()))
period = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(df["試験区分"].unique()))

# フィルタリング処理
filtered_df = df.copy()
if field != "すべて":
    filtered_df = filtered_df[filtered_df["分野"] == field]
if period != "すべて":
    filtered_df = filtered_df[filtered_df["試験区分"] == period]

# クイズ出題
if len(filtered_df) == 0:
    st.warning("その条件には該当する問題がありません。")
else:
    quiz = filtered_df.sample(1).iloc[0]
    word = quiz["用語"]
    correct = quiz["説明"]

    # 他の説明を選択肢に追加
    wrong_choices = filtered_df[filtered_df["用語"] != word]["説明"].sample(3, replace=True).tolist()
    options = wrong_choices + [correct]
    random.shuffle(options)

    st.subheader(f"この用語の説明は？：**{word}**")
    answer = st.radio("選択肢", options)

    if st.button("答え合わせ"):
        if answer == correct:
            st.success("正解！🎉")
        else:
            st.error(f"不正解… 正解は「{correct}」でした")