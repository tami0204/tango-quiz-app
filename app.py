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

# --- ここからセッション状態の初期化ロジックを記述 ---

# セッション状態のデフォルト値
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
    "debug_mode": False,
    "quiz_mode": "復習", # quiz_mode もここで初期化すること
    "main_data_source_radio": "初期データ", # ラジオボタンのキーと同期
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- ここまでセッション状態の初期化ロジック ---


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
    /* --- フォントサイズ調整: h3 (単語), p (説明文), stRadio (選択肢) --- */
    h3 {
        font-size: 1.75em; /* 元のh3より少し小さく */
    }
    p { /* 説明文などの標準的な段落のフォントサイズ */
        font-size: 0.95em; 
    }
    /* 選択肢ボタンのスタイル */
    .stRadio > label > div {
        background-color: #F0F2F6; /* 薄いグレーの背景 */
        padding: 10px 15px; /* パディングを少し減らす */
        margin-bottom: 7px; /* マージンを少し減らす */
        border-radius: 8px;
        border: 1px solid #DDDDDD;
        transition: all 0.2s ease;
        font-size: 0.9em; /* 選択肢のフォントサイズを小さく */
    }
    .stRadio > label > div:hover {
        background-color: #E0E2E6; /* ホバーで少し濃く */
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
        margin-bottom: 10px; /* ボタン間のスペース */
    }
    .stButton>button:hover {
        background-color: #2671c6;
        border-color: #2671c6;
        color: white;
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
    /* 統計情報コンテナ */
    .metric-container {
        border: 1px solid #DDDDDD;
        border-radius: 8px;
        padding: 5px 10px; /* 上下のパディングを減らす */
        margin-bottom: 5px; /* マージンを減らす */
        background-color: #FFFFFF;
        display: flex; /* Flexboxを使用 */
        justify-content: space-between; /* ラベルと値を両端に寄せる */
        align-items: center; /* 垂直方向中央揃え */
    }
    /* サイドバー内のメトリックコンテナの背景色を調整 */
    [data-testid="stSidebar"] .metric-container {
        background-color: #e9ecef; /* サイドバーの背景色と調和するよう調整 */
    }
    /* --- サイドバーの件数表示文字サイズと配置を調整 --- */
    [data-testid="stSidebar"] .metric-value {
        font-size: 1.3em; /* さらに小さく */
        font-weight: bold;
        color: #2F80ED;
        text-align: right; /* 数値を右寄せ */
        flex-grow: 1; /* 値が利用可能なスペースを埋めるようにする */
    }
    [data-testid="stSidebar"] .metric-label {
        font-size: 0.85em; /* 0.8em から少し大きく */
        color: #666666;
        text-align: left; /* ラベルを左寄せ */
        min-width: 40px; /* ラベルの最小幅を設定して揃える */
        padding-right: 5px; /* ラベルと数値の間の余白 */
    }
    /* --- サイドバーの件数表示文字サイズと配置調整ここまで --- */

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
    /* st.radio のラベルを完全に非表示にする */
    div[data-testid="stRadio"] > label[data-testid="stWidgetLabel"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

class QuizApp:
    def __init__(self):
        # セッション状態の初期化は、アプリの先頭で行うため、ここでは何もしない
        pass 

    def _reset_quiz_state_only(self):
        """クイズの進行に関するセッションステートのみをリセットします。
        データソース切り替え時やクイズリセットボタン押下時に呼び出される。
        """
        st.session_state.total = 0
        st.session_state.correct = 0
        st.session_state.latest_result = ""
        st.session_state.latest_correct_description = ""
        st.session_state.current_quiz = None
        st.session_state.quiz_answered = False
        st.session_state.quiz_choice_index = 0 
        
        # '〇×結果' をリセットするために、DataFrameを明示的に更新
        if st.session_state.quiz_df is not None:
            # SettingWithCopyWarningを避けるために .loc を使用
            st.session_state.quiz_df.loc[:, '〇×結果'] = '' 
            st.session_state.quiz_df.loc[:, '正解回数'] = 0
            st.session_state.quiz_df.loc[:, '不正解回数'] = 0
            st.session_state.quiz_df.loc[:, '最終実施日時'] = pd.NaT # 日付もリセット

            # debug: st.sidebar.write(f"DEBUG: _reset_quiz_state_only: quiz_df['〇×結果'] reset. First 5: {st.session_state.quiz_df['〇×結果'].head()}")


    def _load_initial_data(self):
        """初期データをロードし、セッション状態に設定します。"""
        try:
            df = pd.read_csv("tango.csv", encoding='utf-8')
            st.session_state.quiz_df = self._process_df_types(df)
            st.success("初期データをロードしました！")
            self._reset_quiz_state_only() # ロード後にクイズ状態をリセット
        except FileNotFoundError:
            st.error("エラー: 初期データファイル 'tango.csv' が見つかりません。")
            st.session_state.quiz_df = None
        except Exception as e:
            st.error(f"初期データのロード中にエラーが発生しました: {e}")
            st.session_state.quiz_df = None

    def _load_uploaded_data(self):
        """アップロードされたデータをロードし、セッション状態に設定します。"""
        if st.session_state.uploaded_df_temp is not None:
            st.session_state.quiz_df = self._process_df_types(st.session_state.uploaded_df_temp.copy())
            st.success(f"'{st.session_state.uploaded_file_name}' をロードしました！")
            self._reset_quiz_state_only() # ロード後にクイズ状態をリセット
        else:
            st.warning("アップロードされたデータが見つかりません。")
            st.session_state.quiz_df = None # データがない場合はNoneを設定

    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameに対して、必要なカラムの型変換と初期化を適用します。
        このメソッドでは、ロードされたデータフレームをStreamlitのセッション状態に保存する前に、
        既存の〇×結果、正解・不正解回数、最終実施日時をリセットします。
        これにより、アップロードされた過去のデータにこれらの情報が含まれていても、
        クイズ開始時には常にクリーンな状態から始められます。
        """
        # 必ず新しいDataFrameのコピーを操作するようにする
        df_processed = df.copy() 
        
        column_configs = {
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
            if col_name not in df_processed.columns:
                df_processed[col_name] = config['default']
            else:
                if config.get('replace_nan'):
                    df_processed[col_name] = df_processed[col_name].astype(str).replace('nan', '')
                if config.get('numeric_coerce'):
                    df_processed[col_name] = pd.to_numeric(df_processed[col_name], errors='coerce').fillna(config['default']).astype(int)
                if config['type'] == 'datetime':
                    df_processed[col_name] = pd.to_datetime(df_processed[col_name], errors='coerce')
                elif config['type'] == str and not config.get('replace_nan'):
                    df_processed[col_name] = df_processed[col_name].astype(str)
        
        # '〇×結果' カラムが存在しない場合は追加し、存在するなら強制的に空文字列で初期化
        if '〇×結果' not in df_processed.columns:
            df_processed['〇×結果'] = ''
        else:
            df_processed['〇×結果'] = '' # 既存の列も強制的に空に

        # 正解回数、不正解回数もここでリセットする（念のため）
        if '正解回数' not in df_processed.columns: df_processed['正解回数'] = 0
        else: df_processed['正解回数'] = 0
        
        if '不正解回数' not in df_processed.columns: df_processed['不正解回数'] = 0
        else: df_processed['不正解回数'] = 0

        if '最終実施日時' not in df_processed.columns: df_processed['最終実施日時'] = pd.NaT
        else: df_processed['最終実施日時'] = pd.NaT
        
        return df_processed

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
                    # ここで _process_df_types が呼び出され、'〇×結果' がリセットされる
                    st.session_state.quiz_df = self._process_df_types(uploaded_df.copy())
                    st.session_state.data_source_selection = "アップロード" # データソースをアップロードに切り替える
                    self._reset_quiz_state_only() # クイズ状態もリセット
                    st.success(f"'{uploaded_file.name}' をロードしました！")
                    st.rerun() # データソース変更を即時反映
                except Exception as e:
                    st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
                    st.session_state.uploaded_df_temp = None
                    st.session_state.uploaded_file_name = None
                    st.session_state.uploaded_file_size = None
            # else: 同じファイルが再度選択された場合は何もしない（既にロードされている）
        else:
            # アップロードされたファイルがクリアされた場合
            # st.session_state.uploader が None になった場合
            if st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
                 # This means the uploader was cleared by the user.
                 # Reset uploaded state and revert to initial data
                 st.session_state.uploaded_df_temp = None
                 st.session_state.uploaded_file_name = None
                 st.session_state.uploaded_file_size = None
                 st.session_state.data_source_selection = "初期データ"
                 self._load_initial_data() # 初期データを再ロードし、状態をリセット
                 st.rerun()


    @staticmethod
    def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
        """セッション状態のフィルターに基づいてDataFrameをフィルターします。"""
        # defensive copy to avoid SettingWithCopyWarning later, though not strictly necessary here
        filtered_df = df.copy()

        if st.session_state.filter_category != "すべて":
            filtered_df = filtered_df[filtered_df["カテゴリ"] == st.session_state.filter_category]
        if st.session_state.filter_field != "すべて":
            filtered_df = filtered_df[filtered_df["分野"] == st.session_state.filter_field]
        if st.session_state.filter_level != "すべて":
            filtered_df = filtered_df[filtered_df["シラバス改定有無"] == st.session_state.filter_level]
        
        return filtered_df

    def load_quiz(self): 
        """
        クイズの単語をロードします。選択されたモードに基づいて出題ロジックが変更されます。
        このメソッドが呼ばれるたびに、常に最新のフィルタリングされたデータと未回答データを取得します。
        """
        if st.session_state.quiz_df is None or st.session_state.quiz_df.empty:
            st.session_state.current_quiz = None
            return # データがない場合は何もしない

        # 最新のフィルタリングされたデータを取得
        df_filtered = QuizApp._apply_filters(st.session_state.quiz_df)
        # 最新の未回答データを取得
        remaining_df_for_quiz = df_filtered[df_filtered["〇×結果"] == '']

        # 前のクイズが回答済みの場合にのみインデックスを進める
        if st.session_state.quiz_answered: 
            st.session_state.quiz_answered = False 
            st.session_state.quiz_choice_index += 1 

        quiz_candidates_df = pd.DataFrame()
        
        if st.session_state.quiz_mode == "未回答":
            if not remaining_df_for_quiz.empty: 
                quiz_candidates_df = remaining_df_for_quiz.assign(temp_weight=1) 
            
        elif st.session_state.quiz_mode == "苦手":
            struggled_answered = df_filtered[
                (df_filtered["〇×結果"] != '') & 
                (df_filtered["不正解回数"] > df_filtered["正解回数"])
            ].copy()
            if not struggled_answered.empty:
                struggled_answered['temp_weight'] = struggled_answered['不正解回数'] + 5 
                quiz_candidates_df = pd.concat([quiz_candidates_df, struggled_answered], ignore_index=True)

            low_correct_count_answered = df_filtered[
                (df_filtered['〇×結果'] != '') & 
                (df_filtered["正解回数"] <= 3) 
            ].copy()
            if not low_correct_count_answered.empty:
                low_correct_count_answered = low_correct_count_answered[~low_correct_count_answered['単語'].isin(quiz_candidates_df['単語'])]
                if not low_correct_count_answered.empty:
                    low_correct_count_answered['temp_weight'] = low_correct_count_answered['正解回数'].apply(lambda x: 4 - x) 
                    quiz_candidates_df = pd.concat([quiz_candidates_df, low_correct_count_answered], ignore_index=True)
            

        elif st.session_state.quiz_mode == "復習":
            if not df_filtered.empty:
                quiz_candidates_df = df_filtered.assign(temp_weight=1) 
            
        
        if quiz_candidates_df.empty:
            st.session_state.current_quiz = None
            return

        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')

        if quiz_candidates_df.empty:
            st.session_state.current_quiz = None
            return

        weights = quiz_candidates_df['temp_weight'].tolist()
        
        if not weights or all(w == 0 for w in weights): 
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
        
        # st.session_state.quiz_choice_index は既に次のクイズのために更新されている

        if st.session_state.debug_mode:
            st.session_state.debug_message_quiz_start = f"DEBUG: New quiz loaded: '{st.session_state.current_quiz['単語']}' (Mode: {st.session_state.quiz_mode})"
        else:
            st.session_state.debug_message_quiz_start = "" 
        st.session_state.debug_message_answer_update = "" 
        st.session_state.debug_message_error = ""
        st.session_state.debug_message_answer_end = ""


    def _handle_answer_submission(self, user_answer):
        """ユーザーの回答を処理し、セッション状態を更新します。"""
        if st.session_state.current_quiz:
            correct_answer_description = st.session_state.current_quiz["説明"]
            term = st.session_state.current_quiz["単語"]
            
            # DataFrameを更新する際に、単語名でインデックスを検索し、locで直接更新
            # これにより、Streamlitが変更を検知しやすくなります。
            idx = st.session_state.quiz_df.index[st.session_state.quiz_df["単語"] == term].tolist()
            if idx:
                idx = idx[0] # 該当するインデックスを取得
                st.session_state.quiz_answered = True
                
                # locを使って複数カラムを一度に更新
                if user_answer == correct_answer_description:
                    st.session_state.quiz_df.loc[idx, ['〇×結果', '正解回数', '最終実施日時']] = ['〇', st.session_state.quiz_df.loc[idx, '正解回数'] + 1, datetime.now()]
                    st.session_state.latest_result = "正解！🎉"
                    st.session_state.correct += 1
                else:
                    st.session_state.quiz_df.loc[idx, ['〇×結果', '不正解回数', '最終実施日時']] = ['×', st.session_state.quiz_df.loc[idx, '不正解回'] + 1, datetime.now()]
                    st.session_state.latest_result = "不正解…💧"
                
                st.session_state.total += 1
                st.session_state.latest_correct_description = correct_answer_description

                if st.session_state.debug_mode:
                    st.session_state.debug_message_answer_update = f"DEBUG: '{term}'の正解回数: {st.session_state.quiz_df.loc[idx, '正解回数']}, 不正解回数: {st.session_state.quiz_df.loc[idx, '不正解回数']}. 〇×結果: {st.session_state.quiz_df.loc[idx, '〇×結果']}"
            else:
                if st.session_state.debug_mode:
                    st.session_state.debug_message_error = f"DEBUG: エラー: 単語 '{term}' がDataFrameに見つかりません。"

    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズのUIを表示します。"""
        if st.session_state.debug_mode:
            st.expander("デバッグ情報", expanded=False).write(st.session_state.debug_message_quiz_start)

        # クイズの開始・リロードボタン
        if st.button("クイズ開始 / 次の問題", key="start_quiz_button"):
            self.load_quiz() 
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
            else:
                current_df_filtered = QuizApp._apply_filters(st.session_state.quiz_df)
                current_remaining_df = current_df_filtered[current_df_filtered["〇×結果"] == '']

                if len(current_df_filtered) == 0:
                    st.info("選択されたフィルター条件に合致する単語が見つかりませんでした。フィルター設定を変更してください。")
                elif st.session_state.quiz_mode == "未回答" and len(current_remaining_df) == 0:
                    st.info("おめでとうございます！選択されたフィルター条件で、すべての未回答単語をクリアしました。フィルターを変更するか、別のクイズモードを試してください。")
                elif st.session_state.quiz_mode == "苦手":
                    struggled_candidates = current_df_filtered[
                        (current_df_filtered["〇×結果"] != '') & 
                        (current_df_filtered["不正解回数"] > current_df_filtered["正解回数"])
                    ]
                    low_correct_candidates = current_df_filtered[
                        (current_df_filtered['〇×結果'] != '') & 
                        (current_df_filtered["正解回数"] <= 3) 
                    ]
                    if struggled_candidates.empty and low_correct_candidates.empty:
                        st.info("「苦手」モードで出題すべき単語がありません。全ての苦手な単語を克服したようです！フィルターを変更するか、別のクイズモードを試してください。")
                    else:
                        st.info("現在のクイズモードで出題できる単語が見つかりませんでした。フィルター設定を変更するか、別のクイズモードを試してください。")
                elif st.session_state.quiz_mode == "復習" and not current_df_filtered.empty:
                    st.info("復習する単語が見つかりませんでした。フィルター設定を変更するか、クイズモードを切り替えてください。")
                else:
                    st.info("現在のクイズモードで出題できる単語が見つかりませんでした。フィルター設定を変更するか、別のクイズモードを試してください。")
                
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
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

    # サイドバーのデータソース選択
    st.sidebar.header("📚 データソース")
    data_source_options_radio = ["初期データ", "アップロード"]

    def on_data_source_change():
        """ラジオボタンが変更されたときに呼び出されるコールバック関数"""
        st.session_state.data_source_selection = st.session_state.main_data_source_radio
        
        if st.session_state.data_source_selection == "初期データ":
            quiz_app._load_initial_data() 
            st.session_state.uploaded_df_temp = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
        else: # "アップロード"が選択された場合
            if st.session_state.uploaded_df_temp is not None:
                quiz_app._load_uploaded_data()
            else: # アップロードデータがまだない場合
                st.warning("アップロードデータが選択されていません。CSVファイルをアップロードしてください。")
        st.rerun() # データソース変更を即時反映

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
        # アップロード選択中にファイルが削除された場合
        if st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
             # uploaded_fileがNoneだがuploaded_df_tempが残っている場合、これはユーザーがファイルをクリアしたことを意味する
             st.session_state.uploaded_df_temp = None
             st.session_state.uploaded_file_name = None
             st.session_state.uploaded_file_size = None
             st.session_state.data_source_selection = "初期データ"
             quiz_app._load_initial_data()
             st.rerun()


    # アプリケーションの初期ロード時に初期データをロード
    if st.session_state.quiz_df is None:
        if st.session_state.data_source_selection == "初期データ":
            quiz_app._load_initial_data()
        elif st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
            quiz_app._load_uploaded_data()


    # タブの作成
    tab1, tab2 = st.tabs(["クイズ", "データビューア"])

    # --- サイドバーに表示するフィルターと件数の計算を、sidebarコンテキスト内で実行 ---
    with st.sidebar:
        st.header("🎯 クイズモード")
        quiz_modes = ["未回答", "苦手", "復習"]
        # ラジオボタンの変更時に quiz_app._reset_quiz_state_only を呼び出し、状態をリセット
        st.session_state.quiz_mode = st.radio(
            "",
            quiz_modes, 
            index=quiz_modes.index(st.session_state.quiz_mode) if st.session_state.quiz_mode in quiz_modes else 0,
            key="quiz_mode_radio",
            label_visibility="hidden",
            on_change=quiz_app._reset_quiz_state_only # クイズモード変更時にクイズの状態をリセット
        )

        st.header("クイズの絞り込み") 
        
        # フィルターの適用と件数の計算
        df_filtered = pd.DataFrame()
        remaining_df = pd.DataFrame()

        if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
            df_base_for_filters = st.session_state.quiz_df.copy() 

            categories = ["すべて"] + df_base_for_filters["カテゴリ"].dropna().unique().tolist()
            st.session_state.filter_category = st.selectbox(
                "カテゴリで絞り込み", categories, 
                index=categories.index(st.session_state.filter_category) if st.session_state.filter_category in categories else 0,
                key="filter_category_selectbox",
                on_change=quiz_app._reset_quiz_state_only # フィルター変更時にクイズの状態をリセット
            )

            fields = ["すべて"] + df_base_for_filters["分野"].dropna().unique().tolist()
            st.session_state.filter_field = st.selectbox(
                "分野で絞り込み", fields, 
                index=fields.index(st.session_state.filter_field) if st.session_state.filter_field in fields else 0,
                key="filter_field_selectbox",
                on_change=quiz_app._reset_quiz_state_only # フィルター変更時にクイズの状態をリセット
            )

            valid_syllabus_changes = df_base_for_filters["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
            syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
            
            st.session_state.filter_level = st.selectbox(
                "🔄 シラバス改定有無で絞り込み", 
                syllabus_change_options, 
                index=syllabus_change_options.index(st.session_state.filter_level) if st.session_state.filter_level in syllabus_change_options else 0,
                key="filter_level_selectbox",
                on_change=quiz_app._reset_quiz_state_only # フィルター変更時にクイズの状態をリセット
            )

            # ここでフィルターを適用し、常に最新の df_filtered と remaining_df を取得
            df_filtered = QuizApp._apply_filters(st.session_state.quiz_df) 
            # '〇×結果'が空のものを「未回答」とみなす
            remaining_df = df_filtered[df_filtered["〇×結果"] == '']
        else:
            st.info("データがロードされていません。") 
        
        # 各件数をサイドバーに表示
        st.markdown("---")
        st.subheader("📊 クイズ進捗")
        
        # フィルタリングされた単語の総数を計算
        filtered_count = len(df_filtered)

        st.markdown(f"<div class='metric-container'><span class='metric-label'>正解：</span><span class='metric-value'>{st.session_state.correct}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><span class='metric-label'>回答：</span><span class='metric-value'>{st.session_state.total}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><span class='metric-label'>未回答：</span><span class='metric-value'>{len(remaining_df)}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><span class='metric-label'>対象：</span><span class='metric-value'>{filtered_count}</span></div>", unsafe_allow_html=True)

        # デバッグモードの切り替え
        st.markdown("---")
        st.subheader("開発者ツール")
        st.session_state.debug_mode = st.checkbox(
            "デバッグモードを有効にする", 
            value=st.session_state.debug_mode, 
            key="debug_mode_checkbox"
        )
    # --- サイドバーの処理はここまで ---

    with tab1:
        st.header("情報処理試験対策クイズ")
        # メインコンテンツで quiz_app.display_quiz を呼び出す際は、
        # サイドバーで計算された df_filtered と remaining_df を渡す
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
