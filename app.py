import streamlit as st
import pandas as pd
import random
import os
import datetime

# --- カスタムCSSの定義 ---
def set_custom_css():
    st.markdown(
        """
        <style>
        /* 全体の余白とフォントサイズ調整 */
        .stApp {
            padding-top: 20px; /* 全体の上部余白を少し減らす */
            padding-bottom: 20px; /* 全体Dの下部余白を少し減らす */
        }
        .stApp > header { /* Streamlitのデフォルトヘッダーを非表示 */
            display: none;
        }

        /* サイドバー全体の最上部パディングをさらに厳密にゼロにする */
        .stSidebar > div:first-child {
            padding-top: 0px !important; 
            margin-top: 0px !important;
            padding-bottom: 20px;
        }
        /* サイドバー内のコンテナの上部余白も調整 */
        .stSidebar .st-emotion-cache-1oe5zby { /* Streamlitの内部コンテナクラスの可能性あり。バージョンにより変更の可能性あり */
            padding-top: 0px !important;
            margin-top: 0px !important;
        }
        .stSidebar .stRadio div { /* ラジオボタンの選択肢間の余白を調整 */
            padding-top: 5px;
            padding-bottom: 5px;
        }
        .stSidebar h2, .stSidebar h3 { /* サイドバーの見出しの上下余白 */
            margin-top: 0.2rem; /* 見出しの上部余白をさらに減らす */
            margin-bottom: 0.8rem;
        }
        
        /* ボタンのスタイル調整：幅を内容に合わせ、横並びにする */
        div.stButton > button, .stDownloadButton button {
            width: auto !important; /* 幅を自動調整 */
            min-width: unset !important; /* 最小幅の制約をなくす */
            padding-left: 1rem; /* 左右のパディング */
            padding-right: 1rem;
            margin-bottom: 10px; /* ボタンの下余白 */
            margin-right: 5px; /* ボタン間の右マージン */
            display: inline-flex; /* Flexboxで横並びにする */
            justify-content: center; /* 中央揃え */
            align-items: center; /* 中央揃え */
        }

        /* 水平線（HR）のスタイル調整 */
        hr {
            margin-top: 1.0rem; /* HRの上下余白を調整 */
            margin-bottom: 1.0rem;
            border-top: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        /* フォーム内の余白調整 */
        .stForm {
            padding: 15px;
            border: 1px solid rgba(0, 0, 0, 0.05);
            border-radius: 5px;
            margin-bottom: 20px;
        }

        /* セクション間の余白を統一 */
        .st-emotion-cache-1r6dmzm {
            margin-bottom: 20px; 
        }

        /* info, success, warningなどのメッセージボックスの余白 */
        .stAlert {
            margin-top: 10px;
            margin-bottom: 10px;
        }

        /* プログレスバーの上のラベルを非表示に */
        .stProgress > div > div > div > div {
            font-size: 0;
        }

        /* ファイルアップローダーのスタイル調整 */
        .stFileUploader {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            margin-top: -10px;
            margin-bottom: 10px;
        }
        .stFileUploader label {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- QuizAppクラスの完全な定義 ---
class QuizApp:
    def __init__(self, original_df: pd.DataFrame):
        self.kana_labels = ["ア", "イ", "ウ", "エ", "オ"]
        self.defaults = {
            "total": 0,
            "correct": 0,
            "answered_words": set(),
            "latest_result": "",
            "latest_correct_description": "",
            "current_quiz": None,
            "quiz_answered": False,
            "quiz_choice_index": 0,
            "quiz_df": None,
            "uploaded_df_temp": None, 
            "uploaded_file_name": None, 
            "uploaded_file_size": None, 
            "data_source_selection": "初期データ", 
            "filter_category": "すべて",
            "filter_field": "すべて",
            "filter_level": "すべて",
            "debug_message_quiz_start": "",
            "debug_message_answer_update": "",
            "debug_message_error": "",
            "debug_message_answer_end": "",
        }
        
        self._initialize_session()
        
        self.initial_df = self._process_df_types(original_df.copy())

        if st.session_state.quiz_df is None:
            if st.session_state.data_source_selection == "初期データ":
                self._load_initial_data()
            elif st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
                self._load_uploaded_data()

    def _initialize_session(self):
        """セッション状態をデフォルト値で初期化します。既に存在する場合は更新しません。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _load_initial_data(self):
        """初期データをquiz_dfにロードします。"""
        st.session_state.quiz_df = self.initial_df.copy()
        st.session_state.answered_words = set(st.session_state.quiz_df[
            (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
        ]["単語"].tolist())
        self._reset_quiz_state_only() 

    def _load_uploaded_data(self):
        """アップロードされたデータをquiz_dfにロードします。"""
        if st.session_state.uploaded_df_temp is not None:
            st.session_state.quiz_df = st.session_state.uploaded_df_temp.copy()
            st.session_state.answered_words = set(st.session_state.quiz_df[
                (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
            ]["単語"].tolist())
            self._reset_quiz_state_only() 

    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameに対して、必要なカラムの型変換と初期化を適用します。"""
        if '〇×結果' not in df.columns: df['〇×結果'] = ''
        else: df['〇×結果'] = df['〇×結果'].astype(str).replace('nan', '')

        for col_name in ['正解回数', '不正解回数']:
            if col_name not in df.columns: df[col_name] = 0
            else: df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0).astype(int)

        for col_name in ['最終実施日時', '次回実施予定日時']:
            if col_name not in df.columns: df[col_name] = pd.NaT
            else: df[col_name] = pd.to_datetime(df[col_name], errors='coerce') 
        
        if 'シラバス改定有無' not in df.columns: df['シラバス改定有無'] = ''
        else: df['シラバス改定有無'] = df['シラバス改定有無'].astype(str).replace('nan', '')
            
        if '午後記述での使用例' not in df.columns: df['午後記述での使用例'] = ''
        if '使用理由／文脈' not in df.columns: df['使用理由／文脈'] = ''
        if '試験区分' not in df.columns: df['試験区分'] = ''
        
        if '出題確率（推定）' not in df.columns: df['出題確率（推定）'] = '' 
        
        if '改定の意図・影響' not in df.columns: df['改定の意図・影響'] = ''

        return df

    def _reset_quiz_state_only(self):
        """クイズの進行に関するセッションステートのみをリセットします。"""
        st.session_state.total = 0
        st.session_state.correct = 0
        st.session_state.latest_result = ""
        st.session_state.latest_correct_description = ""
        st.session_state.current_quiz = None
        st.session_state.quiz_answered = False
        st.session_state.quiz_choice_index = 0
        st.session_state.debug_message_quiz_start = ""
        st.session_state.debug_message_answer_update = ""
        st.session_state.debug_message_error = ""
        st.session_state.debug_message_answer_end = ""

    # 学習履歴リセットボタンが不要になったため、このメソッドは呼び出されませんが、
    # 機能を維持するために残しておくこともできます。今回は削除をしないままコメントアウトします。
    # def _reset_learning_history(self):
    #     """現在のquiz_dfの学習履歴をリセットし、フィルターもデフォルトに戻します。"""
    #     st.session_state.quiz_df['〇×結果'] = ''
    #     st.session_state.quiz_df['正解回数'] = 0
    #     st.session_state.quiz_df['不正解回数'] = 0
    #     st.session_state.quiz_df['最終実施日時'] = pd.NaT
    #     st.session_state.quiz_df['次回実施予定日時'] = pd.NaT

    #     st.session_state.answered_words = set()

    #     self._reset_quiz_state_only() 

    #     st.session_state.filter_category = "すべて"
    #     st.session_state.filter_field = "すべて"
    #     st.session_state.filter_level = "すべて"

    #     st.success("✅ 現在の学習データの進捗をリセットしました。")
    #     st.rerun()

    def filter_data(self):
        """データフレームをフィルターし、残りの単語を返します。
        このメソッドは、サイドバーにフィルターUIを表示する役割も持ちます。
        """
        if st.session_state.quiz_df is None or st.session_state.quiz_df.empty:
            return pd.DataFrame(), pd.DataFrame() 

        df = st.session_state.quiz_df.copy()

        categories = ["すべて"] + df["カテゴリ"].dropna().unique().tolist()
        st.session_state.filter_category = st.sidebar.selectbox(
            "カテゴリで絞り込み", categories, 
            index=categories.index(st.session_state.filter_category) if st.session_state.filter_category in categories else 0,
            key="filter_category_selectbox"
        )
        if st.session_state.filter_category != "すべて":
            df = df[df["カテゴリ"] == st.session_state.filter_category]

        fields = ["すべて"] + df["分野"].dropna().unique().tolist()
        st.session_state.filter_field = st.sidebar.selectbox(
            "分野で絞り込み", fields, 
            index=fields.index(st.session_state.filter_field) if st.session_state.filter_field in fields else 0,
            key="filter_field_selectbox"
        )
        if st.session_state.filter_field != "すべて":
            df = df[df["分野"] == st.session_state.filter_field]

        valid_syllabus_changes = df["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
        syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
        
        st.session_state.filter_level = st.sidebar.selectbox(
            "🔄 シラバス改定有無で絞り込み", 
            syllabus_change_options, 
            index=syllabus_change_options.index(st.session_state.filter_level) if st.session_state.filter_level in syllabus_change_options else 0,
            key="filter_level_selectbox"
        )
        if st.session_state.filter_level != "すべて":
            df = df[df["シラバス改定有無"] == st.session_state.filter_level]

        remaining_df = df[~df["単語"].isin(st.session_state.answered_words)]

        return df, remaining_df

    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズの単語をロードします。不正解回数や最終実施日時を考慮します。"""
        if st.session_state.quiz_answered: 
            st.session_state.quiz_answered = False 
            st.session_state.quiz_choice_index += 1 

        quiz_candidates_df = pd.DataFrame()

        answered_and_struggled = df_filtered[
            (df_filtered["単語"].isin(st.session_state.answered_words)) &
            (df_filtered["不正解回数"] > df_filtered["正解回数"])
        ].copy()

        if not answered_and_struggled.empty:
            answered_and_struggled['temp_weight'] = answered_and_struggled['不正解回数'] + 1
            quiz_candidates_df = pd.concat([quiz_candidates_df, answered_and_struggled], ignore_index=True)

        if not remaining_df.empty:
            remaining_df_copy = remaining_df.copy()
            remaining_df_copy['temp_weight'] = 1
            quiz_candidates_df = pd.concat([quiz_candidates_df, remaining_df_copy], ignore_index=True)
            
        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')

        if quiz_candidates_df.empty:
            st.info("現在のフィルター条件に一致する単語がないか、すべての単語を回答しました！フィルターを変更するか、学習データをリセットしてください。")
            st.session_state.current_quiz = None
            return

        weights = quiz_candidates_df['temp_weight'].tolist()
        
        if sum(weights) == 0:
            selected_quiz_row = quiz_candidates_df.sample(n=1).iloc[0]
        else:
            selected_quiz_row = quiz_candidates_df.sample(n=1, weights=weights).iloc[0]

        st.session_state.current_quiz = selected_quiz_row.to_dict()

        correct_description = st.session_state.current_quiz["説明"]
        
        all_descriptions = st.session_state.quiz_df["説明"].unique().tolist()
        
        other_descriptions = [desc for desc in all_descriptions if desc != correct_description]
        
        num_wrong_choices = min(3, len(other_descriptions))
        
        wrong_choices = random.sample(other_descriptions, num_wrong_choices)

        choices = wrong_choices + [correct_description]
        random.shuffle(choices)
        st.session_state.current_quiz["choices"] = choices
        
        st.session_state.quiz_choice_index += 1 

        st.session_state.debug_message_quiz_start = f"DEBUG: 新しいクイズがロードされました: '{st.session_state.current_quiz['単語']}'"
        st.session_state.debug_message_answer_update = "" 
        st.session_state.debug_message_error = ""
        st.session_state.debug_message_answer_end = ""


    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズを表示し、ユーザーの回答を処理します。"""
        current_quiz_data = st.session_state.current_quiz
        if not current_quiz_data:
            return

        st.subheader(f"問題: **{current_quiz_data['単語']}**")
        st.write(f"🧩 **午後記述での使用例：** {current_quiz_data.get('午後記述での使用例', 'N/A')}")
        st.write(f"🎯 **使用理由／文脈：** {current_quiz_data.get('使用理由／文脈', 'N/A')}")
        st.write(f"🕘 **試験区分：** {current_quiz_data.get('試験区分', 'N/A')}")
        st.write(f"📈 **出題確率（推定）：** {current_quiz_data.get('出題確率（推定）', 'N/A')}　📝 **改定の意図・影響：** {current_quiz_data.get('改定の意図・影響', 'N/A')}")
        
        with st.form(key=f"quiz_form_{st.session_state.quiz_choice_index}"):
            selected_option_text = st.radio(
                "説明を選択してください:",
                options=current_quiz_data["choices"],
                format_func=lambda x: f"{self.kana_labels[current_quiz_data['choices'].index(x)]}. {x}",
                key=f"quiz_radio_{st.session_state.quiz_choice_index}",
                disabled=st.session_state.quiz_answered
            )
            submit_button = st.form_submit_button("✅ 答え合わせ", disabled=st.session_state.quiz_answered)

            if submit_button and not st.session_state.quiz_answered:
                self._handle_answer_submission(selected_option_text, current_quiz_data)
                st.rerun()

        if st.session_state.quiz_answered:
            st.markdown(f"### {st.session_state.latest_result}")
            if st.session_state.latest_result.startswith("❌"):
                st.info(f"正解は: **{st.session_state.latest_correct_description}** でした。")
            else:
                st.success(f"正解は: **{st.session_state.latest_correct_description}** でした！")
            
            current_word_encoded = current_quiz_data['単語'].replace(' ', '+')
            st.markdown(
                f'<a href="https://www.google.com/search?q=Gemini+{current_word_encoded}" target="_blank">'
                f'<img src="https://www.gstatic.com/lamda/images/gemini_logo_lockup_eval_ja_og.svg" alt="Geminiに質問する" width="50">'
                f'</a>',
                unsafe_allow_html=True
            )
            
            st.markdown("---")
            st.subheader("現在のデバッグ情報")
            if st.session_state.debug_message_quiz_start:
                st.write(st.session_state.debug_message_quiz_start)
            if st.session_state.debug_message_answer_update:
                st.write(st.session_state.debug_message_answer_update)
            if st.session_state.debug_message_error:
                st.error(st.session_state.debug_message_error)
            if st.session_state.debug_message_answer_end:
                st.write(st.session_state.debug_message_answer_end)

            st.write(f"**クイズ回答済みフラグ:** `{st.session_state.quiz_answered}`")
            st.write(f"**合計問題数:** `{st.session_state.total}`")
            st.write(f"**正解数:** `{st.session_state.correct}`")

            current_word_stats_df = st.session_state.quiz_df[st.session_state.quiz_df['単語'] == current_quiz_data['単語']]
            if not current_word_stats_df.empty:
                st.write(f"**現在の単語の正解回数:** `{current_word_stats_df['正解回数'].iloc[0]}`")
                st.write(f"**現在の単語の不正解回数:** `{current_word_stats_df['不正解回数'].iloc[0]}`")
            else:
                st.write(f"**現在の単語の統計:** N/A (DataFrameに見つかりません)")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➡️ 次の問題へ", key=f"next_quiz_button_{st.session_state.quiz_choice_index}"):
                    st.session_state.current_quiz = None
                    st.session_state.quiz_answered = False
                    st.rerun()
            with col2:
                if st.button("🔄 この単語をもう一度出題", key=f"retry_quiz_button_{st.session_state.quiz_choice_index}"):
                    st.session_state.quiz_answered = False
                    st.rerun()

    def _handle_answer_submission(self, selected_option_text: str, current_quiz_data: dict):
        """ユーザーの回答を処理し、結果を更新します。"""
        st.session_state.debug_message_quiz_start = f"DEBUG: _handle_answer_submission 開始。選択肢='{selected_option_text}'"

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

        temp_df = st.session_state.quiz_df.copy(deep=True)
        
        word = current_quiz_data["単語"]
        idx_list = temp_df[temp_df["単語"] == word].index.tolist()
        
        if idx_list:
            idx = idx_list[0]
            
            temp_df.at[idx, '〇×結果'] = result_mark
            
            if is_correct:
                temp_df.at[idx, '正解回数'] += 1
            else:
                temp_df.at[idx, '不正解回数'] += 1
            
            temp_df.at[idx, '最終実施日時'] = datetime.datetime.now()
            temp_df.at[idx, '次回実施予定日時'] = datetime.datetime.now() 

            st.session_state.debug_message_answer_update = f"DEBUG: '{word}' の学習履歴を更新しました。正解回数={temp_df.at[idx, '正解回数']}, 不正解回数={temp_df.at[idx, '不正解回数']}"
            st.session_state.debug_message_error = ""
        else:
            st.session_state.debug_message_error = f"DEBUG: エラー - 単語 '{word}' がDataFrameに見つかりませんでした。"
            st.session_state.debug_message_answer_update = ""

        st.session_state.quiz_df = temp_df

        st.session_state.quiz_answered = True
        st.session_state.debug_message_answer_end = f"DEBUG: _handle_answer_submission 終了。quiz_answered={st.session_state.quiz_answered}, total={st.session_state.total}, correct={st.session_state.correct}"

    def show_progress(self, df_filtered: pd.DataFrame):
        """学習の進捗を表示します。"""
        st.sidebar.subheader("学習の進捗")
        
        total_filtered_words = len(df_filtered)
        answered_filtered_words = len(df_filtered[df_filtered["単語"].isin(st.session_state.answered_words)])

        if total_filtered_words == 0:
            st.sidebar.info("現在のフィルター条件に一致する単語がありません。")
            return

        progress_percent = (answered_filtered_words / total_filtered_words) if total_filtered_words > 0 else 0
        
        st.sidebar.markdown(f"**<span style='font-size: 1.1em;'>回答済み: {answered_filtered_words} / {total_filtered_words} 単語</span>**", unsafe_allow_html=True)
        st.sidebar.progress(progress_percent)

    def show_completion(self):
        """すべての問題が終了した際に表示するメッセージ。"""
        st.success("🎉 おめでとうございます！現在のフィルター条件のすべての問題に回答しました！")
        st.write(f"合計 {st.session_state.total} 問中、{st.session_state.correct} 問正解しました。")
        if st.session_state.total > 0:
            st.write(f"正答率: {st.session_state.correct / st.session_state.total * 100:.2f}%")
        else:
            st.write("まだ問題に回答していません。")

    def display_statistics(self):
        """単語ごとの正解・不正解回数と日時情報を表示します。"""
        st.subheader("単語ごとの学習統計")
        
        display_cols = ['単語', '説明', 'カテゴリ', '分野', 'シラバス改定有無', 
                        '正解回数', '不正解回数', '〇×結果', '最終実施日時', '次回実施予定日時']
        
        cols_to_display = [col for col in display_cols if col in st.session_state.quiz_df.columns]
        display_df = st.session_state.quiz_df[cols_to_display].copy()
        
        display_df = display_df[
            (display_df['正解回数'] > 0) | (display_df['不正解回数'] > 0)
        ].sort_values(by=['不正解回数', '正解回数', '最終実施日時'], ascending=[False, False, False])
        
        if not display_df.empty:
            if '最終実施日時' in display_df.columns:
                display_df['最終実施日時'] = display_df['最終実施日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            if '次回実施予定日時' in display_df.columns:
                display_df['次回実施予定日時'] = display_df['次回実施予定日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("まだ回答履歴のある単語はありません。")

    def offer_download(self):
        """現在の学習データのCSVダウンロードボタンを提供します。"""
        now = datetime.datetime.now()
        file_name = f"tango_learning_data_{now.strftime('%Y%m%d_%H%M%S')}.csv"

        df_to_save = st.session_state.quiz_df.copy(deep=True)
        if '最終実施日時' in df_to_save.columns:
            df_to_save['最終実施日時'] = df_to_save['最終実施日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        if '次回実施予定日時' in df_to_save.columns:
            df_to_save['次回実施予定日時'] = df_to_save['次回実施予定日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

        csv_quiz_data = df_to_save.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        return csv_quiz_data, file_name 

    def handle_upload_logic(self, uploaded_file):
        """アップロードされたファイルの処理ロジックをカプセル化。"""
        if uploaded_file is not None:
            # ファイル名とサイズが変わった場合のみ再処理
            if st.session_state.uploaded_file_name != uploaded_file.name or \
               st.session_state.get('uploaded_file_size') != uploaded_file.size: 
                try:
                    uploaded_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
                    
                    required_core_cols = ["単語", "説明", "カテゴリ", "分野"]
                    missing_core_cols = [col for col in required_core_cols if col not in uploaded_df.columns]
                    if missing_core_cols:
                        st.sidebar.error(f"アップロードされたCSVには、以下の**必須カラム**が不足しています: {', '.join(missing_core_cols)}。")
                        st.sidebar.info("これらはクイズの出題に不可欠な情報です。正しい形式のCSVファイルをアップロードしてください。")
                        st.session_state.uploaded_df_temp = None
                        st.session_state.uploaded_file_name = None
                        st.session_state.uploaded_file_size = None
                        return

                    processed_uploaded_df = self._process_df_types(uploaded_df.copy(deep=True))
                    st.session_state.uploaded_df_temp = processed_uploaded_df
                    st.session_state.uploaded_file_name = uploaded_file.name
                    st.session_state.uploaded_file_size = uploaded_file.size
                    
                    st.session_state.data_source_selection = "アップロード" # ファイルがアップロードされたら、確実にアップロードモードにする
                    self._load_uploaded_data() 
                    st.rerun() 
                except Exception as e:
                    st.sidebar.error(f"CSVファイルの読み込み中にエラーが発生しました。ファイル形式が正しいか確認してください: {e}")
                    st.session_state.uploaded_df_temp = None
                    st.session_state.uploaded_file_name = None
                    st.session_state.uploaded_file_size = None


# --- main関数の定義 ---
def main():
    st.set_page_config(layout="wide", page_title="IT用語クイズアプリ", page_icon="📝")
    set_custom_css()

    csv_path = os.path.join(os.path.dirname(__file__), 'tango.csv')
    if not os.path.exists(csv_path):
        st.error(f"エラー: tango.csv が見つかりません。パス: {csv_path}")
        st.stop()

    try:
        original_df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"初期データの読み込み中にエラーが発生しました: {e}")
        st.stop()

    quiz_app = QuizApp(original_df) 

    st.title("📝 IT用語クイズアプリ")
    st.markdown("毎日少しずつIT用語を学習し、知識を定着させましょう！")

    # --- サイドバーのレイアウト調整 ---
    # ヘッダーをサイドバーの最上部に配置
    st.sidebar.header("設定とデータ")
    
    data_source_options_radio = ["アップロード", "初期データ"]
    
    def on_data_source_change():
        if st.session_state.main_data_source_radio != st.session_state.data_source_selection:
            st.session_state.data_source_selection = st.session_state.main_data_source_radio
            
            if st.session_state.data_source_selection == "初期データ":
                quiz_app._load_initial_data()
                st.session_state.uploaded_df_temp = None
                st.session_state.uploaded_file_name = None
                st.session_state.uploaded_file_size = None
            else: # "アップロード"が選択された場合
                if st.session_state.uploaded_df_temp is not None:
                    quiz_app._load_uploaded_data()
            
            st.rerun() 

    selected_source_radio = st.sidebar.radio(
        "📚 **使用するデータソースを選択**",
        options=data_source_options_radio,
        key="main_data_source_radio",
        index=data_source_options_radio.index(st.session_state.data_source_selection) if st.session_state.data_source_selection in data_source_options_radio else 0,
        on_change=on_data_source_change
    )

    uploaded_file = st.sidebar.file_uploader(
        "CSVファイルをアップロード", 
        type=["csv"], 
        key="uploader", 
        label_visibility="hidden",
        disabled=(st.session_state.data_source_selection == "初期データ")
    )
    
    if uploaded_file is not None:
        quiz_app.handle_upload_logic(uploaded_file)

    # 学習履歴リセットボタンの表示を削除
    if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
        csv_data, file_name = quiz_app.offer_download()
        st.sidebar.download_button( # download_button は col_dl の外に出す（単独で表示するため）
            "📥 **結果ダウンロード**", 
            data=csv_data, 
            file_name=file_name, 
            mime="text/csv",
            key="download_button"
        )
    # 以前 col_reset にあった学習履歴リセットボタンのコードは削除されました

    st.sidebar.markdown("---") 

    st.sidebar.header("クイズの絞り込み")
    
    df_filtered = pd.DataFrame()
    remaining_df = pd.DataFrame()
    
    if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
        df_filtered, remaining_df = quiz_app.filter_data()
    else:
        pass 

    if st.session_state.current_quiz is None: 
        if not df_filtered.empty and len(remaining_df) > 0:
            if st.sidebar.button("▶️ **クイズ開始**", key="sidebar_start_quiz_button"):
                quiz_app.load_quiz(df_filtered, remaining_df)
                st.rerun()
        elif len(df_filtered) > 0 and len(remaining_df) == 0:
             st.sidebar.info("現在のフィルター条件のすべての問題に回答しました。")
        elif len(df_filtered) == 0: 
             st.sidebar.info("現在のフィルター条件に一致する単語がありません。フィルターを変更してください。")
    
    st.sidebar.markdown("---") 

    quiz_app.show_progress(df_filtered)

    st.markdown("---") 
    
    if st.session_state.quiz_df is None or st.session_state.quiz_df.empty:
        if st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is None:
            st.info("アップロードモードが選択されていますが、まだファイルがアップロードされていません。サイドバーからCSVファイルをアップロードしてください。")
        else:
            st.info("クイズを開始するには、まず有効な学習データをロードしてください。") 
    elif st.session_state.current_quiz is None:
        if len(df_filtered) > 0 and len(remaining_df) > 0:
            st.info("データがロードされました！サイドバーの「クイズ開始」ボタンをクリックしてください。")
        elif len(df_filtered) > 0 and len(remaining_df) == 0:
            quiz_app.show_completion()
        else: 
            st.info("現在のフィルター条件に一致する単語がないか、データがありません。フィルターを変更するか、新しいデータをアップロードしてください。")
    else:
        quiz_app.display_quiz(df_filtered, remaining_df)
    
    st.markdown("---") 
    
    if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
        quiz_app.display_statistics()

if __name__ == "__main__":
    main()
