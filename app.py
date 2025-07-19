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
            "latest_correct_description": "", # 正解の説明を保持する新しい状態変数
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
        # ドロップダウンメニューのキーをユニークにするため、現在のセッション状態に依存させる
        # これにより、セッションリセット時に以前の選択が残り、エラーになることを防ぐ
        current_category = st.session_state.get("filter_category", "すべて")
        current_field = st.session_state.get("filter_field", "すべて")
        current_level = st.session_state.get("filter_level", "すべて")

        category_options = ["すべて"] + sorted(self.df["カテゴリ"].dropna().unique())
        field_options = ["すべて"] + sorted(self.df["分野"].dropna().unique())
        level_options = ["すべて"] + sorted(self.df["試験区分"].dropna().unique())

        # セレクトボックスの値がオプションに含まれていない場合、デフォルトに戻す
        if current_category not in category_options:
            current_category = "すべて"
        if current_field not in field_options:
            current_field = "すべて"
        if current_level not in level_options:
            current_level = "すべて"

        category = st.selectbox("カテゴリを選ぶ", category_options, index=category_options.index(current_category), key="filter_category")
        field = st.selectbox("分野を選ぶ", field_options, index=field_options.index(current_field), key="filter_field")
        level = st.selectbox("試験区分を選ぶ", level_options, index=level_options.index(current_level), key="filter_level")


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
            # 正解の説明が含まれないようにし、かつ重複を考慮して3つ選択
            wrong_options_pool = df_filtered[df_filtered["説明"] != correct_description]["説明"].drop_duplicates().tolist()
            
            # 選択肢が足りない場合は、不足分を「（不正解の選択肢なし）」のようなダミーで埋めることも検討できますが、
            # ここではシンプルに可能な範囲で取得します。
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
                "出題確率（推定）": q.get("出題確率（推定）", "N/A"), # 新しい列を追加
                "シラバス改定有無": q.get("シラバス改定有無", "N/A"),    # 新しい列を追加
                "改定の意図・影響": q.get("改定の意図・影響", "N/A")    # 新しい列を追加
            }
            st.session_state.quiz_answered = False
            st.session_state.quiz_choice_index = 0 # 新しいクイズでは最初の選択肢をデフォルトに
            st.session_state.latest_result = "" # 新しいクイズでは結果をリセット
            st.session_state.latest_correct_description = "" # 新しいクイズでは正解の説明をリセット
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
        # 新しい列の表示を追加
        st.markdown(f"📈 **出題確率（推定）：** {q['出題確率（推定）']}")
        st.markdown(f"🔄 **シラバス改定有無：：** {q['シラバス改定有無']}")
        st.markdown(f"📝 **改定の意図・影響：** {q['改定の意図・影響']}")


    def _handle_answer_submission(self, selected_option_text, current_quiz_data):
        """ユーザーの回答を処理し、結果を更新します。"""
        st.session_state.total += 1
        st.session_state.answered_words.add(current_quiz_data["単語"])

        is_correct = (selected_option_text == current_quiz_data["説明"])
        result_mark = "〇" if is_correct else "×"

        # ここで正解の説明も一緒に保存
        st.session_state.latest_correct_description = current_quiz_data['説明']

        st.session_state.latest_result = (
            "✅ 正解！🎉" if is_correct
            else f"❌ 不正解…" # 不正解の場合は単純なメッセージにとどめる
        )
        st.session_state.correct += 1 if is_correct else 0

        # 履歴に記録
        # 選択肢のインデックスが options の範囲内であることを確認
        try:
            choice_kana = self.kana_labels[current_quiz_data["選択肢"].index(selected_option_text)]
        except ValueError:
            choice_kana = "不明" # 選択肢リストにない場合
        
        try:
            correct_kana = self.kana_labels[current_quiz_data["選択肢"].index(current_quiz_data["説明"])]
        except ValueError:
            correct_kana = "不明" # 選択肢リストにない場合

        st.session_state.history.append({
            "単語": current_quiz_data["単語"],
            "私の選択": choice_kana,
            "正解": correct_kana,
            "正誤": result_mark,
            "記述例": current_quiz_data["記述"],
            "文脈": current_quiz_data["文脈"],
            "試験区分": current_quiz_data["区分"],
            "説明（正解）": current_quiz_data["説明"] # 履歴に正解の説明を追加
        })
        st.session_state.quiz_answered = True

    def _display_result_and_next_button(self):
        """回答結果と次の問題へのボタンを表示します。"""
        st.info(st.session_state.latest_result)
        # 正解/不正解に関わらず、単語の説明を表示
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

        # st.radioのindex引数をquiz_choice_indexで管理
        # 回答済みの場合はラジオボタンを無効化
        selected_labeled_option = st.radio(
            "選択肢を選んでください",
            labeled_options,
            index=st.session_state.quiz_choice_index,
            key=f"quiz_radio_{st.session_state.total}",
            disabled=st.session_state.quiz_answered # 回答済みなら無効化
        )

        # 選択されたオプションのテキストとインデックスを取得
        selected_option_index = labeled_options.index(selected_labeled_option)
        selected_option_text = q["選択肢"][selected_option_index]

        # quiz_choice_indexを更新（ユーザーが選択肢を変更した場合に備える）
        if st.session_state.quiz_choice_index != selected_option_index and not st.session_state.quiz_answered:
            st.session_state.quiz_choice_index = selected_option_index
            # 選択肢を変更しただけでRERUNはしない（ボタンクリック時のみ）

        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                self._handle_answer_submission(selected_option_text, q)
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

    def reset_session_button(self):
        """セッションをリセットするためのボタンを表示します。"""
        if st.button("🔁 セッションをリセット"):
            self._reset_session_state() # 抽出したリセットロジックを呼び出す


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
            /* Disabled radio button styling */
            .stRadio > label[data-baseweb="radio"] > div > span[data-testid="stDecoration"] {
                cursor: default !important; /* カーソルをデフォルトに */
            }
            .stRadio > label[data-baseweb="radio"][data-state="disabled"] {
                opacity: 0.7; /* 無効化された選択肢の見た目を少し暗くする */
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
            /* Selectbox styling - Currently selected value display area */
            [data-testid="stSelectbox"] > div:first-child > div:first-child {
                background-color: white !important; /* 現在の選択値が表示される部分を白に */
            }
            /* Selectbox styling - Dropdown arrow container */
            [data-testid="stSelectbox"] div[data-baseweb="select"] div[role="button"] {
                background-color: white !important; /* ドロップダウンの矢印がある部分の背景も白に */
            }
            /* For the dropdown options when opened */
            div[data-baseweb="select"] div[role="listbox"] {
                background-color: white; /* ドロップダウンリストの背景色を白に */
                border-radius: 8px;
                border: 1px solid #ddd;
            }
            /* Selectbox内のテキスト色を調整する場合 (必要であれば) */
            [data-testid="stSelectbox"] div[data-baseweb="select"] span {
                color: #333; /* またはお好みの色 */
            }
            </style>
            """, unsafe_allow_html=True)


        st.title("用語クイズアプリ")

        df_filtered, remaining_df = self.filter_data()
        self.show_progress(df_filtered)

        with st.expander("📂 読み込みデータの確認"):
            st.dataframe(self.df.head())

        # 問題が未設定かつ残りの問題がある場合に新しいクイズをロード
        if st.session_state.current_quiz is None and len(remaining_df) > 0:
            self.load_quiz(df_filtered, remaining_df)

        if len(remaining_df) == 0 and st.session_state.current_quiz is None:
            self.show_completion()
        elif st.session_state.current_quiz: # current_quiz が None でない場合にのみ表示
            self.display_quiz(df_filtered, remaining_df)

        self.offer_download()
        st.markdown("---") # 区切り線
        self.reset_session_button() # リセットボタンの呼び出し

# アプリ実行（tango.csv に上記フォーマットでデータを保存してください）
try:
    df = pd.read_csv("tango.csv")
    # tango.csvの列検証を新しいCSV様式に合わせて更新
    required_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分", "出題確率（推定）", "シラバス改定有無", "改定の意図・影響"]
    if not all(col in df.columns for col in required_columns):
        st.error(f"❌ 'tango.csv' に必要な列が不足しています。不足している列: {', '.join([col for col in required_columns if col not in df.columns])}")
        st.stop() # アプリの実行を停止
    
    app = QuizApp(df)
    app.run()
except FileNotFoundError:
    st.error("❌ 'tango.csv' が見つかりません。")
    st.info(f"必要な列：{', '.join(['カテゴリ', '分野', '単語', '説明', '午後記述での使用例', '使用理由／文脈', '試験区分', '出題確率（推定）', 'シラバス改定有無', '改定の意図・影響'])}")
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("データファイル 'tango.csv' の内容を確認してください。")
