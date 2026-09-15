#!/usr/bin/env bash
# One-command setup for running natively (without Docker).
# Usage: ./scripts/setup.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example (edit it with your DATABASE_URL / GROQ_API_KEY)"
  cp .env.example .env
else
  echo "==> .env already exists, leaving it as-is"
fi

echo "==> Setting up backend virtualenv"
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "==> Running database migrations"
alembic upgrade head

echo "==> Ingesting sample transcripts (replace data/transcripts/*.txt with real ones first for a real demo)"
python -m app.ingestion.ingest_transcripts

cd ..
echo "==> Installing frontend dependencies"
cd frontend
npm install

cd ..
cat <<'EOF'

Setup complete. In two separate terminals, run:

  Terminal 1 (backend):  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
  Terminal 2 (frontend): cd frontend && npm run dev

Also make sure Ollama is running if you want to use the local provider:
  ollama serve
  ollama pull llama3.1:8b
EOF
