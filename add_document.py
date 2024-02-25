# Gitリポジトリから埋め込み表現（Embeddings）を取得してPineconeに保存する
import logging # ロギング機能を提供するPythonの標準ライブラリ
import os # オペレーティングシステムとやり取りするための機能を提供するPythonの標準ライブラリ

import pinecone
from dotenv import load_dotenv
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Pinecone
from langchain.document_loaders import GitLoader

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

# PineconeをLangChainのVectors storeとして使う準備を整える関数
def initialize_vectorstore():
    # Pineconeに接続し、APIキーと環境を設定する
    pinecone.init(
        api_key=os.environ["PINECONE_API_KEY"],
        environment=os.environ["PINECONE_ENV"],
    )

    # インデックス名を取得し、OpenAIEmbeddingsを用いてPineconeに既存のインデックスを作成する
    index_name = os.environ["PINECONE_INDEX"]
    # OpenAI の埋め込み（ベクトル表現）を取得します。これは、テキストや単語などの自然言語処理タスクで使用されるテキストデータの特徴を表現するベクトルです。
    # 例えば、ある単語が他の単語とどの程度関連しているかを数値化することができます
    embeddings = OpenAIEmbeddings()
    return Pinecone.from_existing_index(index_name, embeddings)

# GitLoaderで対象のリポジトリを読み込み、CharacterTextSplitterで分割して、Pineconeに保存する
if __name__ == "__main__":
    clone_url = "https://github.com/newbee1939/memo"
    branch = "main"
    repo_path = "./"
    filter_ext = ".md"

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
