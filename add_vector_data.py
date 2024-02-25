# Gitリポジトリから埋め込み表現（Embeddings）を取得してPineconeに保存する
import logging # ロギング機能を提供するPythonの標準ライブラリ
import os # オペレーティングシステムとやり取りするための機能を提供するPythonの標準ライブラリ

import pinecone
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import GitLoader
from initialize_vectorstore import initialize_vectorstore

# .envファイルから環境変数を読み込む
load_dotenv()

# ロギング設定を行う。ログのフォーマットとログレベルを指定する
# https://www.tohoho-web.com/python/logging.html#format
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", 
    level=logging.INFO
)
# loggerオブジェクトを作成する
# 引数はロガー名、__name__はモジュール名
logger = logging.getLogger(__name__)

def __delete_all_vector_data():
    index_name = os.environ["PINECONE_INDEX"]

    if index_name in pinecone.list_indexes():
        pinecone.delete_index(index_name)

    pinecone.create_index(name=index_name, metric="cosine", dimension=1536)

# GitLoaderで対象のリポジトリを読み込み、CharacterTextSplitterで分割して、Pineconeに保存する
if __name__ == "__main__":
    # 全てのVector Dataを全て消す
    __delete_all_vector_data()

    clone_url = "https://github.com/newbee1939/memo"
    branch = "main"
    repo_path = "./tmp/"
    filter_ext = ".md"

    if os.path.exists(repo_path):
        clone_url = None

    loader = GitLoader(
        clone_url=clone_url,
        branch=branch,
        repo_path=repo_path,
        file_filter=lambda file_path: file_path.endswith(filter_ext),
    )

    raw_docs = loader.load()

    # 読み込んだドキュメントの数をログに記録する
    logger.info("Loaded %d documents", len(raw_docs))

    # CharacterTextSplitterを使用してドキュメントを分割する
    text_splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    docs = text_splitter.split_documents(raw_docs)

    # 分割したドキュメントの数をログに記録する
    logger.info("Split %d documents", len(docs))

    # ベクトルストアを初期化する
    vectorstore = initialize_vectorstore()

    # 分割されたドキュメントをPineconeに追加する
    # P212: 重複登録されないために対策が必要
    vectorstore.add_documents(docs)
