import streamlit as st
import pandas as pd
import random
import os
import plotly.express as px # グラフ描画用にPlotlyをインポート

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
            "history": [], # 全回答履歴（詳細ログ用）
            "current_round": 1, # 1～15列の記録に使用する現在の回数インデックス (ループなし)
            "quiz_df": None # 更新されたクイズデータを保持するDataFrame
        }
        self._initialize_session()

        # アプリ初回起動時、またはセッションリセット時にquiz_dfを初期化
        if st.session_state.quiz_df is None:
            st.session_state.quiz_df = df.copy()
            # 1～15列を文字列型に変換（〇×を格納するため）し、NaNを空文字列に変換
            for i in range(1, 16):
                col_name = str(i)
                if col_name in st.session_state.quiz_df.columns:
                    st.session_state.quiz_df[col_name] = st.session_state.quiz_df[col_name].astype(str).replace('nan', '')
            
            # 各単語の「正解回数」と「不正解回数」を初期化する新しい列を追加
            # これらはアプリ内部で統計情報として利用され、CSVに直接書き込まれるわけではないが、ダウンロード時には含まれる
            st.session_state.quiz_df['正解回数'] = 0
            st.session_state.quiz_df['不正解回数'] = 0

            # 既存の1～15列の〇×を基に初期の正解・不正解回数を計算
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
                
        # initial_dfはセッションリセット用に元のDataFrameを保持
        # これには初期状態のデータのみが含まれ、正解回数/不正解回数の列は含まれない
        self.initial_df = df.copy() 

    def _initialize_session(self):
        """Streamlitのセッション状態を初期化またはデフォルト値に設定します。"""
        for key, val in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val
            # answered_wordsがセット型であることを保証
            if key == "answered_words" and not isinstance(st.session_state[key], set):
                st.session_state[key] = set(st.session_state[key])

    def _reset_session_state(self):
        """セッション状態をデフォルト値にリセットします。
        quiz_dfも初期読み込み時の状態に戻し、統計情報を再計算します。
        """
        st.session_state.quiz_df = self.initial_df.copy()
        for i in range(1, 16):
            col_name = str(i)
            if col_name in st.session_state.quiz_df.columns:
                st.session_state.quiz_df[col_name] = st.session_state.quiz_df[col_name].astype(str).replace('nan', '')
        
        # リセット時も正解・不正解回数列を初期化し、既存の〇×から再計算
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
            if key != "quiz_df": # quiz_dfは上記で初期化済みなのでスキップ
                st.session_state[key] = val if not isinstance(val, set) else set()
        st.success("✅ セッションをリセットしました")
        st.rerun()

    def filter_data(self):
        """ユーザーの選択に基づいてデータをフィルタリングし、Streamlitのselectboxを更新します。"""
        current_category = st.session_state.get("filter_category", "すべて")
        current_field = st.session_state.get("filter_field", "すべて")
        current_level = st.session_state.get("filter_level", "すべて")

        # フィルタリングオプションはquiz_dfから取得
        category_options = ["すべて"] + sorted(st.session_state.quiz_df["カテゴリ"].dropna().unique())
        field_options = ["すべて"] + sorted(st.session_state.quiz_df["分野"].dropna().unique())
        level_options = ["すべて"] + sorted(st.session_state.quiz_df["試験区分"].dropna().unique())

        # selectboxの表示と、現在の選択をセッション状態に保存
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

        # まだ回答していない単語に限定
        remaining = df_filtered[~df_filtered["単語"].isin(st.session_state.answered_words)]
        
        return df_filtered, remaining

    def show_progress(self, df_filtered):
        """現在の学習進捗（回答数、正解数、現在の記録列）を表示します。"""
        st.markdown(f"📊 **進捗：{len(st.session_state.answered_words)} / {len(df_filtered)} 語**")
        st.markdown(f"🔁 **総回答：{st.session_state.total} 回 / 🎯 正解：{st.session_state.correct} 回**")
        display_round = min(st.session_state.current_round, 15) # 15回目以降は「15回目」と表示
        st.markdown(f"🗓️ **現在の記録列：{display_round}回目**")

    def load_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """新しいクイズをロードし、セッション状態を更新します。不正解回数に基づいて出題します。"""
        if not remaining_df.empty:
            # 不正解回数を重みとして使用 (不正解回数 + 1 で、最低重み1を保証)
            weights = (remaining_df['不正解回数'] + 1).tolist()
            
            # 重みの合計が0になることを避ける（通常は発生しないが安全のため）
            if sum(weights) == 0:
                q = remaining_df.sample(1).iloc[0] # 重み付けできない場合はランダム
            else:
                q = remaining_df.sample(weights=weights, n=1).iloc[0]

            correct_description = q["説明"]

            # 正解以外の選択肢をプールから選び、3つに制限
            wrong_options_pool = df_filtered[df_filtered["説明"] != correct_description]["説明"].drop_duplicates().tolist()
            num_wrong_options = min(3, len(wrong_options_pool))
            wrong_options = random.sample(wrong_options_pool, num_wrong_options)

            # 正解と不正解の選択肢を混ぜてシャッフル
            options = wrong_options + [correct_description]
            random.shuffle(options)

            # 現在のクイズ情報をセッション状態に保存
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
            st.session_state.quiz_answered = False # 回答前状態にリセット
            st.session_state.quiz_choice_index = 0 # 選択肢インデックスをリセット
            st.session_state.latest_result = "" # 結果メッセージをクリア
            st.session_state.latest_correct_description = "" # 正解説明をクリア
        else:
            st.session_state.current_quiz = None # 出題する問題がない場合

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
        st.session_state.total += 1 # 総回答数をインクリメント
        st.session_state.answered_words.add(current_quiz_data["単語"]) # 回答済み単語に追加

        is_correct = (selected_option_text == current_quiz_data["説明"]) # 正誤判定
        result_mark = "〇" if is_correct else "×" # 〇または×

        st.session_state.latest_correct_description = current_quiz_data['説明'] # 正解の説明を保存

        st.session_state.latest_result = (
            "✅ 正解！🎉" if is_correct
            else f"❌ 不正解…"
        )
        st.session_state.correct += 1 if is_correct else 0 # 正解数を更新

        # --- 実施回数列（1～15列）と正解・不正解回数の更新ロジック ---
        temp_df = st.session_state.quiz_df.copy() # quiz_dfをコピーして更新

        word = current_quiz_data["単語"]
        if word in temp_df["単語"].values:
            idx = temp_df[temp_df["単語"] == word].index[0] # 該当する単語の行インデックスを取得
            
            # 1～15列への〇×記録: current_roundが15を超えたら、常に15列目に記録
            column_to_update = str(min(st.session_state.current_round, 15))
            if column_to_update in temp_df.columns:
                temp_df.at[idx, column_to_update] = result_mark # 〇または×を書き込む
            else:
                st.warning(f"警告: 列 '{column_to_update}' がDataFrameに見つかりません。CSVファイルを確認してください。")
            
            # 正解回数・不正解回数の更新
            if is_correct:
                temp_df.at[idx, '正解回数'] += 1
            else:
                temp_df.at[idx, '不正解回数'] += 1
        
        st.session_state.quiz_df = temp_df # 更新したDataFrameをセッション状態に戻す

        # current_round をインクリメント (15を超えても増え続けるが、記録は15列目)
        st.session_state.current_round += 1
        # --- 実施回数列と正解・不正解回数の更新ロジックここまで ---

        # 回答履歴ログに追加
        try:
            choice_kana = self.kana_labels[current_quiz_data["選択肢"].index(selected_option_text)]
        except ValueError:
            choice_kana = "不明" # 選択肢がリストに見つからない場合
        
        try:
            correct_kana = self.kana_labels[current_quiz_data["選択肢"].index(current_quiz_data["説明"])]
        except ValueError:
            correct_kana = "不明" # 正解選択肢がリストに見つからない場合

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
        st.session_state.quiz_answered = True # 回答済みフラグをTrueに

    def _display_result_and_next_button(self):
        """回答結果メッセージと次の問題へ進むボタンを表示します。"""
        st.info(st.session_state.latest_result) # 結果メッセージ表示
        st.markdown(f"💡 **説明:** {st.session_state.latest_correct_description}") # 正解の説明表示

        if st.button("➡️ 次の問題へ"): # 「次の問題へ」ボタン
            st.session_state.current_quiz = None # 現在のクイズをクリア
            st.session_state.quiz_answered = False # 回答済みフラグをリセット
            st.rerun() # アプリを再実行して次の問題をロード

    def display_quiz(self, df_filtered: pd.DataFrame, remaining_df: pd.DataFrame):
        """クイズの質問と選択肢を表示し、回答を処理します。"""
        q = st.session_state.current_quiz
        if not q:
            return

        self._display_quiz_question() # 問題の表示

        labeled_options = [f"{self.kana_labels[i]}：{txt}" for i, txt in enumerate(q["選択肢"])] # 選択肢にカナラベルを付与

        # ラジオボタンで選択肢を表示。回答済みなら無効化。
        selected_labeled_option = st.radio(
            "選択肢を選んでください",
            labeled_options,
            index=st.session_state.quiz_choice_index,
            key=f"quiz_radio_{st.session_state.total}", # ユニークなキーを生成
            disabled=st.session_state.quiz_answered # 回答済みなら選択不可
        )

        selected_option_index = labeled_options.index(selected_labeled_option)
        selected_option_text = q["選択肢"][selected_option_index]

        # 選択肢が変更された場合、セッション状態を更新
        if st.session_state.quiz_choice_index != selected_option_index and not st.session_state.quiz_answered:
            st.session_state.quiz_choice_index = selected_option_index

        if not st.session_state.quiz_answered: # 未回答の場合のみ「答え合わせ」ボタンを表示
            if st.button("✅ 答え合わせ"):
                self._handle_answer_submission(selected_option_text, q) # 回答処理を実行
                st.rerun() # アプリを再実行して結果を表示
        else: # 回答済みの場合、結果表示と次の問題ボタンを表示
            self._display_result_and_next_button()

    def show_completion(self):
        """すべての問題に回答した際のメッセージを表示します。"""
        st.success("🎉 すべての問題に回答しました！")
        st.balloons() # バルーンアニメーション

    def offer_download(self):
        """現在の学習データと回答履歴のCSVダウンロードボタンを提供します。"""
        # 現在の更新された学習データ（quiz_df）をダウンロード（〇×と統計情報含む）
        csv_quiz_data = st.session_state.quiz_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 **現在の学習データをダウンロード** (〇×・統計含む)", data=csv_quiz_data, file_name="updated_tango_data_with_stats.csv", mime="text/csv")
        
        # 個別の回答履歴もダウンロード
        df_log = pd.DataFrame(st.session_state.history or [])
        if not df_log.empty:
            csv_history = df_log.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("📥 回答履歴をダウンロード", data=csv_history, file_name="quiz_results.csv", mime="text/csv")
        else:
            st.info("まだ回答履歴がありません。")

    def reset_session_button(self):
        """セッションをリセットするためのボタンを表示します。"""
        if st.button("🔁 セッションをリセット"):
            self._reset_session_state()

    def display_statistics(self):
        """学習統計情報（全体の正答率、苦手な単語トップ5、カテゴリ別/分野別正答率グラフ）を表示します。"""
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
        # フィルタリングされたデータ（quiz_df）の中から、かつ回答済みの単語のみを対象に統計をとる
        answered_df = st.session_state.quiz_df[st.session_state.quiz_df["単語"].isin(st.session_state.answered_words)].copy()

        if not answered_df.empty:
            # 不正解回数が1以上のものを対象にする、または0でも含めてランキング（今回は0でも含めて表示）
            top_5_difficult = answered_df.sort_values(by='不正解回数', ascending=False).head(5)
            
            if not top_5_difficult.empty:
                for idx, row in top_5_difficult.iterrows():
                    total_attempts = row['正解回数'] + row['不正解回数']
                    if total_attempts > 0: # 回答がある場合のみ正答率を計算
                        accuracy = (row['正解回数'] / total_attempts) * 100
                        st.write(f"**{row['単語']}**: 不正解 {row['不正解回数']}回 / 正解 {row['正解回数']}回 (正答率: {accuracy:.1f}%)")
                    else: # まだ回答数0だがリストアップされた場合
                        st.write(f"**{row['単語']}**: まだ回答していません。")
            else:
                st.info("まだ苦手な単語はありません。") # (should not happen if answered_df is not empty)
        else:
            st.info("まだ回答した単語がありません。")

        st.markdown("---")

        # カテゴリ別・分野別の正答率グラフ
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
        
        # 回答数があるカテゴリのみ表示対象とする
        category_stats_filtered = category_stats[category_stats['total_attempts'] > 0].sort_values(by='正答率', ascending=True)

        if not category_stats_filtered.empty:
            st.write("###### カテゴリ別")
            fig_category = px.bar(
                category_stats_filtered, 
                x='カテゴリ', 
                y='正答率', 
                color='正答率', # 正答率によってバーの色が変わる
                color_continuous_scale=px.colors.sequential.Viridis, # 配色
                title='カテゴリ別 正答率',
                labels={'正答率': '正答率 (%)'},
                text_auto='.1f' # グラフに値を直接表示 (小数点以下1桁)
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

        # 回答数がある分野のみ表示対象とする
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

        # カスタムCSSスタイリング
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

        # フィルタリングオプションと進捗表示
        df_filtered, remaining_df = self.filter_data()
        self.show_progress(df_filtered)

        # 統計表示は展開可能なセクションに格納
        with st.expander("📊 **学習統計を表示**"):
            self.display_statistics()

        # 読み込みデータの確認も展開可能セクションに
        with st.expander("📂 **読み込みデータの確認**"):
            st.dataframe(st.session_state.quiz_df.head()) # quiz_dfの現在の状態を表示

        # クイズのロードと表示
        if st.session_state.current_quiz is None and not remaining_df.empty:
            self.load_quiz(df_filtered, remaining_df)

        if remaining_df.empty and st.session_state.current_quiz is None:
            self.show_completion() # すべての問題に回答済み
        elif st.session_state.current_quiz:
            self.display_quiz(df_filtered, remaining_df) # クイズを表示

        # データダウンロードとセッションリセットボタン
        self.offer_download()
        st.markdown("---")
        self.reset_session_button()

# --- アプリ実行部分 ---
try:
    if not os.path.exists("tango.csv"):
        st.error("❌ 'tango.csv' が見つかりません。")
        info_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分", "出題確率（推定）", "シラバス改定有無", "改定の意図・影響"] + [str(i) for i in range(1, 16)]
        st.info(f"必要な列：{', '.join(info_columns)}")
        st.stop()

    df = pd.read_csv("tango.csv")
    
    # 必要な列がCSVに存在するかチェック
    required_columns = ["カテゴリ", "分野", "単語", "説明", "午後記述での使用例", "使用理由／文脈", "試験区分", "出題確率（推定）", "シラバス改定有無", "改定の意図・影響"]
    for i in range(1, 16):
        required_columns.append(str(i))

    if not all(col in df.columns for col in required_columns):
        st.error(f"❌ 'tango.csv' に必要な列が不足しています。不足している列: {', '.join([col for col in required_columns if col not in df.columns])}")
        st.stop()
    
    app = QuizApp(df)
    app.run()
except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("データファイル 'tango.csv' の内容を確認してください。列名やデータ形式が正しいか、CSVが破損していないか確認してください。")
