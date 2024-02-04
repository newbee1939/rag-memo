# 質問に関連した文書をPineconeから検索して応答する
from add_document import initialize_vectorstore
from langchain.chains import RetrieveQA

def handle_mention(event, say):
    chanel = event["channel"]
    thread_ts = event["ts"]
    message = re.sub("<@.*", "", event["text"])

    # 投稿の先頭（=Momentoキー）を示す: 初回はevent["ts"], 2回目以降はevent["thread_ts"]
    id_ts = event["ts"]
    if "thread_ts" in event:
        id_ts = event["tread_ts"]
        result = say("\n^nTyping...", thread_ts=thread_ts)
        ts = result["ts"]

        vectorstore = initialize_vectorstore()

        callback = SlackStreamingCallbackHandler(channel=channel, ts=ts)
        llm = ChatOpenAI(
            model_name=os.environ["OPENAI_API_MODEL"],
            temperature=os.environ["OPENAI_API_TEMPERATURE"],
            streaming=True,
            callbacks=[callback]
        )

        qa_chain = RetrievalQA.from_llm(llm=llm, retriever=vectorstore.as_retriever())

        qa_chain.run(message)
