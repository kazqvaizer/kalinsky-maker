FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY app/ app/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

VOLUME ["/app/sources", "/app/media", "/app/data"]

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
