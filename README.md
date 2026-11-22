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

AI crop-disease detection API (YOLOv8n classifier, 38 PlantVillage classes)
with JWT auth and MongoDB persistence.

## Required Space secrets (Settings → Variables and secrets)

| Variable | Example |
|---|---|
| `MONGODB_URI` | `mongodb+srv://<username>:<password>@cluster.mongodb.net/agriscan` |
| `JWT_SECRET_KEY` | long random string (≥32 chars) |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` (comma-separated) |
| `ENV` | `production` |

The app refuses to start without a valid `JWT_SECRET_KEY`.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

API docs: `/docs` (disabled when `ENV=production`).
