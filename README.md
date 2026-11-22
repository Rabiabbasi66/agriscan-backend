---
title: AgriScan 3D API
emoji: 🌾
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# AgriScan 3D — FastAPI Backend

AI crop-disease detection API. YOLOv8n classifier (38 PlantVillage classes),
JWT auth, MongoDB persistence, per-IP rate limiting, hardened upload validation.

**Live:** `https://rabiabbasi66--agriscan-api-fastapi-app.us-east.modal.run`
(hosted on Modal.com serverless — scales to zero when idle)

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `MONGODB_URI` | yes | MongoDB Atlas connection string |
| `JWT_SECRET_KEY` | yes | ≥32 chars, no default — app refuses to start without it |
| `ALLOWED_ORIGINS` | prod | Comma-separated origins, e.g. `https://app.vercel.app` |
| `ENV` | prod | `production` disables `/docs`, `/redoc`, `/openapi.json` |
| `ENABLE_DOMAIN_ROUTERS` | no | `false` (default) — fields/uploads/results/notifications off |

See `.env.example` for the full list.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

## Modal.com deploy

```bash
pip install modal && modal token new
modal secret create agriscan-secrets \
  MONGODB_URI="..." JWT_SECRET_KEY="..." \
  ALLOWED_ORIGINS="https://your-app.vercel.app" ENV="production"
modal deploy modal_app.py
```

## Docker

```bash
docker build -t agriscan-api .
docker run -p 7860:7860 --env-file .env agriscan-api
```

## Tests

```bash
pytest tests/ -q
```
