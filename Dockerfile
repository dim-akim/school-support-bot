FROM python:3.12.7-slim-bookworm AS builder

WORKDIR /app
COPY poetry.lock pyproject.toml ./

RUN python -m pip install --no-cache-dir poetry==1.8.4 \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi

FROM python:3.12.7-slim-bookworm
WORKDIR /app
COPY --from=builder /app .
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH=/app
COPY bot bot
CMD ["python", "bot"]
