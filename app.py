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
        """ユーザーの選択に基づいてデータをフィルタリングし、Streamlitのselectboxを更新します。
        カテゴリ選択に基づいて分野の選択肢を絞り込みます。
        """
        df_base = st.session_state.quiz_df.copy()

        # カテゴリの選択
        category_options = ["すべて"] + sorted(df_base["カテゴリ"].dropna().unique())
        current_category = st.session_state.get("filter_category", "すべて")
        category_index = category_options.index(current_category) if current_category in category_options else 0
        
        category = st.selectbox("カテゴリを選ぶ", category_options, index=category_index, key="filter_category")

        df_filtered_by_category = df_base.copy()
        if category != "すべて":
            df_filtered_by_category = df_base[df_base["カテゴリ"] == category]

        # 分野の選択 (カテゴリ選択に基づいて絞り込む)
        # フィルタリングされたデータフレームから分野のユニークな値を取得
        field_options = ["すべて"] + sorted(df_filtered_by_category["分野"].dropna().unique())
        current_field = st.session_state.get("filter_field", "すべて")
        # 現在の選択が新しいオプションリストに含まれていない場合は「すべて」にリセット
        field_index = field_options.index(current_field) if current_field in field_options else 0

        field = st.selectbox("分野を選ぶ", field_options, index=field_index, key="filter_field")

        # 試験区分の選択 (カテゴリと分野の選択に基づいて絞り込む)
        df_filtered_by_field = df_filtered_by_category.copy()
        if field != "すべて":
            df_filtered_by_field = df_filtered_by_category[df_filtered_by_category["分野"] == field]

        level_options = ["すべて"] + sorted(df_filtered_by_field["試験区分"].dropna().unique())
        current_level = st.session_state.get("filter_level", "すべて")
        level_index = level_options.index(current_level) if current_level in level_options else 0
        
        level = st.selectbox("試験区分を選ぶ", level_options, index=level_index, key="filter_level")

        df_final_filtered = df_filtered_by_field.copy()
        if level != "すべて":
            df_final_filtered = df_filtered_by_field[df_filtered_by_field["試験区分"] == level]

        # ここでfilter_dataの変更が反映されるように、
        # answered_wordsのフィルタリングはdf_final_filteredに対して行う
        remaining = df_final_filtered[~df_final_filtered["単語"].isin(st.session_state.answered_words)]
        
        return df_final_filtered, remaining

    def show_progress(self, df_filtered):
        """現在の学習進捗（回答数、正解数）を表示します。"""
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答：{st.session_state.total} 回 / 🎯 正解：{st.session_state.correct} 回**")
        
    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """新しいクイズをロードし、セッション状態を更新します。不正解回数に基づいて出題します。"""
        # ここが最も重要な修正点です。
        # remaining_df はすでにカテゴリ・分野・試験区分でフィルタリングされたデータなので、
        # ここから問題を選ぶことで、フィルター選択がクイズに反映されます。
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
            wrong_options = random.sample(wrong_options_pool, num_wrong_options)

            options = wrong_options + [correct_description]
            random.shuffle(options)

            st.session_state.current_quiz = {
                "単語": q["単語"],
                "説明": q["説明"], 
                "選択肢": options,
                "記述": q.get("午後記述での使用例", "N/A"),
                "文脈": q.get("使用理由／文脈", "N/A"),
                "区分": q.get("試験区分", "N/A"),
                "出題確率（推定）": q.get("出題確率（推定）", "N/A"),
                "シラバス改定有無": q.get("シラバス改定有無", "N/A"),
                "改定の意図・影響": q.get("改定の意図・影響", "N/A"), 
            } 

            st.session_state.quiz_answered = False
            st.session_state.quiz_choice_index = 0
            st.session_state.latest_result = ""
            st.session_state.latest_correct_description = ""
        else:
            st.session_state.current_quiz = None

    def _display_quiz_question(self):
        """クイズの質問と関連情報を表示します。"""
        q = st.session_state.current_quiz
        if not q:
            return

        st.subheader(f"この用語の説明は？：**{q['単語']}**")
        st.markdown(f"🧩 **午後記述での使用例：** {q['記述']}")
        st.markdown(f"🎯 **使用理由／文脈：** {q['文脈']}")
        st.markdown(f"🕘 **試験区分：** {q['区分']}")
        st.markdown(f"📈 **出題確率（推定）：** {q['出題確率（推定）']}　🔄 **シラバス改定有無：** {q['シラバス改定有無']}　📝 **改定の意図・影響：** {q['改定の意図・影響']}")

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
            
        st.session_state.quiz_df = temp_df

        st.session_state.quiz_answered = True

    def _display_result_and_next_button(self):
        """回答結果メッセージと次の問題へ進むボタンを表示します。"""
        st.info(st.session_state.latest_result)
        st.markdown(f"💡 **説明:** {st.session_state.latest_correct_description}")

        if st.button("➡️ 次の問題へ"):
            st.session_state.current_quiz = None
            st.session_state.quiz_answered = False
            st.rerun()

    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """
