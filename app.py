import streamlit as st
import pandas as pd
import random
import io
from datetime import datetime, timedelta
import os
import sys

# pytzライブラリをインポート
import pytz

# --- Streamlitページの初期設定 ---
st.set_page_config(
    page_title="情報処理試験対策クイズ",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ここからセッション状態の初期化ロジック ---
defaults = {
    "quiz_df": None,
    "current_quiz": None,
    "total": 0,
    "correct": 0,
    "latest_result": "",
    "latest_correct_description": "",
    "quiz_answered": False,
    "quiz_choice_index": 0,
    "filter_category": "すべて",
    "filter_field": "すべて",
    "filter_level": "すべて",
    "data_source_selection": "初期データ",
    "uploaded_df_temp": None,
    "uploaded_file_name": None,
    "uploaded_file_size": None,
    "answered_words": set(),
    "debug_mode": False,
    "quiz_mode": "復習",
    "main_data_source_radio": "初期データ",
    "current_data_file": "tango.csv",
    "last_loaded_file_message": "", # 新しいセッション状態：最後にロードされたファイルメッセージ
    "has_shown_initial_load_message": False # 起動時のロードメッセージを一度だけ表示するためのフラグ
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val
    if key == "answered_words" and not isinstance(st.session_state[key], set):
        st.session_state[key] = set(st.session_state[key])
# --- ここまでセッション状態の初期化ロジック ---


# --- カスタムCSSの適用 ---
st.markdown("""
<style>
    /* 全体のフォントを調整 */
    body {
        font-family: 'Segoe UI', sans-serif;
    }
    /* タイトル */
    h1 {
        color: #2F80ED;
        text-align: center;
        margin-bottom: 0.5em;
    }
    /* サブヘッダー */
    h2, h3, h4 {
        color: #333333;
    }
    /* --- フォントサイズ調整: h3 (単語), p (説明文), stRadio (選択肢) --- */
    h3 {
        font-size: 1.75em;
    }
    p { /* 説明文などの標準的な段落のフォントサイズ */
        font-size: 0.95em;
    }
    /* 選択肢ボタンのスタイル */
    .stRadio > label > div {
        background-color: #F0F2F6;
        padding: 10px 15px;
        margin-bottom: 7px;
        border-radius: 8px;
        border: 1px solid #DDDDDD;
        transition: all 0.2s ease;
        font-size: 0.9em;
    }
    .stRadio > label > div:hover {
        background-color: #E0E2E6;
        border-color: #C0C0C0;
    }
    /* --- フォントサイズ調整ここまで --- */

    /* ボタンのスタイル */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #2F80ED;
        color: white;
        background-color: #2F80ED;
        padding: 10px 20px;
        font-size: 16px;
        transition: all 0.2s ease;
        margin-bottom: 10px;
    }
    .stButton>button:hover {
        background-color: #2671c6;
        border-color: #2671c6;
        color: white;
    }
    /* 正解・不正解時の背景色 */
    .correct-answer-feedback {
        background-color: #D4EDDA;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .incorrect-answer-feedback {
        background-color: #F8D7DA;
        color: #721C24;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    /* メッセージボックス */
    .st.info, .st.success, .st.warning, .st.error {
        border-radius: 8px;
    }
    /* サイドバーの調整 */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #6c757d;
        border-color: #6c757d;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #5a6268;
        border-color: #5a6268;
    }
    /* 統計情報コンテナ */
    .metric-container {
        border: 1px solid #DDDDDD;
        border-radius: 8px;
        padding: 5px 10px;
        margin-bottom: 5px;
        background-color: #FFFFFF;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    /* サイドバー内のメトリックコンテナの背景色を調整 */
    [data-testid="stSidebar"] .metric-container {
        background-color: #e9ecef;
    }
    /* --- サイドバーの件数表示文字サイズと配置を調整 --- */
    [data-testid="stSidebar"] .metric-value {
        font-size: 1.3em;
        font-weight: bold;
        color: #2F80ED;
        text-align: right;
        flex-grow: 1;
    }
    [data-testid="stSidebar"] .metric-label {
        font-size: 0.85em;
        color: #666666;
        text-align: left;
        min-width: 40px;
        padding-right: 5px;
    }
    /* --- サイドバーの件数表示文字サイズと配置調整ここまで --- */

    /* データフレーム表示 */
    .stDataFrame {
        border: 1px solid #DDDDDD;
        border-radius: 8px;
        overflow: hidden;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* st.radio のラベルを完全に非表示にする */
    div[data-testid="stRadio"] > label[data-testid="stWidgetLabel"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

class QuizApp:
    def __init__(self):
        # 日本時間のタイムゾーンオブジェクトを事前に作成
        self.jst_timezone = pytz.timezone('Asia/Tokyo')

    def _reset_quiz_state_only(self):
        st.session_state.total = 0
        st.session_state.correct = 0
        st.session_state.latest_result = ""
        st.session_state.latest_correct_description = ""
        st.session_state.current_quiz = None
        st.session_state.quiz_answered = False
        st.session_state.quiz_choice_index = 0
        st.session_state.answered_words = set()
        if st.session_state.debug_mode:
            st.info("DEBUG: クイズ状態（スコア、現在の問題など）がリセットされました。")


    def _load_data_from_file(self, file_path, is_initial_load=False):
        """指定されたファイルパスからデータをロードし、quiz_dfを更新する。成功可否を返す。
        メッセージ表示は呼び出し元で行う。
        """
        try:
            # UTF-8で読み込みを試行し、エラー時には Shift-JIS (CP932) で再試行
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='cp932') # Shift-JISのPythonエンコーディング名

            st.session_state.quiz_df = self._process_df_types(df)
            st.session_state.current_data_file = file_path # ファイル名をセッション状態に保存

            # 初回ロード時以外はクイズ状態をリセット
            if not is_initial_load:
                self._reset_quiz_state_only()

            return True # ロード成功
        except FileNotFoundError:
            st.session_state.quiz_df = None
            return False # ロード失敗
        except Exception as e:
            st.error(f"データファイル '{file_path}' のロード中にエラーが発生しました: {e}")
            st.session_state.quiz_df = None
            return False # ロード失敗

    def _load_initial_data(self):
        """初期データまたは既存の結果データをロードする。メッセージはここで表示。"""
        initial_results_file = "tango_results.csv"
        # 既存の結果ファイルがあればそれを優先的にロード
        if os.path.exists(initial_results_file):
            if self._load_data_from_file(initial_results_file, is_initial_load=True):
                st.session_state.last_loaded_file_message = f"'{initial_results_file}' (結果ファイル) をロードしました！"
                st.session_state.data_source_selection = "初期データ"
                st.session_state.main_data_source_radio = "初期データ"
        else:
            # 結果ファイルがなければ元の初期データをロード
            if self._load_data_from_file("tango.csv", is_initial_load=True):
                st.session_state.last_loaded_file_message = f"初期データ 'tango.csv' をロードしました！"

    def _load_uploaded_data(self):
        """アップロードされたデータまたはその結果ファイルをロードする。メッセージはここで表示。"""
        if st.session_state.uploaded_df_temp is not None:
            uploaded_file_base_name = os.path.splitext(st.session_state.uploaded_file_name)[0]
            uploaded_results_file_name = f"{uploaded_file_base_name}_results.csv"
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            uploaded_results_file_path = os.path.join(script_dir, uploaded_results_file_name)

            # アップロードされたファイルの対応する結果ファイルがあればロード
            if os.path.exists(uploaded_results_file_path):
                if self._load_data_from_file(uploaded_results_file_path, is_initial_load=True):
                    st.session_state.last_loaded_file_message = f"'{uploaded_results_file_name}' (既存の結果ファイル) をロードしました！"
                    st.session_state.data_source_selection = "アップロード"
                    st.session_state.main_data_source_radio = "アップロード"
            else:
                # 結果ファイルがなければ、アップロードされた元のファイルを直接ロード
                st.session_state.quiz_df = self._process_df_types(st.session_state.uploaded_df_temp.copy())
                self._reset_quiz_state_only() # ここは必要なので残す
                st.session_state.last_loaded_file_message = f"'{st.session_state.uploaded_file_name}' をロードしました！"
                st.session_state.data_source_selection = "アップロード"
                st.session_state.main_data_source_radio = "アップロード"
                st.session_state.current_data_file = st.session_state.uploaded_file_name # こちらも更新
        else:
            # アップロードデータがない場合
            st.session_state.last_loaded_file_message = "アップロードされたデータが見つかりません。"
            st.session_state.quiz_df = None # データがない状態にする
            st.session_state.data_source_selection = "初期データ" # データなしの場合初期データ選択に戻す
            st.session_state.main_data_source_radio = "初期データ"

    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """データフレームの列の型を適切に処理する"""
        column_configs = {
            '〇×結果': {'type': str, 'default': '', 'replace_nan': True},
            '正解回数': {'type': int, 'default': 0, 'numeric_coerce': True},
            '不正解回数': {'type': int, 'default': 0, 'numeric_coerce': True},
            '最終実施日時': {'type': 'datetime', 'default': pd.NaT},
            '次回実施予定日時': {'type': 'datetime', 'default': pd.NaT},
            'シラバス改定有無': {'type': str, 'default': '', 'replace_nan': True},
            '午後記述での使用例': {'type': str, 'default': ''},
            '使用理由／文脈': {'type': str, 'default': ''},
            '試験区分': {'type': str, 'default': ''},
            '出題確率（推定）': {'type': str, 'default': ''},
            '改定の意図・影響': {'type': str, 'default': ''},
        }

        for col_name, config in column_configs.items():
            if col_name not in df.columns:
                df[col_name] = config['default']
            else:
                if config.get('replace_nan'):
                    df[col_name] = df[col_name].astype(str).replace('nan', '')
                if config.get('numeric_coerce'):
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(config['default']).astype(int)
                if config['type'] == 'datetime':
                    # CSVから読み込む際にタイムゾーン情報がない場合はJSTとしてローカライズ
                    # タイムゾーン情報がある場合はJSTに変換
                    df[col_name] = pd.to_datetime(df[col_name], errors='coerce', utc=True)
                    # NaNでない場合のみタイムゾーン変換を適用
                    df[col_name] = df[col_name].apply(lambda x: x.tz_convert(self.jst_timezone) if pd.notna(x) and x.tz is not None else (x.tz_localize(self.jst_timezone, ambiguous='infer') if pd.notna(x) else pd.NaT))
                elif config['type'] == str and not config.get('replace_nan'):
                    df[col_name] = df[col_name].astype(str)

        return df

    def handle_upload_logic(self, uploaded_file):
        """ファイルアップロード時のロジック。メッセージはここで設定し、main関数で表示。"""
        if uploaded_file is not None:
            # ファイルが変更されたか、または初回アップロードかを判断
            is_new_upload_or_content_changed = (
                st.session_state.uploaded_file_name != uploaded_file.name or
                st.session_state.uploaded_file_size != uploaded_file.size or
                st.session_state.uploaded_df_temp is None # テンポラリデータがない場合も新規とみなす
            )

            if is_new_upload_or_content_changed:
                try:
                    uploaded_df_raw = uploaded_file.getvalue().decode('utf-8')
                    uploaded_df = pd.read_csv(io.StringIO(uploaded_df_raw))

                    st.session_state.uploaded_df_temp = uploaded_df
                    st.session_state.uploaded_file_name = uploaded_file.name
                    st.session_state.uploaded_file_size = uploaded_file.size

                    uploaded_results_file_name = f"{os.path.splitext(uploaded_file.name)[0]}_results.csv"
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    uploaded_results_file_path = os.path.join(script_dir, uploaded_results_file_name)

                    if os.path.exists(uploaded_results_file_path):
                        if self._load_data_from_file(uploaded_results_file_path):
                            st.session_state.last_loaded_file_message = f"'{uploaded_results_file_name}' (既存の結果ファイル) をロードしました！"
                            st.session_state.data_source_selection = "アップロード"
                            st.session_state.main_data_source_radio = "アップロード"
                    else:
                        st.session_state.quiz_df = self._process_df_types(uploaded_df.copy())
                        self._reset_quiz_state_only()
                        st.session_state.last_loaded_file_message = f"'{uploaded_file.name}' をロードしました！"
                        st.session_state.data_source_selection = "アップロード"
                        st.session_state.main_data_source_radio = "アップロード"
                        st.session_state.current_data_file = uploaded_file.name

                except Exception as e:
                    st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
                    st.session_state.uploaded_df_temp = None
                    st.session_state.uploaded_file_name = None
                    st.session_state.uploaded_file_size = None
                    st.session_state.last_loaded_file_message = "ファイルの読み込み中にエラーが発生しました。"
            # else: # 同一ファイルが再アップロードされた場合は、何もしない（メッセージも出さない）
        else:
            # アップロードファイルがなくなった場合（例えば、ファイル選択がクリアされた場合）
            st.session_state.uploaded_df_temp = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
            if st.session_state.data_source_selection == "アップロード": # アップロードモードからクリアされた場合
                st.session_state.data_source_selection = "初期データ"
                st.session_state.main_data_source_radio = "初期データ"
                self._load_initial_data() # 初期データに戻す
            # else: # 初期データモードで何もアップロードされていない場合は何もしない
            #       st.session_state.last_loaded_file_message = "" # メッセージをクリア


    @staticmethod
    def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
        """フィルターを適用してデータフレームを返す"""
        filtered_df = df.copy()
        if st.session_state.filter_category != "すべて":
            filtered_df = filtered_df[filtered_df["カテゴリ"] == st.session_state.filter_category]
        if st.session_state.filter_field != "すべて":
            filtered_df = filtered_df[filtered_df["分野"] == st.session_state.filter_field]
        if st.session_state.filter_level != "すべて":
            filtered_df = filtered_df[filtered_df["シラバス改定有無"] == st.session_state.filter_level]
        return filtered_df

    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """次のクイズ問題をロードする"""
        if st.session_state.quiz_answered:
            st.session_state.quiz_answered = False
            st.session_state.quiz_choice_index += 1

        quiz_candidates_df = pd.DataFrame()

        if st.session_state.quiz_mode == "未回答":
            if not remaining_df.empty:
                quiz_candidates_df = remaining_df.assign(temp_weight=1)
        elif st.session_state.quiz_mode == "苦手":
            # 不正解回数が正解回数を上回るもの
            struggled_answered = df_filtered[
                (df_filtered["〇×結果"] != '') &
                (df_filtered["不正解回数"] > df_filtered["正解回数"])
            ].copy()
            if not struggled_answered.empty:
                struggled_answered['temp_weight'] = struggled_answered['不正解回数'] + 5 # 重みを高く
                quiz_candidates_df = pd.concat([quiz_candidates_df, struggled_answered], ignore_index=True)

            # 正解回数が3回以下のもの（かつ、上記と重複しないもの）
            low_correct_count_answered = df_filtered[
                (df_filtered['〇×結果'] != '') &
                (df_filtered["正解回数"] <= 3)
            ].copy()
            if not low_correct_count_answered.empty:
                low_correct_count_answered = low_correct_count_answered[~low_correct_count_answered['単語'].isin(quiz_candidates_df['単語'])]
                if not low_correct_count_answered.empty:
                    low_correct_count_answered['temp_weight'] = low_correct_count_answered['正解回数'].apply(lambda x: 4 - x) # 正解が少ないほど重く
                    quiz_candidates_df = pd.concat([quiz_candidates_df, low_correct_count_answered], ignore_index=True)
        elif st.session_state.quiz_mode == "復習":
            # 全体を対象（回答済みか未回答かは問わない）
            if not df_filtered.empty:
                quiz_candidates_df = df_filtered.assign(temp_weight=1)

        if quiz_candidates_df.empty:
            st.session_state.current_quiz = None
            return

        # 重複する単語を除外し、重みでソートして、上位からランダム選択
        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')
        if quiz_candidates_df.empty:
            st.session_state.current_quiz = None
            return

        weights = quiz_candidates_df['temp_weight'].tolist()
        if all(w == 0 for w in weights) or sum(weights) == 0: # 重みがすべて0の場合の対策
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

        if st.session_state.debug_mode:
            st.session_state.debug_message_quiz_start = f"DEBUG: New quiz loaded: '{st.session_state.current_quiz['単語']}' (Mode: {st.session_state.quiz_mode})"
        else:
            st.session_state.debug_message_quiz_start = ""
        st.session_state.debug_message_answer_update = ""
        st.session_state.debug_message_error = ""
        st.session_state.debug_message_answer_end = ""

    def _save_quiz_data_to_csv(self):
        """クイズデータをCSVファイルに保存する"""
        try:
            save_directory = os.path.dirname(os.path.abspath(__file__))
            base_name = os.path.splitext(st.session_state.current_data_file)[0]
            save_path = os.path.join(save_directory, f"{os.path.basename(base_name)}_results.csv")

            df_to_save = st.session_state.quiz_df.copy()
            # CSV保存時もタイムゾーンを考慮してUTCに変換し、tz情報を削除して保存
            for col in ['最終実施日時', '次回実施予定日時']:
                if col in df_to_save.columns and pd.api.types.is_datetime64_any_dtype(df_to_save[col]):
                    # NaNでない場合のみ処理
                    df_to_save[col] = df_to_save[col].apply(lambda x: x.tz_convert('UTC').tz_localize(None) if pd.notna(x) and x.tz is not None else (x.tz_localize(None) if pd.notna(x) and x.tz is None else pd.NaT))
            
            # NaNを空文字列に変換して保存（Excelでの表示を考慮）
            df_to_save = df_to_save.fillna('')

            df_to_save.to_csv(save_path, index=False, encoding='utf-8')
            if st.session_state.debug_mode:
                st.info(f"DEBUG: データが '{save_path}' に保存されました。")
        except Exception as e:
            st.error(f"データの保存中にエラーが発生しました: {e}")
            if st.session_state.debug_mode:
                st.error(f"DEBUG: データ保存エラー: {e}")

    def _handle_answer_submission(self, user_answer):
        """ユーザーの回答を処理し、データを更新する"""
        if st.session_state.current_quiz:
            correct_answer_description = st.session_state.current_quiz["説明"]
            term = st.session_state.current_quiz["単語"]

            idx = st.session_state.quiz_df[st.session_state.quiz_df["単語"] == term].index
            if not idx.empty:
                idx = idx[0]
                st.session_state.quiz_answered = True

                if st.session_state.quiz_df.loc[idx, '〇×結果'] == '':
                    st.session_state.quiz_df.loc[idx, '〇×結果'] = '〇' if user_answer == correct_answer_description else '×'

                if user_answer == correct_answer_description:
                    st.session_state.quiz_df.loc[idx, '正解回数'] += 1
                    st.session_state.latest_result = "正解！🎉"
                    st.session_state.correct += 1
                else:
                    st.session_state.quiz_df.loc[idx, '不正解回数'] += 1
                    st.session_state.latest_result = "不正解…💧"

                # 現在の日本時間を取得し、タイムゾーン情報を付与
                current_jst_time = datetime.now(self.jst_timezone) 

                st.session_state.quiz_df.loc[idx, '最終実施日時'] = current_jst_time

                st.session_state.total += 1
                st.session_state.answered_words.add(term)
                st.session_state.latest_correct_description = correct_answer_description

                self._save_quiz_data_to_csv()

                if st.session_state.debug_mode:
                    st.info(f"DEBUG: JSTで取得した時刻: {current_jst_time}") # デバッグ用に表示
                    st.info(f"DEBUG: '最終実施日時'として設定された値: {st.session_state.quiz_df.loc[idx, '最終実施日時']}")
                    st.session_state.debug_message_answer_update = f"DEBUG: '{term}'の正解回数: {st.session_state.quiz_df.loc[idx, '正解回数']}, 不正解回数: {st.session_state.quiz_df.loc[idx, '不正解回数']}"
            else:
                if st.session_state.debug_mode:
                    st.session_state.debug_message_error = f"DEBUG: エラー: 単語 '{term}' がDataFrameに見つかりません。"

    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズ表示ロジック"""
        if st.session_state.debug_mode:
            st.expander("デバッグ情報", expanded=False).write(st.session_state.debug_message_quiz_start)

        if st.button("クイズ開始 / 次の問題", key="start_quiz_button"):
            current_df_filtered = QuizApp._apply_filters(st.session_state.quiz_df)
            current_remaining_df = current_df_filtered[current_df_filtered["〇×結果"] == '']
            self.load_quiz(current_df_filtered, current_remaining_df)
            st.session_state.latest_result = ""
            st.session_state.latest_correct_description = ""
            st.rerun()

        if st.session_state.current_quiz:
            st.markdown(f"### 単語: **{st.session_state.current_quiz['単語']}**")
            st.caption(f"カテゴリ: {st.session_state.current_quiz['カテゴリ']} / 分野: {st.session_state.current_quiz['分野']}")

            if st.session_state.quiz_answered:
                if st.session_state.latest_result == "正解！🎉":
                    st.markdown(f"<div class='correct-answer-feedback'>{st.session_state.latest_result}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='incorrect-answer-feedback'>{st.session_state.latest_result}</div>", unsafe_allow_html=True)
                st.info(f"正解は: **{st.session_state.latest_correct_description}**")
                description_html = f"""
                <div style="background-color: #f0f8ff; padding: 15px; border-left: 5px solid #2F80ED; margin-top: 15px; border-radius: 5px;">
                    <p><strong>単語の説明:</strong> {st.session_state.current_quiz['説明']}</p>
                    <p><strong>試験区分:</strong> {st.session_state.current_quiz.get('試験区分', 'N/A')}</p>
                    <p><strong>午後記述での使用例:</strong> {st.session_state.current_quiz.get('午後記述での使用例', 'N/A')}</p>
                    <p><strong>使用理由／文脈:</strong> {st.session_state.current_quiz.get('使用理由／文脈', 'N/A')}</p>
                    <p><strong>シラバス改定有無:</strong> {st.session_state.current_quiz.get('シラバス改定有無', 'N/A')}</p>
                    <p><strong>改定の意図・影響:</strong> {st.session_state.current_quiz.get('改定の意図・影響', 'N/A')}</p>
                </div>
                """
                st.markdown(description_html, unsafe_allow_html=True)

                if st.session_state.debug_mode:
                    st.expander("デバッグ情報", expanded=False).write(st.session_state.debug_message_answer_update)

            else:
                user_answer = st.radio(
                    "この単語の説明として正しいものはどれですか？",
                    st.session_state.current_quiz["choices"],
                    index=None,
                    key=f"quiz_choice_{st.session_state.quiz_choice_index}"
                )
                if user_answer:
                    self._handle_answer_submission(user_answer)
                    st.rerun()
        else:
            if st.session_state.quiz_df is None or st.session_state.quiz_df.empty:
                st.info("データがロードされていません。サイドバーからデータソースを選択またはアップロードしてください。")
            elif len(df_filtered) == 0:
                st.info("選択されたフィルター条件に合致する単語が見つかりませんでした。フィルター設定を変更してください。")
            elif st.session_state.quiz_mode == "未回答" and len(remaining_df) == 0:
                st.info("おめでとうございます！すべての未回答単語をクリアしました。フィルターを変更するか、別のクイズモードを試してください。")
            elif st.session_state.quiz_mode == "苦手" and (df_filtered['不正解回数'] <= df_filtered['正解回数']).all() and (df_filtered['正解回数'] > 3).all():
                st.info("「苦手」モードで出題すべき単語がありません。全ての苦手な単語を克服したようです！フィルターを変更するか、別のクイズモードを試してください。")
            elif st.session_state.quiz_mode == "復習" and not df_filtered.empty:
                st.info("復習する単語が見つかりませんでした。フィルター設定を変更するか、クイズモードを切り替えてください。")
            else:
                st.info("現在のクイズモードで出題できる単語が見つかりませんでした。フィルター設定を変更するか、別のクイズモードを試してください。")

            if st.session_state.debug_mode:
                st.expander("デバッグ情報", expanded=False).write("DEBUG: current_quiz is None.")

    def display_data_viewer(self):
        """データビューアの表示とCSVダウンロード機能"""
        if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
            # データフレームを表示する前に、タイムゾーン付きの列を日本時間に変換して表示形式を整える
            df_display = st.session_state.quiz_df.copy()
            for col in ['最終実施日時', '次回実施予定日時']:
                if col in df_display.columns and pd.api.types.is_datetime64_any_dtype(df_display[col]):
                    # タイムゾーン情報がない場合はJSTとしてローカライズし、ある場合はJSTに変換
                    if df_display[col].dt.tz is None:
                        df_display[col] = df_display[col].dt.tz_localize(self.jst_timezone, ambiguous='infer')
                    else:
                        df_display[col] = df_display[col].dt.tz_convert(self.jst_timezone)
                    # 表示形式を整える (例: 2025-07-21 19:48:57)
                    df_display[col] = df_display[col].dt.strftime('%Y-%m-%d %H:%M:%S')

            st.dataframe(df_display, height=500) # heightを追加

            @st.cache_data
            def convert_df_to_csv(df):
                output = io.StringIO()
                # CSVダウンロード時は、Pandasがタイムゾーン情報をそのまま文字列として書き出すため、
                # まずタイムゾーンをUTCに変換し、タイムゾーン情報を削除してから保存
                df_to_export = df.copy()
                for col in ['最終実施日時', '次回実施予定日時']:
                    if col in df_to_export.columns and pd.api.types.is_datetime64_any_dtype(df_to_export[col]):
                        # NaNでない場合のみ処理
                        df_to_export[col] = df_to_export[col].apply(lambda x: x.tz_convert('UTC').tz_localize(None) if pd.notna(x) and x.tz is not None else (x.tz_localize(None) if pd.notna(x) and x.tz is None else pd.NaT))
                        # フォーマットを統一してCSVに書き出す
                        df_to_export[col] = df_to_export[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # NaNを空文字列に変換してCSVに保存
                df_to_export = df_to_export.fillna('')

                df_to_export.to_csv(output, index=False, encoding='utf_8_sig')
                return output.getvalue().encode('utf-8')

            csv_data = convert_df_to_csv(st.session_state.quiz_df)

            timestamp = datetime.now(self.jst_timezone).strftime("%Y%m%d_%H%M%SS") # ダウンロードファイル名もJSTで
            file_name = f"TANGO_{timestamp}.csv"

            st.download_button(
                label="現在のデータをCSVでダウンロード",
                data=csv_data,
                file_name=file_name,
                mime="text/csv",
            )
        else:
            st.info("表示するデータがありません。")

# アプリケーションの実行
def main():
    quiz_app = QuizApp()

    # アプリ起動時に一度だけロード処理を試みる
    if st.session_state.quiz_df is None and not st.session_state.has_shown_initial_load_message:
        if st.session_state.data_source_selection == "初期データ":
            quiz_app._load_initial_data()
        elif st.session_state.data_source_selection == "アップロード":
            # アップロードデータが存在するか確認してからロードを試みる
            if st.session_state.uploaded_df_temp is not None:
                quiz_app._load_uploaded_data()
            else:
                # アップロードモードだがまだファイルが選択されていない場合
                st.session_state.quiz_df = None # 明示的にデータなし状態にする
                st.session_state.last_loaded_file_message = "CSVファイルをアップロードしてください。"
        # 初回ロードメッセージの表示制御
        if st.session_state.last_loaded_file_message:
            st.session_state.has_shown_initial_load_message = True
            st.success(st.session_state.last_loaded_file_message)
            st.session_state.last_loaded_file_message = "" # 表示したらクリア

    st.sidebar.header("📚 データソース")
    data_source_options_radio = ["初期データ", "アップロード"]

    def on_data_source_change():
        """サイドバーのラジオボタン変更時のコールバック"""
        st.session_state.data_source_selection = st.session_state.main_data_source_radio
        st.session_state.has_shown_initial_load_message = False # データソース切り替え時はメッセージを再表示可能にする
        if st.session_state.data_source_selection == "初期データ":
            quiz_app._load_initial_data()
            # 初期データ選択時はアップロード関連のセッション状態をクリア
            st.session_state.uploaded_df_temp = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
        else: # アップロードが選択された場合
            if st.session_state.uploaded_df_temp is not None:
                # 既にアップロード済みのデータがあればそれをロード
                quiz_app._load_uploaded_data()
            else:
                # まだファイルがアップロードされていない場合
                st.session_state.quiz_df = None # データがない状態にする
                st.session_state.last_loaded_file_message = "CSVファイルをアップロードしてください。"
        st.rerun() # 変更を反映させるために再実行

    selected_source_radio = st.sidebar.radio(
        "**データソースを選択**",
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

    # uploaded_fileが選択されたら処理
    if uploaded_file is not None and st.session_state.data_source_selection == "アップロード":
        # Streamlitのファイルアップローダーはファイル選択時だけでなく、
        # アプリケーションが再実行されるたびにファイルオブジェクトを返すため、
        # content_changedのチェックで不要な再ロードを避ける
        if (st.session_state.uploaded_file_name != uploaded_file.name or
            st.session_state.uploaded_file_size != uploaded_file.size):
            quiz_app.handle_upload_logic(uploaded_file)
            st.rerun() # 新しいファイルがアップロードされたら再実行
    elif uploaded_file is None and st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
        # アップロードモードで、以前ファイルがあったが、ファイルアップローダーがクリアされた場合
        # （ファイルの選択を解除した場合など）
        quiz_app.handle_upload_logic(uploaded_file) # アップロードデータのリセット処理
        st.rerun()

    # データソース切り替え時のメッセージ表示は on_data_source_change で行うため、ここでの重複表示は削除。

    st.title("情報処理試験対策クイズ")

    tab1, tab2 = st.tabs(["クイズ", "データビューア"])

    # サイドバーの残りの部分
    with st.sidebar:
        st.header("🎯 クイズモード")
        quiz_modes = ["未回答", "苦手", "復習"]
        current_quiz_mode_index = quiz_modes.index(st.session_state.quiz_mode) if st.session_state.quiz_mode in quiz_modes else 0
        
        selected_quiz_mode = st.radio(
            "**モードを選択**",
            options=quiz_modes,
            index=current_quiz_mode_index,
            key="quiz_mode_radio",
            on_change=lambda: quiz_app._reset_quiz_state_only() # モード変更時にクイズ状態をリセット
        )
        st.session_state.quiz_mode = selected_quiz_mode


        # フィルターオプション
        st.header("🔍 フィルター")
        if st.session_state.quiz_df is not None:
            categories = ["すべて"] + st.session_state.quiz_df["カテゴリ"].unique().tolist()
            fields = ["すべて"] + st.session_state.quiz_df["分野"].unique().tolist()
            levels = ["すべて"] + st.session_state.quiz_df["シラバス改定有無"].unique().tolist()
        else:
            categories = ["すべて"]
            fields = ["すべて"]
            levels = ["すべて"]

        selected_category = st.selectbox(
            "カテゴリで絞り込み",
            options=categories,
            index=categories.index(st.session_state.filter_category) if st.session_state.filter_category in categories else 0,
            key="filter_category_select",
            on_change=lambda: quiz_app._reset_quiz_state_only() # フィルター変更時にクイズ状態をリセット
        )
        st.session_state.filter_category = selected_category

        selected_field = st.selectbox(
            "分野で絞り込み",
            options=fields,
            index=fields.index(st.session_state.filter_field) if st.session_state.filter_field in fields else 0,
            key="filter_field_select",
            on_change=lambda: quiz_app._reset_quiz_state_only() # フィルター変更時にクイズ状態をリセット
        )
        st.session_state.filter_field = selected_field

        selected_level = st.selectbox(
            "シラバス改定有無で絞り込み",
            options=levels,
            index=levels.index(st.session_state.filter_level) if st.session_state.filter_level in levels else 0,
            key="filter_level_select",
            on_change=lambda: quiz_app._reset_quiz_state_only() # フィルター変更時にクイズ状態をリセット
        )
        st.session_state.filter_level = selected_level
        
        # 統計情報の表示
        st.header("📊 クイズ進捗")
        if st.session_state.quiz_df is not None:
            df_filtered_for_stats = quiz_app._apply_filters(st.session_state.quiz_df)
            total_filtered = len(df_filtered_for_stats)
            answered_filtered = len(df_filtered_for_stats[df_filtered_for_stats["〇×結果"] != ''])
            unanswered_filtered = len(df_filtered_for_stats[df_filtered_for_stats["〇×結果"] == ''])
            correct_filtered = df_filtered_for_stats["正解回数"].sum()
            incorrect_filtered = df_filtered_for_stats["不正解回数"].sum()

            col_label, col_value = st.columns([1, 2])
            with col_label:
                st.markdown("<div class='metric-label'>対象単語数</div>", unsafe_allow_html=True)
            with col_value:
                st.markdown(f"<div class='metric-value'>{total_filtered}</div>", unsafe_allow_html=True)

            col_label, col_value = st.columns([1, 2])
            with col_label:
                st.markdown("<div class='metric-label'>回答済み</div>", unsafe_allow_html=True)
            with col_value:
                st.markdown(f"<div class='metric-value'>{answered_filtered}</div>", unsafe_allow_html=True)

            col_label, col_value = st.columns([1, 2])
            with col_label:
                st.markdown("<div class='metric-label'>未回答</div>", unsafe_allow_html=True)
            with col_value:
                st.markdown(f"<div class='metric-value'>{unanswered_filtered}</div>", unsafe_allow_html=True)

            col_label, col_value = st.columns([1, 2])
            with col_label:
                st.markdown("<div class='metric-label'>正解数</div>", unsafe_allow_html=True)
            with col_value:
                st.markdown(f"<div class='metric-value'>{correct_filtered}</div>", unsafe_allow_html=True)

            col_label, col_value = st.columns([1, 2])
            with col_label:
                st.markdown("<div class='metric-label'>不正解数</div>", unsafe_allow_html=True)
            with col_value:
                st.markdown(f"<div class='metric-value'>{incorrect_filtered}</div>", unsafe_allow_html=True)
        else:
            st.info("データをロードすると進捗が表示されます。")


        st.markdown("---") # 区切り線
        st.header("⚙️ オプション")
        if st.session_state.quiz_df is not None:
            if st.button("未回答単語のリセット", key="reset_unanswered_btn"):
                st.session_state.quiz_df["〇×結果"] = ''
                st.session_state.quiz_df["最終実施日時"] = pd.NaT # 日付もリセット
                quiz_app._reset_quiz_state_only()
                quiz_app._save_quiz_data_to_csv()
                st.success("未回答単語の状態がリセットされました。")
                st.rerun()

            if st.button("全単語の学習履歴をリセット", key="reset_all_history_btn"):
                st.session_state.quiz_df["〇×結果"] = ''
                st.session_state.quiz_df["正解回数"] = 0
                st.session_state.quiz_df["不正解回数"] = 0
                st.session_state.quiz_df["最終実施日時"] = pd.NaT
                st.session_state.quiz_df["次回実施予定日時"] = pd.NaT
                quiz_app._reset_quiz_state_only()
                quiz_app._save_quiz_data_to_csv()
                st.success("全単語の学習履歴がリセットされました。")
                st.rerun()

        st.checkbox("デバッグモード", key="debug_mode", value=st.session_state.debug_mode,
                    help="開発者向けのデバッグ情報を表示します。")
        if st.session_state.debug_mode:
            st.info(f"DEBUG: 現在のデータファイル: {st.session_state.current_data_file}")


    # メインタブのコンテンツ
    if st.session_state.quiz_df is not None:
        df_filtered = quiz_app._apply_filters(st.session_state.quiz_df)
        remaining_df = df_filtered[df_filtered["〇×結果"] == '']
    else:
        df_filtered = pd.DataFrame()
        remaining_df = pd.DataFrame()

    with tab1:
        quiz_app.display_quiz(df_filtered, remaining_df)

    with tab2:
        st.header("登録単語データ一覧")
        quiz_app.display_data_viewer()

if __name__ == "__main__":
    main()
