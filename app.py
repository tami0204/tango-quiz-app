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
            "history": [],
            "next_trigger": False
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
            return

        st.subheader(f"この用語の説明は？：**{q['word']}**")
        labeled = [f"{self.kana_labels[i]}：{txt}" for i, txt in enumerate(q["options"])]
        selected = st.radio("選択肢を選んでください", labeled,
                            index=0 if st.session_state.quiz_choice is None
                            else labeled.index(st.session_state.quiz_choice))
        st.session_state.quiz_choice = selected

        choice_idx = labeled.index(selected)
        choice_text = q["options"][choice_idx]
        choice_kana = self.kana_labels[choice_idx]
        correct_kana = self.kana_labels[q["options"].index(q["correct"])]

        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                st.session_state.total += 1
                st.session_state.answered_words.add(q["word"])
                result = "〇" if choice_text == q["correct"] else "×"
                st.session_state.latest_result = (
                    "✅ 正解！🎉" if result == "〇"
                    else f"❌ 不正解… 正解は「{q['correct']}」でした。"
                )
                st.session_state.correct += 1 if result == "〇" else 0
                st.session_state.history.append({
                    "用語": q["word"],
                    "私の選択": choice_kana,
                    "正解": correct_kana,
                    "正誤": result
                })
                st.session_state.quiz_answered = True

        if st.session_state.quiz_answered:
            st.info(st.session_state.latest_result)
            if st.button("➡️ 次の問題へ"):
                st.session_state.current_quiz = None
                st.session_state.quiz_answered = False
                st.session_state.quiz_choice = None
                st.session_state.next_trigger = True

    def show_completion(self):
        st.success("🎉 すべての問題に回答しました！")

    def offer_download(self):
        df_log = pd.DataFrame(st.session_state.history or [])
        csv = df_log.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 学習記録をCSVで保存", data=csv, file_name="quiz_results.csv", mime="text/csv")

    def reset_session_button(self):
        if st.button("🔁 セッションをリセット"):
            for key, val in self.defaults.items():
                st.session_state[key] = val if not isinstance(val, set) else set()
            st.success("✅ セッションをリセットしました")

    def run(self):
        if st.session_state.get("next_trigger"):
            st.session_state.next_trigger = False
            st.experimental_rerun()

        df_filtered, remaining_df = self.filter_data()
        self.show_progress(df_filtered)

        if st.session_state.current_quiz is None and len(remaining_df) > 0:
            self.load_quiz(df_filtered, remaining_df)
        if len(remaining_df) == 0:
            self.show_completion()
        else:
            self.display_quiz(df_filtered, remaining_df)

        self.offer_download()
        self.reset_session_button()

# --- アプリ起動 ---
df = pd.read_csv("tango.csv")
app = QuizApp(df)
app.run()
