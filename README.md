# rag-memo

## 概要

技術メモにRAGを導入するためのアプリ。

## 使用技術

- Python
- Slack Bolt for Python
- [Pinecone](https://www.pinecone.io/)
    - GitHubログインを使用
- [Memento](https://www.gomomento.com/)
    - スレッド内のChat機能のキャッシュに利用する
    - GitHubログインを使用

## リンク

- 「技術メモ」SlackワークスペースのURL
    - w1707316441-wp8500715.slack.com
- Slackのアプリケーション一覧画面
    - https://api.slack.com/apps
- 今回作成したSlackアプリ
    - https://api.slack.com/apps/A06HKQ009TP?created=1

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
3. `pipenv shell`で仮想環境の中に入る（仮想環境に入る必要がない場合は、`pipenv install --system`を実行することでその場にインストールできる。コンテナ内の）
4. 追加でパッケージを入れたい場合は`pipenv install --dev hoge`や`pipenv install hoge`を使う

参考1: https://qiita.com/y-tsutsu/items/54c10e0b2c6b565c887a
参考2: https://zenn.dev/nekoallergy/articles/py-env-pipenv01
参考3: https://qiita.com/Ouvill/items/b1f9aa2fd7d8630466c6

## メモ

- pipenv の仮想環境は、1 つのフォルダに 1 つの環境が対応しています

## 参考記事

- RAGの実案件に取り組んできた今までの知見をまとめてみた
    - https://dev.classmethod.jp/articles/rag-knowledge-on-real-projects/
- Slack BoltをGoogle Cloudにデプロイするノウハウ
    - https://zenn.dev/bisque/articles/slack-bolt-on-google-cloud
    - Cloud Runが良さそう？

## TODO

- アプリの仕組みやアーキテクチャを理解する
    - コードの内容も完全に理解する
- 自分なりにコードをカスタマイズする
    - GitHubのリポジトリmemoの内容をベクターデータとして保存できるようにする
- CI/CDでCloud RunもしくはCloud Functionsにデプロイする（安い方）
    - Slack BoltをGoogle Cloudにデプロイするノウハウ
    - https://zenn.dev/bisque/articles/slack-bolt-on-google-cloud
- P212のPineconeへのテキストの重複登録を対応する
- GitHub Actionsによる自動デプロイ
- Zennにまとめる
    - Python環境構築
    - 技術メモのすヽめ
    - 技術メモをRAGに取り込んでみた