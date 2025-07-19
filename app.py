import streamlit as st
import pandas as pd
import random

class QuizApp:
    def __init__(self, df: pd.DataFrame):
        self.kana_labels = ["ア", "イ", "ウ", "エ", "オ"] # カナラベルは固定
        self.defaults = {
            "total": 0,
            "correct": 0,
            "answered_words": set(),
            "latest_result": "",
            "latest_correct_description": "",
            "current_quiz": None,
            "quiz_answered": False,
            "quiz_choice_index": 0,
            "history": [],
            "current_round": 1, # 新規追加：現在更新すべき実施回数列
            "quiz_df": None # 新規追加：セッション状態にクイズ用DataFrameを保持
        }
        self._initialize_session()

        # アプリ初回起動時、またはリセット時にquiz_dfを初期化
        if st.session_state.quiz_df is None:
            st.session_state.quiz_df = df.copy() # オリジナルDataFrameをセッション状態にコピー

    def _initialize_session(self):
        """セッション状態を初期化またはデフォルト値に設定します。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _reset_session_state(self):
        """セッション状態をデフォルト値にリセットします。"""
        # quiz_df は外部から渡されたdfを元に再初期化
        st.session_state.quiz_df = self.initial_df.copy() # 初期読み込み時のdfを保持しておく必要があります
        for key, val in self.defaults.items():
            if key != "quiz_df": # quiz_dfは上記で初期化済みなのでスキップ
                st.session_state[key] = val if not isinstance(val, set) else set()
        st.success("✅ セッションをリセットしました")
        st.rerun()

    def filter_data(self):
        """ユーザーの選択に基づいてデータをフィルタリングします。
           ここではセッション状態のquiz_dfを使用します。"""
        current_category = st.session_state.get("filter_category", "すべて")
        current_field = st.session_state.get("filter_field", "すべて")
        current_level = st.session_state.get("filter_level", "すべて")

        # フィルタリングオプションはquiz_dfから取得
        category_options = ["すべて"] + sorted(st.session_state.quiz_df["カテゴリ"].dropna().unique())
        field_options = ["すべて"] + sorted(st.session_state.quiz_df["分野"].dropna().unique())
        level_options = ["すべて"] + sorted(st.session_state.quiz_df["試験区分"].dropna().unique())

        if current_category not in category_options:
            current_category = "すべて"
        if current_field not in field_options:
            current_field = "すべて"
        if current_level not in level_options:
            current_level = "すべて"

        category = st.selectbox("カテゴリを選ぶ", category_options, index=category_options.index(current_category), key="filter_category")
        field = st.selectbox("分野を選ぶ", field_options, index=field_options.index(current_field), key="filter_field")
        level = st.selectbox("試験区分を選ぶ", level_options, index=level_options.index(current_level), key="filter_level")

        # st.session_state.quiz_df をフィルタリング
        df_filtered = st.session_state.quiz_df.copy()
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
        st.markdown(f"🗓️ **現在の実施回数更新列：{st.session_state.current_round}回目**") # 新規追加：現在の更新回数表示

    def load_quiz(self, df_filtered, remaining_df):
        """新しいクイズをロードし、セッション状態を更新します。"""
        if len(remaining_df) > 0:
            q = remaining_df.sample(1).iloc[0]
            correct_description = q["説明"]

            wrong_options_pool = df_filtered[df_filtered["説明"] != correct_description]["説明"].drop_duplicates().tolist()
            num_wrong_options = min(3, len(wrong_options_pool))
            wrong_options = random.sample(wrong_options_pool, num_wrong_options)

            options = wrong_options + [correct_description]
            random.shuffle(options)

            st.session_state.current_quiz = {
                "単語": q["単語"],
                "説明": correct_description,
                "選択肢": options,
                "記述": q.get("午後記述での使用例", "N/A"),
                "文脈": q.get("使用理由／文脈", "N/A"),
                "区分": q.get("試験区分", "N/A"),
                "出題確率（推定）": q.get("出題確率（推定）", "N/A"),
                "シラバス改定有無": q.get("シラバス改定有無", "N/A"),
                "改定の意図・影響": q.get("改定の意図・影響", "N/A")
            }
            st.session_state.quiz_answered = False
            st.session_state.quiz_choice_index = 0
            st.session_state.latest_result = ""
            st.session_state.latest_correct_description = ""
        else:
            st.session_state.current_quiz = None

    def _display_quiz_question(self):
        """クイズの質問と関連情報を表示します。"""
        q = st.session_state.current_quiz
        if not q:
            return

        st.subheader(f"この用語の説明は？：**{q['単語']}**")
        st.markdown(f"🧩 **午後記述での使用例：** {q['記述']}")
        st.markdown(f"🎯 **使用理由／文脈：** {q['文脈']}")
        st.markdown(f"🕘 **試験区分：** {q['区分']}")
        st.markdown(f"📈 **出題確率（推定）：** {q['出題確率（推定）']}　🔄 **シラバス改定有無：** {q['シラバス改定有無']}　📝 **改定の意図・影響：** {q['改定の意図・影響']}")


    def _handle_answer_submission(self, selected_option_text, current_quiz_data):
        """ユーザーの回答を処理し、結果を更新します。"""
        st.session_state.total += 1
        st.session_state.answered_words.add(current_quiz_data["単語"])

        is_correct = (selected_option_text == current_quiz_data["説明"])
        result_mark = "〇" if is_correct else "×"

        st.session_state.latest_correct_description = current_quiz_data['説明']

        st.session_state.latest_result = (
            "✅ 正解！🎉" if is_correct
            else f"❌ 不正解…"
        )
        st.session_state.correct += 1 if is_correct else 0

        # --- 実施回数列の更新ロジック ---
        # quiz_df をコピーし、更新する
        temp_df = st.session_state.quiz_df.copy()
        
        # 現在の単語のインデックスを取得
        word = current_quiz_data["単語"]
        # .loc を使って、単語が一致する行の current_round 列を更新
        # DataFrameが複数行同じ単語を持つ可能性は低いが、念のため.index[0]で最初のマッチング行を取得
        if word in temp_df["単語"].values:
            idx = temp_df[temp_df["単語"] == word].index[0]
            column_to_update = str(st.session_state.current_round) # 列名は文字列として扱う
            
            # その列が存在することを確認
            if column_to_update in temp_df.columns:
                temp_df.at[idx, column_to_update] = result_mark
            else:
                st.warning(f"警告: 列 '{column_to_update}' がDataFrameに見つかりません。CSVファイルを確認してください。")
        
        st.session_state.quiz_df = temp_df # 更新したDataFrameをセッション状態に戻す

        # current_round をインクリメント（1～15でループ）
        st.session_state.current_round = (st.session_state.current_round % 15) + 1
        # --- 実施回数列の更新ロジックここまで ---

        try:
            choice_kana = self.kana_labels[current_quiz_data["選択肢"].index(selected_option_text)]
        except ValueError:
            choice_kana = "不明"
        
        try:
            correct_kana = self.kana_labels[current_quiz_data["選択肢"].index(current_quiz_data["説明"])]
        except ValueError:
            correct_kana = "不明"

        st.session_state.history.append({
            "単語": current_quiz_data["単語"],
            "私の選択": choice_kana,
            "正解": correct_kana,
            "正誤": result_mark,
            "記述例": current_quiz_data["記述"],
            "文脈": current_quiz_data["文脈"],
            "試験区分": current_quiz_data["区分"],
            "説明（正解）": current_quiz_data["説明"]
        })
        st.session_state.quiz_answered = True

    def _display_result_and_next_button(self):
        """回答結果と次の問題へのボタンを表示します。"""
        st.info(st.session_state.latest_result)
        st.markdown(f"💡 **説明:** {st.session_state.latest_correct_description}")

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

        selected_labeled_option = st.radio(
            "選択肢を選んでください",
            labeled_options,
            index=st.session_state.quiz_choice_index,
            key=f"quiz_radio_{st.session_state.total}",
            disabled=st.session_state.quiz_answered
        )

        selected_option_index = labeled_options.index(selected_labeled_option)
        selected_option_text = q["選択肢"][selected_option_index]

        if st.session_state.quiz_choice_index != selected_option_index and not st.session_state.quiz_answered:
            st.session_state.quiz_choice_index = selected_option_index

        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                self._handle_answer_submission(selected_option_text, q)
                st.rerun()
        else:
            self._display_result_and_next_button()

    def show_completion(self):
        """すべての問題に回答した際のメッセージを表示します。"""
        st.success("🎉 すべての問題に回答しました！")
        st.balloons()

    def offer_download(self):
        """学習履歴のCSVダウンロードボタンを提供します。"""
        # quiz_df の現在の状態をダウンロードできるように変更
        csv = st.session_state.quiz_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 現在の学習データをCSVで保存", data=csv, file_name="updated_tango.csv", mime="text/csv")
        
        # 個別の回答履歴もダウンロードできるように残す
        df_log = pd.DataFrame(st.session_state.history or [])
        if not df_log.empty:
            csv_history = df_log.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 回答履歴をCSVで保存", data=csv_history, file_name="quiz_results.csv", mime="text/csv")
        else:
            st.info("まだ回答履歴がありません。")

    def reset_session_button(self):
        """セッションをリセットするためのボタンを表示します。"""
        if st.button("🔁 セッションをリセット"):
            self._reset_session_state()


    def run(self):
        """アプリケーションのメイン実行ロジックです。"""
        st.set_page_config(layout="wide", page_title="用語クイズアプリ")

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
            /* Disabled radio button styling */
            .stRadio > label[data-baseweb="radio"] > div > span[data-testid="stDecoration"] {
                cursor: default !important;
            }
            .stRadio > label[data-baseweb="radio"][data-state="disabled"] {
                opacity: 0.7;
                cursor: not-allowed;
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
            /* Selectbox styling: The main display area of the selectbox */
            div[data-baseweb="select"] > div:first-child {
                background-color: white !important;
                border: 1px solid #999 !important; /* ここで枠線を追加 */
                border-radius: 8px;
            }
            /* Selectbox styling: The dropdown list */
            div[data-baseweb="select"] div[role="listbox"] {
                background-color: white !important;
                border: 1px solid #999 !important; /* ドロップダウンリストにも枠線を追加 */
                border-radius: 8px;
            }
            /* Selectbox styling: Specifically targeting the input field inside the selectbox */
            div[data-baseweb="select"] input[type="text"] {
                background-color: white !important; /* 初期表示の「すべて」が入る部分 */
                border: none !important; /* この部分のデフォルトのボーダーを削除 (親要素のボーダーで十分なため) */
            }
            /* Selectbox内のテキスト色を調整 */
            div[data-baseweb="select"] span {
                color: #333;
            }
            </style>
            """, unsafe_allow_html=True)


        st.title("用語クイズアプリ")

        df_filtered, remaining_df = self.filter_data()
        self.show_progress(df_filtered)

        with st.expander("📂 読み込みデータの確認"):
            # ここでは quiz_df の先頭を表示
            st.dataframe(st.session_state.quiz_df.head())

        if st.session_state.current_quiz is None and len(remaining_df) > 0:
            self.load_quiz(df_filtered, remaining_df)

        if len(remaining_df) == 0 and st.session_state.current_quiz is None:
            self.show_completion()
        elif st.session_state.current_quiz:
            self.display_quiz(df_filtered, remaining_df)

        self.offer_download()
        st.markdown("---")
        self.reset_session_button()

# アプリ実行（tango.csv に上記フォーマットでデータを保存してください）
try:
    df = pd.read_csv("tango.csv")
    
    required_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分", "出題確率（推定）", "シラバス改定有無", "改定の意図・影響"]
    for i in range(1, 16): # 1から15までの列を追加
        required_columns.append(str(i))

    if not all(col in df.columns for col in required_columns):
        st.error(f"❌ 'tango.csv' に必要な列が不足しています。不足している列: {', '.join([col for col in required_columns if col not in df.columns])}")
        st.stop()
    
    # QuizAppインスタンス作成時に、オリジナルのdfを保持するように変更
    app = QuizApp(df)
    app.initial_df = df.copy() # リセット用にオリジナルのdfを保持
    app.run()
except FileNotFoundError:
    st.error("❌ 'tango.csv' が見つかりません。")
    info_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分", "出題確率（推定）", "シラバス改定有無", "改定の意図・影響"] + [str(i) for i in range(1, 16)]
    st.info(f"必要な列：{', '.join(info_columns)}")
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("データファイル 'tango.csv' の内容を確認してください。")
