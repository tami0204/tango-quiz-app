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
            st.session_state[key] = val if key not in st.session_state else st.session_state[key]

    def filter_data(self):
        category = st.selectbox("カテゴリを選ぶ", ["すべて"] + sorted(self.df["カテゴリ"].dropna().unique()))
        field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(self.df["分野"].dropna().unique()))
        level = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(self.df["試験区分"].dropna().unique()))
        df_filtered = self.df.copy()
        if category != "すべて":
            df_filtered = df_filtered[df_filtered["カテゴリ"] == category]
        if field != "すべて":
            df_filtered = df_filtered[df_filtered["分野"] == field]
        if level != "すべて":
            df_filtered = df_filtered[df_filtered["試験区分"] == level]
        remaining = df_filtered[~df_filtered["単語"].isin(st.session_state.answered_words)]
        return df_filtered, remaining

    def show_progress(self, df_filtered):
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答：{st.session_state.total} 回 / 🎯 正解：{st.session_state.correct} 回**")

    def load_quiz(self, df_filtered, remaining_df):
        if len(remaining_df) > 0:
            q = remaining_df.sample(1).iloc[0]
            correct = q["説明"]
            wrongs = (
                df_filtered[df_filtered["単語"] != q["単語"]]["説明"]
                .drop_duplicates()
                .sample(min(3, len(df_filtered) - 1))
                .tolist()
            )
            options = wrongs + [correct]
            random.shuffle(options)
            st.session_state.current_quiz = {
                "単語": q["単語"],
                "説明": correct,
                "選択肢": options,
                "記述": q.get("午後記述での使用例", ""),
                "文脈": q.get("使用理由／文脈", ""),
                "区分": q.get("試験区分", "")
            }
            st.session_state.quiz_answered = False
            st.session_state.quiz_choice = f"{self.kana_labels[0]}：{options[0]}"

    def display_quiz(self, df_filtered, remaining_df):
        q = st.session_state.current_quiz
        if not q:
            return

        st.subheader(f"この用語の説明は？：**{q['単語']}**")
        st.markdown(f"🧩 **午後記述での使用例：** {q['記述']}")
        st.markdown(f"🎯 **使用理由／文脈：** {q['文脈']}")
        st.markdown(f"🕘 **試験区分：** {q['区分']}")

        labeled = [f"{self.kana_labels[i]}：{txt}" for i, txt in enumerate(q["選択肢"])]
        selected = st.radio("選択肢を選んでください", labeled,
            index=labeled.index(st.session_state.quiz_choice),
            key=f"quiz_radio_{st.session_state.total}")
        st.session_state.quiz_choice = selected

        choice_idx = labeled.index(selected)
        choice_text = q["選択肢"][choice_idx]
        choice_kana = self.kana_labels[choice_idx]
        correct_kana = self.kana_labels[q["選択肢"].index(q["説明"])]

        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                st.session_state.total += 1
                st.session_state.answered_words.add(q["単語"])
                result = "〇" if choice_text == q["説明"] else "×"
                st.session_state.latest_result = (
                    "✅ 正解！🎉" if result == "〇"
                    else f"❌ 不正解… 正解は「{q['説明']}」でした。"
                )
                st.session_state.correct += 1 if result == "〇" else 0
                st.session_state.history.append({
                    "単語": q["単語"],
                    "私の選択": choice_kana,
                    "正解": correct_kana,
                    "正誤": result,
                    "記述例": q["記述"],
                    "文脈": q["文脈"],
                    "試験区分": q["区分"]
                })
                st.session_state.quiz_answered = True

        if st.session_state.quiz_answered:
            st.info(st.session_state.latest_result)
            if st.button("➡️ 次の問題へ"):
                st.session_state.current_quiz = None
                st.session_state.quiz_answered = False
                st.rerun()

    def show_completion(self):
        st.success("🎉 すべての問題に回答しました！")

    def offer_download(self):
        df_log = pd.DataFrame(st.session_state.history or [])
        csv = df_log.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 学習履歴をCSVで保存", data=csv, file_name="quiz_results.csv", mime="text/csv")

    def reset_session_button(self):
        if st.button("🔁 セッションをリセット"):
            for key, val in self.defaults.items():
                st.session_state[key] = val if not isinstance(val, set) else set()
            st.success("✅ セッションをリセットしました")
            st.rerun()

    def run(self):
        df_filtered, remaining_df = self.filter_data()
        self.show_progress(df_filtered)
        with st.expander("📂 読み込みデータの確認"):
            st.dataframe(self.df.head())
        if st.session_state.current_quiz is None and len(remaining_df) > 0:
            self.load_quiz(df_filtered, remaining_df)
        if len(remaining_df) == 0:
            self.show_completion()
        else:
            self.display_quiz(df_filtered, remaining_df)
        self.offer_download()
        self.reset_session_button()

# アプリ実行（tango.csv に上記フォーマットでデータを保存してください）
try:
    df = pd.read_csv("tango.csv")
    app = QuizApp(df)
    app.run()
except FileNotFoundError:
    st.error("❌ 'tango.csv' が見つかりません。")
    st.info("必要な列：カテゴリ,分野,単語,説明,午後記述での使用例,使用理由／文脈,試験区分")
