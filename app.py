import os
import re
import time
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from typing import Any
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.schema import LLMResult
from langchain.memory import MomentoChatMessageHistory, ConversationBufferMemory
from langchain.schema import LLMResult
from langchain.chains import ConversationalRetrievalChain
from datetime import timedelta
from add_document import initialize_vectorstore

CHAT_UPDATE_INTERVAL_SECOND = 1

load_dotenv()

app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
)

# Slack AppのDMにメッセージを送ったときに動く処理
class SlackStreamingCallbackHandler(BaseCallbackHandler):
    last_token_send_time = time.time()
    ai_generated_message = ""

    def __init__(self, channel, ts):
        self.channel = channel
        self.ts = ts
        self.interval = CHAT_UPDATE_INTERVAL_SECOND
        self.update_count = 0

    # 新しいトークンの生成タイミングで実行する処理
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        # 生成されたトークンをメッセージに追加していく
        self.ai_generated_message += token

        now = time.time()
        # CHAT_UPDATE_INTERVAL_SECOND(1秒)間隔でLLMの回答を更新する 
        if now - self.last_token_send_time > CHAT_UPDATE_INTERVAL_SECOND:
            # SlackのAPIを使用してLLMの回答を更新する
            app.client.chat_update(
                channel=self.channel, ts=self.ts, text=f"{self.ai_generated_message}..." # まだ回答途中なので末尾は「...」にしておく
            )
            self.last_token_send_time = now
            self.update_count += 1

            # chat_update処理は1分間に50回までのコール制限があり、これを超えるとRateLimitErrorになる
            # そこで、update_countが現在の更新間隔x10より多くなるたびに更新間隔を2倍にすることで
            # 短時間でAPIを叩き過ぎないようにする
            if self.update_count / 10 > self.interval:
                self.interval = self.interval * 2

    # LLMの処理の終了のタイミングで実行する処理
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        message_blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": self.ai_generated_message}},
        ]
        # 最終的な回答を表示
        app.client.chat_update(
            channel=self.channel,
            ts=self.ts,
            text=self.ai_generated_message,
            blocks=message_blocks,
        )

# Slack AppのDMにメッセージを送ったときに動く処理
def handle_direct_message(event, say):
    # 投稿のキー(=Momentoキー):初回=event["ts"],2回目以降=event["thread_ts"]
    # 初回のtsと同一スレッドに投稿したときのthread_tsは同じ値になる
    # 逆に初回のtsと同一スレッドに投稿したときのtsは異なる値になる
    id_ts = event["ts"]
    if "thread_ts" in event:
        id_ts = event["thread_ts"]

    # Slack に "Typing..." というメッセージを送信し、その結果を result 変数に格納
    # Channelではなく送信メッセージのスレッド内に返す
    result = say("\n\nTyping...✍️", thread_ts=id_ts)
    # 送信したメッセージのタイムスタンプを取得し、ts 変数に格納
    ts = result["ts"]

    # 独自情報が格納してあるベクトルストアを初期化し、その結果を vectorstore 変数に格納
    vectorstore = initialize_vectorstore()

    # Momentoからチャットメッセージの履歴を取得し、history 変数に格納
    history = MomentoChatMessageHistory.from_client_params(
        id_ts,
        os.environ["MOMENTO_CACHE"],
        timedelta(hours=int(os.environ["MOMENTO_TTL"])),
    )
    # ChatCompletionAPIはステートレスであり、会話履歴を踏まえた応答を得るには、会話履歴をリクエストに含める必要がある
    # 会話履歴の保存などの便利な機能を提供するのがLangChainの「memory」
    # ConversationBufferMemoryは単純に会話履歴を保持する
    memory = ConversationBufferMemory(
        chat_memory=history, memory_key="chat_history", return_messages=True
    )

    callback = SlackStreamingCallbackHandler(channel=event["channel"], ts=ts)
    llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        streaming=True, # ストリーミングで回答を得るための設定
        callbacks=[callback]
    )
    condense_question_llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
    )
    # RAGを用いた回答
    # LangChainにおいてテキストに関連するドキュメントを得るインターフェースを「Retriever」という
    # 入力に関連する文書を取得（Retrieve）するのに加えて、取得した内容をPromptTemplateにcontextとして埋め込んで、LLMに質問して回答（QA）してもらいたい
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
        condense_question_llm=condense_question_llm,
    )

    user_sent_message = event["text"]
    qa_chain.run(user_sent_message)

# P180
# Slack Event APIは3秒経過してもサーバーからの応答が完了しない場合エラーになり、最大3回までリトライする
# つまり、投稿が増えていく
# それを防ぐために、LazyリスナーでSlackのリトライ前に単純応答を返す
# Slackに3秒以内に単純な応答を返した後で、コールバックで応答を書き込んでいく
def just_ack(ack):
    ack()
app.event("message")(ack=just_ack, lazy=[handle_direct_message])

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
