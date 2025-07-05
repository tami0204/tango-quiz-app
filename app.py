import streamlit as st
import pandas as pd
import random

# CSV読み込み
df = pd.read_csv("tango.csv")

st.title("📘 単語クイズアプリ（午前・午後対応）")

# セッションステートの初期化
if "total" not in st.session_state:
    st.session_state.total = 0
    
if "correct" not in st.session_state:
    st.session_state.correct = 0
    
if "answered_words" not in st.session_state:
    st.session_state.answered_words = set()
    
if "latest_result" not in st.session_state:
    st.session_state.latest_result = ""

# 分野・試験区分でフィルター
field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(df["分野"].unique()))
period = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(df["試験区分"].unique()))

# フィルタリング処理
filtered_df = df.copy()

if field != "すべて":
    filtered_df = filtered_df[filtered_df["分野"] == field]
    
if period != "すべて":
    filtered_df = filtered_df[filtered_df["試験区分"] == period]

# 未出題データの絞り込み
remaining_df = filtered_df[~filtered_df["用語"].isin(st.session_state.answered_words)]

# 進捗と正解数表示
st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)}語中 {len(filtered_df)} 語学習済み**")

st.markdown(f"🔁 **これまで {st.session_state.total} 回回答 / 🎯 正解数：{st.session_state.correct} 回**")

# クイズ出題
if len(filtered_df) == 0:
    st.warning("その条件には該当する問題がありません。")
elif len(remaining_df) == 0:
    st.success("🎉 全ての問題に回答しました！お疲れさまでした！")
else:
    quiz = remaining_df.sample(1).iloc[0]
    word = quiz["用語"]
    correct = quiz["説明"]

    # 選択肢を生成（重複なし）
    wrong_choices = (
        filtered_df[filtered_df["用語"] != word]["説明"]
        .drop_duplicates()
        .sample(min(3, len(filtered_df)-1))
        .tolist()
    )
    options = wrong_choices + [correct]
    random.shuffle(options)

    st.subheader(f"この用語の説明は？：**{word}**")
    answer = st.radio("選択肢", options)

    if st.button("答え合わせ"):
        st.session_state.total += 1
        st.session_state.answered_words.add(word)

        if answer == correct:
            st.session_state.correct += 1
            st.session_state.latest_result = "✅ 正解！🎉"
        else:
            st.session_state.latest_result = f"❌ 不正解… 正解は「{correct}」でした。"

# 結果を表示（最新の回答に関するメッセージ）
if st.session_state.latest_result:
    st.info(st.session_state.latest_result)