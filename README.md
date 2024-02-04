# rag-memo

## 使用技術

- [Pinecone](https://www.pinecone.io/)
    - GitHubログインを使用

## 参考実装

https://github.com/newbee1939/langchain-book/tree/main/chapter8

## バージョン管理方法

1. `pipenv --python 3.10.13`で仮想環境を作る
2. `pipenv install --dev`もしくは`pipenv install`でパッケージをインストール
3. `pipenv shell`で仮想環境の中に入る
4. 追加でパッケージを入れたい場合は`pipenv install --dev hoge`や`pipenv install hoge`を使う

参考1: https://qiita.com/y-tsutsu/items/54c10e0b2c6b565c887a
参考2: https://zenn.dev/nekoallergy/articles/py-env-pipenv01

## メモ

- pipenv の仮想環境は、1 つのフォルダに 1 つの環境が対応しています