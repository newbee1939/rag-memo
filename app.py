# 質問に関連した文書をPineconeから検索して応答する
from add_document import initialize_vectorstore
from langchain.chains import RetrievalQA
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event["ts"]
    message = re.sub("<@.*", "", event["text"])

    # 投稿の先頭（=Momentoキー）を示す: 初回はevent["ts"], 2回目以降はevent["thread_ts"]
    id_ts = event["ts"]
    if "thread_ts" in event:
        id_ts = event["tread_ts"]
        result = say("\n^nTyping...", thread_ts=thread_ts)
        ts = result["ts"]

        history = MomentoChaMessageHistory.from_client_params(
            id_ts,
            os.environ["MOMENTO_CACHE"],
            timedelta(hours=int(os.environ["MOMENTO_TTL"])),
        ) 
        memory = ConversationBufferMemory(
            chat_memory=history, memory_key="chat_history", return_messages=True
        )

        vectorstore = initialize_vectorstore()

        callback = SlackStreamingCallbackHandler(channel=channel, ts=ts)
        llm = ChatOpenAI(
            model_name=os.environ["OPENAI_API_MODEL"],
            temperature=os.environ["OPENAI_API_TEMPERATURE"],
            streaming=True,
            callbacks=[callback]
        )

        condense_question_llm = ChatOpenAI(
            model_name=os.environ["OPENAI_API_MODEL"],
            temperature=os.environ["OPENAI_API_TEMPERATURE"],
        )

        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            memory=memory,
            condense_question_llm=condense_question_llm,
        )

        qa_chain.run(message)
