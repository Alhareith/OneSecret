FROM node:22-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN npm install -g corepack@latest \
    && corepack pnpm --dir frontend install --frozen-lockfile \
    && corepack pnpm --dir frontend run build \
    && python3 -m venv /opt/onesecret-venv \
    && /opt/onesecret-venv/bin/pip install --no-cache-dir -r backend/requirements.txt

ENV NODE_ENV=production \
    PATH="/opt/onesecret-venv/bin:${PATH}" \
    PYTHONPATH="/app/backend" \
    ONESECRET_REQUIRE_CONFIGURATION=true

CMD ["sh", "-c", "cd /app/backend && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT}\" --no-access-log"]
