FROM node:22-bookworm-slim AS web-build
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV API_INTERNAL_URL=http://127.0.0.1:8000
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=web-build /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home spendwise
COPY --chown=spendwise:spendwise backend/ ./backend/
COPY --chown=spendwise:spendwise --from=web-build /web/.next/standalone ./frontend/
COPY --chown=spendwise:spendwise --from=web-build /web/.next/static ./frontend/.next/static/
COPY --chown=spendwise:spendwise deploy/start.py ./deploy/start.py
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PYTHONUNBUFFERED=1 PORT=10000
USER spendwise
EXPOSE 10000
CMD ["python", "/app/deploy/start.py"]
