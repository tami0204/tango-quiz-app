import streamlit as st
import pandas as pd
import random
import os
import plotly.express as px
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
        if '正解回数' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['正解回数'] = 0
        if '不正解回数' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['不正解回数'] = 0
        
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
        # 'シラバス改定有無' 列を文字列型に変換し、空白を除去、空文字列とNaNを除外してユニークな値を取得
        valid_syllabus_changes = df["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
        syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
        
        st.session_state.filter_level = st.sidebar.selectbox( # フィルター名を「習熟度」から「シラバス改定有無」に変更
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
        # フィルターされたdf_filteredの中から、回答済みで、かつ不正解回数が正解回数より多い単語を抽出
        answered_and_struggled = df_filtered[
            (df_filtered["単語"].isin(st.session_state.answered_words)) &
            (df_filtered["不正解回数"] > df_filtered
