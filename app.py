import streamlit as st
import pandas as pd
import random
import os
import plotly.express as px

class QuizApp:
    def __init__(self, df: pd.DataFrame):
        self.kana_labels = ["ア", "イ", "ウ", "エ", "オ"]
        self.defaults = {
            "total": 0, # 総回答数
            "correct": 0, # 総正解数
            "answered_words": set(), # 回答済みの単語（このセッションで一度でも回答した単語）
            "latest_result": "", # 最新の回答結果メッセージ
            "latest_correct_description": "", # 最新の正解の説明
            "current_quiz": None, # 現在出題中のクイズデータ
            "quiz_answered": False, # 現在のクイズが回答済みかどうかのフラグ
            "quiz_choice_index": 0, # 選択肢のラジオボタンの初期選択インデックス
            "quiz_df": None # 更新されたクイズデータを保持するDataFrame
        }
        self._initialize_session()

        if st.session_state.quiz_df is None:
            st.session_state.quiz_df = df.copy()
            
            # '〇×結果' 列の初期化とNaNの置換
            if '〇×結果' not in st.session_state.quiz_df.columns:
                st.session_state.quiz_df['〇×結果'] = ''
            else:
                st.session_state.quiz_df['〇×結果'] = st.session_state.quiz_df['〇×結果'].astype(str).replace('nan', '')

            # '正解回数' '不正解回数' 列の初期化
            if '正解回数' not in st.session_state.quiz_df.columns:
                st.session_state.quiz_df['正解回数'] = 0
            if '不正解回数' not in st.session_state.quiz_df.columns:
                st.session_state.quiz_df['不正解回数'] = 0
                
        self.initial_df = df.copy() 

    def _initialize_session(self):
        """Streamlitのセッション状態を初期化またはデフォルト値に設定します。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _reset_session_state(self):
        """セッション状態をデフォルト値にリセットします。"""
        st.session_state.quiz_df = self.initial_df.copy()
        
        if '〇×結果' not in st.session_state.quiz_df.columns:
            st.session_state.quiz_df['〇×結果'] = ''
        else:
            st.session_state.quiz_df['〇×結果'] = st.session_state.quiz_df['〇×結果'].astype(str).replace('nan', '')

        st.session_state.quiz_df['正解回数'] = 0
        st.session_state.quiz_df['不正解回数'] = 0

        for key, val in self.defaults.items():
            if key != "quiz_df":
                st.session_state[key] = val if not isinstance(val, set) else set()
        st.success("✅ セッションをリセットしました")
        st.rerun()

    def filter_data(self):
        """ユーザーの選択に基づいてデータをフィルタリングし、Streamlitのselectboxを更新します。"""
        current_category = st.session_state.get("filter_category", "すべて")
        current_field = st.session_state.get("filter_field", "すべて")
        current_level = st.session_state.get("filter_level", "すべて")

        category_options = ["すべて"] + sorted(st.session_state.quiz_df["カテゴリ"].dropna().unique())
        field_options = ["すべて"] + sorted(st.session_state.quiz_df["分野"].dropna().unique())
        level_options = ["すべて"] + sorted(st.session_state.quiz_df["試験区分"].dropna().unique())

        category = st.selectbox("カテゴリを選ぶ", category_options, index=category_options.index(current_category), key="filter_category")
        field = st.selectbox("分野を選ぶ", field_options, index=field_options.index(current_field), key="filter_field")
        level = st.selectbox("試験区分を選ぶ", level_options, index=level_options.index(current_level), key="filter_
