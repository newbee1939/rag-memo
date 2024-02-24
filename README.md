# rag-memo

## 概要

技術メモにRAGを導入するためのアプリ。

※RAG=Retrieval Augmented Generation

## 環境構築

1. ngrok.yml作成

```shell
cp docker/ngrok.yml.example docker/ngrok.yml
```

2. ngrok.ymlの`NGROK_AUTH_TOKEN`にngrokのトークンを設定

Your Authtoken:  https://dashboard.ngrok.com/get-started/your-authtoken

3. コンテナ立ち上げ

```
docker compose up -d
```

4. `localhost:4040`にアクセスしてhttpsのエンドポイントURLを取得

5. エンドポイントのURLを以下のページに設定

https://api.slack.com/apps/A06HKQ009TP/event-subscriptions

ex: https://9b57-210-194-190-35.ngrok-free.app/slack/events

6. コンテナに入る

```shell
docker compose exec app bash
```

7. Install Packages

```shell
pipenv install --system
```

8. Slack Bolt起動

```shell
python app.py
```

9. SlackのDMでアプリにメッセージを送ったら返ってくるはず

w1707316441-wp8500715.slack.com

## 使用技術

- Python
- Slack Bolt for Python
- [Pinecone](https://www.pinecone.io/)
    - ベクターデータの保存
    - GitHubログインを使用
- [Memento](https://www.gomomento.com/)
    - スレッド内のChat機能のキャッシュに利用する
    - GitHubログインを使用
- [Google Cloud](https://console.cloud.google.com/welcome?project=gig-sample-383607)
    - Cloud Run
    - Artifact Registry
    - Workload Identity
        - など    
- [ngrok](https://dashboard.ngrok.com/get-started/setup/macos)
    - GitHubログインを使用
    - DockerHub
        - https://hub.docker.com/r/ngrok/ngrok
    - ドキュメント
        - https://ngrok.com/docs/using-ngrok-with/docker/    

## Deploy方法

- 以下のページのURLにCloud RunのURLを設定
    - https://api.slack.com/apps/A06HKQ009TP/event-subscriptions
    - 以下の値
        - https://rag-memo-4wzpkyxieq-an.a.run.app/slack/events

## 関連リンク

- 「技術メモ」SlackワークスペースのURL
    - w1707316441-wp8500715.slack.com
- Slackのアプリケーション一覧画面
    - https://api.slack.com/apps
- 今回作成したSlackアプリ
    - https://api.slack.com/apps/A06HKQ009TP?created=1
- Google Cloud のクレジット情報
    - https://console.cloud.google.com/billing/010B07-FE92ED-4BE343?hl=ja&project=gig-sample-383607

## 参考実装

https://github.com/newbee1939/langchain-book/tree/main/chapter8

## 参考書籍

- ChatGPT/LangChainによるチャットシステム構築[実践]入門
    - 7章と8章がメイン

## インストールするパッケージ一覧

- requirements.txt
    - https://github.com/newbee1939/langchain-book/blob/main/chapter8/requirements.txt
- requirements-dev.txt
    - https://github.com/newbee1939/langchain-book/blob/main/chapter8/requirements-dev.txt

## バージョン管理方法（pipenvを利用）

0. コンテナを立ち上げて、appコンテナの中に入る
1. `pipenv --python 3.10.13`で仮想環境を作る
2. `pipenv install --dev`もしくは`pipenv install`でパッケージをインストール
3. `pipenv shell`で仮想環境の中に入る（仮想環境に入る必要がない場合は、`pipenv install --system`を実行することでコンテナ内のその場にインストールできる）
4. 追加でパッケージを入れたい場合は`pipenv install --dev hoge`や`pipenv install hoge`を使う

参考1: https://qiita.com/y-tsutsu/items/54c10e0b2c6b565c887a
参考2: https://zenn.dev/nekoallergy/articles/py-env-pipenv01
参考3: https://qiita.com/Ouvill/items/b1f9aa2fd7d8630466c6

## メモ

- pipenv の仮想環境は1 つのフォルダに 1 つの環境が対応している

## 参考記事

- RAGの実案件に取り組んできた今までの知見をまとめてみた
    - https://dev.classmethod.jp/articles/rag-knowledge-on-real-projects/
- Slack BoltをGoogle Cloudにデプロイするノウハウ
    - https://zenn.dev/bisque/articles/slack-bolt-on-google-cloud
- Bolt 入門ガイド（HTTP）
    - https://slack.dev/bolt-python/ja-jp/tutorial/getting-started-http

## TODO

- リポジトリの更新をベクターデータベースに反映させる
- 自分なりにコードをカスタマイズする
    - GitHubのリポジトリmemoの内容をベクターデータとして保存できるようにする
- P212のPineconeへのテキストの重複登録を対応する
- Zennにまとめる
    - Python環境構築方法について
    - pipenvとか、その他Pythonについて学んだことをまとめる
        - Pythonの基礎文法とかもブログにも投稿して良さそう
    - 技術メモのすヽめ
    - 技術メモをRAGに取り込んでみた
        - rag-memoをテンプレートとして配布してもいいかも
- memoのリポジトリにSlackのリンク貼る
- 業務経歴の個人開発に追加する
- Terraformでコード化しておいていつでも再現できるようにしておく
    - 記事にする
