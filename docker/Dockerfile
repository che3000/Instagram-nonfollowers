FROM python:3.12.7-alpine3.20

# 安全更新與必要套件（Alpine）
RUN apk add --no-cache ca-certificates tzdata tini && \
    update-ca-certificates

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Taipei

WORKDIR /app

# 先複製所有 requirements 檔案
COPY requirements-web.txt requirements-cli.txt ./

# 根據 MODE 選擇性安裝相依
ARG MODE=web
RUN if [ "$MODE" = "cli" ]; then \
    python -m pip install --no-cache-dir -r requirements-cli.txt; \
    else \
    python -m pip install --no-cache-dir -r requirements-web.txt; \
    fi

# 複製程式碼
COPY main.py app.py ./

# 入口腳本（依 MODE 切換 web/cli）
COPY docker/app-entrypoint.sh /usr/local/bin/app-entrypoint.sh
RUN chmod +x /usr/local/bin/app-entrypoint.sh

# 非 root 執行（Alpine）
RUN addgroup -S runner && adduser -S runner -G runner -h /app && \
    chown -R runner:runner /app
USER runner

# 資料目錄與掛載點
RUN mkdir -p /app/data
VOLUME ["/app/data"]

# Web 介面預設埠
EXPOSE 7860

# 正確處理訊號
ENTRYPOINT ["/sbin/tini", "--"]

# 預設 MODE=web，可於 build/run 覆寫；PORT 於入口腳本預設 7860
ARG MODE=web
ENV MODE=$MODE

# JSON exec form，避免 shell form 訊號問題
CMD ["/usr/local/bin/app-entrypoint.sh"]
