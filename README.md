# Filestavk

A self-hosted, local-first case and document management system for a solo criminal defense attorney in Corpus Christi, TX.

## Quick Start

`at
start.bat
`

- **App:** http://localhost:5173 (or http://YOUR-IP:5173 from any device on the LAN)
- **API Docs:** http://localhost:8000/docs

## First-Time Setup

### 1. Backend
`powershell
cd backend
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your SECRET_KEY and ADMIN_PASSWORD
alembic upgrade head
python seed_data.py   # Optional: loads demo data
python run.py
`

### 2. Frontend
`powershell
cd frontend
npm install
npm run dev -- --host
`

### 3. Gmail (Optional)
1. Go to Settings -> Gmail in the app
2. Follow the OAuth setup instructions
3. Place your Google credentials at ackend/data/gmail_credentials.json

## Features (v0.1)
- Client and case management (Nueces County / state court)
- PDF upload with automatic text extraction (OCR for scanned docs)
- Gmail ingestion via Google OAuth (read-only)
- Bayesian document classification (trainable)
- Pre-built searches with history buffer
- Analytics dashboard
- LAN-accessible from phone/tablet

## Coming in v0.2 (Stubs Present)
- Portal Assist (re:SearchTX manual-confirm lookup)
- CSV/spreadsheet import
- eVoucher preparation workflow
- Document e-signing

## Project Structure
`
Filestavk/
├── backend/           # FastAPI + SQLite
├── frontend/          # React + Vite + Shadcn/ui
├── skills/            # Antigravity agent skills
│   ├── portal-assist/
│   └── gmail-ingestion/
└── start.bat          # Start everything
`

## Tech Stack
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Alembic, SQLite
- **Frontend:** React 18, TypeScript, Vite, Shadcn/ui, TanStack Query
- **Classification:** scikit-learn MultinomialNB + TF-IDF
- **Browser Automation:** Playwright (v0.2)
- **Email:** Google Gmail API (OAuth 2.0)
