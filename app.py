# 質問に関連した文書をPineconeから検索して応答する
# 基本的にはここの実装が変わることはないはず
import os
import re
import time
import json
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from typing import Any
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.schema import LLMResult
from langchain.memory import MomentoChatMessageHistory, ConversationBufferMemory
from langchain.schema import LLMResult
from langchain.chains import ConversationalRetrievalChain
from datetime import timedelta
from add_document import initialize_vectorstore

CHAT_UPDATE_INTERVAL_SEC = 1

load_dotenv()

# ログ
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# NOTE: Botトークンとソケットモードハンドラーを使ってアプリを初期化する
# AWS Lambdaで実行することを想定し、リスナー関数での処理が完了するまでHTTPレスポンスの送信を遅延させる
# AWS LambdaのようなFunction as ServiceではHTTPレスポンスを返した後にスレッドやプロセスの実行を続けることができないため、
# FaaSで応答を別インスタンスで実行可能にする
# FaaSで起動する場合、process_before_response=Trueは必須の設定となる
# 参考: https://slack.dev/bolt-python/ja-jp/concepts
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
    process_before_response=True,
)

# 応答ストリームを受け取るCallbackハンドラークラス
class SlackStreamingCallbackHandler(BaseCallbackHandler):
    # 最後にメッセージを送信した時刻を初期化
    last_send_time = time.time()
    # メッセージを初期化
    message = ""

    def __init__(self, channel, ts):
        self.channel = channel
        self.ts = ts
        self.interval = CHAT_UPDATE_INTERVAL_SEC
        # 投稿を更新した累計回数カウンタ
        self.update_count = 0

    # 新しいトークンの生成タイミングで実行する処理
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        # 生成されたトークンをメッセージに追加
        self.message += token

        now = time.time()
        # CHAT_UPDATE_INTERVAL_SEC秒以上経過していれば
        if now - self.last_send_time > CHAT_UPDATE_INTERVAL_SEC:
            self.last_send_time = now
            # SlackのAPIを使用してメッセージを更新
            app.client.chat_update(
                channel=self.channel, ts=self.ts, text=f"{self.message}..."
            )
            self.last_send_time = now
            self.update_count += 1

            # update_countが現在の更新間隔X10より多くなるたびに更新間隔を2倍にする
            if self.update_count / 10 > self.interval:
                self.interval = self.interval * 2

    # LLMの処理の終了のタイミングで実行する処理
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

# @app.event("app_mention")
def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event["ts"]
    message = re.sub("<@.*>", "", event["text"])

    # 投稿のキー(=Momentoキー):初回=event["ts"],2回目以降=event["thread_ts"]
    id_ts = event["ts"]
    if "thread_ts" in event:
        id_ts = event["thread_ts"]

    result = say("\n\nTyping...", thread_ts=thread_ts)
    ts = result["ts"]

    vectorstore = initialize_vectorstore()

    history = MomentoChatMessageHistory.from_client_params(
        id_ts,
        os.environ["MOMENTO_CACHE"],
        timedelta(hours=int(os.environ["MOMENTO_TTL"])),
    )
    memory = ConversationBufferMemory(
        chat_memory=history, memory_key="chat_history", return_messages=True
    )

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

# P180:LazyリスナーでSlackのリトライ前に単純応答を返す
def just_ack(ack):
    ack()

app.event("app_mention")(ack=just_ack, lazy=[handle_mention])

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

# AWS Lambda上で起動するときの呼び出しに指定するhandler関数を作成
# handler関数でリクエストヘッダを参照し、リトライ時には処理を無視する実装をする
def handler(event, context):
    logger.info("handler called")
    header = event["headers"]
    logger.info(json.dumps(header))

    if "x-slack-retry-num" in header:
        logger.info("SKIP > x-slack-retry-num: %s", header["x-slack-retry-num"])
        return 200

    # AWS Lambda 環境のリクエスト情報を app が処理できるよう変換してくれるアダプター
    slack_handler = SlackRequestHandler(app=app)
    # 応答はそのまま AWS Lambda の戻り値として返せます
    return slack_handler.handle(event, context)