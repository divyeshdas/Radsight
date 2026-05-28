# RadSight — Radiology Intelligence Platform

A production-grade AI-powered radiology report analysis system. Ingests radiology reports via OCR or direct text, runs a full NLP pipeline (NER, classification, risk scoring, semantic embeddings), and surfaces results through a real-time dashboard with forecasting and anomaly detection.

---

## Features

- **AI Pipeline** — BioBERT NER + ClinicalBERT classification + Sentence-BERT embeddings, with ONNX INT8 quantization for 2–3× CPU throughput
- **Semantic Search** — FAISS vector index (HNSW / IVFFlat) with SHA256-keyed Redis embedding cache
- **Analytics** — Prophet time-series forecasting, Isolation Forest anomaly detection, rolling EWMA trends
- **Real-time Dashboard** — WebSocket KPI streaming, 6 ECharts visualisations, live severity and disease prevalence
- **OCR** — PaddleOCR primary, pdfplumber PDF extraction, Tesseract fallback
- **Auth** — JWT with refresh token rotation, Redis-backed blacklisting, role-based access (admin / radiologist / clinician)
- **Dual theme** — Dark and light modes via CSS custom properties, no flash on load

---

## Architecture

```
Browser (Next.js)
    │
    ├── REST  ──► Backend (FastAPI :8000)
    │                  ├── MongoDB (reports, users, findings)
    │                  ├── Redis   (auth tokens, cache)
    │                  ├── httpx ──► AI Services (:8001)
    │                  └── httpx ──► Analytics   (:8002)
    │
    └── WebSocket ──► Analytics (:8002/ws/analytics)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, ECharts, Framer Motion, SWR, Zustand |
| Backend | Python 3.11, FastAPI, Motor (async MongoDB), Redis asyncio |
| AI | BioBERT, ClinicalBERT, Sentence-BERT, scispaCy, ONNX Runtime, FAISS |
| OCR | PaddleOCR, pdfplumber, Tesseract |
| Analytics | Prophet, Isolation Forest, statsmodels, scikit-learn |
| Database | MongoDB 7, Redis 7.2 |
| Deploy | Vercel (frontend), Railway (backend + services), Docker Compose (local) |

---

## Getting Started

### Prerequisites

- Docker 24+ and Docker Compose v2
- Node.js 18+ (for frontend dev only)
- Python 3.11+ (for running scripts locally)

### 1. Clone and configure

```bash
git clone https://github.com/divyeshdas/Radsight.git
cd Radsight
cp .env.example .env
```

Edit `.env` — at minimum change `JWT_SECRET_KEY` to a long random string.

### 2. Start the stack

```bash
docker compose up -d
```

Services:

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| AI Services | http://localhost:8001 |
| Analytics | http://localhost:8002 |
| MongoDB | localhost:27017 |
| Redis | localhost:6379 |

### 3. Seed demo data

```bash
# Creates 3 default users
docker compose exec backend python scripts/seed_data.py

# Generate 50k synthetic reports (takes ~5 min)
docker compose exec backend python scripts/generate_synthetic.py --count 50000 --spikes --seasonal
```

### 4. Run the frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Open http://localhost:3000

**Demo credentials:**

| Role | Email | Password |
|---|---|---|
| Admin | admin@radsight.health | RadSight@Admin2024 |
| Radiologist | radiologist@radsight.health | RadSight@Rad2024 |

---

## ONNX Optimisation (optional)

Run once after the AI services container is up to export INT8 quantized models:

```bash
docker compose exec ai_services python -m optimization.onnx_exporter
```

Models are saved to `./onnx_models/` and loaded automatically on the next restart. Gives 2–3× inference throughput on CPU.

---

## Deployment

### Backend — Railway

1. Create a new Railway project and connect the repo
2. Railway will auto-detect `railway.toml` at the root
3. Add the following environment variables in the Railway dashboard (copy from `.env.example`):
   - `MONGODB_URI` — use Railway's MongoDB plugin or MongoDB Atlas
   - `REDIS_HOST`, `REDIS_PASSWORD` — use Railway's Redis plugin
   - `JWT_SECRET_KEY` — generate with `openssl rand -hex 32`
   - `CORS_ORIGINS` — add your Vercel URL
4. Deploy

The analytics and AI services are deployed as separate Railway services from the same repo, pointing to `analytics/Dockerfile` and `ai-services/Dockerfile` respectively.

### Frontend — Vercel

1. Import the repo in Vercel
2. Set **Root Directory** to `frontend`
3. Add environment variables:
   - `NEXT_PUBLIC_API_URL` — your Railway backend URL (e.g. `https://radsight-backend.up.railway.app`)
   - `NEXT_PUBLIC_WS_URL` — your Railway analytics URL with `wss://` scheme
4. Deploy — Vercel auto-detects Next.js and uses `vercel.json` for install/build commands

---

## API Reference

Interactive docs are available at `http://localhost:8000/docs` when `DEBUG=true`.

Key endpoints:

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Obtain access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Rotate refresh token |
| GET | `/api/v1/reports` | Paginated report list with filters |
| POST | `/api/v1/reports/upload` | Upload PDF / image for OCR + NLP |
| POST | `/api/v1/search/semantic` | FAISS semantic search |
| GET | `/api/v1/analytics/kpis` | Live KPI summary |
| GET | `/api/v1/analytics/forecast` | Prophet 30-day forecast |
| GET | `/api/v1/analytics/anomalies` | Isolation Forest anomaly log |
| WS | `/ws/analytics` | Real-time KPI stream (analytics service) |

---

## Project Structure

```
radsight/
├── backend/          FastAPI REST API, auth, report management
├── ai-services/      NLP pipeline, OCR, FAISS semantic search
├── analytics/        Forecasting, anomaly detection, WebSocket
├── frontend/         Next.js dashboard
├── datasets/         Synthetic data generators and ingestion pipelines
├── scripts/          Seed and data generation CLI scripts
├── docker/           MongoDB init script
├── docker-compose.yml
├── railway.toml      Railway backend deployment config
└── .env.example      All environment variable references
```

---

## Scripts

```bash
# Seed users
python scripts/seed_data.py

# Generate synthetic reports
python scripts/generate_synthetic.py --count 10000 --spikes --seasonal --dry-run

# Export ONNX models
python -m optimization.onnx_exporter   # run inside ai-services container

# Rebuild FAISS index from MongoDB
curl -X POST http://localhost:8001/search/index/rebuild
```
