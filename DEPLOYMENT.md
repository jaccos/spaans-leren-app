# Docker Deployment Overzicht

## Status: ✅ ACTIEF

### Architectuur
```
Browser → http://localhost:80
    ↓
  Nginx (spaans-leren-nginx)
    ├─→ / → Frontend (index.html)
    └─→ /api/* → Backend (spaans-leren-backend:8002)
            ├─→ Ollama (spaans-leren-ollama:11434) 
            └─→ Claude API (fallback)
```

### Actieve Containers
| Container | Image | Poort | Status |
|-----------|-------|-------|--------|
| spaans-leren-nginx | nginx:alpine | 80 | Reverse proxy + frontend |
| spaans-leren-backend | python:3.11-slim | 8002 (intern) | FastAPI + AI |
| spaans-leren-ollama | ollama/ollama | 11434 | Qwen 14B + Mistral 7B |

### Volumes
| Volume | Path | Grootte | Doel |
|--------|------|---------|------|
| spaans-leren-db | /app/data | ~1MB | SQLite database |
| spaans-leren-ollama | /root/.ollama | ~13GB | LLM modellen |

### URLs
- **Applicatie:** http://localhost (of https://spaans.local via OrbStack)
- **API Direct:** Niet beschikbaar (alleen via Nginx)
- **Ollama:** http://localhost:11434

### Quick Commands
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Rebuild
docker-compose build --no-cache
docker-compose up -d

# Logs
docker-compose logs -f nginx
docker-compose logs -f backend
docker-compose logs -f ollama

# Database backup
docker cp spaans-leren-backend:/app/data/spaans_leren.db ./backup-$(date +%Y%m%d).db

# Reset database
docker-compose down
docker volume rm spaans-leren-db
docker-compose up -d
```

### Removed (Lokale variant niet meer ondersteund)
- ❌ start.sh / stop.sh scripts
- ❌ Python HTTP server op poort 3000
- ❌ Direct localhost:8002 backend toegang
- ❌ npm start voor frontend
- ❌ Backend hot-reload scripts

### Development Workflow
1. Edit files in `frontend/index.html` of `backend/*.py`
2. Changes worden automatisch gepikt door volume mounts
3. Frontend: Refresh browser
4. Backend: Auto-reload door uvicorn --reload
5. Nginx config: `docker-compose restart nginx`

---
**Laatst geüpdatet:** 13 November 2025
**Deployment type:** Docker Compose (development + production ready)
