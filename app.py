import streamlit as st
import pandas as pd
import random
import os
import plotly.express as px # グラフ描画用にPlotlyをインポート

class QuizApp:
    def __init__(self, df: pd.DataFrame):
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
            "history": [],
            "current_round": 1, 
            "quiz_df": None 
        }
        self._initialize_session()

        if st.session_state.quiz_df is None:
            st.session_state.quiz_df = df.copy()
            for i in range(1, 16):
                col_name = str(i)
                if col_name in st.session_state.quiz_df.columns:
                    st.session_state.quiz_df[col_name] = st.session_state.quiz_df[col_name].astype(str).replace('nan', '')
            
            st.session_state.quiz_df['正解回数'] = 0
            st.session_state.quiz_df['不正解回数'] = 0

            for index, row in st.session_state.quiz_df.iterrows():
                correct_count = 0
                incorrect_count = 0
                for i in range(1, 16):
                    col_name = str(i)
                    if col_name in row and row[col_name] == '〇':
                        correct_count += 1
                    elif col_name in row and row[col_name] == '×':
                        incorrect_count += 1
                st.session_state.quiz_df.at[index, '正解回数'] = correct_count
                st.session_state.quiz_df.at[index, '不正解回数'] = incorrect_count
                
        self.initial_df = df.copy()

    def _initialize_session(self):
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _reset_session_state(self):
        st.session_state.quiz_df = self.initial_df.copy()
        for i in range(1, 16):
            col_name = str(i)
            if col_name in st.session_state.quiz_df.columns:
                st.session_state.quiz_df[col_name] = st.session_state.quiz_df[col_name].astype(str).replace('nan', '')
        
        st.session_state.quiz_df['正解回数'] = 0
        st.session_state.quiz_df['不正解回数'] = 0

        for index, row in st.session_state.quiz_df.iterrows():
            correct_count = 0
            incorrect_count = 0
            for i in range(1, 16):
                col_name = str(i)
                if col_name in row and row[col_name] == '〇':
                    correct_count += 1
                elif col_name in row and row[col_name] == '×':
                    incorrect_count += 1
            st.session_state.quiz_df.at[index, '正解回数'] = correct_count
            st.session_state.quiz_df.at[index, '不正解回数'] = incorrect_count

        for key, val in self.defaults.items():
            if key != "quiz_df":
                st.session_state[key] = val if not isinstance(val, set) else set()
        st.success("✅ セッションをリセットしました")
        st.rerun()

    def filter_data(self):
        current_category = st.session_state.get("filter_category", "すべて")
        current_field = st.session_state.get("filter_field", "すべて")
        current_level = st.session_state.get("filter_level", "すべて")

        category_options = ["すべて"] + sorted(st.session_state.quiz_df["カテゴリ"].dropna().unique())
        field_options = ["すべて"] + sorted(st.session_state.quiz_df["分野"].dropna().unique())
        level_options = ["すべて"] + sorted(st.session_state.quiz_df["試験区分"].dropna().unique())

        category = st.selectbox("カテゴリを選ぶ", category_options, index=category_options.index(current_category), key="filter_category")
        field = st.selectbox("分野を選ぶ", field_options, index=field_options.index(current_field), key="filter_field")
        level = st.selectbox("試験区分を選ぶ", level_options, index=level_options.index(current_level), key="filter_level")

        # st.session_state.quiz_df をフィルタリング
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
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答：{st.session_state.total} 回 / 🎯 正解：{st.session_state.correct} 回**")
        display_round = min(st.session_state.current_round, 15)
        st.markdown(f"🗓️ **現在の記録列：{display_round}回目**")

    def load_quiz(self, df_filtered, remaining_df):
        if len(remaining_df) > 0:
            weights = (remaining_df['不正解回数'] + 1).tolist()
            
            if sum(weights) == 0:
                q = remaining_df.sample(1).iloc[0]
            else:
                q = remaining_df.sample(weights=weights, n=1).iloc[0]

            correct_description = q["説明"]

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
        q = st.session_state.current_quiz
        if not q:
            return

        st.subheader(f"この用語の説明は？：**{q['単語']}**")
        st.markdown(f"🧩 **午後記述での使用例：** {q['記述']}")
        st.markdown(f"🎯 **使用理由／文脈：** {q['文脈']}")
        st.markdown(f"🕘 **試験区分：** {q['区分']}")
        st.markdown(f"📈 **出題確率（推定）：** {q['出題確率（推定）']}　🔄 **シラバス改定有無：** {q['シラバス改定有無']}　📝 **改定の意図・影響：** {q['改定の意図・影響']}")


    def _handle_answer_submission(self, selected_option_text, current_quiz_data):
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
            
            column_to_update = str(min(st.session_state.current_round, 15))
            if column_to_update in temp_df.columns:
                temp_df.at[idx, column_to_update] = result_mark
            else:
                st.warning(f"警告: 列 '{column_to_update}' がDataFrameに見つかりません。CSVファイルを確認してください。")
            
            if is_correct:
                temp_df.at[idx, '正解回数'] += 1
            else:
                temp_df.at[idx, '不正解回数'] += 1
        
        st.session_state.quiz_df = temp_df

        st.session_state.current_round += 1

        try:
            choice_kana = self.kana_labels[current_quiz_data["選択肢"].index(selected_option_text)]
        except ValueError:
            choice_kana = "不明"
        
        try:
            correct_kana = self.kana_labels[current_quiz_data["選択肢"].index(current_quiz_data["説明"])]
        except ValueError:
            correct_kana = "不明"

        st.session_state.history.append({
            "単語": current_quiz_data["単語"],
            "私の選択": choice_kana,
            "正解": correct_kana,
            "正誤": result_mark,
            "記述例": current_quiz_data["記述"],
            "文脈": current_quiz_data["文脈"],
            "試験区分": current_quiz_data["区分"],
            "説明（正解）": current_quiz_data["説明"]
        })
        st.session_state.quiz_answered = True

    def _display_result_and_next_button(self):
        st.info(st.session_state.latest_result)
        st.markdown(f"💡 **説明:** {st.session_state.latest_correct_description}")

        if st.button("➡️ 次の問題へ"):
            st.session_state.current_quiz = None
            st.session_state.quiz_answered = False
            st.rerun()

    def display_quiz(self, df_filtered, remaining_df):
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

        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                self._handle_answer_submission(selected_option_text, q)
                st.rerun()
        else:
            self._display_result_and_next_button()

    def show_completion(self):
        st.success("🎉 すべての問題に回答しました！")
        st.balloons()

    def offer_download(self):
        csv_quiz_data = st.session_state.quiz_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 **現在の学習データをダウンロード** (〇×・統計含む)", data=csv_quiz_data, file_name="updated_tango_data_with_stats.csv", mime="text/csv")
        
        df_log = pd.DataFrame(st.session_state.history or [])
        if not df_log.empty:
            csv_history = df_log.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("📥 回答履歴をダウンロード", data=csv_history, file_name="quiz_results.csv", mime="text/csv")
        else:
            st.info("まだ回答履歴がありません。")

    def reset_session_button(self):
        if st.button("🔁 セッションをリセット"):
            self._reset_session_state()

    def display_statistics(self):
        """学習統計情報を表示します。"""
        st.subheader("💡 学習統計")

        # 全体の正答率
        if st.session_state.total > 0:
            overall_accuracy = (st.session_state.correct / st.session_state.total) * 100
            st.write(f"**全体正答率:** {overall_accuracy:.1f}% ({st.session_state.correct}/{st.session_state.total} 問)")
        else:
            st.write("**全体正答率:** まだ問題に回答していません。")

        st.markdown("---")

        # 苦手な単語トップ5
        st.markdown("##### 😱 苦手な単語トップ5 (不正解回数が多い順)")
        # フィルタリングされたデータの中から、かつ回答済みの単語のみを対象に統計をとる
        # quiz_df はフィルタリング前の全体のデータを持つので、回答済みの単語に絞る
        answered_df = st.session_state.quiz_df[st.session_state.quiz_df["単語"].isin(st.session_state.answered_words)].copy()

        if not answered_df.empty:
            # 不正解回数が0の単語は除外するか、下位に表示されるようにする
            # ここでは不正解回数が1以上のものを対象にするか、または0でも含めてランキング
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

        # カテゴリ別・分野別の正答率
        st.markdown("##### 📈 カテゴリ別 / 分野別 正答率")
        
        # まず合計回数を計算し、分母が0になることを避ける
        stats_df = st.session_state.quiz_df.copy()
        stats_df['合計回答回数'] = stats_df['正解回数'] + stats_df['不正解回数']
        
        # カテゴリ別
        category_stats = stats_df.groupby("カテゴリ").agg(
            total_correct=('正解回数', 'sum'),
            total_incorrect=('不正解回数', 'sum'),
            total_attempts=('合計回答回数', 'sum')
        ).reset_index()
        category_stats['正答率'] = category_stats.apply(lambda row: (row['total_correct'] / row['total_attempts'] * 100) if row['total_attempts'] > 0 else 0, axis=1)
        
        # 回答数があるカテゴリのみ表示
        category_stats_filtered = category_stats[category_stats['total_attempts'] > 0].sort_values(by='正答率', ascending=True)

        if not category_stats_filtered.empty:
            st.write("###### カテゴリ別")
            fig_category = px.bar(
                category_stats_filtered, 
                x='カテゴリ', 
                y='正答率', 
                color='正答率', 
                color_continuous_scale=px.colors.sequential.Viridis,
                title='カテゴリ別 正答率',
                labels={'正答率': '正答率 (%)'},
                text_auto='.1f' # グラフに値を直接表示
            )
            fig_category.update_layout(xaxis_title="カテゴリ", yaxis_title="正答率 (%)")
            st.plotly_chart(fig_category, use_container_width=True)
        else:
            st.info("まだカテゴリ別の回答がありません。")

        # 分野別
        field_stats = stats_df.groupby("分野").agg(
            total_correct=('正解回数', 'sum'),
            total_incorrect=('不正解回数', 'sum'),
            total_attempts=('合計回答回数', 'sum')
        ).reset_index()
        field_stats['正答率'] = field_stats.apply(lambda row: (row['total_correct'] / row['total_attempts'] * 100) if row['total_attempts'] > 0 else 0, axis=1)

        # 回答数がある分野のみ表示
        field_stats_filtered = field_stats[field_stats['total_attempts'] > 0].sort_values(by='正答率', ascending=True)

        if not field_stats_filtered.empty:
            st.write("###### 分野別")
            fig_field = px.bar(
                field_stats_filtered, 
                x='分野', 
                y='正答率', 
                color='正答率', 
                color_continuous_scale=px.colors.sequential.Viridis,
                title='分野別 正答率',
                labels={'正答率': '正答率 (%)'},
                text_auto='.1f'
            )
            fig_field.update_layout(xaxis_title="分野", yaxis_title="正答率 (%)")
            st.plotly_chart(fig_field, use_container_width=True)
        else:
            st.info("まだ分野別の回答がありません。")


    def run(self):
        st.set_page_config(layout="wide", page_title="用語クイズアプリ")

        st.markdown("""
            <style>
            .stApp {
                background-color: #f0f2f6;
            }
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                border-radius: 12px;
                padding: 10px 24px;
                font-size: 16px;
                transition-duration: 0.4s;
                box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19);
            }
            .stButton>button:hover {
                background-color: #45a049;
                color: white;
            }
            .stRadio > label {
                font-size: 18px;
                margin-bottom: 10px;
                padding: 10px;
                border-radius: 8px;
                background-color: #e6e6e6;
                border: 1px solid #ddd;
            }
            .stRadio > label:hover {
                background-color: #dcdcdc;
            }
            /* Disabled radio button styling */
            .stRadio > label[data-baseweb="radio"] > div > span[data-testid="stDecoration"] {
                cursor: default !important;
            }
            .stRadio > label[data-baseweb="radio"][data-state="disabled"] {
                opacity: 0.7;
                cursor: not-allowed;
            }
            .stRadio > label > div > p {
                font-weight: bold;
            }
            h1, h2, h3 {
                color: #2e4053;
            }
            .stInfo {
                background-color: #e0f2f7;
                color: #2196F3;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
                border: 1px solid #90caf9;
            }
            .stSuccess {
                background-color: #e8f5e9;
                color: #4CAF50;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
                border: 1px solid #a5d6a7;
            }
            .stError {
                background-color: #ffebee;
                color: #f44336;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
                border: 1px solid #ef9a9a;
            }
            /* Selectbox styling: The main display area of the selectbox */
            div[data-baseweb="select"] > div:first-child {
                background-color: white !important;
                border: 1px solid #999 !important;
                border-radius: 8px;
            }
            /* Selectbox styling: The dropdown list */
            div[data-baseweb="select"] div[role="listbox"] {
                background-color: white !important;
                border: 1px solid #999 !important;
                border-radius: 8px;
            }
            /* Selectbox styling: Specifically targeting the input field inside the selectbox */
            div[data-baseweb="select"] input[type="text"] {
                background-color: white !important;
                border: none !important;
            }
            /* Selectbox内のテキスト色を調整 */
            div[data-baseweb="select"] span {
                color: #333;
            }
            </style>
            """, unsafe_allow_html=True)


        st.title("用語クイズアプリ")

        df_filtered, remaining_df = self.filter_data()
        self.show_progress(df_filtered)

        # 統計表示を展開可能なセクションに格納
        with st.expander("📊 学習統計を表示"):
            self.display_statistics()

        with st.expander("📂 読み込みデータの確認"):
            st.dataframe(st.session_state.quiz_df.head()) # quiz_dfの現在の状態を表示

        if st.session_state.current_quiz is None and len(remaining_df) > 0:
            self.load_quiz(df_filtered, remaining_df)

        if len(remaining_df) == 0 and st.session_state.current_quiz is None:
            self.show_completion()
        elif st.session_state.current_quiz:
            self.display_quiz(df_filtered, remaining_df)

        self.offer_download()
        st.markdown("---")
        self.reset_session_button()

# アプリ実行
try:
    if not os.path.exists("tango.csv"):
        st.error("❌ 'tango.csv' が見つかりません。")
        info_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分", "出題確率（推定）", "シラバス改定有無", "改定の意図・影響"] + [str(i) for i in range(1, 16)]
        st.info(f"必要な列：{', '.join(info_columns)}")
        st.stop()

    df = pd.read_csv("tango.csv")
