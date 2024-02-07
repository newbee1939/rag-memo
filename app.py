# 質問に関連した文書をPineconeから検索して応答する
import json
import logging
import os
import re
import time
from datetime import timedelta
from typing import Any

from add_document import initialize_vectorstore
from dotenv import load_dotenv
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, MomentoChatMessageHistory
from langchain.schema import LLMResult
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

CHAT_UPDATE_INTERVAL_SEC = 1

load_dotenv()

# ログ
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ボットトークンを使ってアプリを初期化します
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
    process_before_response=True,
)

class SlackStreamingCallbackHandler(BaseCallbackHandler):
    last_send_time = time.time()
    message = ""

    def __init__(self, channel, ts):
        self.channel = channel
        self.ts = ts
        self.interval = CHAT_UPDATE_INTERVAL_SEC
        # 投稿を更新した累計回数カウンタ
        self.update_count = 0

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.message += token

        now = time.time()
        if now - self.last_send_time > self.interval:
            app.client.chat_update(
                channel=self.channel, ts=self.ts, text=f"{self.message}\n\nTyping..."
            )
            self.last_send_time = now
            self.update_count += 1

            # update_countが現在の更新間隔X10より多くなるたびに更新間隔を2倍にする
            if self.update_count / 10 > self.interval:
                self.interval = self.interval * 2

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        message_context = "OpenAI APIで生成される情報は不正確または不適切な場合がありますが、当社の見解を述べるものではありません。"
        message_blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": self.message}},
            {"type": "divider"},
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": message_context}],
            },
        ]
        app.client.chat_update(
            channel=self.channel,
            ts=self.ts,
            text=self.message,
            blocks=message_blocks,
        )

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

        history = MomentoChatMessageHistory.from_client_params(
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
