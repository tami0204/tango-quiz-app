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
        # Streamlitのセッションステートを初期化します。
        # アプリのリロード時にも状態が保持されるようにします。
        for key, val in self.defaults.items():
            st.session_state[key] = val if key not in st.session_state else st.session_state[key]

    def filter_data(self):
        # ユーザーが分野と試験区分でデータをフィルタリングできるようにします。
        field = st.selectbox("分野を選ぶ", ["すべて"] + sorted(self.df["分野"].dropna().unique()))
        period = st.selectbox("試験区分を選ぶ", ["すべて"] + sorted(self.df["試験区分"].dropna().unique()))
        df_filtered = self.df.copy()
        if field != "すべて":
            df_filtered = df_filtered[df_filtered["分野"] == field]
        if period != "すべて":
            df_filtered = df_filtered[df_filtered["試験区分"] == period]
        # まだ回答されていない単語を抽出します。
        remaining = df_filtered[~df_filtered["用語"].isin(st.session_state.answered_words)]
        return df_filtered, remaining

    def show_progress(self, df_filtered):
        # クイズの進捗状況と正答率を表示します。
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答数：{st.session_state.total} 回 / 🎯 正解数：{st.session_state.correct} 回**")

    def load_quiz(self, df_filtered, remaining_df):
        # 新しいクイズの問題をロードします。
        if len(remaining_df) > 0:
            q = remaining_df.sample(1).iloc[0] # 残っている単語からランダムに1つ選択
            correct = q["説明"]
            # 正解以外の選択肢をランダムに3つ（またはそれ以下）選択します。
            wrongs = (
                df_filtered[df_filtered["用語"] != q["用語"]]["説明"]
                .drop_duplicates()
                .sample(min(3, len(df_filtered) - 1))
                .tolist()
            )
            options = wrongs + [correct]
            random.shuffle(options) # 選択肢をシャッフルします。
            st.session_state.current_quiz = {
                "word": q["用語"],
                "correct": correct,
                "options": options
            }
            st.session_state.quiz_answered = False
            st.session_state.quiz_choice = None

    def display_quiz(self, df_filtered, remaining_df):
        # 現在のクイズの問題と選択肢を表示します。
        q = st.session_state.current_quiz
        if not q:
            return

        st.subheader(f"この用語の説明は？：**{q['word']}**")
        # 選択肢にカナラベル（ア、イ、ウ…）を付けます。
        labeled = [f"{self.kana_labels[i]}：{txt}" for i, txt in enumerate(q["options"])]
        
        # st.radioに一意のkeyを追加し、ウィジェットが確実に再レンダリングされるようにします。
        selected = st.radio("選択肢を選んでください", labeled,
                            index=0 if st.session_state.quiz_choice is None
                            else labeled.index(st.session_state.quiz_choice),
                            key=f"quiz_radio_{st.session_state.total}") # ここにkeyを追加

        st.session_state.quiz_choice = selected

        choice_idx = labeled.index(selected)
        choice_text = q["options"][choice_idx]
        choice_kana = self.kana_labels[choice_idx]
        correct_kana = self.kana_labels[q["options"].index(q["correct"])]

        if not st.session_state.quiz_answered:
            # 答え合わせボタンを表示します。
            if st.button("✅ 答え合わせ"):
                st.session_state.total += 1
                st.session_state.answered_words.add(q["word"]) # 回答済みの単語に追加
                result = "〇" if choice_text == q["correct"] else "×"
                st.session_state.latest_result = (
                    "✅ 正解！🎉" if result == "〇"
                    else f"❌ 不正解… 正解は「{q['correct']}」でした。"
                )
                st.session_state.correct += 1 if result == "〇" else 0
                # 学習履歴を記録します。
                st.session_state.history.append({
                    "用語": q["word"],
                    "私の選択": choice_kana,
                    "正解": correct_kana,
                    "正誤": result
                })
                st.session_state.quiz_answered = True

        if st.session_state.quiz_answered:
            # 答え合わせの結果を表示し、次の問題へのボタンを表示します。
            st.info(st.session_state.latest_result)
            if st.button("➡️ 次の問題へ"):
                st.session_state.current_quiz = None
                st.session_state.quiz_answered = False
                st.session_state.quiz_choice = None
                # Streamlitの性質上、ボタンが押されるとアプリ全体が再実行され、
                # その際に load_quiz() が再度呼ばれて次の問題が設定されます。

    def show_completion(self):
        # すべての問題に回答した場合のメッセージを表示します。
        st.success("🎉 すべての問題に回答しました！")

    def offer_download(self):
        # 学習記録をCSVとしてダウンロードするボタンを提供します。
        df_log = pd.DataFrame(st.session_state.history or [])
        csv = df_log.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 学習記録をCSVで保存", data=csv, file_name="quiz_results.csv", mime="text/csv")

    def reset_session_button(self):
        # セッションをリセットするボタンを提供します。
        if st.button("🔁 セッションをリセット"):
            for key, val in self.defaults.items():
                st.session_state[key] = val if not isinstance(val, set) else set() # セットは新しい空のセットで初期化
            st.success("✅ セッションをリセットしました")

    def run(self):
        # アプリケーションのメインロジックです。
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
# tango.csvファイルを読み込み、QuizAppインスタンスを作成して実行します。
# このファイルはスクリプトと同じディレクトリに存在する必要があります。
try:
    df = pd.read_csv("tango.csv")
    app = QuizApp(df)
    app.run()
except FileNotFoundError:
    st.error("エラー: 'tango.csv' ファイルが見つかりません。スクリプトと同じディレクトリに配置してください。")
    st.info("`tango.csv`は、少なくとも`用語`、`説明`、`分野`、`試験区分`の列を持つ必要があります。")
    st.code("""
用語,説明,分野,試験区分
Apple,リンゴです,果物,初級
Banana,バナナです,果物,初級
Computer,計算機です,IT,応用
Network,通信網です,IT,応用
    """)

