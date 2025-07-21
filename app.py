import streamlit as st
import pandas as pd
import io

# --- 1. セッションステートの初期化 ---
# アプリケーションが初回起動時、またはリロード時にのみ実行される
if 'main_data_source_radio' not in st.session_state:
    st.session_state.main_data_source_radio = "ファイルから選択" # デフォルトの選択肢

if 'uploaded_file_content' not in st.session_state:
    st.session_state.uploaded_file_content = None # アップロードされたファイルの内容
    
if 'data_frame' not in st.session_state:
    st.session_state.data_frame = None # 読み込まれたデータフレーム

# --- 2. コールバック関数の定義 ---
def on_data_source_change():
    """
    データソースのラジオボタンが変更されたときに呼び出される関数。
    選択が変わった際に、関連するセッションステートをリセットします。
    これにより、例えば「ファイルから選択」から「データベースから」に変えたときに、
    以前アップロードしたファイルの情報が残らないようにします。
    """
    st.session_state.uploaded_file_content = None
    st.session_state.data_frame = None
    st.info(f"データソースが '{st.session_state.main_data_source_radio}' に変更されました。")
    # 必要であれば、ここで追加の初期化処理やメッセージ表示を行う

def process_uploaded_file(uploaded_file):
    """
    アップロードされたファイルを処理し、セッションステートにデータフレームとして保存する関数。
    """
    if uploaded_file is not None:
        try:
            # ファイルの拡張子に基づいて読み込み方法を決定
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension == 'csv':
                df = pd.read_csv(uploaded_file)
            elif file_extension in ['xls', 'xlsx']:
                df = pd.read_excel(uploaded_file)
            else:
                st.error("サポートされていないファイル形式です。CSVまたはExcelファイルをアップロードしてください。")
                st.session_state.data_frame = None
                return
            
            st.session_state.data_frame = df
            st.session_state.uploaded_file_content = uploaded_file # ファイルオブジェクト自体も保存（必要であれば）
            st.success(f"ファイル '{uploaded_file.name}' が正常に読み込まれました！")
            
        except Exception as e:
            st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
            st.session_state.data_frame = None
            st.session_state.uploaded_file_content = None
    else:
        st.session_state.data_frame = None
        st.session_state.uploaded_file_content = None

# --- 3. Streamlit UIの構築 ---
st.set_page_config(layout="wide") # ページレイアウトを広げる
st.title("多機能データビューア")

st.markdown("---")

# データソース選択ラジオボタン
st.header("1. データソースを選択")
selected_source = st.radio(
    "データをどこから取得しますか？",
    ("ファイルから選択", "データベースから取得", "APIから取得"),
    key='main_data_source_radio', # セッションステートのキーと紐付け
    on_change=on_data_source_change # 変更時にコールバック関数を呼び出す
)

st.markdown("---")

# 選択されたデータソースに応じたUIとロジック
st.header("2. データ取得と表示")

if st.session_state.main_data_source_radio == "ファイルから選択":
    st.subheader("CSV/Excelファイルのアップロード")
    uploaded_file = st.file_uploader(
        "ここにCSVまたはExcelファイルをドラッグ＆ドロップしてください",
        type=["csv", "xls", "xlsx"],
        key="file_uploader" # アップローダーウィジェットにもキーを設定
    )
    
    # ファイルがアップロードされたら処理
    if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file_content:
        # 新しいファイルがアップロードされた場合のみ処理を実行
        # (すでに同じファイルが選択されている場合は再処理しない)
        process_uploaded_file(uploaded_file)
    elif st.session_state.data_frame is not None:
        st.info(f"現在、ファイル '{st.session_state.uploaded_file_content.name}' が読み込まれています。")
    elif uploaded_file is None and st.session_state.uploaded_file_content is None:
        st.info("ファイルが選択されていません。")

elif st.session_state.main_data_source_radio == "データベースから取得":
    st.subheader("データベース接続設定")
    st.warning("この機能は現在開発中です。")
    # ここにデータベース接続のための入力フィールドやボタンを追加
    # 例: db_host = st.text_input("ホスト名")
    #     db_user = st.text_input("ユーザー名")
    #     if st.button("データベースに接続"):
    #         # データベース接続ロジック
    st.session_state.data_frame = None # データソースが変わったのでデータをクリア

elif st.session_state.main_data_source_radio == "APIから取得":
    st.subheader("APIエンドポイント設定")
    st.warning("この機能は現在開発中です。")
    # ここにAPIキーやエンドポイントの入力フィールドを追加
    # 例: api_key = st.text_input("APIキー")
    #     endpoint = st.text_input("APIエンドポイント")
    #     if st.button("APIからデータを取得"):
    #         # API呼び出しロジック
    st.session_state.data_frame = None # データソースが変わったのでデータをクリア

st.markdown("---")

# --- 4. データの表示 ---
st.header("3. 読み込まれたデータ")

if st.session_state.data_frame is not None:
    st.subheader("データプレビュー")
    st.write(f"データには **{st.session_state.data_frame.shape[0]} 行**、**{st.session_state.data_frame.shape[1]} 列** があります。")
    st.dataframe(st.session_state.data_frame.head()) # 最初の5行を表示
    
    # 簡易統計情報
    st.subheader("簡易統計情報")
    st.write(st.session_state.data_frame.describe())
    
    # ダウンロードボタン
    csv_data = st.session_state.data_frame.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="CSVとしてダウンロード",
        data=csv_data,
        file_name="processed_data.csv",
        mime="text/csv",
    )
else:
    st.info("データを読み込んでください。")

st.markdown("---")
st.caption("powered by Streamlit & Pandas")
