import streamlit as st
import pandas as pd
import random
import os
import datetime

# QuizAppクラスの定義は変更なし。
# 前回の回答で提供したQuizAppクラスのコードをそのまま使用してください。
# ここではmain関数のみを提示します。

def main():
    st.set_page_config(layout="wide", page_title="IT用語クイズアプリ", page_icon="📝")

    csv_path = os.path.join(os.path.dirname(__file__), 'tango.csv')
    if not os.path.exists(csv_path):
        st.error(f"エラー: tango.csv が見つかりません。パス: {csv_path}")
        st.stop()

    try:
        original_df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"初期データの読み込み中にエラーが発生しました: {e}")
        st.stop()

    quiz_app = QuizApp(original_df)

    st.title("📝 IT用語クイズアプリ")
    st.markdown("毎日少しずつIT用語を学習し、知識を定着させましょう！")

    st.sidebar.header("設定とデータ")
    
    data_source_options_radio = ["アップロード", "初期データ"]
    selected_source_radio = st.sidebar.radio(
        "📚 **使用するデータソースを選択**",
        options=data_source_options_radio,
        key="main_data_source_radio",
        index=data_source_options_radio.index(st.session_state.data_source_selection) if st.session_state.data_source_selection in data_source_options_radio else 0
    )

    if selected_source_radio != st.session_state.data_source_selection:
        st.session_state.data_source_selection = selected_source_radio
        
        if st.session_state.data_source_selection == "初期データ":
            quiz_app._initialize_quiz_df_from_original()
            st.sidebar.success("✅ 初期データに切り替えました。")
            st.session_state.uploaded_df_temp = None
            st.session_state.uploaded_file_name = None
            st.session_state.uploaded_file_size = None
        else: # "アップロード"が選択された場合
            if st.session_state.uploaded_df_temp is not None:
                st.session_state.quiz_df = st.session_state.uploaded_df_temp.copy()
                st.session_state.answered_words = set(st.session_state.quiz_df[
                    (st.session_state.quiz_df['正解回数'] > 0) | (st.session_state.quiz_df['不正解回数'] > 0)
                ]["単語"].tolist())
                st.sidebar.success(f"✅ アップロードされたデータ ({st.session_state.uploaded_file_name}) を適用しました。")
            else:
                st.sidebar.info("ファイルをアップロードしてください。")
                quiz_app._initialize_quiz_df_from_original() 
        
        for key in ["total", "correct", "latest_result", "latest_correct_description",
                    "current_quiz", "quiz_answered", "quiz_choice_index",
                    "filter_category", "filter_field", "filter_level"]:
            if key in quiz_app.defaults:
                st.session_state[key] = quiz_app.defaults[key] if not isinstance(quiz_app.defaults[key], set) else set()
        
        st.rerun()

    st.sidebar.markdown("---")

    if st.session_state.data_source_selection == "アップロード":
        quiz_app.upload_data() 
    
    st.sidebar.markdown("---")

    quiz_app.offer_download()

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 **現在のデータの学習履歴をリセット**", help="現在使用しているデータソースの学習の進捗（正解/不正解回数、回答済み単語）を初期状態に戻します。", key="reset_button"):
        quiz_app._reset_session_state()

    st.sidebar.markdown("---")
    st.sidebar.header("クイズの絞り込み")
    
    df_filtered = pd.DataFrame()
    remaining_df = pd.DataFrame()
    if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
        df_filtered, remaining_df = quiz_app.filter_data()
    else:
        st.sidebar.warning("有効な学習データがロードされていません。")

    # 💡 修正点: クイズ開始ボタンのロジックを統合し、より汎用的にする
    if st.session_state.current_quiz is None: # まだクイズが始まっていない場合のみボタンを表示
        if not df_filtered.empty and len(remaining_df) > 0:
            # データソースの種類に関わらず、利用可能な問題があればボタンを表示
            # アップロードと初期データでキーを分ける
            button_key = "sidebar_start_quiz_button_initial" if st.session_state.data_source_selection == "初期データ" else "sidebar_start_quiz_button_uploaded"
            if st.sidebar.button("▶️ **クイズ開始**", key=button_key):
                quiz_app.load_quiz(df_filtered, remaining_df)
                st.rerun()
        elif len(df_filtered) > 0 and len(remaining_df) == 0:
             st.sidebar.info("現在のフィルター条件のすべての問題に回答しました。")
        # elif len(df_filtered) == 0: # この条件は "有効な学習データがロードされていません。" でカバーされる
        #      st.sidebar.info("現在のフィルター条件に一致する単語がありません。")

    st.sidebar.markdown("---")

    quiz_app.show_progress(df_filtered)

    if st.session_state.quiz_df.empty:
        st.info("クイズを開始するには、まず有効な学習データをロードしてください。")
    elif st.session_state.current_quiz is None:
        if len(df_filtered) > 0 and len(remaining_df) > 0:
            st.info("データがロードされました！サイドバーの「クイズ開始」ボタンをクリックしてください。")
        elif len(df_filtered) > 0 and len(remaining_df) == 0:
            quiz_app.show_completion()
        else:
            st.info("現在のフィルター条件に一致する単語がないか、データがありません。フィルターを変更するか、新しいデータをアップロードしてください。")
    else:
        quiz_app.display_quiz(df_filtered, remaining_df)
    
    st.markdown("---")
    if st.session_state.quiz_df is not None and not st.session_state.quiz_df.empty:
        quiz_app.display_statistics()

if __name__ == "__main__":
    main()
