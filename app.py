import streamlit as st
import pandas as pd
import random
import os
import datetime

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
            "quiz_answered": False, # 回答済みかどうかのフラグ
            "quiz_choice_index": 0, # Streamlitのフォームのキーをユニークにするためのインデックス
            "quiz_df": None, # メインの学習データ
            "filter_category": "すべて",
            "filter_field": "すべて",
            "filter_level": "すべて", # 'シラバス改定有無'フィルター用
        }
        self._initialize_session()
        
        # initial_dfはtango.csvの初期データ（テンプレート）として保持
        # これは_reset_session_stateでquiz_dfを初期状態に戻す際に使用
        self.initial_df = self._process_df_types(original_df.copy())

        # アプリ起動時、またはアップロードがない場合に初期データを設定
        if st.session_state.quiz_df is None:
            self._initialize_quiz_df_from_original()

    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameに対して、必要なカラムの型変換と初期化を適用します。
        初期データ読み込み時とアップロードデータ読み込み時の両方で使用します。
        """
        
        # 〇×結果カラムの初期化またはクリーンアップ
        if '〇×結果' not in df.columns:
            df['〇×結果'] = ''
        else:
            df['〇×結果'] = df['〇×結果'].astype(str).replace('nan', '')

        # 数値カラムの型変換を堅牢に
        for col in ['正解回数', '不正解回数']:
            if col not in df.columns:
                df[col] = 0
            else:
                # 数値に変換できないものはNaNとなり、fillna(0)で0に
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # 日時カラムの型変換を堅牢に
        for col in ['最終実施日時', '次回実施予定日時']:
            if col not in df.columns:
                df[col] = pd.NaT # Not a Time (PandasのdatetimeのNaN)
            else:
                # 日時に変換できないものはNaTに
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # シラバス改定有無カラムの初期化 (必要であれば)
        if 'シラバス改定有無' not in df.columns:
            df['シラバス改定有無'] = ''
        else:
            df['シラバス改定有無'] = df['シラバス改定有無'].astype(str).replace('nan', '')
            
        # その他の必須ではないが、データに存在する可能性のあるカラムの処理
        if '午後記述での使用例' not in df.columns: df['午後記述での使用例'] = ''
        if '使用理由／文脈' not in df.columns: df['使用理由／文脈'] = ''
        if '試験区分' not in df.columns: df['試験区分'] = ''
        if '出題確率（推定）' not in df.columns: df['出題確率（推定）'] = ''
        if '改定の意図・影響' not in df.columns: df['改定の意図・影響'] = ''

        return df

    def _initialize_session(self):
        """セッション状態をデフォルト値で初期化します。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            # answered_wordsがセット型であることを保証
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _initialize_quiz_df_from_original(self):
        """アプリ起動時またはリセット時にinitial_dfからquiz_dfを初期化します。"""
        st.session_state.quiz_df = self.initial_df.copy()
        
        # 回答済み単語セットも初期化 (回答回数が0でない単語)
        st.session_state.answered_words = set(st.session_state.quiz_df[
            (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
        ]["単語"].tolist())

    def _reset_session_state(self):
        """セッション状態をデフォルト値にリセットし、quiz_dfをinitial_dfに戻します。"""
        # まずquiz_dfをinitial_dfの内容で初期化
        self._initialize_quiz_df_from_original() 
        
        # その他のセッション状態をデフォルトに戻す
        for key, val in self.defaults.items():
            if key not in ["quiz_df", "filter_category", "filter_field", "filter_level"]: # quiz_dfとフィルターは後で適切に設定
                st.session_state[key] = val if not isinstance(val, set) else set()
        st.session_state.filter_category = "すべて"
        st.session_state.filter_field = "すべて"
        st.session_state.filter_level = "すべて"
        st.session_state.current_quiz = None # 現在のクイズをリセット
        st.session_state.quiz_answered = False # 回答済みフラグをリセット
        st.session_state.quiz_choice_index = 0 # フォームのキーもリセット

        st.success("✅ セッションをリセットし、学習データを初期化しました。")
        st.rerun()

    def filter_data(self):
        """データフレームをフィルターし、残りの単語を返します。"""
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

        # 回答済みの単語を除外して、まだ出題されていない単語のリストを作成
        remaining_df = df[~df["単語"].isin(st.session_state.answered_words)]

        return df, remaining_df

    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズの単語をロードします。不正解回数や最終実施日時を考慮します。"""
        # load_quizが呼ばれる前にquiz_answeredがFalseになっていることを確認
        if st.session_state.quiz_answered: 
            st.session_state.quiz_answered = False 
            st.session_state.quiz_choice_index += 1 # フォームのリセットも確実に行う

        quiz_candidates_df = pd.DataFrame() # 出題候補のDataFrame

        # 1. 不正解回数が多く、かつ回答履歴がある単語を優先的に候補に入れる
        answered_and_struggled = df_filtered[
            (df_filtered["単語"].isin(st.session_state.answered_words)) &
            (df_filtered["不正解回数"] > df_filtered["正解回数"])
        ].copy()

        if not answered_and_struggled.empty:
            answered_and_struggled['temp_weight'] = answered_and_struggled['不正解回数'] + 1
            quiz_candidates_df = pd.concat([quiz_candidates_df, answered_and_struggled], ignore_index=True)

        # 2. まだ出題されていない単語を候補に入れる
        if not remaining_df.empty:
            remaining_df_copy = remaining_df.copy()
            remaining_df_copy['temp_weight'] = 1 # まだ出題されていない単語の重み
            quiz_candidates_df = pd.concat([quiz_candidates_df, remaining_df_copy], ignore_index=True)
            
        # 重複する単語がある場合、不正解回数が多い方を優先するためにソート
        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')

        if quiz_candidates_df.empty:
            st.info("現在のフィルター条件に一致する単語がないか、すべての単語を回答しました！フィルターを変更するか、学習データをリセットしてください。")
            st.session_state.current_quiz = None
            return

        weights = quiz_candidates_df['temp_weight'].tolist()
        
        if sum(weights) == 0: # 全ての重みが0の場合、ランダムに選択 (エラー回避)
            selected_quiz_row = quiz_candidates_df.sample(n=1).iloc[0]
        else:
            selected_quiz_row = quiz_candidates_df.sample(n=1, weights=weights).iloc[0]

        st.session_state.current_quiz = selected_quiz_row.to_dict()

        correct_description = st.session_state.current_quiz["説明"]
        
        # quiz_df全体から、現在の問題の「説明」と異なる説明文を抽出
        # まずユニークな説明文のリストを取得
        all_descriptions = st.session_state.quiz_df["説明"].unique().tolist()
        
        # 正しい説明文を除外
        other_descriptions = [desc for desc in all_descriptions if desc != correct_description]
        
        # 間違った選択肢の数を調整
        num_wrong_choices = min(3, len(other_descriptions))
        
        # 間違った選択肢をランダムに選択
        wrong_choices = random.sample(other_descriptions, num_wrong_choices)

        choices = wrong_choices + [correct_description]
        random.shuffle(choices)
        st.session_state.current_quiz["choices"] = choices
        
        # load_quizが呼ばれるたびにquiz_choice_indexをインクリメントし、フォームのキーをユニークにする
        st.session_state.quiz_choice_index += 1 

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
        
        # フォームのキーに quiz_choice_index を含めて、問題が変わるたびにフォームをリセット
        with st.form(key=f"quiz_form_{st.session_state.quiz_choice_index}"):
            selected_option_text = st.radio(
                "説明を選択してください:",
                options=current_quiz_data["choices"],
                format_func=lambda x: f"{self.kana_labels[current_quiz_data['choices'].index(x)]}. {x}",
                key=f"quiz_radio_{st.session_state.quiz_choice_index}", # ラジオボタンのキーもフォームのキーと連動
                disabled=st.session_state.quiz_answered # 回答済みの場合は無効化
            )
            submit_button = st.form_submit_button("✅ 答え合わせ", disabled=st.session_state.quiz_answered)

            # デバッグ出力: ボタンが押されたことを確認
            if submit_button:
                st.write(f"DEBUG: '答え合わせ' ボタンが押されました。quiz_answered={st.session_state.quiz_answered}")

            # フォームが送信され、かつまだ回答されていない場合のみ処理
            if submit_button and not st.session_state.quiz_answered:
                self._handle_answer_submission(selected_option_text, current_quiz_data)
                st.rerun() # 回答処理後、画面を更新して結果を表示

        if st.session_state.quiz_answered:
            st.markdown(f"### {st.session_state.latest_result}")
            if st.session_state.latest_result.startswith("❌"):
                st.info(f"正解は: **{st.session_state.latest_correct_description}** でした。")
            else:
                st.success(f"正解は: **{st.session_state.latest_correct_description}** でした！")
            
            # Geminiへの質問ボタン
            st.markdown(
                f'<a href="https://www.google.com/search?q=Gemini+%E3%81%A8%E3%81%AF" target="_blank">'
                f'<img src="https://www.gstatic.com/lamda/images/gemini_logo_lockup_eval_ja_og.svg" alt="Geminiに質問する" width="50">'
                f'</a>',
                unsafe_allow_html=True
            )
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                # 「次の問題へ」ボタンが押されたら、quiz_answeredをリセットして次の問題をロード
                if st.button("➡️ 次の問題へ", key=f"next_quiz_button_{st.session_state.quiz_choice_index}"):
                    st.session_state.current_quiz = None
                    st.session_state.quiz_answered = False # 回答済みフラグをリセット
                    st.rerun()
            with col2:
                # 「この単語をもう一度出題」ボタンもquiz_answeredをリセット
                if st.button("🔄 この単語をもう一度出題", key=f"retry_quiz_button_{st.session_state.quiz_choice_index}"):
                    st.session_state.quiz_answered = False # 回答済みフラグをリセット
                    st.rerun()

    def _handle_answer_submission(self, selected_option_text: str, current_quiz_data: dict):
        """ユーザーの回答を処理し、結果を更新します。"""
        st.write(f"DEBUG: _handle_answer_submission 開始。選択肢='{selected_option_text}'")

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

        # DataFrameのコピーをdeep=Trueで確実に行う
        temp_df = st.session_state.quiz_df.copy(deep=True)
        
        word = current_quiz_data["単語"]
        # quiz_df内の該当単語のインデックスを見つける
        idx_list = temp_df[temp_df["単語"] == word].index.tolist()
        
        if idx_list: # 単語が見つかった場合
            idx = idx_list[0] # 最初のマッチを使用
            
            temp_df.at[idx, '〇×結果'] = result_mark
            
            if is_correct:
                temp_df.at[idx, '正解回数'] += 1
            else:
                temp_df.at[idx, '不正解回数'] += 1
            
            temp_df.at[idx, '最終実施日時'] = datetime.datetime.now()
            # 次回実施予定日時は、今回は最終実施日時と同じに設定（間隔学習などのロジックは別途実装が必要）
            temp_df.at[idx, '次回実施予定日時'] = datetime.datetime.now() 

            st.write(f"DEBUG: '{word}' の学習履歴を更新しました。正解回数={temp_df.at[idx, '正解回数']}, 不正解回数={temp_df.at[idx, '不正解回数']}")
        else:
            st.write(f"DEBUG: エラー - 単語 '{word}' がDataFrameに見つかりませんでした。")


        st.session_state.quiz_df = temp_df # 更新されたDataFrameをセッションに保存

        st.session_state.quiz_answered = True
        st.write(f"DEBUG: _handle_answer_submission 終了。quiz_answered={st.session_state.quiz_answered}, total={st.session_state.total}, correct={st.session_state.correct}")

    def show_progress(self, df_filtered: pd.DataFrame):
        """学習の進捗を表示します。"""
        st.subheader("学習の進捗")
        
        total_filtered_words = len(df_filtered)
        answered_filtered_words = len(df_filtered[df_filtered["単語"].isin(st.session_state.answered_words)])

        if total_filtered_words == 0:
            st.info("現在のフィルター条件に一致する単語がありません。")
            return

        progress_percent = (answered_filtered_words / total_filtered_words) if total_filtered_words > 0 else 0
        
        # プログレスバーの上のテキストを大きく表示
        st.markdown(f"**<span style='font-size: 1.5em;'>回答済み: {answered_filtered_words} / {total_filtered_words} 単語</span>**", unsafe_allow_html=True)
        st.progress(progress_percent) # プログレスバー自体はシンプルに表示

    def show_completion(self):
        """すべての問題が終了した際に表示するメッセージ。"""
        st.success("🎉 おめでとうございます！すべての問題に回答しました！")
        st.write(f"合計 {st.session_state.total} 問中、{st.session_state.correct} 問正解しました。")
        st.write(f"正答率: {st.session_state.correct / st.session_state.total * 100:.2f}%")

    def display_statistics(self):
        """単語ごとの正解・不正解回数と日時情報を表示します。"""
        st.subheader("単語ごとの学習統計")
        
        # 表示するカラムを明示的に指定
        display_cols = ['単語', '説明', 'カテゴリ', '分野', 'シラバス改定有無', 
                        '正解回数', '不正解回数', '〇×結果', '最終実施日時', '次回実施予定日時']
        
        # quiz_dfにあるカラムのみを抽出して表示 (アップロードデータによっては全カラムがない場合があるため)
        cols_to_display = [col for col in display_cols if col in st.session_state.quiz_df.columns]
        display_df = st.session_state.quiz_df[cols_to_display].copy()
        
        # 回答履歴のある単語のみ表示、またはすべての単語を表示するか選択肢を設けることも可能だが、今回は回答履歴のみ
        display_df = display_df[
            (display_df['正解回数'] > 0) | (display_df['不正解回数'] > 0)
        ].sort_values(by=['不正解回数', '正解回数', '最終実施日時'], ascending=[False, False, False])
        
        if not display_df.empty:
            # 表示用に日時フォーマットを適用、既にNaTであれば空文字列になる
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

        # ダウンロード用に日時フォーマットを適用、既にNaTであれば空文字列になる
        df_to_save = st.session_state.quiz_df.copy(deep=True) # deep=Trueで完全なコピーを確保
        if '最終実施日時' in df_to_save.columns:
            df_to_save['最終実施日時'] = df_to_save['最終実施日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        if '次回実施予定日時' in df_to_save.columns:
            df_to_save['次回実施予定日時'] = df_to_save['次回実施予定日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

        csv_quiz_data = df_to_save.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 **現在の学習データをダウンロード**", data=csv_quiz_data, file_name=file_name, mime="text/csv")

    def upload_data(self):
        """ユーザーがCSVファイルをアップロードする機能を提供します。"""
        uploaded_file = st.sidebar.file_uploader("⬆️ **学習データをアップロードして再開**", type=["csv"])
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
                
                # アップロードされたCSVに必要な必須カラムが含まれているかチェック
                required_core_cols = ["単語", "説明", "カテゴリ", "分野"]
                missing_core_cols = [col for col in required_core_cols if col not in uploaded_df.columns]
                if missing_core_cols:
                    st.error(f"アップロードされたCSVには、以下の**必須カラム**が不足しています: {', '.join(missing_core_cols)}。")
                    st.info("これらはクイズの出題に不可欠な情報です。正しい形式のCSVファイルをアップロードしてください。")
                    return

                # アップロードされたDataFrameに型変換を適用し、不足する学習履歴カラムを初期化
                processed_uploaded_df = self._process_df_types(uploaded_df.copy(deep=True))
                
                st.session_state.quiz_df = processed_uploaded_df
                
                # アップロードされたデータに基づいてanswered_wordsを更新
                st.session_state.answered_words = set(st.session_state.quiz_df[
                    (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
                ]["単語"].tolist())

                # その他のセッション状態をリセットし、新しいデータでクイズを再開
                st.session_state.total = 0
                st.session_state.correct = 0
                st.session_state.latest_result = ""
                st.session_state.latest_correct_description = ""
                st.session_state.current_quiz = None
                st.session_state.quiz_answered = False
                st.session_state.quiz_choice_index = 0
                st.session_state.filter_category = "すべて"
                st.session_state.filter_field = "すべて"
                st.session_state.filter_level = "すべて"

                st.success("✅ 学習データを正常にアップロードしました！")
                st.rerun()

            except Exception as e:
                st.error(f"CSVファイルの読み込み中にエラーが発生しました。ファイル形式が正しいか確認してください: {e}")

# Streamlitアプリのメイン部分
def main():
    st.set_page_config(layout="wide", page_title="IT用語クイズアプリ", page_icon="📝")

    # CSVファイルがapp.pyと同じディレクトリに存在することを確認
    csv_path = os.path.join(os.path.dirname(__file__), 'tango.csv') # ここを修正しました！
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

    # サイドバーのコントロール
    st.sidebar.header("設定とデータ")
    quiz_app.offer_download() # ダウンロードボタンをサイドバーに配置
    quiz_app.upload_data() # アップロード機能をサイドバーに配置
    if st.sidebar.button("🔄 **学習履歴をリセット**", help="現在の学習の進捗（正解/不正解回数、回答済み単語）を初期状態に戻します。", key="reset_button"):
        quiz_app._reset_session_state()

    st.sidebar.markdown("---")
    st.sidebar.header("クイズの絞り込み")
    df_filtered, remaining_df = quiz_app.filter_data()

    st.sidebar.markdown("---")

    quiz_app.show_progress(df_filtered)

    if st.session_state.current_quiz is None and not st.session_state.quiz_answered:
        quiz_app.load_quiz(df_filtered, remaining_df)
    
    if st.session_state.current_quiz:
        quiz_app.display_quiz(df_filtered, remaining_df)
    elif len(df_filtered) > 0 and len(remaining_df) == 0:
        quiz_app.show_completion() # 全ての単語を回答した場合
    
    st.markdown("---")
    quiz_app.display_statistics()

if __name__ == "__main__":
    main()
