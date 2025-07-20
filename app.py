import streamlit as st
import os
import sys
import platform
import subprocess
import logging
import datetime
import importlib.metadata # Python 3.8+ for package versions

# --- ロギング設定 (Streamlit CloudのLogsに出力されます) ---
# アプリケーションのログレベルをDEBUGに設定
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("--- Streamlit Debug App Started ---")

# --- UI上へのデバッグ情報出力 ---
st.set_page_config(layout="wide", page_title="デバッグ情報アプリ")

st.title("🚀 Streamlit デプロイ デバッグ情報")
st.write("このアプリは、デプロイ環境での問題を診断するための情報を提供します。")
st.write("---")

st.header("1. 環境変数 (Env Vars)")
st.info("⚠ 重要: 機密情報はst.secrets['key']で安全に管理してください。ここでは環境変数の一部のみ表示します。")
if st.checkbox("環境変数を表示"):
    env_vars = os.environ
    for key, value in env_vars.items():
        # 機密性の高い情報を表示しないようにフィルタリング
        if any(secret_word in key.lower() for secret_word in ["key", "password", "token", "secret", "cred"]):
            st.write(f"**{key}**: *********")
        else:
            st.write(f"**{key}**: {value}")

st.write("---")

st.header("2. Python 環境情報")
st.write(f"**Python バージョン**: {sys.version}")
st.write(f"**Python 実行可能パス**: {sys.executable}")
st.write(f"**プラットフォーム**: {platform.platform()}")
st.write(f"**現在の作業ディレクトリ**: {os.getcwd()}")
st.write(f"**Python パス (sys.path)**:")
for p in sys.path:
    st.write(f"- `{p}`")

st.write("---")

st.header("3. インストール済みパッケージ")
st.info("特に 'streamlit' や 'requirements.txt' に記載したパッケージのバージョンを確認してください。")
if st.checkbox("インストール済みパッケージ一覧を表示"):
    try:
        # pip freeze の代わりに importlib.metadata を使用 (よりプログラム的)
        installed_packages = {dist.name: dist.version for dist in importlib.metadata.distributions()}
        for pkg, ver in sorted(installed_packages.items()):
            st.write(f"- `{pkg}=={ver}`")
        logger.info("Successfully listed installed packages.")
    except Exception as e:
        st.error(f"パッケージ一覧の取得中にエラーが発生しました: {e}")
        logger.error(f"Failed to list packages: {e}")
    
    # 伝統的な pip freeze --local も試す (subprocess 実行)
    st.subheader("`pip freeze --local` の出力 (参考)")
    try:
        pip_freeze_output = subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--local"]).decode("utf-8")
        st.code(pip_freeze_output)
        logger.info("Successfully executed 'pip freeze --local'.")
    except Exception as e:
        st.error(f"pip freeze の実行中にエラーが発生しました: {e}")
        logger.error(f"Failed to execute 'pip freeze --local': {e}")


st.write("---")

st.header("4. ファイルシステムの内容 (重要)")
st.warning("このセクションでファイルが見つからない場合、パスの問題が疑われます。")
st.write(f"**アプリの実行パス**: `{os.path.dirname(__file__)}`") # スクリプト自身のディレクトリ

# リポジトリのルート (通常は /mount/src/your-repo-name) を確認
repo_root = "/mount/src/" + os.path.basename(os.getcwd()) # あるいは os.path.dirname(os.path.abspath(__file__))

st.write(f"**推定されるリポジトリのルート**: `{repo_root}`")

# 特定のディレクトリの内容を表示する関数
def list_directory_contents(path):
    st.subheader(f"ディレクトリ `{path}` の内容:")
    try:
        if not os.path.exists(path):
            st.error(f"パス '{path}' は存在しません。")
            logger.warning(f"Path does not exist: {path}")
            return
        
        contents = os.listdir(path)
        if not contents:
            st.write("(このディレクトリは空です)")
            logger.info(f"Directory {path} is empty.")
        for item in contents:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                st.write(f"- 📂 `{item}/`")
            else:
                st.write(f"- 📄 `{item}`")
        logger.info(f"Successfully listed contents of {path}.")
    except Exception as e:
        st.error(f"ディレクトリの内容を読み取る際にエラーが発生しました: {e}")
        logger.error(f"Error listing directory contents for {path}: {e}")

# 確認したいパスをここに追加
list_directory_contents(repo_root) # リポジトリのルート
list_directory_contents(os.path.join(repo_root, 'data')) # もし 'data' フォルダがある場合
# list_directory_contents('/tmp') # 一時ファイルを確認する場合など

st.write("---")

st.header("5. 現在時刻")
st.write(f"アプリ実行時の現在時刻: {datetime.datetime.now()}")

st.write("---")

st.header("6. カスタムコードチェック (例)")
# ここにあなたの元のアプリの特定のコードスニペットをコピー＆ペーストして、
# エラーが出ないか確認するデバッグブロックを記述します。
# 例: データファイルの読み込み
try:
    # 例: もし 'data' フォルダに 'my_quiz_data.csv' があるなら
    # import pandas as pd
    # df = pd.read_csv(os.path.join(repo_root, 'data', 'my_quiz_data.csv'))
    # st.success(f"データファイル 'my_quiz_data.csv' を正常に読み込みました。行数: {len(df)}")
    # logger.info("Data file loaded successfully.")
    st.info("ここにあなたのコードの一部を貼り付けてテストできます。")
except FileNotFoundError:
    st.error("データファイルが見つかりません。ファイルパスを確認してください。")
    logger.error("Data file not found error.")
except Exception as e:
    st.error(f"カスタムコード実行中にエラーが発生しました: {e}")
    logger.error(f"Error in custom code execution: {e}")

logger.info("--- Streamlit Debug App Finished ---")

# --- アプリのクラッシュテスト (オプション) ---
# st.button("アプリを意図的にクラッシュさせる (ログを確認)")
# if st.button("クラッシュテスト"):
#     raise Exception("これは意図的なクラッシュです。ログに表示されるか確認してください。")
