import streamlit as st
import pandas as pd
import random
import io
from datetime import datetime, timedelta

# Streamlitページの初期設定
st.set_page_config(
    page_title="情報処理試験対策クイズ",
    page_icon="📚",
    layout="centered", # 'centered' or 'wide'
    initial_sidebar_state="expanded" # 'auto', 'expanded', 'collapsed'
)

# カスタムCSSの適用
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
        margin-bottom: 10px; /* ボタン間のスペース */
    }
    .stButton>button:hover {
        background-color: #2671c6;
        border-color: #2671c6;
        color: white;
    }
    /* 選択肢ボタンのスタイル */
    .stRadio > label > div {
        background-color: #F0F2F6; /* 薄いグレーの背景 */
        padding: 12px 15px;
        margin-bottom: 8px;
        border-radius: 8px;
        border: 1px solid #DDDDDD;
        transition: all 0.2s ease;
        font-size: 15px;
    }
    .stRadio > label > div:hover {
        background-color: #E0E2E6; /* ホバーで少し濃く */
        border-color: #C0C0C0;
    }
    /* 正解・不正解時の背景色 */
    .correct-answer-feedback {
        background-color: #D4EDDA; /* 緑 */
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .incorrect-answer-feedback {
        background-color: #F8D7DA; /* 赤 */
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
        background-color: #f8f9fa; /* ライトグレー */
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #6c757d; /* サイドバーボタンは異なる色 */
        border-color: #6c757d;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #5a6268;
        border-color: #5a6268;
    }
    /* 統計情報 */
    .metric-container {
        border: 1px solid #DDDDDD;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 10px;
        background-color: #FFFFFF;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #2F80ED;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666666;
    }
    /* データフレーム表示 */
    .stDataFrame {
        border: 1px solid #DDDDDD;
        border-radius: 8px;
        overflow: hidden; /* 角丸を適用するために必要 */
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

class QuizApp:
    def __init__(self):
        # セッション状態のデフォルト値
        self.defaults = {
            "quiz_df": None,
            "current_quiz": None,
            "total": 0,
            "correct": 0,
            "latest_result": "",
            "latest_correct_description": "",
            "quiz_answered": False,
            "quiz_choice_index": 0, # クイズの選択肢の表示を制御するためのインデックス
            "filter_category": "すべて",
            "filter_field": "すべて",
            "filter_level": "すべて",
            "data_source_selection": "初期データ",
            "uploaded_df_temp": None,
            "uploaded_file_name": None,
            "uploaded_file_size": None,
            "answered_words": set(), # 既に回答した単語を追跡するためのセット
            "debug_mode": False, # デバッグモードのフラグ
        }
        self._initialize_session()

    def _initialize_session(self):
        """セッション状態をデフォルト値で初期化します。既に存在する場合は更新しません。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            # answered_wordsがリストとしてロードされた場合の変換
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _reset_quiz_state_only(self):
        """クイズの進行に関するセッションステートのみをリセットします。"""
        st.session_state.total = 0
        st.session_state.correct = 0
        st.session_state.latest_result = ""
        st.session_state.latest_correct_description = ""
        st.session_state.current_quiz = None
        st.session_state.quiz_answered = False
        st.session_state.quiz_choice_index = 0
        st.session_state.answered_words = set()

    def _load_initial_data(self):
        """初期データをロードし、セッション状態に設定します。"""
        try:
            # CSVファイルを直接読み込む (エンコーディング指定)
            df = pd.read_csv("quiz_data.csv", encoding='utf-8')
            st.session_state.quiz_df = self._process_df_types(df)
            st.success("初期データをロードしました！")
            self._reset_quiz_state_only()
        except FileNotFoundError:
            st.error("エラー: 初期データファイル 'quiz_data.csv' が見つかりません。")
            st.session_state.quiz_df = None
        except Exception as e:
            st.error(f"初期データのロード中にエラーが発生しました: {e}")
            st.session_state.quiz_df = None

    def _load_uploaded_data(self):
        """アップロードされたデータをロードし、セッション状態に設定します。"""
        if st.session_state.uploaded_df_temp is not None:
            st.session_state.quiz_df = self._process_df_types(st.session_state.uploaded_df_temp.copy())
            st.success(f"'{st.session_state.uploaded_file_name}' をロードしました！")
            self._reset_quiz_state_only()
        else:
            st.warning("アップロードされたデータが見つかりません。")
            st.session_state.quiz_df = None # データがない場合はNoneを設定

    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameに対して、必要なカラムの型変換と初期化を適用します。"""
        
        # 列の型とデフォルト値/処理を定義します
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
                    df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
                elif config['type'] == str and not config.get('replace_nan'):
                    df[col_name] = df[col_name].astype(str)

        return df

    def handle_upload_logic(self, uploaded_file):
        """
        ファイルアップロードのロジックを処理します。
        新しいファイルがアップロードされた場合のみ、データを読み込み、一時的に保存します。
        """
        if uploaded_file is not None:
            # 同じファイルが再アップロードされたか、ファイル名とサイズでチェック
            if (st.session_state.uploaded_file_name != uploaded_file.name or 
                st.session_state.uploaded_file_size != uploaded_file.size):
                
                try:
                    # CSVを読み込み、一時的にセッション状態に保存
                    uploaded_df = pd.read_csv(io.StringIO(uploaded_file.getvalue().decode('utf-8')))
                    st.session_state.uploaded_df_temp = uploaded_df
                    st.session_state.uploaded_file_name = uploaded_file.name
                    st.session_state.uploaded_file_size = uploaded_file.size
                    
                    # アップロードされたファイルをすぐにアクティブなデータソースとして設定
                    st.session_state.quiz_df = self._process_df_types(uploaded_df.copy())
                    st.session_state.data_source_selection = "アップロード" # データソースをアップロードに切り替える
                    st.session_state.main_data_source_radio = "アップロード" # ラジオボタンの状態も更新
                    self._reset_quiz_state_only()
                    st.success(f"'{uploaded_file.name}' をロードしました！")
                except Exception as e:
                    st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
                    st.session_state.uploaded_df_temp = None
                    st.session_state.uploaded_file_name = None
                    st.session_state.uploaded_file_size = None
            else:
                # 同じファイルが再度選択された場合、特に何もしない（既にロードされている）
                pass
        else:
            # アップロードされたファイルがクリアされた場合
            st.session_state.uploaded_df_temp = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
            # もし現在アップロードデータが選択されていれば、初期データに戻すなどの処理も検討
            if st.session_state.data_source_selection == "アップロード":
                st.session_state.data_source_selection = "初期データ"
                st.session_state.main_data_source_radio = "初期データ"
                self._load_initial_data()


    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """セッション状態のフィルターに基づいてDataFrameをフィルターします。"""
        filtered_df = df.copy()

        if st.session_state.filter_category != "すべて":
            filtered_df = filtered_df[filtered_df["カテゴリ"] == st.session_state.filter_category]
        if st.session_state.filter_field != "すべて":
            filtered_df = filtered_df[filtered_df["分野"] == st.session_state.filter_field]
        if st.session_state.filter_level != "すべて":
            filtered_df = filtered_df[filtered_df["シラバス改定有無"] == st.session_state.filter_level]
        
        return filtered_df

    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """
        クイズの単語をロードします。選択されたモードに基づいて出題ロジックが変更されます。
        """
        if st.session_state.quiz_answered: 
            st.session_state.quiz_answered = False 
            st.session_state.quiz_choice_index += 1 

        quiz_candidates_df = pd.DataFrame()
        
        if st.session_state.quiz_mode == "未回答":
            if not remaining_df.empty:
                quiz_candidates_df = remaining_df.assign(temp_weight=1) # 未回答単語はすべて等しい重み
            else:
                st.session_state.current_quiz = None
                return

        elif st.session_state.quiz_mode == "苦手":
            # 1. 不正解回数が正解回数を上回る、かつ回答済みの単語 (最優先)
            struggled_answered = df_filtered[
                (df_filtered["〇×結果"] != '') & 
                (df_filtered["不正解回数"] > df_filtered["正解回数"])
            ].copy()
            if not struggled_answered.empty:
                struggled_answered['temp_weight'] = struggled_answered['不正解回数'] + 5 
                quiz_candidates_df = pd.concat([quiz_candidates_df, struggled_answered], ignore_index=True)

            # 2. 正解回数が3回以下の、かつ回答済みの単語 (次点、ただし上記と重複しない)
            low_correct_count_answered = df_filtered[
                (df_filtered['〇×結果'] != '') & 
                (df_filtered["正解回数"] <= 3) 
            ].copy()
            if not low_correct_count_answered.empty:
                low_correct_count_answered = low_correct_count_answered[~low_correct_count_answered['単語'].isin(quiz_candidates_df['単語'])]
                if not low_correct_count_answered.empty:
                    low_correct_count_answered['temp_weight'] = low_correct_count_answered['正解回数'].apply(lambda x: 4 - x) 
                    quiz_candidates_df = pd.concat([quiz_candidates_df, low_correct_count_answered], ignore_index=True)
            
            if quiz_candidates_df.empty:
                st.session_state.current_quiz = None
                return

        elif st.session_state.quiz_mode == "復習":
            if not df_filtered.empty:
                quiz_candidates_df = df_filtered.assign(temp_weight=1) # 全て等しい重みでランダム出題
            else:
                st.session_state.current_quiz = None
                return
        
        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')

        if quiz_candidates_df.empty:
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

        # デバッグモードが有効な場合のみメッセージを設定
        if st.session_state.debug_mode:
            st.session_state.debug_message_quiz_start = f"DEBUG: New quiz loaded: '{st.session_state.current_quiz['単語']}' (Mode: {st.session_state.quiz_mode})"
        else:
            st.session_state.debug_message_quiz_start = "" # デバッグモードでない場合はクリア
        st.session_state.debug_message_answer_update = "" 
        st.session_state.debug_message_error = ""
        st.session_state.debug_message_answer_end = ""


    def _handle_answer_submission(self, user_answer):
        """ユーザーの回答を処理し、セッション状態を更新します。"""
        if st.session_state.current_quiz:
            correct_answer_description = st.session_state.current_quiz["説明"]
            term = st.session_state.current_quiz["単語"]
            
            # DataFrameを更新
            idx = st.session_state.quiz_df[st.session_state.quiz_df["単語"] == term].index
            if not idx.empty:
                idx = idx[0]
                st.session_state.quiz_answered = True
                
                # '〇×結果'を更新 (正解なら'〇'、不正解なら'×')
                st.session_state.quiz_df.loc[idx, '〇×結果'] = '〇' if user_answer == correct_answer_description else '×'

                # 正解回数/不正解回数を更新
                if user_answer == correct_answer_description:
                    st.session_state.quiz_df.loc[idx, '正解回数'] += 1
                    st.session_state.latest_result = "正解！🎉"
                    st.session_state.correct += 1
                else:
                    st.session_state.quiz_df.loc[idx, '不正解回数'] += 1
                    st.session_state.latest_result = "不正解…💧"
                
                st.session_state.quiz_df.loc[idx, '最終実施日時'] = datetime.now()
                st.session_state.total += 1
                st.session_state.latest_correct_description = correct_answer_description
                st.session_state.answered_words.add(term) # 回答済み単語に追加

                if st.session_state.debug_mode:
                    st.session_state.debug_message_answer_update = f"DEBUG: '{term}'の正解回数: {st.session_state.quiz_df.loc[idx, '正解回数']}, 不正解回数: {st.session_state.quiz_df.loc[idx, '不正解回数']}"
            else:
                if st.session_state.debug_mode:
                    st.session_state.debug_message_error = f"DEBUG: エラー: 単語 '{term}' がDataFrameに見つかりません。"

    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズのUIを表示します。"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-container'><div class='metric-value'>{st.session_state.correct}</div><div class='metric-label'>正解数</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-container'><div class='metric-value'>{st.session_state.total}</div><div class='metric-label'>回答数</div></div>", unsafe_allow_html=True)
        with col3:
            # 未回答の単語数を表示
            st.markdown(f"<div class='metric-container'><div class='metric-value'>{len(remaining_df)}</div><div class='metric-label'>未回答単語</div></div>", unsafe_allow_html=True)
        
        # デバッグメッセージの表示 (デバッグモードが有効な場合のみ)
        if st.session_state.debug_mode:
            st.expander("デバッグ情報", expanded=False).write(st.session_state.debug_message_quiz_start)


        # クイズの開始・リロードボタン
        if st.button("クイズ開始 / 次の問題", key="start_quiz_button"):
            self.load_quiz(df_filtered, remaining_df)
            st.session_state.latest_result = "" # 新しい問題では結果をリセット
            st.session_state.latest_correct_description = ""
            if st.session_state.debug_mode:
                st.expander("デバッグ情報", expanded=False).write(st.session_state.debug_message_quiz_start)

        if st.session_state.current_quiz:
            st.markdown(f"### 単語: **{st.session_state.current_quiz['単語']}**")
            st.caption(f"カテゴリ: {st.session_state.current_quiz['カテゴリ']} / 分野: {st.session_state.current_quiz['分野']}")
            
            # 回答済みの場合、正解・不正解を表示
            if st.session_state.quiz_answered:
                if st.session_state.latest_result == "正解！🎉":
                    st.markdown(f"<div class='correct-answer-feedback'>{st.session_state.latest_result}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='incorrect-answer-feedback'>{st.session_state.latest_result}</div>", unsafe_allow_html=True)
                st.info(f"正解は: **{st.session_state.latest_correct_description}**")
                # 詳細情報の表示 (改行を考慮)
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
                # 選択肢の表示
                user_answer = st.radio(
                    "この単語の説明として正しいものはどれですか？",
                    st.session_state.current_quiz["choices"],
                    index=None, # デフォルトで何も選択されていない状態
                    key=f"quiz_choice_{st.session_state.quiz_choice_index}"
                )
                if user_answer:
                    self._handle_answer_submission(user_answer)
                    # 回答後に再描画を促す（結果表示のため）
                    st.rerun()
        else:
            if st.session_state.quiz_df is None or st.session_state.quiz_df.empty:
                st.info("データがロードされていません。サイドバーからデータソースを選択またはアップロードしてください。")
            else:
                st.info("選択されたフィルター条件に合致する単語が見つかりませんでした。フィルター設定を変更するか、クイズモードを切り替えてください。")
                
            if st.session_state.debug_mode:
                st.expander("デバッグ情報", expanded=False).write("DEBUG: current_quiz is None.")

    def display_data_viewer(self):
        """データビューアのUIを表示します。"""
        if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
            st.dataframe(st.session_state.quiz_df)
            
            # データのエクスポート
            @st.cache_data
            def convert_df_to_csv(df):
                return df.to_csv(index=False).encode('utf-8')

            csv_data = convert_df_to_csv(st.session_state.quiz_df)
            
            st.download_button(
                label="現在のデータをCSVでダウンロード",
                data=csv_data,
                file_name="quiz_data_with_results.csv",
                mime="text/csv",
            )
        else:
            st.info("表示するデータがありません。")

# アプリケーションの実行
def main():
    quiz_app = QuizApp()

    # サイドバーのデータソース選択
    st.sidebar.header("📚 データソース")
    data_source_options_radio = ["初期データ", "アップロード"]

    def on_data_source_change():
        """ラジオボタンが変更されたときに呼び出されるコールバック関数"""
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
                # ファイルが選択されていない場合はアップローダーが自動的にNoneを返すので、
                # uploaded_df_tempがない場合は何もロードしない

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
    
    # ファイルアップロードのハンドリング
    if uploaded_file is not None:
        quiz_app.handle_upload_logic(uploaded_file)
    else:
        # アップローダーがクリアされた場合、かつ現在アップロードデータソースが選択されている場合、
        # 初期データに戻す
        if st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is None:
            st.session_state.data_source_selection = "初期データ"
            st.session_state.main_data_source_radio = "初期データ"
            quiz_app._load_initial_data()


    # アプリケーションの初期ロード時に初期データをロード
    if st.session_state.quiz_df is None and st.session_state.data_source_selection == "初期データ":
        quiz_app._load_initial_data()
    elif st.session_state.quiz_df is None and st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
         quiz_app._load_uploaded_data()

    # タブの作成
    tab1, tab2 = st.tabs(["クイズ", "データビューア"])

    with tab1:
        st.header("情報処理試験対策クイズ")
        
        # クイズモードの選択
        st.sidebar.header("🎯 クイズモード")
        quiz_modes = ["復習", "未回答", "苦手"]
        st.session_state.quiz_mode = st.sidebar.radio(
            "クイズモードを選択", 
            quiz_modes, 
            index=quiz_modes.index(st.session_state.quiz_mode) if st.session_state.quiz_mode in quiz_modes else 0,
            key="quiz_mode_radio"
        )

        st.sidebar.header("クイズの絞り込み") 
        
        df_filtered = pd.DataFrame()
        remaining_df = pd.DataFrame()

        if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
            df_base_for_filters = st.session_state.quiz_df.copy() 

            categories = ["すべて"] + df_base_for_filters["カテゴリ"].dropna().unique().tolist()
            st.session_state.filter_category = st.sidebar.selectbox(
                "カテゴリで絞り込み", categories, 
                index=categories.index(st.session_state.filter_category) if st.session_state.filter_category in categories else 0,
                key="filter_category_selectbox"
            )

            fields = ["すべて"] + df_base_for_filters["分野"].dropna().unique().tolist()
            st.session_state.filter_field = st.sidebar.selectbox(
                "分野で絞り込み", fields, 
                index=fields.index(st.session_state.filter_field) if st.session_state.filter_field in fields else 0,
                key="filter_field_selectbox"
            )

            valid_syllabus_changes = df_base_for_filters["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
            syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
            
            st.session_state.filter_level = st.sidebar.selectbox(
                "🔄 シラバス改定有無で絞り込み", 
                syllabus_change_options, 
                index=syllabus_change_options.index(st.session_state.filter_level) if st.session_state.filter_level in syllabus_change_options else 0,
                key="filter_level_selectbox"
            )

            df_filtered = quiz_app._apply_filters(st.session_state.quiz_df)
            remaining_df = df_filtered[df_filtered["〇×結果"] == '']
        else:
            st.sidebar.info("データがロードされていません。") 
        
        # デバッグモードの切り替え
        st.sidebar.markdown("---")
        st.sidebar.subheader("開発者ツール")
        st.session_state.debug_mode = st.sidebar.checkbox(
            "デバッグモードを有効にする", 
            value=st.session_state.debug_mode, 
            key="debug_mode_checkbox"
        )

        quiz_app.display_quiz(df_filtered, remaining_df)

    with tab2:
        st.header("登録データ一覧")
        quiz_app.display_data_viewer()

    # フッターの表示
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; margin-top: 20px; font-size: 0.8em; color: #666;">
        <p>Powered by Streamlit and Gemini</p>
        <p>© 2024 Your Company Name or Your Name. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
