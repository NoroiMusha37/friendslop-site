FROM ghcr.io/astral-sh/uv:0.11.16-python3.13-trixie-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# The virtual environment lives in /opt/venv, outside /app, so mounting the project folder doesn't hide it
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
