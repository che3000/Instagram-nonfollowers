# Python 3.12 slim base
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates tini && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY main.py ./

# Non-root user
RUN useradd -m runner && chown -R runner:runner /app
USER runner

# Persisted data (session & CSV)
RUN mkdir -p /app/data
VOLUME ["/app/data"]

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "main.py"]
