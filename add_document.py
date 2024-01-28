# PDFファイルのテキストから埋め込み表現（Embeddings）を取得してPineconeに保存する
import logging
import os
import sys

import pinecone
from dotenv import load_dotenv
from langchain.document_loaders import UnstructuredPDFLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Pinecone

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# PineconeをLangChainのVectors storeとして使う準備を整える関数
def initialize_vectorstore():
    pinecone.init(
        api_key=os.environ["PINECONE_API_KEY"],
        environment=os.environ["PINECONE_ENV"],
    )

    index_name = os.environ["PINECONE_INDEX"]
    embeddings = OpenAIEmbeddings()
    return Pinecone.from_existing_index(index_name, embeddings)