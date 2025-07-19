import streamlit as st
import pandas as pd
import random

class QuizApp:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.kana_labels = ["ア", "イ", "ウ", "エ", "オ"] # カナラベルは固定
        self.defaults = {
            "total": 0,
            "correct": 0,
            "answered_words": set(),
            "latest_result": "",
            "current_quiz": None,
            "quiz_answered": False,
            "quiz_choice_index": 0, # 選択肢のインデックスを保存するように変更
            "history": []
        }
        self._initialize_session()

    def _initialize_session(self):
        """セッション状態を初期化またはデフォルト値に設定します。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            # answered_wordsはセットとして初期化を保証
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _reset_session_state(self):
        """セッション状態をデフォルト値にリセットします。"""
        for key, val in self.defaults.items():
            st.session_state[key] = val if not isinstance(val, set) else set()
        st.success("✅ セッションをリセットしました")
        st.rerun()

    def filter_data(self):
        """ユーザーの選択に基づいてデータをフィルタリングします。"""
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
        """現在の学習進捗を表示します。"""
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答：{st.session_state.total} 回 / 🎯 正解：{st.session_state.correct} 回**")

    def load_quiz(self, df_filtered, remaining_df):
        """新しいクイズをロードし、セッション状態を更新します。"""
        if len(remaining_df) > 0:
            q = remaining_df.sample(1).iloc[0]
            correct_description = q["説明"]

            # 不正解の選択肢を生成
            wrong_options = (
                df_filtered[df_filtered["単語"] != q["単語"]]["説明"]
                .drop_duplicates()
                .sample(min(3, len(df_filtered.drop_duplicates(subset=["説明"])) - 1)) # 説明の重複を考慮
                .tolist()
            )

            options = wrong_options + [correct_description]
            random.shuffle(options)

            st.session_state.current_quiz = {
                "単語": q["単語"],
                "説明": correct_description,
                "選択肢": options,
                "記述": q.get("午後記述での使用例", "N/A"),
                "文脈": q.get("使用理由／文脈", "N/A"),
                "区分": q.get("試験区分", "N/A")
            }
            st.session_state.quiz_answered = False
            st.session_state.quiz_choice_index = 0 # 新しいクイズでは最初の選択肢をデフォルトに
        else:
            st.session_state.current_quiz = None # 問題がなくなったらクイズをクリア

    def _display_quiz_question(self):
        """クイズの質問と関連情報を表示します。"""
        q = st.session_state.current_quiz
        if not q:
            return

        st.subheader(f"この用語の説明は？：**{q['単語']}**")
        st.markdown(f"🧩 **午後記述での使用例：** {q['記述']}")
        st.markdown(f"🎯 **使用理由／文脈：** {q['文脈']}")
        st.markdown(f"🕘 **試験区分：** {q['区分']}")

    def _handle_answer_submission(self, selected_option_text, current_quiz_data):
        """ユーザーの回答を処理し、結果を更新します。"""
        st.session_state.total += 1
        st.session_state.answered_words.add(current_quiz_data["単語"])

        is_correct = (selected_option_text == current_quiz_data["説明"])
        result_mark = "〇" if is_correct else "×"
        st.session_state.latest_result = (
            "✅ 正解！🎉" if is_correct
            else f"❌ 不正解… 正解は「{current_quiz_data['説明']}」でした。"
        )
        st.session_state.correct += 1 if is_correct else 0

        # 履歴に記録
        choice_kana = self.kana_labels[current_quiz_data["選択肢"].index(selected_option_text)]
        correct_kana = self.kana_labels[current_quiz_data["選択肢"].index(current_quiz_data["説明"])]

        st.session_state.history.append({
            "単語": current_quiz_data["単語"],
            "私の選択": choice_kana,
            "正解": correct_kana,
            "正誤": result_mark,
            "記述例": current_quiz_data["記述"],
            "文脈": current_quiz_data["文脈"],
            "試験区分": current_quiz_data["区分"]
        })
        st.session_state.quiz_answered = True

    def _display_result_and_next_button(self):
        """回答結果と次の問題へのボタンを表示します。"""
        st.info(st.session_state.latest_result)
        if st.button("➡️ 次の問題へ"):
            st.session_state.current_quiz = None
            st.session_state.quiz_answered = False
            st.rerun()

    def display_quiz(self, df_filtered, remaining_df):
        """クイズの質問と選択肢を表示し、回答を処理します。"""
        q = st.session_state.current_quiz
        if not q:
            return

        self._display_quiz_question()

        labeled_options = [f"{self.kana_labels[i]}：{txt}" for i, txt in enumerate(q["選択肢"])]

        # st.radioのindex引数をquiz_choice_indexで管理
        selected_labeled_option = st.radio(
            "選択肢を選んでください",
            labeled_options,
            index=st.session_state.quiz_choice_index,
            key=f"quiz_radio_{st.session_state.total}"
        )

        # 選択されたオプションのテキストとインデックスを取得
        selected_option_index = labeled_options.index(selected_labeled_option)
        selected_option_text = q["選択肢"][selected_option_index]

        # quiz_choice_indexを更新（ユーザーが選択肢を変更した場合に備える）
        if st.session_state.quiz_choice_index != selected_option_index:
            st.session_state.quiz_choice_index = selected_option_index


        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                self._handle_answer_submission(selected_option_text, q)
                # 答え合わせ後、選択肢のインデックスを保持したままにするため、rerunしない
                # ただし、結果表示のために再描画される
                st.rerun() # 結果表示のためにrerunが必要
        else:
            self._display_result_and_next_button()

    def show_completion(self):
        """すべての問題に回答した際のメッセージを表示します。"""
        st.success("🎉 すべての問題に回答しました！")
        st.balloons() # お祝いのアニメーション

    def offer_download(self):
        """学習履歴のCSVダウンロードボタンを提供します。"""
        df_log = pd.DataFrame(st.session_state.history or [])
        if not df_log.empty:
            csv = df_log.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 学習履歴をCSVで保存", data=csv, file_name="quiz_results.csv", mime="text/csv")
        else:
            st.info("まだ学習履歴がありません。")


    def run(self):
        """アプリケーションのメイン実行ロジックです。"""
        st.set_page_config(layout="wide", page_title="用語クイズアプリ") # ページ設定をワイドに

        # カスタムCSSの適用
        st.markdown("""
            <style>
            .stApp {
                background-color: #f0f2f6;
            }
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                border-radius: 12px;
                padding: 10px 24px;
                font-size: 16px;
                transition-duration: 0.4s;
                box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19);
            }
            .stButton>button:hover {
                background-color: #45a049;
                color: white;
            }
            .stRadio > label {
                font-size: 18px;
                margin-bottom: 10px;
                padding: 10px;
                border-radius: 8px;
                background-color: #e6e6e6;
                border: 1px solid #ddd;
            }
            .stRadio > label:hover {
                background-color: #dcdcdc;
            }
            .stRadio > label > div > p {
                font-weight: bold;
            }
            h1, h2, h3 {
                color: #2e4053;
            }
            .stInfo {
                background-color: #e0f2f7;
                color: #2196F3;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
                border: 1px solid #90caf9;
            }
            .stSuccess {
                background-color: #e8f5e9;
                color: #4CAF50;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
                border: 1px solid #a5d6a7;
            }
            .stError {
                background-color: #ffebee;
                color: #f44336;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
                border: 1px solid #ef9a9a;
            }
            </style>
            """, unsafe_allow_html=True)


        st.title("用語クイズアプリ")

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
        st.markdown("---") # 区切り線
        self.reset_session_button() # リセットボタンの呼び出し

# アプリ実行（tango.csv に上記フォーマットでデータを保存してください）
try:
    df = pd.read_csv("tango.csv")
    # tango.csvの列検証を追加
    required_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分"]
    if not all(col in df.columns for col in required_columns):
        st.error(f"❌ 'tango.csv' に必要な列が不足しています。不足している列: {', '.join([col for col in required_columns if col not in df.columns])}")
        st.stop() # アプリの実行を停止
    
    app = QuizApp(df)
    app.run()
except FileNotFoundError:
    st.error("❌ 'tango.csv' が見つかりません。")
    st.info("必要な列：カテゴリ,分野,単語,説明,午後記述での使用例,使用理由／文脈,試験区分")
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("データファイル 'tango.csv' の内容を確認してください。")

