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
            "quiz_df": None, # 更新されたクイズデータを保持するDataFrame
            # フィルターの選択状態をセッションステートに保持
            "filter_category": "すべて",
            "filter_field": "すべて",
            "filter_level": "すべて"
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
            # quiz_dfとフィルター選択状態以外のキーをリセット
            if key not in ["quiz_df", "filter_category", "filter_field", "filter_level"]:
                st.session_state[key] = val if not isinstance(val, set) else set()
        
        # フィルター選択状態もデフォルトにリセット
        st.session_state.filter_category = "すべて"
        st.session_state.filter_field = "すべて"
        st.session_state.filter_level = "すべて"

        st.success("✅ セッションをリセットしました")
        st.rerun()

    def _on_filter_change_internal(self, filter_type: str, new_value: str):
        """
        フィルターが変更されたときに呼び出される内部ハンドラ。
        セッションステートのフィルター値を更新し、クイズ状態をリセットする。
        """
        # フィルターの値を更新
        st.session_state[f"filter_{filter_type}"] = new_value

        # クイズ状態をリセット
        st.session_state.current_quiz = None
        st.session_state.answered_words = set() 
        st.session_state.total = 0
        st.session_state.correct = 0
        st.session_state.latest_result = ""
        st.session_state.latest_correct_description = ""
        st.session_state.quiz_answered = False
        st.session_state.quiz_choice_index = 0
        # Streamlitがセッションステートの変更を検知して自動的に再描画する
        
    def filter_data(self):
        """ユーザーの選択に基づいてデータをフィルタリングし、Streamlitのselectboxを更新します。
        カテゴリ選択に基づいて分野の選択肢を絞り込みます。
        """
        df_base = st.session_state.quiz_df.copy() # ベースとなるデータフレーム (全回答履歴を含む)

        # カテゴリの選択
        category_options = ["すべて"] + sorted(df_base["カテゴリ"].dropna().unique())
        # 現在のセッションステートの値を初期選択値として使用
        category = st.selectbox(
            "カテゴリを選ぶ", 
            category_options, 
            index=category_options.index(st.session_state.filter_category) if st.session_state.filter_category in category_options else 0, 
            key="filter_category", 
            on_change=self._on_filter_change_internal, # 直接インスタンスメソッドをコールバックに指定
            args=("category", st.session_state.filter_category) # on_changeで引数を渡す
        )
        # on_changeでst.session_state.filter_categoryは更新されるが、
        # selectboxの戻り値も使うので、ここで再設定する
        st.session_state.filter_category = category

        # カテゴリでフィルタリング
        df_filtered_by_category = df_base.copy()
        if st.session_state.filter_category != "すべて":
            df_filtered_by_category = df_base[df_base["カテゴリ"] == st.session_state.filter_category]

        # 分野の選択 (カテゴリ選択に基づいて絞り込む)
        field_options = ["すべて"] + sorted(df_filtered_by_category["分野"].dropna().unique())
        field = st.selectbox(
            "分野を選ぶ", 
            field_options, 
            index=field_options.index(st.session_state.filter_field) if st.session_state.filter_field in field_options else 0, 
            key="filter_field", 
            on_change=self._on_filter_change_internal, 
            args=("field", st.session_state.filter_field)
        )
        st.session_state.filter_field = field # on_changeで更新されるが、ここでも再設定

        # 分野でフィルタリング
        df_filtered_by_field = df_filtered_by_category.copy()
        if st.session_state.filter_field != "すべて":
            df_filtered_by_field = df_filtered_by_category[df_filtered_by_category["分野"] == st.session_state.filter_field]

        # 試験区分の選択 (カテゴリと分野の選択に基づいて絞り込む)
        level_options = ["すべて"] + sorted(df_filtered_by_field["試験区分"].dropna().unique())
        level = st.selectbox(
            "試験区分を選ぶ", 
            level_options, 
            index=level_options.index(st.session_state.filter_level) if st.session_state.filter_level in level_options else 0, 
            key="filter_level", 
            on_change=self._on_filter_change_internal, 
            args=("level", st.session_state.filter_level)
        )
        st.session_state.filter_level = level # on_changeで更新されるが、ここでも再設定

        # 試験区分でフィルタリング
        df_final_filtered = df_filtered_by_field.copy()
        if st.session_state.filter_level != "すべて":
            df_final_filtered = df_filtered_by_field[df_filtered_by_field["試験区分"] == st.session_state.filter_level]

        # 最終的に表示対象となる単語数と、そのうちまだ回答していない単語を計算
        remaining = df_final_filtered[~df_final_filtered["単語"].isin(st.session_state.answered_words)]
        
        return df_final_filtered, remaining # フィルターされた全単語と、そのうち未回答の単語


    def show_progress(self, df_filtered):
        """現在の学習進捗（回答数、正解数）を表示します。"""
        answered_in_filter = df_filtered[df_filtered["単語"].isin(st.session_state.answered_words)]
        
        st.markdown(f"📊 **進捗：{len(answered_in_filter)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答 (現フィルター内)：{st.session_state.total} 回 / 🎯 正解 (現フィルター内)：{st.session_state.correct} 回**")
        
    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """新しいクイズをロードし、セッション状態を更新します。不正解回数に基づいて出題します。"""
        if not remaining_df.empty:
            weights = (remaining_df['不正解回数'] + 1).tolist()
            
            if sum(weights) == 0:
                q = remaining_df.sample(1).iloc[0]
            else:
                weights = [w if pd.notna(w) and w != float('inf') and w != float('-inf') else 1 for w in weights]
                if sum(weights) == 0:
                    q = remaining_df.sample(1).iloc[0]
                else:
                    q = remaining_df.sample(weights=weights, n=1).iloc[0]

            correct_description = q["説明"]
            # 選択肢プールの対象も、フィルタリングされたdf_filtered全体から取得する
            wrong_options_pool = df_filtered[df_filtered["説明"] != correct_description]["説明"].drop_duplicates().tolist()
            num_wrong_options = min(3, len(wrong_options_pool))
