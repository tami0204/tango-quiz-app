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
        other_descriptions = st.session_state.quiz_df[st.session_state.quiz_df["説明"] != correct_description]["説明"].unique().tolist()
        
        num_wrong_choices = min(3, len(other_descriptions))
        wrong_choices =
