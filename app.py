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
                # ここが修正された箇所です
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
                # answered_wordsがセットでない場合、セットに変換
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
            if key != "quiz_df": # quiz_dfは初期DFから再生成するため除外
                st.session_state[key] = val if not isinstance(val, set) else set() # セットは新しい空セットにする
        st.success("✅ セッションをリセットしました")
        st.rerun()

    def filter_data(self):
        """ユーザーの選択に基づいてデータをフィルタリングし、Streamlitのselectboxを更新します。"""
        current_category = st.session_state.get("filter_category", "すべて")
        current_field = st.session_state.get("filter_field", "すべて")
        current_level = st.session_state.get("filter_level", "すべて")

        # Dropdown options are generated from DataFrame columns, ensure they are correct.
        category_options = ["すべて"] + sorted(st.session_state.quiz_df["カテゴリ"].dropna().unique())
        field_options = ["すべて"] + sorted(st.session_state.quiz_df["分野"].dropna().unique())
        level_options = ["すべて"] + sorted(st.session_state.quiz_df["試験区分"].dropna().unique())

        category = st.selectbox("カテゴリを選ぶ", category_options, index=category_options.index(current_category), key="filter_category")
        field = st.selectbox("分野を選ぶ", field_options, index=field_options.index(current_field), key="filter_field")
        level = st.selectbox("試験区分を選ぶ", level_options, index=level_options.index(current_level), key="filter_level")

        df_filtered = st.session_state.quiz_df.copy()
        if category != "すべて":
            df_filtered = df_filtered[df_filtered["カテゴリ"] == category]
        if field != "すべて":
            df_filtered = df_filtered[df_filtered["分野"] == field]
        if level != "すべて":
            df_filtered = df_filtered[df_filtered["試験区分"] == level]

        remaining = df_filtered[~df_filtered["単語"].isin(st.session_state.answered_words)]
        
        return df_filtered, remaining

    def show_progress(self, df_filtered):
        """現在の学習進捗（回答数、正解数）を表示します。"""
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答：{st.session_state.total} 回 / 🎯 正解：{st.session_state.correct} 回**")
        
    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """新しいクイズをロードし、セッション状態を更新します。不正解回数に基づいて出題します。"""
        if not remaining_df.empty:
            weights = (remaining_df['不正解回数'] + 1).tolist()
            
            if sum(weights) == 0:
                q = remaining_df.sample(1).iloc[0]
            else:
                # 重みにNaNや無限大がないことを確認
                weights = [w if pd.notna(w) and w != float('inf') and w != float('-inf') else 1 for w in weights]
                if sum(weights) == 0: # 全ての重みが0になった場合も考慮
                    q = remaining_df.sample(1).iloc[0]
                else:
                    q = remaining_df.sample(weights=weights, n=1).iloc[0]


            correct_description = q["説明"]
            # 正しい説明をpoolから除外し、重複をなくす
            wrong_options_pool = df_filtered[df_filtered["説明"] != correct_description]["説明"].drop_duplicates().tolist()
            num_wrong_options = min(3, len(wrong_options_pool))
            wrong_options = random.sample(wrong_options_pool, num_wrong_options)

            options = wrong_options + [correct_description]
            random.shuffle(options)

            st.session_state.current_quiz = {
                "単語": q["単語"],
                "説明": correct_description,
                "選択肢": options,
                "記述": q.get("午後記述での使用例", "N/A"),
                "文脈": q.get("使用理由／文脈", "N/A"),
                "区分": q.get("試験区分", "N/A"),
                "出題確率（推定）": q.get("出題確率（推定）", "N/A"),
                "シラバス改定有無": q.get("シラバス改定有無", "N/A"),
                "改定の意図・影響": q.get("改定の意図・影響", "N/A")
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
        """クイズの質問と選択肢を表示し、回答を処理します。"""
        q = st.session_state.current_quiz
        if not q:
            return

        self._display_quiz_question()

        labeled_options = [f"{self.kana_labels[i]}：{txt}" for i, txt in enumerate(q["選択肢"])]

        selected_labeled_option = st.radio(
            "選択肢を選んでください",
            labeled_options,
            index=st.session_state.quiz_choice_index,
            key=f"quiz_radio_{st.session_state.total}", 
            disabled=st.session_state.quiz_answered
        )

        selected_option_index = labeled_options.index(selected_labeled_option)
        selected_option_text = q["選択肢"][selected_option_index]

        if st.session_state.quiz_choice_index != selected_option_index and not st.session_state.quiz_answered:
            st.session_state.quiz_choice_index = selected_option_index

        # 「答え合わせ」ボタン
        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                self._handle_answer_submission(selected_option_text, q)
                st.rerun()
        else:
            self._display_result_and_next_button()

        # Geminiアイコンを常に表示
        st.markdown(
            f'<div style="text-align: left; margin-top: 10px;">' # ボタンとの間隔を調整
            f'<a href="https://gemini.google.com/" target="_blank">'
            f'<img src="https://www.gstatic.com/lamda/images/gemini_logo_lockup_eval_ja_og.svg" alt="Geminiに質問する" width="50">'
            f'</a>'
            f'</div>',
            unsafe_allow_html=True
        )

    def show_completion(self):
        """すべての問題に回答した際のメッセージを表示します。"""
        st.success("🎉 すべての問題に回答しました！")
        st.balloons()

    def offer_download(self):
        """現在の学習データのCSVダウンロードボタンを提供します。"""
        csv_quiz_data = st.session_state.quiz_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 **現在の学習データをダウンロード** (〇×・統計含む)", data=csv_quiz_data, file_name="updated_tango_data_with_stats.csv", mime="text/csv")
        
    def reset_session_button(self):
        """セッションをリセットするためのボタンを表示します。"""
        if st.button("🔁 セッションをリセット"):
            self._reset_session_state()

    def display_statistics(self):
        """学習統計情報（全体の正答率、苦手な単語トップ5、カテゴリ別/分野別正答率グラフ）を表示します。"""
        st.subheader("💡 学習統計")

        if st.session_state.total > 0:
            overall_accuracy = (st.session_state.correct / st.session_state.total) * 100
            st.write(f"**全体正答率:** {overall_accuracy:.1f}% ({st.session_state.correct}/{st.session_state.total} 問)")
        else:
            st.write("**全体正答率:** まだ問題に回答していません。")

        st.markdown("---")

        st.markdown("##### 😱 苦手な単語トップ5 (不正解回数が多い順)")
        answered_df = st.session_state.quiz_df[st.session_state.quiz_df["単語"].isin(st.session_state.answered_words)].copy()

        if not answered_df.empty:
            top_5_difficult = answered_df.sort_values(by='不正解回数', ascending=False).head(5)
            
            if not top_5_difficult.empty:
                for idx, row in top_5_difficult.iterrows():
                    total_attempts = row['正解回数'] + row['不正解回数']
                    if total_attempts > 0:
                        accuracy = (row['正解回数'] / total_attempts) * 100
                        st.write(f"**{row['単語']}**: 不正解 {row['不正解回数']}回 / 正解 {row['正解回数']}回 (正答率: {accuracy:.1f}%)")
                    else:
                        st.write(f"**{row['単語']}**: まだ回答していません。")
            else:
                st.info("まだ苦手な単語はありません。")
        else:
            st.info("まだ回答した単語がありません。")

        st.markdown("---")

        st.markdown("##### 📈 カテゴリ別 / 分野別 正答率")
        
        stats_df = st.session_state.quiz_df.copy()
        stats_df['合計回答
