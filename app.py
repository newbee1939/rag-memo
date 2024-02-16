# 質問に関連した文書をPineconeから検索して応答する
# 基本的にはここの実装が変わることはないはず
import os
import re
import time
# import json
# import logging
from dotenv import load_dotenv
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
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
# logging.basicConfig(
#     format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# NOTE: Botトークンとソケットモードハンドラーを使ってアプリを初期化する
# AWS Lambdaで実行することを想定し、リスナー関数での処理が完了するまでHTTPレスポンスの送信を遅延させる
# AWS LambdaのようなFunction as ServiceではHTTPレスポンスを返した後にスレッドやプロセスの実行を続けることができないため、
# FaaSで応答を別インスタンスで実行可能にする
# FaaSで起動する場合、process_before_response=Trueは必須の設定となる
# 参考: https://slack.dev/bolt-python/ja-jp/concepts
# initialize application
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    token=os.environ["SLACK_BOT_TOKEN"],
    # process_before_response=True,
)

# 応答ストリームを受け取るCallbackハンドラークラス
class SlackStreamingCallbackHandler(BaseCallbackHandler):
    # 最後にメッセージを送信した時刻を初期化（現在時刻）
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
        # CHAT_UPDATE_INTERVAL_SEC(1秒)間隔で更新する 
        if now - self.last_send_time > CHAT_UPDATE_INTERVAL_SEC:
            self.last_send_time = now
            # SlackのAPIを使用してメッセージを更新
            app.client.chat_update(
                channel=self.channel, ts=self.ts, text=f"{self.message}..."
            )
            self.last_send_time = now
            self.update_count += 1

            # chat.update処理はSlack APIにおいてTier3のメソッドとして定義されており、1分間に50回までのコール制限がある
            # これを超えるとRateLimitErrorになる
            # そこで、当初1秒間隔で更新しているchat.update処理を、10回ごとに更新間隔を2倍に増やしていくことで、
            # Chat Completion APIの応答時間が長時間かかっても問題が発生しないようにする
            # update_countが現在の更新間隔X10より多くなるたびに更新間隔を2倍にする
            if self.update_count / 10 > self.interval:
                self.interval = self.interval * 2

    # LLMの処理の終了のタイミングで実行する処理
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        message_blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": self.message}},
            {"type": "divider"},
        ]
        # 最終的な回答を表示
        app.client.chat_update(
            channel=self.channel,
            ts=self.ts,
            text=self.message,
            blocks=message_blocks,
        )

def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event["ts"]
    # event["text"] 中のすべてのユーザーメンションを削除し、空の文字列で置き換える
    message = re.sub("<@.*>", "", event["text"])

    # 投稿のキー(=Momentoキー):初回=event["ts"],2回目以降=event["thread_ts"]
    id_ts = event["ts"]
    if "thread_ts" in event:
        id_ts = event["thread_ts"]

    # Slack に "Typing..." というメッセージを送信し、その結果を result 変数に格納
    # Channelではなくメンションされたスレッド内に返す
    result = say("\n\nTyping...✍️", thread_ts=thread_ts)
    # 送信したメッセージのタイムスタンプを取得し、ts 変数に格納
    ts = result["ts"]

    # 情報が格納してあるベクトルストアを初期化し、その結果を vectorstore 変数に格納
    vectorstore = initialize_vectorstore()

    # Momentoからチャットメッセージの履歴を取得し、history 変数に格納
    history = MomentoChatMessageHistory.from_client_params(
        id_ts,
        os.environ["MOMENTO_CACHE"],
        timedelta(hours=int(os.environ["MOMENTO_TTL"])),
    )
    # メモリーを初期化し、チャット履歴を含む会話バッファを設定
    # ChatCompletionAPIはステートレスであり、会話履歴を踏まえた応答を得るには、会話履歴をリクエストに含める必要がある
    # 会話履歴の保存などの便利な機能を提供するのがLangChain「memory」
    # ConversationBufferMemoryは単純に会話履歴を保持する
    memory = ConversationBufferMemory(
        chat_memory=history, memory_key="chat_history", return_messages=True
    )

    callback = SlackStreamingCallbackHandler(channel=channel, ts=ts)
    # OpenAIのチャットモデルを初期化
    llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
        streaming=True, # ストリーミングで回答を得るための設定
        callbacks=[callback]
    )

    # 質問を簡略化するための OpenAI モデルを初期化
    condense_question_llm = ChatOpenAI(
        model_name=os.environ["OPENAI_API_MODEL"],
        temperature=os.environ["OPENAI_API_TEMPERATURE"],
    )
    # RAGを用いた回答
    # LangChainにおいてテキストに関連するドキュメントを得るインターフェースを「Retriever」という
    # 入力に関連する文書を取得（Retrieve）するのに加えて、取得した内容をPromptTemplateにcontextとして
    # 埋め込んで、LLMに質問して回答（QA）してもらいたい
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
        condense_question_llm=condense_question_llm,
    )

    qa_chain.run(message)

# P180
# Slack Event APIは3秒経過してもサーバーからの応答が完了しない場合エラーになり、最大3回までリトライする
# つまり、投稿が増えていく
# それを防ぐために、LazyリスナーでSlackのリトライ前に単純応答を返す
# Slackに3秒以内に単純な応答を返した後で、コールバックで応答を書き込んでいく
def just_ack(ack):
    ack()
app.event("app_mention")(ack=just_ack, lazy=[handle_mention])

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

# # AWS Lambda上で起動するときの呼び出しに指定するhandler関数を作成
# # handler関数でリクエストヘッダを参照し、リトライ時には処理を無視する実装をする
# def handler(event, context):
#     logger.info("handler called")
#     header = event["headers"]
#     logger.info(json.dumps(header))

#     if "x-slack-retry-num" in header:
#         logger.info("SKIP > x-slack-retry-num: %s", header["x-slack-retry-num"])
#         return 200

#     # AWS Lambda 環境のリクエスト情報を app が処理できるよう変換してくれるアダプター
#     slack_handler = SlackRequestHandler(app=app)
#     # 応答はそのまま AWS Lambda の戻り値として返せます
#     return slack_handler.handle(event, context)