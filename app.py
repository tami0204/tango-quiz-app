import streamlit as st
import pandas as pd
import random
import os
import plotly.express as px
import datetime # datetimeモジュールを追加

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
            "filter_level": "すべて"
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
        if '正解回数' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['正解回数'] = 0
        if '不正解回数' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['不正解回数'] = 0
        
        # 新しい日時カラムの初期化
        if '最終実施日時' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['最終実施日時'] = pd.NaT # Not a Time (PandasのdatetimeのNaN)
        else:
            st.session_state.quiz_df['最終実施日時'] = pd.to_datetime(st.session_state.quiz_df['最終実施日時'], errors='coerce')
        
        if '次回実施予定日時' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['次回実施予定日時'] = pd.NaT
        else:
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
        st.session_state.filter_level = "すべて"

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
        # 'シラバス改定有無' 列を文字列型に変換し、空白を除去、空文字列とNaNを除外してユニークな値を取得
        valid_syllabus_changes = df["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
        syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
        
        st.session_state.filter_level = st.sidebar.selectbox( # フィルター名とキーを「シラバス改定有無」に合わせる
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
        ].copy() # SettingWithCopyWarningを避けるため.copy()

        if not answered_and_struggled.empty:
            # 不正解回数が多いほど選択されやすいように重み付け
            answered_and_struggled['temp_weight'] = answered_and_struggled['不正解回数'] + 1
            quiz_candidates_df = pd.concat([quiz_candidates_df, answered_and_struggled], ignore_index=True)

        # 2. まだ出題されていない単語を候補に入れる
        if not remaining_df.empty:
            remaining_df_copy = remaining_df.copy()
            remaining_df_copy['temp_weight'] = 1 # まだ回答していない単語の重み
            quiz_candidates_df = pd.concat([quiz_candidates_df, remaining_df_copy], ignore_index=True)
            
        # 重複する単語がある場合、不正解回数が多い方を優先するためにソート
        quiz_candidates_df = quiz_candidates_df.sort_values(by='temp_weight', ascending=False).drop_duplicates(subset='単語', keep='first')


        # 候補が空の場合の処理
        if quiz_candidates_df.empty:
            # 全ての単語が回答済み、または現在のフィルターに該当する単語がない
            st.info("現在のフィルター条件に一致する単語がないか、すべての単語を回答しました！フィルターを変更するか、学習データをリセットしてください。")
            st.session_state.current_quiz = None
            return

        # 候補の中から重み付けサンプリング
        weights = quiz_candidates_df['temp_weight'].tolist()
        
        # 重みの合計が0でないことを確認
        if sum(weights) == 0:
            # 全ての重みが0の場合は、単純にランダムサンプリング
            selected_quiz_row = quiz_candidates_df.sample(n=1).iloc[0]
        else:
            selected_quiz_row = quiz_candidates_df.sample(n=1, weights=weights).iloc[0]

        st.session_state.current_quiz = selected_quiz_row.to_dict()

        # 選択肢を生成
        correct_description = st.session_state.current_quiz["説明"]
        
        # 正しい説明を除く、他の説明文をランダムに選ぶ
        other_descriptions = st.session_state.quiz_df[st.session_state.quiz_df["説明"] != correct_description]["説明"].unique().tolist()
        
        # 選択肢の数を調整（最大4つ、ただし利用可能な説明文の数を超えない）
        # 間違った選択肢を3つ選ぶ場合
        num_wrong_choices = min(3, len(other_descriptions))
        wrong_choices = random.sample(other_descriptions, num_wrong_choices)

        choices = wrong_choices + [correct_description]
        
        random.shuffle(choices) # 選択肢をシャッフル
        st.session_state.current_quiz["choices"] = choices
        
        # 正解のインデックスを保存 (ラジオボタンの初期選択用。回答後には使わない)
        # st.session_state.quiz_choice_index = choices.index(correct_description) 
        st.session_state.quiz_choice_index = 0 # 初期選択は常に最初でOK

    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズを表示し、ユーザーの回答を処理します。"""
        current_quiz_data = st.session_state.current_quiz
        if not current_quiz_data:
            return # current_quiz_dataがNoneの場合は何もしない

        st.subheader(f"問題: **{current_quiz_data['単語']}**")
        st.markdown(f"🧩 **午後記述での使用例：** {current_quiz_data.get('午後記述での使用例', 'N/A')}")
        st.markdown(f"🎯 **使用理由／文脈：** {current_quiz_data.get('使用理由／文脈', 'N/A')}")
        st.markdown(f"🕘 **試験区分：** {current_quiz_data.get('試験区分', 'N/A')}")
        st.markdown(f"📈 **出題確率（推定）：** {current_quiz_data.get('出題確率（推定）', 'N/A')}　📝 **改定の意図・影響：** {current_quiz_data.get('改定の意図・影響', 'N/A')}")
        
        with st.form("quiz_form"):
            selected_option_text = st.radio(
                "説明を選択してください:",
                options=current_quiz_data["choices"],
                format_func=lambda x: f"{self.kana_labels[current_quiz_data['choices'].index(x)]}. {x}",
                key=f"quiz_radio_{st.session_state.total}", # ユニークキーで再描画時の問題回避
                disabled=st.session_state.quiz_answered # 回答済みなら選択不可
            )
            submit_button = st.form_submit_button("✅ 答え合わせ", disabled=st.session_state.quiz_answered)

            if submit_button and not st.session_state.quiz_answered:
                self._handle_answer_submission(selected_option_text, current_quiz_data)
                st.rerun() # 回答後に再実行して結果を表示

        if st.session_state.quiz_answered:
            st.markdown(f"### {st.session_state.latest_result}")
            if st.session_state.latest_result.startswith("❌"):
                st.info(f"正解は: **{st.session_state.latest_correct_description}** でした。")
            
            # Geminiへの質問ボタン (既存)
            st.markdown(
                f'<div style="text-align: left; margin-top: 10px;">'
                f'<a href="https://gemini.google.com/" target="_blank">'
                f'<img src="https://www.gstatic.com/lamda/images/gemini_logo_lockup_eval_ja_og.svg" alt="Geminiに質問する" width="50">'
                f'</a>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➡️ 次の問題へ"):
                    st.session_state.current_quiz = None # 次の問題をロードするためにリセット
                    st.session_state.quiz_answered = False
                    st.rerun()
            with col2:
                if st.button("🔄 この単語をもう一度出題"):
                    st.session_state.quiz_answered = False
                    st.rerun() # 同じ問題を再表示

    def _handle_answer_submission(self, selected_option_text: str, current_quiz_data: dict):
        """ユーザーの回答を処理し、結果を更新します。"""
        st.session_state.total += 1
        st.session_state.answered_words.add(current_quiz_data["単語"])

        is_correct = (selected_option_text == current_quiz_data["
