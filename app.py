import streamlit as st
import pandas as pd
import random
import os
import datetime

# --- ここからQuizAppクラスの定義 ---
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
            "uploaded_df_temp": None,
            "uploaded_file_name": None,
            "uploaded_file_size": None,
            "data_source_selection": "初期データ",
            "filter_category": "すべて",
            "filter_field": "すべて",
            "filter_level": "すべて",
            "debug_message_quiz_start": "",
            "debug_message_answer_update": "",
            "debug_message_error": "",
            "debug_message_answer_end": "",
        }
        self._initialize_session()
        
        self.initial_df = self._process_df_types(original_df.copy())

        if st.session_state.quiz_df is None:
            if st.session_state.data_source_selection == "初期データ":
                self._initialize_quiz_df_from_original()
            elif st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is None:
                self._initialize_quiz_df_from_original() 
            elif st.session_state.data_source_selection == "アップロード" and st.session_state.uploaded_df_temp is not None:
                st.session_state.quiz_df = st.session_state.uploaded_df_temp.copy()
                st.session_state.answered_words = set(st.session_state.quiz_df[
                    (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
                ]["単語"].tolist())
            else:
                self._initialize_quiz_df_from_original()
                
    def _process_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrameに対して、必要なカラムの型変換と初期化を適用します。"""
        if '〇×結果' not in df.columns: df['〇×結果'] = ''
        else: df['〇×結果'] = df['〇×結果'].astype(str).replace('nan', '')

        for col in ['正解回数', '不正解回数']:
            if col not in df.columns: df[col] = 0
            else: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        for col in ['最終実施日時', '次回実施予定日時']:
            if col not in df.columns: df[col] = pd.NaT
            else: df[col] = pd.to_datetime(df[col], errors='coerce') 
        
        if 'シラバス改定有無' not in df.columns: df['シラバス改定有無'] = ''
        else: df['シラバス改定有無'] = df['シラバス改定有無'].astype(str).replace('nan', '')
            
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
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _initialize_quiz_df_from_original(self):
        """アプリ起動時またはリセット時にinitial_dfからquiz_dfを初期化します。"""
        st.session_state.quiz_df = self.initial_df.copy()
        st.session_state.answered_words = set(st.session_state.quiz_df[
            (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
        ]["単語"].tolist())

    def _reset_session_state(self):
        """現在のquiz_dfの学習履歴のみをリセットします。データソースは維持されます。"""
        st.session_state.quiz_df['〇×結果'] = ''
        st.session_state.quiz_df['正解回数'] = 0
        st.session_state.quiz_df['不正解回数'] = 0
        st.session_state.quiz_df['最終実施日時'] = pd.NaT
        st.session_state.quiz_df['次回実施予定日時'] = pd.NaT

        st.session_state.answered_words = set()

        for key, val in self.defaults.items():
            if key not in ["quiz_df", "data_source_selection", "uploaded_df_temp", "uploaded_file_name", "uploaded_file_size",
                           "filter_category", "filter_field", "filter_level"]: 
                st.session_state[key] = val if not isinstance(val, set) else set()
        
        st.session_state.current_quiz = None 
        st.session_state.quiz_answered = False 
        st.session_state.quiz_choice_index = 0
