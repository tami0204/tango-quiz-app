import streamlit as st
import pandas as pd
import random

# CSV読み込み
df = pd.read_csv("tango.csv")

st.title("📘 単語クイズアプリ（午前・午後対応）")

# --- 初期化 ---
kana_labels = ["ア", "イ", "ウ", "エ", "オ"]
defaults = {
    "total": 0,
    "correct": 0,
    "answered_words": set(),
    "latest_result": "",
    "current_quiz": None,
    "quiz_answered": False,
    "quiz_choice": None,
    "history": []
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val if not isinstance(val, set) else set()

# --- フィルター選択 ---
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

# --- クイズ出題 ---
def load_quiz():
    if len(remaining_df) > 0:
        q = remaining_df.sample(1).iloc[0]
        correct = q["説明"]
        wrongs = (
            filtered_df[filtered_df["用語"] != q["用語"]]["説明"]
            .drop_duplicates()
            .sample(min(3, len(filtered_df) - 1))
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
    else:
        st.session_state.current_quiz = None

if st.session_state.current_quiz is None and len(filtered_df) > 0:
    load_quiz()

# --- 全問終了時 ---
if len(filtered_df) == 0:
    st.success("🎉 すべての問題に回答しました！")

# --- 履歴保存表示 ---
df_log = pd.DataFrame(st.session_state.history or [])
csv = df_log.to_csv(index=False).encode("utf-8-sig")
st.download_button("📥 学習記録をCSVで保存", data=csv, file_name="quiz_results.csv", mime="text/csv")

# --- セッションリセット（終了後のみ表示） ---
if len(filtered_df) == 0 and st.button("🔁 セッションをリセット"):
    for k in defaults:
        st.session_state[k] = defaults[k] 
        if not isinstance(defaults[k], set) :
        else set()
    st.rerun()

# --- クイズ表示と答え合わせ ---
elif st.session_state.current_quiz:
    q = st.session_state.current_quiz
    st.subheader(f"この用語の説明は？：**{q['word']}**")
    labeled = [f"{kana_labels[i]}：{txt}" for i, txt in enumerate(q["options"])]
    selected = st.radio("選択肢を選んでください", labeled,
                        index=0 if st.session_state.quiz_choice is None else labeled.index(st.session_state.quiz_choice))
    st.session_state.quiz_choice = selected

    choice_idx = labeled.index(selected)
    choice_text = q["options"][choice_idx]
    choice_kana = kana_labels[choice_idx]
    correct_kana = kana_labels[q["options"].index(q["correct"])]

    if not st.session_state.quiz_answered:
        if st.button("✅ 答え合わせ"):
            st.session_state.total += 1
            st.session_state.answered_words.add(q["word"])
            result = "〇" if choice_text == q["correct"] else "×"
            if result == "〇":
                st.session_state.correct += 1
                st.session_state.latest_result = "✅ 正解！🎉"
            else:
                st.session_state.latest_result = f"❌ 不正解… 正解は「{q['correct']}」でした。"

            st.session_state.history.append({
                "用語": q["word"],
                "私の選択": choice_kana,
                "正解": correct_kana,
                "正誤": result
            })

            st.session_state.quiz_answered = True
            st.rerun()
    else:
        st.info(st.session_state.latest_result)
        if st.button("➡️ 次の問題へ"):
            st.session_state.current_quiz = None
            st.rerun()
