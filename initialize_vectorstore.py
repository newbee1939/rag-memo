import os

import pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone

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