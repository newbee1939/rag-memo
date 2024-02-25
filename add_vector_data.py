import logging
import os
import pinecone
import shutil
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import GitLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    pinecone.init(
        api_key=os.environ["PINECONE_API_KEY"],
        environment=os.environ["PINECONE_ENV"],
    )

    index_name = os.environ["PINECONE_INDEX"]

    if index_name in pinecone.list_indexes():
        # 全てのVector Dataを削除
        pinecone.delete_index(index_name)

    pinecone.create_index(name=index_name, metric="cosine", dimension=1536)

    clone_url = "https://github.com/newbee1939/memo"
    branch = "main"
    repo_path = "./tmp/"
    filter_ext = ".md"

    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)

    loader = GitLoader(
        clone_url=clone_url,
        branch=branch,
        repo_path=repo_path,
        file_filter=lambda file_path: file_path.endswith(filter_ext),
    )

    raw_docs = loader.load()

    # 読み込んだドキュメントの数をログに記録
    logger.info("Loaded %d documents", len(raw_docs))

    # ドキュメントを分割
    text_splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    docs = text_splitter.split_documents(raw_docs)

    # 分割したドキュメントの数をログに記録
    logger.info("Split %d documents", len(docs))

    # 分割されたドキュメントをPineconeに追加
    embeddings = OpenAIEmbeddings()
    vectorstore = Pinecone.from_existing_index(index_name, embeddings)

    vectorstore.add_documents(docs)
