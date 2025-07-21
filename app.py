import streamlit as st
import pandas as pd
import random
import os
import datetime

class QuizApp:
    def __init__(self, original_df: pd.DataFrame):
        # アプリで使用するデフォルトのセッション状態変数を定義
        self.kana_labels = ["ア", "イ", "ウ", "エ", "オ"]
        self.defaults = {
            "total": 0, # クイズの合計回答数
            "correct": 0, # クイズの正解数
            "answered_words": set(), # 回答済みの単語を格納するセット
            "latest_result": "", # 最新の回答結果（正解/不正解）
            "latest_correct_description": "", # 最新のクイズの正解説明
            "current_quiz": None, # 現在出題中のクイズデータ
            "quiz_answered": False, # 現在のクイズに回答済みかどうかのフラグ
            "quiz_choice_index": 0, # Streamlitのフォームキーをユニークにするためのインデックス
            "quiz_df": None, # メインの学習データ（tango.csvまたはアップロードデータ）
            "uploaded_df_temp": None, # アップロードされた一時的なデータ
            "uploaded_file_name": None, # アップロードされたファイル名
            "uploaded_file_size": None, # アップロードされたファイルのサイズ（再アップロード判定用）
            "data_source_selection": "初期データ", # ラジオボタンの選択状態を保持（"アップロード"または"初期データ"）
            "filter_category": "すべて", # カテゴリフィルターの選択状態
            "filter_field": "すべて", # 分野フィルターの選択状態
            "filter_level": "すべて", # シラバス改定有無フィルターの選択状態
            "debug_message_quiz_start": "", # クイズ開始時のデバッグメッセージ
            "debug_message_answer_update": "", # 回答更新時のデバッグメッセージ
            "debug_message_error": "", # エラー発生時のデバッグメッセージ
            "debug_message_answer_end": "", # 回答処理終了時のデバッグメッセージ
        }
        # セッション状態を初期化
        self._initialize_session()
        
        # tango.csvから読み込んだオリジナルのデータを保持
        self.initial_df = self._process_df_types(original_df.copy())

        # アプリ起動時またはquiz_dfがNoneの場合の初期データロードロジック
        if st.session_state.quiz_df is None:
            if st.session_state.data_source_selection == "初期データ":
                self._initialize_quiz_df_from_original()
            # "アップロード"が選択されており、かつ一時データがない場合、一時的に初期データをロード
            elif st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is None:
                self._initialize_quiz_df_from_original() 
            # "アップロード"が選択されており、かつ一時データがある場合、その一時データをロード
            elif st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
                st.session_state.quiz_df = st.session_state.uploaded_df_temp.copy()
                # ロードしたデータに基づいて回答済み単語セットを更新
                st.session_state.answered_words = set(st.session_state.quiz_df[
                    (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
                ]["単語"].tolist())
            else:
                # 予期せぬ状態の場合のフォールバック
                self._initialize_quiz_df_from_original()
                
    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameの必要なカラムの型変換と初期化を堅牢に行います。"""
        
        # '〇×結果'カラムの存在チェックと初期化/クリーンアップ
        if '〇×結果' not in df.columns:
            df['〇×結果'] = ''
        else:
            df['〇×結果'] = df['〇×結果'].astype(str).replace('nan', '')

        # '正解回数', '不正解回数'カラムの数値型変換とNaNの0埋め
        for col in ['正解回数', '不正解回数']:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # 日時カラムの型変換とNaN（NaT）の処理
        for col in ['最終実施日時', '次回実施予定日時']:
            if col not in df.columns:
                df[col] = pd.NaT # Not a Time (PandasのdatetimeのNaN)
            else:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # 'シラバス改定有無'カラムの初期化/クリーンアップ
        if 'シラバス改定有無' not in df.columns:
            df['シラバス改定有無'] = ''
        else:
            df['シラバス改定有無'] = df['シラバス改定有無'].astype(str).replace('nan', '')
            
        # その他の任意カラムの存在チェックと初期化
        if '午後記述での使用例' not in df.columns: df['午後記述での使用例'] = ''
        if '使用理由／文脈' not in df.columns: df['使用理由／文脈'] = ''
        if '試験区分' not in df.columns: df['試験区分'] = ''
        if '出題確率（推定）' not in df.columns: df['出題確率（推定）'] = ''
        if '改定の意図・影響' not in df.columns: df['改定の意図・影響'] = ''

        return df

    def _initialize_session(self):
        """Streamlitのセッション状態をデフォルト値で初期化します。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            # answered_wordsがセット型であることを保証
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _initialize_quiz_df_from_original(self):
        """initial_df (tango.csv) からquiz_dfを初期化し、学習履歴もリセットします。"""
        st.session_state.quiz_df = self.initial_df.copy()
        
        # 回答済み単語セットも初期化（正解・不正解回数が0でない単語を対象）
        st.session_state.answered_words = set(st.session_state.quiz_df[
            (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
        ]["単語"].tolist())

    def _reset_session_state(self):
        """現在アクティブな学習データの進捗（正解/不正解回数など）のみをリセットします。
        データソースの切り替えは行いません。
        """
        # quiz_df内の学習履歴関連カラムをリセット
        st.session_state.quiz_df['〇×結果'] = ''
        st.session_state.quiz_df['正解回数'] = 0
        st.session_state.quiz_df['不正解回数'] = 0
        st.session_state.quiz_df['最終実施日時'] = pd.NaT
        st.session_state.quiz_df['次回実施予定日時'] = pd.NaT

        # 回答済み単語セットをクリア
        st.session_state.answered_words = set()

        # その他のセッション状態変数をデフォルトに戻す（データソース関連、フィルターは維持）
        for key, val in self.defaults.items():
            if key not in ["quiz_df", "data_source_selection", "uploaded_df_temp", "uploaded_file_name", "uploaded_file_size",
                           "filter_category", "filter_field", "filter_level"]: 
                st.session_state[key] = val if not isinstance(val, set) else set() # setの場合は新しいセットを作成
        
        # 現在のクイズをリセットし、回答済みフラグもFalseに
        st.session_state.current_quiz = None 
        st.session_state.quiz_answered = False 
        st.session_state.quiz_choice_index = 0 # フォームキーもリセット

        # フィルターも初期値に戻す
        st.session_state.filter_category = "すべて"
        st.session_state.filter_field = "すべて"
        st.session_state.filter_level = "すべて"

        st.success("✅ 現在の学習データの進捗をリセットしました。")
        st.rerun()

    def filter_data(self):
        """データフレームをフィルター条件に基づいて絞り込み、フィルター結果と残り単語を返します。"""
        df = st.session_state.quiz_df.copy()

        # カテゴリフィルター
        categories = ["すべて"] + df["カテゴリ"].dropna().unique().tolist()
        st.session_state.filter_category = st.sidebar.selectbox(
            "カテゴリで絞り込み", categories, index=categories.index(st.session_state.filter_category) if st.session_state.filter_category in categories else 0
        )
        if st.session_state.filter_category != "すべて":
            df = df[df["カテゴリ"] == st.session_state.filter_category]

        # 分野フィルター
        fields = ["すべて"] + df["分野"].dropna().unique().tolist()
        st.session_state.filter_field = st.sidebar.selectbox(
            "分野で絞り込み", fields, index=fields.index(st.session_state.filter_field) if st.session_state.filter_field in fields else 0
        )
        if st.session_state.filter_field != "すべて":
            df = df[df["分野"] == st.session_state.filter_field]

        # シラバス改定有無のフィルター
        valid_syllabus_changes = df["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
        syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
        
        st.session_state.filter_level = st.sidebar.selectbox(
            "🔄 シラバス改定有無で絞り込み", 
            syllabus_change_options, 
            index=syllabus_change_options.index(st.session_state.filter_level) if st.session_state.filter_level in syllabus_change_options else 0
        )
        if st.session_state.filter_level != "すべて":
            df = df[df["シラバス改定有無"] == st.session_state.filter_level]

        # 回答済みの単語を除外し、まだ出題されていない単語のリストを作成
        remaining_df = df[~df["単語"].isin(st.session_state.answered_words)]

        return df, remaining_df

    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズの単語をロードします。不正解回数や最終実施日時を考慮して出題単語を選択します。"""
        # 前のクイズが回答済みの場合、回答済みフラグとフォームキーをリセット
        if st.session_state.quiz_answered: 
            st.session_state.quiz_answered = False 
            st.session_state.quiz_choice_index += 1 

        quiz_candidates_df = pd.DataFrame() # 出題候補のDataFrame

        # 1. 不正解回数が多く、かつ回答履歴がある単語を優先的に候補に入れる
        # 回答済みかつ不正解回数が多い単語を抽出
        answered_and_struggled = df_filtered[
            (df_filtered["単語"].isin(st.session_state.answered_words)) &
            (df_filtered["不正解回数"] > df_filtered["正解回数"])
        ].copy()

        if not answered_and_struggled.empty:
            answered_and_struggled['temp_weight'] = answered_and_struggled['不正解回数'] + 1 # 不正解回数が多いほど重み付け
            quiz_candidates_df = pd.concat([quiz_candidates_df, answered_and_struggled], ignore_index=True)

        # 2. まだ出題されていない単語を候補に入れる
        if not remaining_df.empty:
            remaining_df_copy = remaining_df.copy()
            remaining_df_copy['temp_weight'] = 1 # まだ出題されていない単語の重み
            quiz_candidates_df = pd.concat([quiz_candidates_df, remaining_df_copy], ignore_index=True)
            
        # 重複する単語がある場合、不正解回数が多い（temp_weightが高い）方を優先
        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')

        if quiz_candidates_df.empty:
            st.info("現在のフィルター条件に一致する単語がないか、すべての単語を回答しました！フィルターを変更するか、学習データをリセットしてください。")
            st.session_state.current_quiz = None
            return

        # 重みに基づいて単語をランダム選択
        weights = quiz_candidates_df['temp_weight'].tolist()
        
        if sum(weights) == 0: # 全ての重みが0の場合（全ての単語がtemp_weight=0）、均等にランダム選択
            selected_quiz_row = quiz_candidates_df.sample(n=1).iloc[0]
        else:
            selected_quiz_row = quiz_candidates_df.sample(n=1, weights=weights).iloc[0]

        st.session_state.current_quiz = selected_quiz_row.to_dict()

        correct_description = st.session_state.current_quiz["説明"]
        
        # 誤った選択肢を生成
        all_descriptions = st.session_state.quiz_df["説明"].unique().tolist()
        other_descriptions = [desc for desc in all_descriptions if desc != correct_description]
        
        num_wrong_choices = min(3, len(other_descriptions)) # 最大3つの誤答選択肢
        wrong_choices = random.sample(other_descriptions, num_wrong_choices)

        choices = wrong_choices + [correct_description]
        random.shuffle(choices) # 選択肢をシャッフル
        st.session_state.current_quiz["choices"] = choices
        
        st.session_state.quiz_choice_index += 1 # フォームのリセット用にインデックスをインクリメント

        # デバッグメッセージを更新 (セッション状態に保存し、常時表示)
        st.session_state.debug_message_quiz_start = f"DEBUG: 新しいクイズがロードされました: '{st.session_state.current_quiz['単語']}'"
        st.session_state.debug_message_answer_update = "" 
        st.session_state.debug_message_error = "" 
        st.session_state.debug_message_answer_end = "" 


    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """現在のクイズを表示し、ユーザーの回答を受け付けて処理します。"""
        current_quiz_data = st.session_state.current_quiz
        if not current_quiz_data:
            return

        st.subheader(f"問題: **{current_quiz_data['単語']}**")
        # 各種関連情報を表示（データに存在しない場合はN/A）
        st.write(f"🧩 **午後記述での使用例：** {current_quiz_data.get('午後記述での使用例', 'N/A')}")
        st.write(f"🎯 **使用理由／文脈：** {current_quiz_data.get('使用理由／文脈', 'N/A')}")
        st.write(f"🕘 **試験区分：** {current_quiz_data.get('試験区分', 'N/A')}")
        st.write(f"📈 **出題確率（推定）：** {current_quiz_data.get('出題確率（推定）', 'N/A')}　📝 **改定の意図・影響：** {current_quiz_data.get('改定の意図・影響', 'N/A')}")
        
        # クイズ回答フォーム
        with st.form(key=f"quiz_form_{st.session_state.quiz_choice_index}"):
            selected_option_text = st.radio(
                "説明を選択してください:",
                options=current_quiz_data["choices"],
                format_func=lambda x: f"{self.kana_labels[current_quiz_data['choices'].index(x)]}. {x}",
                key=f"quiz_radio_{st.session_state.quiz_choice_index}", # ラジオボタンのキーもフォームと連動
                disabled=st.session_state.quiz_answered # 回答済みの場合は無効化
            )
            submit_button = st.form_submit_button("✅ 答え合わせ", disabled=st.session_state.quiz_answered)

            # フォームが送信され、かつまだ回答されていない場合のみ処理
            if submit_button and not st.session_state.quiz_answered:
                st.session_state.debug_message_quiz_start = f"DEBUG: '答え合わせ' ボタンが押されました。選択肢='{selected_option_text}'"
                self._handle_answer_submission(selected_option_text, current_quiz_data)
                st.rerun() # 回答処理後、画面を更新して結果を表示

        # 回答後の結果表示とデバッグ情報
        if st.session_state.quiz_answered:
            st.markdown(f"### {st.session_state.latest_result}")
            if st.session_state.latest_result.startswith("❌"):
                st.info(f"正解は: **{st.session_state.latest_correct_description}** でした。")
            else:
                st.success(f"正解は: **{st.session_state.latest_correct_description}** でした！")
            
            # Geminiへの質問ボタン（単語でGoogle検索）
            current_word_encoded = current_quiz_data['単語'].replace(' ', '+') 
            st.markdown(
                f'<a href="https://www.google.com/search?q=Gemini+{current_word_encoded}" target="_blank">'
                f'<img src="https://www.gstatic.com/lamda/images/gemini_logo_lockup_eval_ja_og.svg" alt="Geminiに質問する" width="50">'
                f'</a>',
                unsafe_allow_html=True
            )
            
            # --- ここに、常に表示したいデバッグメッセージと統計情報ブロック ---
            st.markdown("---")
            st.subheader("現在のデバッグ情報（固定表示）")
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

            # 現在の単語の学習統計を表示
            current_word_stats_df = st.session_state.quiz_df[st.session_state.quiz_df['単語'] == current_quiz_data['単語']]
            if not current_word_stats_df.empty:
                st.write(f"**現在の単語の正解回数:** `{current_word_stats_df['正解回数'].iloc[0]}`")
                st.write(f"**現在の単語の不正解回数:** `{current_word_stats_df['不正解回数'].iloc[0]}`")
            else:
                st.write(f"**現在の単語の統計:** N/A (DataFrameに見つかりません)")
            
            st.markdown("---")
            # ------------------------------------------------------------------
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                # 「次の問題へ」ボタン
                if st.button("➡️ 次の問題へ", key=f"next_quiz_button_{st.session_state.quiz_choice_index}"):
                    st.session_state.current_quiz = None
                    st.session_state.quiz_answered = False # 回答済みフラグをリセット
                    st.rerun()
            with col2:
                # 「この単語をもう一度出題」ボタン
                if st.button("🔄 この単語をもう一度出題", key=f"retry_quiz_button_{st.session_state.quiz_choice_index}"):
                    st.session_state.quiz_answered = False # 回答済みフラグをリセット
                    st.rerun()

    def _handle_answer_submission(self, selected_option_text: str, current_quiz_data: dict):
        """ユーザーの回答を処理し、学習結果をデータフレームに反映させます。"""
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

        # DataFrameを更新するためにコピーを作成
        temp_df = st.session_state.quiz_df.copy(deep=True)
        
        word = current_quiz_data["単語"]
        idx_list = temp_df[temp_df["単語"] == word].index.tolist()
        
        if idx_list: # 単語が見つかった場合
            idx = idx_list[0] 
            
            temp_df.at[idx, '〇×結果'] = result_mark
            
            if is_correct:
                temp_df.at[idx, '正解回数'] += 1
            else:
                temp_df.at[idx, '不正解回数'] += 1
            
            temp_df.at[idx, '最終実施日時'] = datetime.datetime.now()
            temp_df.at[idx, '次回実施予定日時'] = datetime.datetime.now() 

            st.session_state.debug_message_answer_update = f"DEBUG: '{word}' の学習履歴を更新しました。正解回数={temp_df.at[idx, '正解回数']}, 不正解回数={temp_df.at[idx, '不正解回数']}"
            st.session_state.debug_message_error = "" # エラーがあればリセット
        else:
            st.session_state.debug_message_error = f"DEBUG: エラー - 単語 '{word}' がDataFrameに見つかりませんでした。"
            st.session_state.debug_message_answer_update = "" 

        st.session_state.quiz_df = temp_df # 更新されたDataFrameをセッションに保存

        st.session_state.quiz_answered = True
        st.session_state.debug_message_answer_end = f"DEBUG: _handle_answer_submission 終了。quiz_answered={st.session_state.quiz_answered}, total={st.session_state.total}, correct={st.session_state.correct}"

    def show_progress(self, df_filtered: pd.DataFrame):
        """学習の進捗状況をプログレスバーで表示します。"""
        st.subheader("学習の進捗")
        
        total_filtered_words = len(df_filtered)
        answered_filtered_words = len(df_filtered[df_filtered["単語"].isin(st.session_state.answered_words)])

        if total_filtered_words == 0:
            st.info("現在のフィルター条件に一致する単語がありません。")
            return

        progress_percent = (answered_filtered_words / total_filtered_words) if total_filtered_words > 0 else 0
        
        st.markdown(f"**<span style='font-size: 1.5em;'>回答済み: {answered_filtered_words} / {total_filtered_words} 単語</span>**", unsafe_allow_html=True)
        st.progress(progress_percent)

    def show_completion(self):
        """全ての単語を回答し終えた際に表示するメッセージです。"""
        st.success("🎉 おめでとうございます！現在のフィルター条件のすべての問題に回答しました！")
        st.write(f"合計 {st.session_state.total} 問中、{st.session_state.correct} 問正解しました。")
        if st.session_state.total > 0:
            st.write(f"正答率: {st.session_state.correct / st.session_state.total * 100:.2f}%")
        else:
            st.write("まだ問題に回答していません。")

    def display_statistics(self):
        """単語ごとの正解・不正解回数、最終実施日時などの学習統計を表示します。"""
        st.subheader("単語ごとの学習統計")
        
        # 表示するカラムを明示的に指定（アップロードデータにないカラムは自動で除外）
        display_cols = ['単語', '説明', 'カテゴリ', '分野', 'シラバス改定有無', 
                        '正解回数', '不正解回数', '〇×結果', '最終実施日時', '次回実施予定日時']
        
        cols_to_display = [col for col in display_cols if col in st.session_state.quiz_df.columns]
        display_df = st.session_state.quiz_df[cols_to_display].copy()
        
        # 回答履歴のある単語のみを抽出して表示し、不正解回数などでソート
        display_df = display_df[
            (display_df['正解回数'] > 0) | (display_df['不正解回数'] > 0)
        ].sort_values(by=['不正解回数', '正解回数', '最終実施日時'], ascending=[False, False, False])
        
        if not display_df.empty:
            # 表示用に日時フォーマットを適用（NaTは空文字列に変換）
            if '最終実施日時' in display_df.columns:
                display_df['最終実施日時'] = display_df['最終実施日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            if '次回実施予定日時' in display_df.columns:
                display_df['次回実施予定日時'] = display_df['次回実施予定日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("まだ回答履歴のある単語はありません。")

    def offer_download(self):
        """現在の学習データをCSVファイルとしてダウンロードするボタンを提供します。"""
        now = datetime.datetime.now()
        file_name = f"tango_learning_data_{now.strftime('%Y%m%d_%H%M%S')}.csv"

        # ダウンロード用に日時フォーマットを適用（NaTは空文字列に変換）
        df_to_save = st.session_state.quiz_df.copy(deep=True) 
        if '最終実施日時' in df_to_save.columns:
            df_to_save['最終実施日時'] = df_to_save['最終実施日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        if '次回実施予定日時' in df_to_save.columns:
            df_to_save['次回実施予定日時'] = df_to_save['次回実施予定日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

        csv_quiz_data = df_to_save.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 **現在の学習データをダウンロード**", data=csv_quiz_data, file_name=file_name, mime="text/csv")

    def upload_data(self):
        """ユーザーがCSVファイルをアップロードする機能を提供します。
        アップロードされたデータは一時的に保存され、ラジオボタンで選択された場合にアクティブになります。
        """
        uploaded_file = st.sidebar.file_uploader("⬆️ **CSVファイルをアップロード**", type=["csv"], key="uploader") 
        
        if uploaded_file is not None:
            try:
                # ファイル名とサイズで、新しいファイルがアップロードされたかチェック
                if st.session_state.uploaded_file_name != uploaded_file.name or \
                   st.session_state.get('uploaded_file_size') != uploaded_file.size: 
                    
                    uploaded_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
                    
                    # 必須カラムのチェック
                    required_core_cols = ["単語", "説明", "カテゴリ", "分野"]
                    missing_core_cols = [col for col in required_core_cols if col not in uploaded_df.columns]
                    if missing_core_cols:
                        st.error(f"アップロードされたCSVには、以下の**必須カラム**が不足しています: {', '.join(missing_core_cols)}。")
                        st.info("これらはクイズの出題に不可欠な情報です。正しい形式のCSVファイルをアップロードしてください。")
                        # エラー時は一時データとファイル情報をクリア
                        st.session_state.uploaded_df_temp = None
                        st.session_state.uploaded_file_name = None
                        st.session_state.uploaded_file_size = None
                        return

                    # データを処理し、一時データとして保存
                    processed_uploaded_df = self._process_df_types(uploaded_df.copy(deep=True))
                    st.session_state.uploaded_df_temp = processed_uploaded_df
                    st.session_state.uploaded_file_name = uploaded_file.name 
                    st.session_state.uploaded_file_size = uploaded_file.size 
                    st.sidebar.success(f"✅ ファイル '{uploaded_file.name}' を一時的に読み込みました。")
                    st.rerun() # 画面更新

            except Exception as e:
                st.sidebar.error(f"CSVファイルの読み込み中にエラーが発生しました。ファイル形式が正しいか確認してください: {e}")
                # エラー時は一時データとファイル情報をクリア
                st.session_state.uploaded_df_temp = None
                st.session_state.uploaded_file_name = None
                st.session_state.uploaded_file_size = None
                st.rerun() # エラーメッセージ表示のために再実行

# Streamlitアプリのメイン関数
def main():
    st.set_page_config(layout="wide", page_title="IT用語クイズアプリ", page_icon="📝")

    # tango.csvファイルの存在チェックと読み込み
    csv_path = os.path.join(os.path.dirname(__file__), 'tango.csv')
    if not os.path.exists(csv_path):
        st.error(f"エラー: tango.csv が見つかりません。パス: {csv_path}")
        st.stop()

    try:
        original_df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"初期データの読み込み中にエラーが発生しました: {e}")
        st.stop()

    # QuizAppインスタンスの作成
    quiz_app = QuizApp(original_df)

    # アプリのタイトルと説明
    st.title("📝 IT用語クイズアプリ")
    st.markdown("毎日少しずつIT用語を学習し、知識を定着させましょう！")

    # サイドバーのセクション
    st.sidebar.header("設定とデータ")
    
    # --- データソース選択ラジオボタン ---
    # ラジオボタンのオプション（短縮版）
    data_source_options_radio = ["アップロード", "初期データ"]
    selected_source_radio = st.sidebar.radio(
        "📚 **使用するデータソースを選択**",
        options=data_source_options_radio,
        key="main_data_source_radio",
        index=data_source_options_radio.index(st.session_state.data_source_selection) if st.session_state.data_source_selection in data_source_options_radio else 0
    )

    # ラジオボタンの選択が変更された場合の処理
    if selected_source_radio != st.session_state.data_source_selection:
        st.session_state.data_source_selection = selected_source_radio
        
        if st.session_state.data_source_selection == "初期データ":
            # 初期データに切り替え
            quiz_app._initialize_quiz_df_from_original()
            st.sidebar.success("✅ 初期データに切り替えました。")
            # アップロード関連の一時データをクリア
            st.session_state.uploaded_df_temp = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
        else: # "アップロード"が選択された場合
            # アップロード済みの一時データがあればそれを適用
            if st.session_state.uploaded_df_temp is not None:
                st.session_state.quiz_df = st.session_state.uploaded_df_temp.copy()
                # アップロードデータに基づいて回答済み単語セットを更新
                st.session_state.answered_words = set(st.session_state.quiz_df[
                    (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
                ]["単語"].tolist())
                st.sidebar.success(f"✅ アップロードされたデータ ({st.session_state.uploaded_file_name}) を適用しました。")
            else:
                # アップロードがまだ行われていない場合のメッセージ
                st.sidebar.info("ファイルをアップロードしてください。")
                # quiz_dfが空にならないように、一時的に初期データをロードしておく
                quiz_app._initialize_quiz_df_from_original() 
                # 選択状態も「初期データ」に戻す（ユーザーにアップロードを促すため）
                st.session_state.data_source_selection = "初期データ" 
                st.rerun() # 変更を反映

        # データソース切り替え時はクイズセッションの進捗をリセット
        # （デバッグメッセージはリセットしない）
        for key in ["total", "correct", "latest_result", "latest_correct_description",
                    "current_quiz", "quiz_answered", "quiz_choice_index",
                    "filter_category", "filter_field", "filter_level"]:
            if key in quiz_app.defaults:
                st.session_state[key] = quiz_app.defaults[key] if not isinstance(quiz_app.defaults[key], set) else set()
        
        st.rerun() # データソース切り替え後、画面全体を再描画

    st.sidebar.markdown("---")

    # データソースの選択に応じてUIを出し分け
    if st.session_state.data_source_selection == "アップロード":
        quiz_app.upload_data() # アップロードUIを表示
        if st.session_state.uploaded_df_temp is None:
            st.sidebar.warning("まだ学習データがアップロードされていません。上記からCSVファイルをアップロードしてください。")
    else: # "初期データ" が選択されている場合
        st.sidebar.info("`tango.csv` (初期データ) を使用しています。")
    
    st.sidebar.markdown("---")

    # ダウンロードボタンの配置
    quiz_app.offer_download()

    st.sidebar.markdown("---")
    # 学習履歴リセットボタン
    if st.sidebar.button("🔄 **現在のデータの学習履歴をリセット**", help="現在使用しているデータソースの学習の進捗（正解/不正解回数、回答済み単語）を初期状態に戻します。", key="reset_button"):
        quiz_app._reset_session_state()

    st.sidebar.markdown("---")
    st.sidebar.header("クイズの絞り込み")
    # quiz_dfが有効な場合にのみフィルターを表示
    if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
        df_filtered, remaining_df = quiz_app.filter_data()
    else:
        st.sidebar.warning("有効な学習データがロードされていません。")
        df_filtered = pd.DataFrame()
        remaining_df = pd.DataFrame()

    st.sidebar.markdown("---")

    # 学習進捗の表示
    quiz_app.show_progress(df_filtered)

    # クイズ開始ロジック
    if st.session_state.quiz_df.empty:
        st.info("クイズを開始するには、まず有効な学習データをロードしてください。")
    elif st.session_state.current_quiz is None: 
        if len(df_filtered) > 0 and len(remaining_df) > 0: # 出題可能な単語がある場合
            st.info("データがロードされました！下のボタンをクリックしてクイズを開始してください。")
            if st.button("▶️ クイズを開始する", key="start_quiz_button"):
                quiz_app.load_quiz(df_filtered, remaining_df)
                st.rerun() 
        elif len(df_filtered) > 0 and len(remaining_df) == 0: # 全て回答済みの場合
            quiz_app.show_completion()
        else: # フィルター条件に一致する単語がない場合
            st.info("現在のフィルター条件に一致する単語がないか、データがありません。フィルターを変更するか、新しいデータをアップロードしてください。")
    else: # 現在のクイズがある場合
        quiz_app.display_quiz(df_filtered, remaining_df)
    
    st.markdown("---")
    # 学習統計の表示
    if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
        quiz_app.display_statistics()

if __name__ == "__main__":
    main()
