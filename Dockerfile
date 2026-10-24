# syntax=docker/dockerfile:1
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so a code change doesn't reinstall them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-editable

RUN useradd --system --uid 10001 bot && mkdir /data /app/.matplotlib && chown bot /data /app/.matplotlib
USER bot

ENV PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/data/bot.db \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/app/.matplotlib

# The bot user has no home folder, so matplotlib's font cache lives here, built once at build
# time instead of on every container start.
RUN python -c "import matplotlib.font_manager"
VOLUME /data

ENTRYPOINT ["fantasy-bot"]
CMD ["bot"]
