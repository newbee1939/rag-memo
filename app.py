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
from langchain.memory import MomentoChatMessageHistory
from langchain.schema import HumanMessage, LLMResult, SystemMessage
from datetime import timedelta

CHAT_UPDATE_INTERVAL_SEC = 1

load_dotenv()

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

    # LLMの処理の終了のタイミングで実行する処理
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        app.client.chat_update(
            channel=self.channel,
            ts=self.ts,
            text=self.message
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

    history = MomentoChatMessageHistory.from_client_params(
        id_ts,
        os.environ["MOMENTO_CACHE"],
        timedelta(hours=int(os.environ["MOMENTO_TTL"])),
    )

    # 履歴の読み出し処理と、ユーザー入力を記憶に追加する処理を追加
    messages = [SystemMessage(content="You are a good assistant.")]
    messages.extend(history.messages)
    messages.append(HumanMessage(content=message))
    history.add_user_message(message)

    callback = SlackStreamingCallbackHandler(channel=channel, ts=ts)
    llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        streaming=True,
        callbacks=[callback] 
    )

    # Chat Completion APIの呼び出し後に、履歴キャッシュへのメッセージの追加処理を追加
    ai_message = llm(messages)
    history.add_message(ai_message)

# P180:LazyリスナーでSlackのリトライ前に単純応答を返す
def just_ack(ack):
    ack()

app.event("app_mention")(ack=just_ack, lazy=[handle_mention])

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
