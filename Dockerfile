FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 10001 tax
WORKDIR /app
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY .claude/skills/de-freelancer-tax .claude/skills/de-freelancer-tax
COPY server server
ENV TAX_SKILL_DIR=/app/.claude/skills/de-freelancer-tax TAX_DATA_ROOT=/data TAX_TOKENS_FILE=/config/tokens.json PYTHONDONTWRITEBYTECODE=1
USER tax
WORKDIR /app/server
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
