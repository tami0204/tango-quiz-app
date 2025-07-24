import streamlit as st
import pandas as pd
import random
import io
from datetime import datetime, timedelta
import time

# Streamlitページの初期設定
st.set_page_config(
    page_title="情報処理試験対策クイズ",
    page_icon="�",
    layout="centered", # 'centered' or 'wide'
    initial_sidebar_state="expanded" # 'auto', 'expanded', 'collapsed'
)

# --- ここからセッション状態の初期化ロジックを記述 ---

# セッション状態のデフォルト値
defaults = {
    "quiz_df": None,
    "current_quiz": None, # 現在出題中のクイズ（選択肢表示用）
    "latest_answered_quiz": None, # 回答後に詳細を表示するためのクイズ情報（一つ前の問題）
    "total": 0,
    "correct": 0,
    "latest_result": "",
    "latest_correct_description": "",
    "selected_answer": None, # ユーザーが選択した回答
    "quiz_choice_index": 0, # st.radio の key をユニークにするためのインデックス
    "filter_category": "すべて",
    "filter_field": "すべて",
    "filter_level": "すべて",
    "data_source_selection": "初期データ",
    "uploaded_df_temp": None,
    "uploaded_file_name": None,
    "uploaded_file_size": None,
    "debug_mode": False,
    "quiz_mode": "復習",
    "main_data_source_radio": "初期データ",
    "force_initial_load": True, # アプリ初回起動時にのみ初期データをロードするためのフラグ
    "processing_answer": False, # 回答処理中フラグ: Trueの間はUIをブロックする（スピナーなど）
    "quiz_state": "question" # "question" (問題表示中) or "answered" (回答済み、結果表示中)
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
        st.session_state.latest_answered_quiz = None # 表示用クイズ情報もクリア
        st.session_state.selected_answer = None # 選択された回答もクリア
        st.session_state.quiz_choice_index = 0 
        st.session_state.processing_answer = False 
        st.session_state.quiz_state = "question" # クイズ状態をリセット

        if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
            st.session_state.quiz_df.loc[:, '〇×結果'] = '' 
            st.session_state.quiz_df.loc[:, '正解回数'] = 0
            st.session_state.quiz_df.loc[:, '不正解回数'] = 0
            st.session_state.quiz_df.loc[:, '最終実施日時'] = pd.NaT 

            if st.session_state.debug_mode:
                st.sidebar.write(f"DEBUG: _reset_quiz_state_only: quiz_df['〇×結果'] reset. First 5: {st.session_state.quiz_df['〇×結果'].head()}")


    def _load_initial_data(self):
        """初期データをロードし、セッション状態に設定します。"""
        try:
            df = pd.read_csv("tango.csv", encoding='utf-8')
            st.session_state.quiz_df = self._process_df_types(df)
            st.success("初期データをロードしました！")
            self._reset_quiz_state_only() 
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
            self._reset_quiz_state_only() 
        else:
            st.warning("アップロードされたデータが見つかりません。")
            st.session_state.quiz_df = None 

    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameに対して、必要なカラムの型変換と、存在しないカラムの初期化を適用します。"""
        df_processed = df.copy() 
        
        column_configs = {
            '単語': {'type': str, 'default': ''}, # 単語列の追加
            '説明': {'type': str, 'default': ''}, # 説明列の追加
            'カテゴリ': {'type': str, 'default': ''}, # カテゴリ列の追加
            '分野': {'type': str, 'default': ''}, # 分野列の追加
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
            '〇×結果': {'type': str, 'default': '', 'replace_nan': True}
        }

        # 必須カラムのチェック (エラーハンドリング強化)
        required_columns = ['単語', '説明', 'カテゴリ', '分野']
        missing_columns = [col for col in required_columns if col not in df_processed.columns]
        if missing_columns:
            st.error(f"エラー: 以下の必須カラムがデータに見つかりません: {', '.join(missing_columns)}")
            st.stop() # アプリの実行を停止

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
        
        return df_processed

    def handle_upload_logic(self, uploaded_file):
        """ファイルアップロードのロジックを処理します。"""
        if uploaded_file is not None:
            # ファイルの内容が変更されたか、初めてアップロードされたかをチェック
            if (st.session_state.uploaded_file_name != uploaded_file.name or 
                st.session_state.uploaded_file_size != uploaded_file.size or
                st.session_state.uploaded_df_temp is None): # 初回アップロード時はtempがNone
                
                try:
                    # UTF-8でデコードを試み、失敗したらShift-JISで試す
                    content_str = uploaded_file.getvalue().decode('utf-8')
                except UnicodeDecodeError:
                    content_str = uploaded_file.getvalue().decode('shift_jis')

                uploaded_df = pd.read_csv(io.StringIO(content_str))
                st.session_state.uploaded_df_temp = uploaded_df
                st.session_state.uploaded_file_name = uploaded_file.name
                st.session_state.uploaded_file_size = uploaded_file.size
                
                st.session_state.quiz_df = self._process_df_types(uploaded_df.copy())
                st.session_state.data_source_selection = "アップロード" 
                self._reset_quiz_state_only() 
            else:
                # 同じファイルが再アップロードされた場合（内容変更なし）
                pass
        else:
            # ファイルアップロードウィジェットがクリアされた場合
            if st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
                st.session_state.uploaded_df_temp = None
                st.session_state.uploaded_file_name = None
                st.session_state.uploaded_file_size = None
                st.session_state.data_source_selection = "初期データ"
                self._load_initial_data() 


    @staticmethod
    def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
        """セッション状態のフィルターに基づいてDataFrameをフィルターします。"""
        filtered_df = df.copy()

        if st.session_state.filter_category != "すべて":
            filtered_df = filtered_df[filtered_df["カテゴリ"] == st.session_state.filter_category]
        if st.session_state.filter_field != "すべて":
            filtered_df = filtered_df[filtered_df["分野"] == st.session_state.filter_field]
        if st.session_state.filter_level != "すべて":
            filtered_df = filtered_df[filtered_df["シラバス改定有無"] == st.session_state.filter_level]
        
        return filtered_df

    def load_quiz(self): 
        """クイズの単語をロードします。"""
        if st.session_state.quiz_df is None or st.session_state.quiz_df.empty:
            st.session_state.current_quiz = None
            return 

        df_filtered = QuizApp._apply_filters(st.session_state.quiz_df)
        remaining_df_for_quiz = df_filtered[df_filtered["〇×結果"] == '']

        st.session_state.quiz_choice_index += 1 
        st.session_state.selected_answer = None # 新しい問題がロードされるので選択された回答をクリア

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
                # 既にstruggled_answeredに含まれている単語を除外
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

        # 重複する単語を除外し、temp_weightでソート
        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')

        if quiz_candidates_df.empty: # 重複排除後も空になる可能性があるので再チェック
            st.session_state.current_quiz = None
            return

        weights = quiz_candidates_df['temp_weight'].tolist()
        
        if not weights or all(w == 0 for w in weights): 
            # 重みが全て0または空の場合、均等にサンプリング
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
        
        if st.session_state.debug_mode:
            st.session_state.debug_message_quiz_start = f"DEBUG: New quiz loaded: '{st.session_state.current_quiz['単語']}' (Mode: {st.session_state.quiz_mode})"
        else:
            st.session_state.debug_message_quiz_start = "" 
        st.session_state.debug_message_answer_update = "" 
        st.session_state.debug_message_error = ""
        st.session_state.debug_message_answer_end = ""


    def _process_answer(self):
        """ユーザーが「回答する」ボタンをクリックしたときに実行される処理。"""
        if st.session_state.current_quiz and st.session_state.selected_answer:
            st.session_state.latest_answered_quiz = st.session_state.current_quiz.copy() # 直前のクイズ情報を保持

            correct_answer_description = st.session_state.latest_answered_quiz["説明"]
            term = st.session_state.latest_answered_quiz["単語"]
            
            # DataFrameを直接変更するため、コピーではなく参照で操作
            idx_list = st.session_state.quiz_df.index[st.session_state.quiz_df["単語"] == term].tolist()
            if idx_list:
                idx = idx_list[0]
                
                # DataFrameの更新
                if st.session_state.selected_answer == correct_answer_description:
                    st.session_state.quiz_df.loc[idx, '〇×結果'] = '〇'
                    st.session_state.quiz_df.loc[idx, '正解回数'] += 1
                    st.session_state.latest_result = "正解！🎉"
                    st.session_state.correct += 1
                else:
                    st.session_state.quiz_df.loc[idx, '〇×結果'] = '×'
                    st.session_state.quiz_df.loc[idx, '不正解回数'] += 1
                    st.session_state.latest_result = "不正解…💧"
                
                st.session_state.quiz_df.loc[idx, '最終実施日時'] = datetime.now() # 実施日時を更新

                st.session_state.total += 1
                st.session_state.latest_correct_description = correct_answer_description
                
                st.session_state.quiz_state = "answered" # 回答済み状態へ遷移
            else:
                if st.session_state.debug_mode:
                    st.session_state.debug_message_error = f"DEBUG: エラー: 単語 '{term}' がDataFrameに見つかりません。"
                st.error("回答処理中にエラーが発生しました。")
        else: # selected_answerがない場合など
            if st.session_state.debug_mode:
                st.session_state.debug_message_error = "DEBUG: 回答処理が実行されましたが、current_quizまたはselected_answerがNoneでした。"
            
        # コールバックの最後にセッションステートを変更するだけ。
        # Streamlitがこれを検知して再実行する。


    def _go_to_next_quiz(self):
        """「次へ」ボタンクリックで次のクイズをロードする処理。"""
        st.session_state.current_quiz = None 
        st.session_state.latest_answered_quiz = None # 前回の回答表示をクリア
        st.session_state.selected_answer = None # 選択肢もクリア
        st.session_state.quiz_state = "question" # 問題表示状態へ遷移
        
        # 次の問題をロード (load_quiz() の中で quiz_choice_index もインクリメントされる)
        self.load_quiz() 


    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズのUIを表示します。"""
        if st.session_state.debug_mode:
            st.expander("デバッグ情報 (問題ロード)", expanded=False).write(st.session_state.debug_message_quiz_start)

        # アプリ起動時やフィルター変更後など、current_quizがまだ設定されていない場合に、最初の問題をロード
        # quiz_state が "question" のときのみロードを試みる
        if st.session_state.current_quiz is None and st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty and st.session_state.quiz_state == "question":
            self.load_quiz()
        
        # 問題が存在する場合のみUIを表示
        if st.session_state.current_quiz:
            st.markdown(f"### 単語: **{st.session_state.current_quiz['単語']}**")
            st.caption(f"カテゴリ: {st.session_state.current_quiz['カテゴリ']} / 分野: {st.session_state.current_quiz['分野']}")
            
            # --- ステートごとの表示制御 ---
            if st.session_state.quiz_state == "question":
                # 問題表示中: ラジオボタンと「回答する」ボタンを表示
                st.session_state.selected_answer = st.radio(
                    "この単語の説明として正しいものはどれですか？",
                    st.session_state.current_quiz["choices"],
                    index=None, 
                    key=f"quiz_choice_{st.session_state.quiz_choice_index}",
                    disabled=False # 問題表示中は常に有効（選択されていないだけ）
                )
                
                # 回答が選択されたら「回答する」ボタンを有効化
                col1, col2 = st.columns(2)
                with col1:
                    st.button(
                        "回答する", 
                        on_click=self._process_answer, 
                        disabled=(st.session_state.selected_answer is None) # 回答が選択されていなければ無効
                    )
                with col2:
                    # ここに「次へ」ボタンを配置しない
                    pass

            elif st.session_state.quiz_state == "answered":
                # 回答済み状態: ラジオボタンは無効化して表示、フィードバックと「次へ」ボタンを表示
                # current_quiz の選択肢を表示し、selected_answer をデフォルトにする
                st.radio(
                    "この単語の説明として正しいものはどれですか？",
                    st.session_state.current_quiz["choices"],
                    index=st.session_state.current_quiz["choices"].index(st.session_state.selected_answer) if st.session_state.selected_answer in st.session_state.current_quiz["choices"] else None,
                    key=f"quiz_choice_{st.session_state.quiz_choice_index}",
                    disabled=True # 回答済みなので無効化
                )
                
                # フィードバックと詳細情報の表示（latest_answered_quiz を使用）
                if st.session_state.latest_answered_quiz: # latest_answered_quiz が存在することを確認
                    if st.session_state.latest_result == "正解！🎉":
                        st.markdown(f"<div class='correct-answer-feedback'>{st.session_state.latest_result}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='incorrect-answer-feedback'>{st.session_state.latest_result}</div>", unsafe_allow_html=True)
                    st.info(f"正解は: **{st.session_state.latest_correct_description}**")
                    
                    description_html = f"""
                    <div style="background-color: #f0f8ff; padding: 15px; border-left: 5px solid #2F80ED; margin-top: 15px; border-radius: 5px;">
                        <p><strong>単語の説明:</strong> {st.session_state.latest_answered_quiz['説明']}</p>
                        <p><strong>試験区分:</strong> {st.session_state.latest_answered_quiz.get('試験区分', 'N/A')}</p>
                        <p><strong>午後記述での使用例:</strong> {st.session_state.latest_answered_quiz.get('午後記述での使用例', 'N/A')}</p>
                        <p><strong>使用理由／文脈:</strong> {st.session_state.latest_answered_quiz.get('使用理由／文脈', 'N/A')}</p>
                        <p><strong>シラバス改定有無:</strong> {st.session_state.latest_answered_quiz.get('シラバス改定有無', 'N/A')}</p>
                        <p><strong>改定の意図・影響:</strong> {st.session_state.latest_answered_quiz.get('改定の意図・影響', 'N/A')}</p>
                    </div>
                    """
                    st.markdown(description_html, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    # ここに「回答する」ボタンを配置しない
                    pass
                with col2:
                    st.button("次へ", on_click=self._go_to_next_quiz, disabled=False) # 回答後は常に有効
                
                if st.session_state.debug_mode:
                    st.expander("デバッグ情報 (回答後)", expanded=False).write(st.session_state.debug_message_answer_update)

        else: # current_quiz が None の場合（問題がない場合）
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
                st.expander("デバッグ情報 (問題なし)", expanded=False).write("DEBUG: current_quiz is None.")


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

    # アプリケーションの初期ロード時に初期データをロード
    if st.session_state.quiz_df is None and st.session_state.force_initial_load:
        quiz_app._load_initial_data()
        st.session_state.force_initial_load = False 

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
            else: 
                st.warning("アップロードデータが選択されていません。CSVファイルをアップロードしてください。")

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
        # 新しいファイルが選択された場合、または前回と異なるファイルの場合のみ処理
        if (st.session_state.uploaded_file_name != uploaded_file.name or 
            st.session_state.uploaded_file_size != uploaded_file.size):
            quiz_app.handle_upload_logic(uploaded_file)
        elif st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is None:
            # アップロードモードなのにtempデータがない場合（例：アプリ再起動後）
            quiz_app.handle_upload_logic(uploaded_file)
    else:
        # アップロードファイルがクリアされた、または選択されていない場合
        if st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
            st.session_state.uploaded_df_temp = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
            st.session_state.data_source_selection = "初期データ"
            quiz_app._load_initial_data()


    # タブの作成
    tab1, tab2 = st.tabs(["クイズ", "データビューア"])

    # --- サイドバーに表示するフィルターと件数の計算を、sidebarコンテキスト内で実行 ---
    with st.sidebar:
        st.header("🎯 クイズモード")
        quiz_modes = ["未回答", "苦手", "復習"]
        st.session_state.quiz_mode = st.radio(
            "",
            quiz_modes, 
            index=quiz_modes.index(st.session_state.quiz_mode) if st.session_state.quiz_mode in quiz_modes else 0,
            key="quiz_mode_radio",
            label_visibility="hidden",
            on_change=quiz_app._reset_quiz_state_only 
        )

        st.header("クイズの絞り込み") 
        
        df_filtered = pd.DataFrame()
        remaining_df = pd.DataFrame()

        if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
            df_base_for_filters = st.session_state.quiz_df.copy() 

            categories = ["すべて"] + df_base_for_filters["カテゴリ"].dropna().unique().tolist()
            st.session_state.filter_category = st.selectbox(
                "カテゴリで絞り込み", categories, 
                index=categories.index(st.session_state.filter_category) if st.session_state.filter_category in categories else 0,
                key="filter_category_selectbox",
                on_change=quiz_app._reset_quiz_state_only 
            )

            fields = ["すべて"] + df_base_for_filters["分野"].dropna().unique().tolist()
            st.session_state.filter_field = st.selectbox(
                "分野で絞り込み", fields, 
                index=fields.index(st.session_state.filter_field) if st.session_state.filter_field in fields else 0,
                key="filter_field_selectbox",
                on_change=quiz_app._reset_quiz_state_only 
            )

            # シラバス改定有無のオプションを動的に取得し、空文字列を削除
            valid_syllabus_changes = df_base_for_filters["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
            syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
            
            st.session_state.filter_level = st.selectbox(
                "🔄 シラバス改定有無で絞り込み", 
                syllabus_change_options, 
                index=syllabus_change_options.index(st.session_state.filter_level) if st.session_state.filter_level in syllabus_change_options else 0,
                key="filter_level_selectbox",
                on_change=quiz_app._reset_quiz_state_only 
            )

            df_filtered = QuizApp._apply_filters(st.session_state.quiz_df) 
            remaining_df = df_filtered[df_filtered["〇×結果"] == '']
        else:
            st.info("データがロードされていません。") 
        
        st.markdown("---")
        st.subheader("📊 クイズ進捗")
        
        filtered_count = len(df_filtered)

        st.markdown(f"<div class='metric-container'><span class='metric-label'>正解：</span><span class='metric-value'>{st.session_state.correct}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><span class='metric-label'>回答：</span><span class='metric-value'>{st.session_state.total}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><span class='metric-label'>未回答：</span><span class='metric-value'>{len(remaining_df)}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-container'><span class='metric-label'>対象：</span><span class='metric-value'>{filtered_count}</span></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("開発者ツール")
        st.session_state.debug_mode = st.checkbox(
            "デバッグモードを有効にする", 
            value=st.session_state.debug_mode, 
            key="debug_mode_checkbox"
        )
    
    with tab1:
        st.header("情報処理試験対策クイズ")
        quiz_app.display_quiz(df_filtered, remaining_df)

    with tab2:
        st.header("登録データ一覧")
        quiz_app.display_data_viewer()

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; margin-top: 20px; font-size: 0.8em; color: #666;">
        <p>Powered by Streamlit and Gemini</p>
        <p>© 2024 Your Company Name or Your Name. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
�
