# AccessBridge AI — backend image
# Python 3.11 slim, FastAPI + uAgents + SQLite.

FROM python:3.11-slim AS backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for lxml (BeautifulSoup parser)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Initialise the database on first run via the lifespan handler.
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# --- Frontend image -------------------------------------------------------
FROM node:20-slim AS frontend

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --omit=dev || npm install
COPY frontend/ .
RUN npm run build

EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
