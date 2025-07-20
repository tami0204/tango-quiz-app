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
            "filter_level": "すべて" # このキーが「シラバス改定有無」の選択を保持するようになる
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
        st.session_state.filter_level = "すべて" # これもデフォルト値に戻す

        st.success("✅ セッションをリセットしました")
        st.rerun()

    def _on_filter_change_internal(self, filter_type: str):
        """
        フィルターが変更されたときに呼び出される内部ハンドラ。
        セッションステートのフィルター値を更新し、クイズ状態をリセットする。
        
        Args:
            filter_type (str): 変更されたフィルターの種類 ('category', 'field', 'level')
        """
        # Streamlitはon_changeが呼び出される前に、該当するキーのセッションステートを更新済み。
        # そのため、new_valueを引数で受け取る必要はなく、st.session_stateから直接取得する。
        # 例えば、filter_typeが"category"の場合、st.session_state.filter_category に最新値が入っている。

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
        category = st.selectbox(
            "カテゴリを選ぶ", 
            category_options, 
            index=category_options.index(st.session_state.filter_category) if st.session_state.filter_category in category_options else 0, 
            key="filter_category", 
            on_change=self._on_filter_change_internal, 
            args=("category",)
        )


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
            args=("field",)
        )


        # 分野でフィルタリング
        df_filtered_by_field = df_filtered_by_category.copy()
        if st.session_state.filter_field != "すべて":
            df_filtered_by_field = df_filtered_by_category[df_filtered_by_category["分野"] == st.session_state.filter_field]

        # シラバス改定有無の選択
        # 'シラバス改定有無' 列を文字列型に変換し、空白を除去、空文字列とNaNを除外してユニークな値を取得
        valid_syllabus_changes = df_filtered_by_field["シラバス改定有無"].astype(str).str.strip().replace('', pd.NA).dropna().unique().tolist()
        syllabus_change_options = ["すべて"] + sorted(valid_syllabus_changes)
        
        # 現在の filter_level の値が syllabus_change_options に存在するか確認し、indexを設定
        index_for_selectbox = 0
        if st.session_state.filter_level in syllabus_change_options:
            index_for_selectbox = syllabus_change_options.index(st.session_state.filter_level)

        syllabus_change_status = st.selectbox(
            "🔄 シラバス改定有無を選ぶ", # ラベルを変更
            syllabus_change_options,
            index=index_for_selectbox,
            key="filter_level", # キーは既存の filter_level を再利用
            on_change=self._on_filter_change_internal,
            args=("level",) # on_changeの引数も既存の level (ここでは filter_level に対応) を再利用
        )
        
        # シラバス改定有無でフィルタリング
        df_final_filtered = df_filtered_by_field.copy()
        if syllabus_change_status != "すべて":
            df_final_filtered = df_filtered_by_field[df_filtered_by_field["シラバス改定有無"] == syllabus_change_status]


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
                # 無限大やNaNが含まれていないかチェックし、適正な重みに変換
                weights = [w if pd.notna(w) and w != float('inf') and w != float('-inf') else 1 for w in weights]
                if sum(weights) == 0: # 全て1になった場合などで合計が0になることを防ぐ
                    q = remaining_df.sample(1).iloc[0]
                else:
                    q = remaining_df.sample(weights=weights, n=1).iloc[0]

            correct_description = q["説明"]
            # 選択肢プールの対象も、フィルタリングされたdf_filtered全体から取得する
            wrong_options_pool = df_filtered[df_filtered["説明"] != correct_description]["説明"].drop_duplicates().tolist()
            num_wrong_options = min(3, len(wrong_options_pool))
            
            # 間違った選択肢をランダムに選ぶ。利用可能な間違った選択肢がない場合も考慮。
            if num_wrong_options > 0:
                wrong_options = random.sample(wrong_options_pool, num_wrong_options)
            else:
                wrong_options = [] # 間違った選択肢がない場合

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
            # remaining_dfが空で、まだcurrent_quizがある場合はリセット
            # これにより、フィルタリングで問題がなくなった場合も完了メッセージが表示される
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
        # 以下の行から「シラバス改定有無」の表示を削除
        st.markdown(f"📈 **出題確率（推定）：** {q['出題確率（推定）']}　📝 **改定の意図・影響：** {q['改定の意図・影響']}")

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

        if not st.session_state.quiz_answered:
            if st.button("✅ 答え合わせ"):
                self._handle_answer_submission(selected_option_text, q)
                st.rerun()
        else:
            self._display_result_and_next_button()

        st.markdown(
            f'<div style="text-align: left; margin-top: 10px;">'
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
        st.subheader("💡 学習統計（全データ対象）") 

        total_attempts_overall = st.session_state.quiz_df['正解回数'].sum() + st.session_state.quiz_df['不正解回数'].sum()
        correct_overall = st.session_state.quiz_df['正解回数'].sum()

        if total_attempts_overall > 0:
            overall_accuracy = (correct_overall / total_attempts_overall) * 100
            st.write(f"**全体正答率:** {overall_accuracy:.1f}% ({correct_overall}/{total_attempts_overall} 問)")
        else:
            st.write("**全体正答率:** まだ問題に回答していません。")

        st.markdown("---")

        st.markdown("##### 😱 苦手な単語トップ5 (不正解回数が多い順)")
        answered_df_stats = st.session_state.quiz_df[
            (st.session_state.quiz_df['正解回数'] > 0) | 
            (st.session_state.quiz_df['不正解回数'] > 0)
        ].copy()


        if not answered_df_stats.empty:
            # 不正解回数がNaNでないことを確認してからソート
            top_5_difficult = answered_df_stats.sort_values(by='不正解回数', ascending=False).head(5)
            
            if not top_5_difficult.empty:
                for idx, row in top_5_difficult.iterrows():
                    total_attempts = row['正解回数'] + row['不正解回数']
                    if total_attempts > 0:
                        accuracy = (row['正解回数'] / total_attempts) * 100
                        st.write(f"**{row['単語']}**: 不正解 {int(row['不正解回数'])}回 / 正解 {int(row['正解回数'])}回 (正答率: {accuracy:.1f}%)")
                    else:
                        st.write(f"**{row['単語']}**: まだ回答していません。")
            else:
                st.info("まだ苦手な単語はありません。")
        else:
            st.info("まだ回答した単語がありません。")

        st.markdown("---")

        st.markdown("##### 📈 カテゴリ別 / 分野別 正答率")
        
        stats_df = st.session_state.quiz_df.copy()
        stats_df['合計回答回数'] = stats_df['正解回数'] + stats_df['不正解回数']
        
        category_stats = stats_df.groupby("カテゴリ").agg(
            total_correct=('正解回数', 'sum'),
            total_incorrect=('不正解回数', 'sum'),
            total_attempts=('合計回答回数', 'sum')
        ).reset_index()
        category_stats['正答率'] = category_stats.apply(lambda row: (row['total_correct'] / row['total_attempts'] * 100) if row['total_attempts'] > 0 else 0, axis=1)
        
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
                text_auto='.1f'
            )
            fig_category.update_layout(xaxis_title="カテゴリ", yaxis_title="正答率 (%)")
            st.plotly_chart(fig_category, use_container_width=True)
        else:
            st.info("まだカテゴリ別の回答がありません。")

        field_stats = stats_df.groupby("分野").agg(
            total_correct=('正解回数', 'sum'),
            total_incorrect=('不正解回数', 'sum'),
            total_attempts=('合計回答回数', 'sum')
        ).reset_index()
        field_stats['正答率'] = field_stats.apply(lambda row: (row['total_correct'] / row['total_attempts'] * 100) if row['total_attempts'] > 0 else 0, axis=1)

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
        """アプリケーションのメイン実行ロジックです。"""
        st.set_page_config(layout="wide", page_title="用語クイズアプリ")

        st.markdown("""
            <style>
            .stApp { background-color: #f0f2f6; }
            .stButton>button { background-color: #4CAF50; color: white; border-radius: 12px; padding: 10px 24px; font-size: 16px; transition-duration: 0.4s; box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19); }
            .stButton>button:hover { background-color: #45a049; color: white; }
            .stRadio > label { font-size: 18px; margin-bottom: 10px; padding: 10px; border-radius: 8px; background-color: #e6e6e6; border: 1px solid #ddd; }
            .stRadio > label:hover { background-color: #dcdcdc; }
            .stRadio > label[data-baseweb="radio"] > div > span[data-testid="stDecoration"] { cursor: default !important; }
            .stRadio > label[data-baseweb="radio"][data-state="disabled"] { opacity: 0.7; cursor: not-allowed; }
            .stRadio > label > div > p { font-weight: bold; }
            h1, h2, h3 { color: #2e4053; }
            .stInfo { background-color: #e0f2f7; color: #2196F3; border-radius: 8px; padding: 15px; margin-top: 20px; border: 1px solid #90caf9; }
            .stSuccess { background-color: #e8f5e9; color: #4CAF50; border-radius: 8px; padding: 15px; margin-top: 20px; border: 1px solid #a5d6a7; }
            .stError { background-color: #ffebee; color: #f44336; border-radius: 8px; padding: 15px; margin-top: 20px; border: 1px solid #ef9a9a; }
            div[data-baseweb="select"] > div:first-child { background-color: white !important; border: 1px solid #999 !important; border-radius: 8px; }
            div[data-baseweb="select"] div[role="listbox"] { background-color: white !important; border: 1px solid #999 !important; border-radius: 8px; }
            div[data-baseweb="select"] input[type="text"] { background-color: white !important; border: none !important; }
            div[data-baseweb="select"] span { color: #333; }
            </style>
            """, unsafe_allow_html=True)

        st.title("用語クイズアプリ")

        df_filtered, remaining_df = self.filter_data()
        self.show_progress(df_filtered)

        with st.expander("📊 **学習統計を表示**"):
            self.display_statistics()

        with st.expander("📂 **読み込みデータの確認**"):
            st.dataframe(st.session_state.quiz_df.head())

        if st.session_state.current_quiz is None and not remaining_df.empty:
            self.load_quiz(df_filtered, remaining_df)

        if remaining_df.empty and st.session_state.current_quiz is None:
            self.show_completion()
        elif st.session_state.current_quiz:
            self.display_quiz(df_filtered, remaining_df)
        else:
            # フィルター条件に合う単語が一つもない場合のメッセージ
            st.info("選択されたフィルター条件に合致する単語が見つからないか、すべての単語に回答済みです。")


        self.offer_download()
        st.markdown("---")
        self.reset_session_button()

# --- アプリ実行部分 ---
try:
    file_name = "tango.csv" 
    
    if not os.path.exists(file_name):
        st.error(f"❌ '{file_name}' が見つかりません。")
        st.info("必要な列: カテゴリ, 分野, 単語, 説明, 午後記述での使用例, 使用理由／文脈, 試験区分, 出題確率（推定）, シラバス改定有無, 改定の意図・影響, 〇×結果")
        st.stop()

    try:
        df = pd.read_csv(file_name, encoding='utf-8', header=0, delimiter=',')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_name, encoding='utf_8_sig', header=0, delimiter=',')
        except Exception as e:
            st.error(f"❌ CSV/TSVファイルのエンコーディングを自動判別できませんでした。エラー: {e}")
            st.info("ファイルがUTF-8 (BOMなし/あり) で保存されているか確認してください。")
            st.stop()
    
    required_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分", "出題確率（推定）", "シラバス改定有無", "改定の意図・影響", "〇×結果"]

    if not all(col in df.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in df.columns]
        st.error(f"❌ '{file_name}' に必要な列が不足しています。不足している列: {', '.join(missing_cols)}")
        st.stop()
    
    app = QuizApp(df)
    app.run()
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("データファイルの内容を確認してください。列名やデータ形式が正しいか、ファイルが破損していないか確認してください。")
