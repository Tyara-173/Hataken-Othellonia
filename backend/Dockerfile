# ベースイメージの指定
FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なファイルをコピー
# Dockerfileと同じ階層にあるファイル・ディレクトリをすべてコピーする
COPY . .

# 依存ライブラリのインストール
RUN pip install --no-cache-dir -r requirements.txt

# ポートの設定
ENV PORT 8080

# コンテナ起動時に実行するコマンド
# backend/main.pyではなく、単にmain.pyとなる
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]