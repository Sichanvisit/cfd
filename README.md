# CFD Project

Windows-based CFD trading workspace with a Python runtime, FastAPI monitoring API, Next.js dashboard, and ML utility scripts.

This README intentionally keeps proprietary strategy details, production tuning logic, broker credentials, and live operating data out of scope. The goal of this repository snapshot is to share the project structure and development workflow without exposing sensitive runtime assets.

## Stack

- Python 3.12
- FastAPI
- pandas-based data processing
- Next.js 14 / React 18
- Node.js 20.x
- MetaTrader 5 integration

## Project layout

- `main.py`: runtime entrypoint
- `backend/`: application, domain, FastAPI, and service modules
- `adapters/`: broker, Telegram, MT5, and observability adapters
- `ml/`: retraining and model utility scripts
- `frontend/next-dashboard/`: monitoring dashboard
- `scripts/`: operational checks and deployment helpers
- `docs/`: design notes and roadmap documents

## Local run flow

### 1. Prepare environment

- Root: copy `.env.example` to `.env` and fill in your local secrets
- Frontend: copy `frontend/next-dashboard/.env.example` to `frontend/next-dashboard/.env.local`
- Use Node `20.x`
- Use your existing Python runtime environment for the project dependencies

### 2. Start services

Windows batch flow:

```bat
manage_cfd.bat start
```

Manual flow:

```bat
python main.py
python -m uvicorn backend.fastapi.app:app --host 127.0.0.1 --port 8010 --workers 1
cd frontend\next-dashboard
npm install
npm run dev
```

### 3. Open local endpoints

- API health: `http://127.0.0.1:8010/health`
- Dashboard: `http://127.0.0.1:3010`

## What is excluded from Git

To keep the repository safe and lightweight, the following are excluded by `.gitignore`:

- `.env` and local env files
- `data/`, `models/`, `logs/`, `releases/`
- `node_modules/`, `.next/`, caches, temp files
- databases, lock files, generated logs
- personal documents and binary installers

## Notes

- The public-facing README does not document the internal trading rules or model decision logic.
- Runtime data and model artifacts are intentionally left out of version control.
- If you want to make this repository reproducible for other developers, the next cleanup step would be exporting a dedicated Python dependency file.
