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
            "quiz_answered": False,
            "quiz_choice_index": 0,
            "quiz_df": None,
            "filter_category": "すべて",
            "filter_field": "すべて",
            "filter_level": "すべて", # 'シラバス改定有無'フィルター用
        }
        self._initialize_session()
        
        self.initial_df = original_df.copy() # 元のDFを保持

        # アプリ起動時、またはアップロードがない場合に初期データを設定
        if st.session_state.quiz_df is None:
            self._initialize_quiz_df_from_original()

    def _initialize_session(self):
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _initialize_quiz_df_from_original(self):
        """元のDataFrameからquiz_dfを初期化し、必要な列を追加します。"""
        st.session_state.quiz_df = self.initial_df.copy()
        
        # 既存の〇×結果, 正解回数, 不正解回数の初期化
        if '〇×結果' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['〇×結果'] = ''
        else:
            st.session_state.quiz_df['〇×結果'] = st.session_state.quiz_df['〇×結果'].astype(str).replace('nan', '')

        # 数値型への変換をより堅牢に
        if '正解回数' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['正解回数'] = 0
        else:
            st.session_state.quiz_df['正解回数'] = pd.to_numeric(st.session_state.quiz_df['正解回数'], errors='coerce').fillna(0).astype(int)

        if '不正解回数' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['不正解回数'] = 0
        else:
            st.session_state.quiz_df['不正解回数'] = pd.to_numeric(st.session_state.quiz_df['不正解回数'], errors='coerce').fillna(0).astype(int)
        
        # 新しい日時カラムの初期化
        if '最終実施日時' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['最終実施日時'] = pd.NaT # Not a Time (PandasのdatetimeのNaN)
        else:
            # CSVからの読み込み時に文字列として入ってくる可能性があるので変換
            st.session_state.quiz_df['最終実施日時'] = pd.to_datetime(st.session_state.quiz_df['最終実施日時'], errors='coerce')
        
        if '次回実施予定日時' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['次回実施予定日時'] = pd.NaT
        else:
            # CSVからの読み込み時に文字列として入ってくる可能性があるので変換
            st.session_state.quiz_df['次回実施予定日時'] = pd.to_datetime(st.session_state.quiz_df['次回実施予定日時'], errors='coerce')

        # 回答済み単語セットも初期化 (回答回数が0でない単語)
        st.session_state.answered_words = set(st.session_state.quiz_df[
            (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
        ]["単語"].tolist())

    def _reset_session_state(self):
        """セッション状態をデフォルト値にリセットします。"""
        self._initialize_quiz_df_from_original() # quiz_dfを初期状態に戻す
        
        for key, val in self.defaults.items():
            if key not in ["quiz_df", "filter_category", "filter_field", "filter_level"]:
                st.session_state[key] = val if not isinstance(val, set) else set()
        st.session_state.filter_category = "すべて"
        st.session_state.filter_field = "すべて"
        st.session_state.filter_level = "すべて" # 'シラバス改定有無'フィルターもリセット

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
        if st.session_state.quiz_answered:
            st.session_state.quiz_answered = False # 回答済みのフラグをリセット

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
            remaining_df_copy['temp_weight'] = 1
            quiz_candidates_df = pd.concat([quiz_candidates_df, remaining_df_copy], ignore_index=True)
            
        # 重複する単語がある場合、不正解回数が多い方を優先するためにソート
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
        other_descriptions = st.session_state.quiz_df[st.session_state.quiz_df["説明"] != correct_description]["説明"].unique().tolist()
        
        num_wrong_choices = min(3, len(other_descriptions))
        wrong_choices = random.sample(other_descriptions, num_wrong_choices)

        choices = wrong_choices + [correct_description]
        random.shuffle(choices)
        st.session_state.current_quiz["choices"] = choices
        
        st.session_state.quiz_choice_index = 0

    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズを表示し、ユーザーの回答を処理します。"""
        current_quiz_data = st.session_state.current_quiz
        if not current_quiz_data:
            return

        st.subheader(f"問題: **{current_quiz_data['単語']}**")
        st.write(f"🧩 **午後記述での使用例：** {current_quiz_data.get('午後記述での使用例', 'N/A')}")
        st.write(f"🎯 **使用理由／文脈：** {current_quiz_data.get('使用理由／文脈', 'N/A')}")
        st.write(f"🕘 **試験区分：** {current_quiz_data.get('試験区分', 'N/A')}")
        st.write(f"📈 **出題確率（推定）：：** {current_quiz_data.get('出題確率（推定）', 'N/A')}　📝 **改定の意図・影響：** {current_quiz_data.get('改定の意図・影響', 'N/A')}")
        
        with st.form("quiz_form"):
            selected_option_text = st.radio(
                "説明を選択してください:",
                options=current_quiz_data["choices"],
                format_func=lambda x: f"{self.kana_labels[current_quiz_data['choices'].index(x)]}. {x}",
                key=f"quiz_radio_{st.session_state.total}",
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
            
            # Geminiへの質問ボタン
            st.markdown(
                f'<a href="https://gemini.google.com/" target="_blank">'
                f'<img src="https://www.gstatic.com/lamda/images/gemini_logo_lockup_eval_ja_og.svg" alt="Geminiに質問する" width="50">'
                f'</a>',
                unsafe_allow_html=True
            )
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➡️ 次の問題へ"):
                    st.session_state.current_quiz = None
                    st.session_state.quiz_answered = False
                    st.rerun()
            with col2:
                if st.button("🔄 この単語をもう一度出題"):
                    st.session_state.quiz_answered = False
                    st.rerun()

    def _handle_answer_submission(self, selected_option_text: str, current_quiz_data: dict):
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

        temp_df = st.session_state.quiz_df.copy()
        
        word = current_quiz_data["単語"]
        if word in temp_df["単語"].values:
            idx = temp_df[temp_df["単語"] == word].index[0]
            
            temp_df.at[idx, '〇×結果'] = result_mark
            
            if is_correct:
                temp_df.at[idx, '正解回数'] += 1
            else:
                temp_df.at[idx, '不正解回数'] += 1
            
            temp_df.at[idx, '最終実施日時'] = datetime.datetime.now()
            temp_df.at[idx, '次回実施予定日時'] = datetime.datetime.now() 

        st.session_state.quiz_df = temp_df

        st.session_state.quiz_answered = True

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
        
        display_df = st.session_state.quiz_df[['単語', '正解回数', '不正解回数', '〇×結果', '最終実施日時', '次回実施予定日時']].copy()
        
        display_df = display_df[
            (display_df['正解回数'] > 0) | (display_df['不正解回数'] > 0)
        ].sort_values(by=['不正解回数', '正解回数', '最終実施日時'], ascending=[False, False, False])
        
        if not display_df.empty:
            display_df['最終実施日時'] = display_df['最終実施日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            display_df['次回実施予定日時'] = display_df['次回実施予定日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("まだ回答履歴のある単語はありません。")

    def offer_download(self):
        """現在の学習データのCSVダウンロードボタンを提供します。"""
        now = datetime.datetime.now()
        file_name = f"tango_learning_data_{now.strftime('%Y%m%d_%H%M%S')}.csv"

        df_to_save = st.session_state.quiz_df.copy()
        df_to_save['最終実施日時'] = df_to_save['最終実施日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        df_to_save['次回実施予定日時'] = df_to_save['次回実施予定日時'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

        csv_quiz_data = df_to_save.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 **現在の学習データをダウンロード**", data=csv_quiz_data, file_name=file_name, mime="text/csv")

    def upload_data(self):
        """ユーザーがCSVファイルをアップロードする機能を提供します。"""
        uploaded_file = st.sidebar.file_uploader("⬆️ **学習データをアップロードして再開**", type=["csv"])
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
                
                required_cols = ["単語", "説明", "カテゴリ", "分野", "正解回数", "不正解回数", "〇×結果", "最終実施日時", "次回実施予定日時"]
                missing_cols = [col for col in required_cols if col not in uploaded_df.columns]
                if missing_cols:
                    st.error(f"アップロードされたCSVには、以下の必要なカラムが不足しています: {', '.join(missing_cols)}。正しい学習データCSVをアップロードしてください。")
                    return

                merged_df = self.initial_df.set_index('単語').copy()
                uploaded_df_for_merge = uploaded_df.set_index('単語')
                
                update_cols = ['〇×結果', '正解回数', '不正解回数', '最終実施日時', '次回実施予定日時']
                
                # アップロードされたデータの型変換をより頑健に
                for col in ['正解回数', '不正解回数']:
                    if col in uploaded_df_for_merge.columns:
                        uploaded_df_for_merge[col] = pd.to_numeric(uploaded_df_for_merge[col], errors='coerce').fillna(0).astype(int)
                
                for col in ['最終実施日時', '次回実施予定日時']:
                    if col in uploaded_df_for_merge.columns:
                        uploaded_df_for_merge[col] = pd.to_datetime(uploaded_df_for_merge[col], errors='coerce')


                merged_df.update(uploaded_df_for_merge[update_cols])
                
                final_df = merged_df.reset_index()

                # 最終的なDataFrameの型も再確認
                final_df['〇×結果'] = final_df['〇×結果'].astype(str).replace('nan', '')
                final_df['正解回数'] = pd.to_numeric(final_df['正解回数'], errors='coerce').fillna(0).astype(int)
                final_df['不正解回数'] = pd.to_numeric(final_df['不正解回数'], errors='coerce').fillna(0).astype(int)
                
                final_df['最終実施日時'] = pd.to_datetime(final_df['最終実施日時'], errors='coerce')
                final_df['次回実施予定日時'] = pd.to_datetime(final_df['次回実施予定日時'], errors='coerce')

                st.session_state.quiz_df = final_df
                
                st.session_state.answered_words = set(st.session_state.quiz_df[
                    (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
                ]["単語"].tolist())

                st.success("✅ 学習データを正常にロードしました！")
                st.rerun()
            except Exception as e:
                st.error(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
                st.info("ファイルが正しいCSV形式であるか、またはエンコーディングが 'utf-8-sig' であるか確認してください。")
                st.info("特に '正解回数' や '不正解回数' カラムに、数値以外の文字や空欄がないかご確認ください。")


    def reset_session_button(self):
        """セッションリセットボタンを表示します。"""
        if st.sidebar.button("🔄 **学習データをリセット**"):
            self._reset_session_state()

    def run(self):
        st.set_page_config(layout="wide", page_title="用語クイズアプリ")
        st.title("🥷 用語クイズアプリ")

        st.sidebar.header("設定")
        self.upload_data()
        self.offer_download()
        self.reset_session_button()

        st.sidebar.markdown("---")
        st.sidebar.header("フィルター")
        df_filtered, remaining_df = self.filter_data()

        st.markdown("---")

        self.show_progress(df_filtered)

        if st.session_state.current_quiz is None:
            self.load_quiz(df_filtered, remaining_df)

        if st.session_state.current_quiz is not None:
            self.display_quiz(df_filtered, remaining_df)
        elif st.session_state.total > 0:
            self.show_completion()
        else:
            st.info("選択されたフィルター条件に一致する単語がありません。フィルターを変更してください。")

        st.markdown("---")
        self.display_statistics()

# アプリケーションの開始点
try:
    data_file_path = "tango.csv"
    
    if not os.path.exists(data_file_path):
        st.error(f"エラー: '{data_file_path}' が見つかりません。")
        st.info("GitHubリポジトリの `app.py` と同じフォルダに、データファイル「tango.csv」があるか確認してください。")
        st.stop()

    df = pd.read_csv(data_file_path, encoding="utf-8-sig")

except Exception as e:
    st.error(f"データファイルの読み込み中にエラーが発生しました: {e}")
    st.info("データファイル「tango.csv」の形式が正しいか、またはエンコーディングが 'utf-8-sig' であるか確認してください。")
    st.info("特に '正解回数' や '不正解回数' カラムに、数値以外の文字や空欄がないかご確認ください。")
    st.stop()

app = QuizApp(df)
app.run()
