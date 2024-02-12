# 質問に関連した文書をPineconeから検索して応答する
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

CHAT_UPDATE_INTERVAL_SEC = 1

load_dotenv()

# NOTE: Botトークンとソケットモードハンドラーを使ってアプリを初期化する。
# AWS Lambdaで実行することを想定し、リスナー関数での処理が完了するまでHTTPレスポンスの送信を遅延させる。
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
    last_send_time = time.time()
    message = ""

    def __init__(self, channel, ts):
        self.channel = channel
        self.ts = ts

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.message += token

        now = time.time()
        if now - self.last_send_time > CHAT_UPDATE_INTERVAL_SEC:
            self.last_send_time = now
            app.client.chat_update(
                channel=self.channel, ts=self.ts, text=f"{self.message}..."
            )

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        app.client.chat_update(
            channel=self.channel,
            ts=self.ts,
            text=self.message
        )

@app.event("app_mention")
def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event["ts"]
    message = re.sub("<@.*>", "", event["text"])

    result = say("\n\nTyping...", thread_ts=thread_ts)
    ts = result["ts"]

    callback = SlackStreamingCallbackHandler(channel=channel, ts=ts)
    llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        streaming=True,
        callbacks=[callback] 
    )

    llm.predict(message)


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
