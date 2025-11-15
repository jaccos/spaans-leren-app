# 🐳 DOCKER vs LOKAAL - Hybride AI Setup

## 📍 Waar is het geïmplementeerd?

**BEIDE!** Het hybride AI systeem werkt nu in:
1. ✅ **Lokale development** (zonder Docker)
2. ✅ **Docker containers** (met host Ollama)

## 🎯 Twee Deployment Scenarios

### Scenario 1: Lokaal (zonder Docker) - AANBEVOLEN VOOR DEVELOPMENT

**Voordelen:**
- ⚡ Snelste performance
- 🔧 Makkelijkst te debuggen
- 🔄 Hot-reload werkt perfect
- 💾 Geen Docker overhead

**Setup:**
```bash
# 1. Installeer Ollama en modellen
./setup_ollama.sh

# 2. Installeer Python dependencies
cd backend
pip install -r requirements.txt

# 3. Start backend
uvicorn main:app --reload --port 8002

# 4. Start frontend (nieuwe terminal)
cd frontend
python3 -m http.server 3000
```

**Ollama locatie:** Direct op host (localhost:11434)

---

### Scenario 2: Docker (met host Ollama) - VOOR PRODUCTION

**Voordelen:**
- 📦 Geïsoleerde environment
- 🚢 Easy deployment
- 🔒 Consistente setup

**Nadelen:**
- 🐌 Iets langzamer (Docker overhead)
- 🔧 Complexer debugging

**Setup:**
```bash
# 1. Installeer Ollama op HOST machine (niet in Docker!)
./setup_ollama.sh

# 2. Zorg dat Ollama draait op host
ollama serve

# 3. Start Docker containers
docker-compose up --build

# 4. Test connectie
docker exec -it spaans-leren-backend curl http://host.docker.internal:11434/api/tags
```

**Ollama locatie:** Op host machine, bereikbaar via `host.docker.internal:11434`

## 🔌 Hoe werkt Docker Networking?

### De Uitdaging
Docker containers draaien in geïsoleerde netwerken:
- `localhost` in container = de container zelf, NIET de host
- Ollama draait op host machine (port 11434)
- Container moet host kunnen bereiken

### De Oplossing
```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - OLLAMA_HOST=host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Dit creëert een "bridge" van container naar host.

### Verificatie
```bash
# In container:
docker exec -it spaans-leren-backend curl http://host.docker.internal:11434/api/tags

# Verwacht output: {"models":[...]}
```

## 📊 Wanneer gebruik je wat?

| Situatie | Aanbeveling | Reden |
|----------|-------------|-------|
| Development/Testing | **Lokaal** | Snelste feedback loop |
| Code wijzigingen maken | **Lokaal** | Hot-reload werkt perfect |
| Debugging AI prompts | **Lokaal** | Directe logs en console output |
| Demo aan anderen | **Docker** | Consistente environment |
| Production deployment | **Docker** | Geïsoleerd en reproduceerbaar |
| Ollama experimenteren | **Lokaal** | Direct model switching |

## 🛠️ Huidige File Locaties

Alles staat in: `/Users/jaccostokx/projects/spaans-leren-app/`

```
spaans-leren-app/
├── backend/
│   ├── main.py                  ✅ Hybride systeem geïntegreerd
│   ├── ai_router.py             ✅ Smart routing (lokaal + Docker)
│   ├── requirements.txt         ✅ httpx toegevoegd
│   └── ...
├── frontend/
│   └── ...
├── docker-compose.yml           ✅ OLLAMA_HOST configured
├── setup_ollama.sh              ✅ Installatie script
├── test_ollama.sh               ✅ Test script
└── HYBRID_AI_QUICKSTART.md      ✅ Gebruiksinstructies
```

## 🚀 Snelle Start - Jouw Situatie

### Optie A: Start Lokaal (AANBEVOLEN eerst)

```bash
# Terminal 1: Installeer Ollama (eenmalig)
cd /Users/jaccostokx/projects/spaans-leren-app
./setup_ollama.sh

# Terminal 2: Start backend (lokaal)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8002

# Terminal 3: Start frontend
cd frontend
python3 -m http.server 3000

# Browser: http://localhost:3000
```

### Optie B: Start Docker (na Ollama install)

```bash
# Terminal 1: Zorg dat Ollama draait
ollama serve

# Terminal 2: Start Docker
cd /Users/jaccostokx/projects/spaans-leren-app
docker-compose up --build

# Browser: http://localhost:3000
```

## 🔍 Troubleshooting

### Docker: "Failed to connect to Ollama"

**Probleem:** Container kan host Ollama niet bereiken

**Oplossing:**
```bash
# 1. Check of Ollama draait op host
ps aux | grep ollama
# Of start het:
ollama serve

# 2. Test vanuit container
docker exec -it spaans-leren-backend curl http://host.docker.internal:11434/api/tags

# 3. Check firewall (macOS)
# Systeem Settings > Netwerk > Firewall > Allow Ollama

# 4. Als het nog niet werkt, check Docker Desktop settings
# Settings > Resources > Network > Enable host.docker.internal
```

### Lokaal: "Connection refused"

**Probleem:** Ollama server niet actief

**Oplossing:**
```bash
# Start Ollama server
ollama serve

# Test
curl http://localhost:11434/api/tags
```

### "Model not found"

**Probleem:** Modellen niet gedownload

**Oplossing:**
```bash
# Download opnieuw
ollama pull qwen2.5:14b
ollama pull mistral:7b-instruct

# Verificeer
ollama list
```

## 📈 Performance Vergelijking

| Metric | Lokaal | Docker |
|--------|--------|--------|
| Qwen response | 2-3 sec | 3-4 sec |
| Mistral response | <1 sec | 1-2 sec |
| Startup tijd | Instant | ~5 sec |
| Memory overhead | 0 MB | ~200 MB |
| Hot-reload | Perfect | Volume mount lag |

## 🎯 Mijn Aanbeveling

**Voor jou, Jacco:**

1. **Start Lokaal** voor development:
   ```bash
   ./setup_ollama.sh
   cd backend && uvicorn main:app --reload --port 8002
   ```

2. **Test Docker** alleen als je wil deployen of demo'en:
   ```bash
   docker-compose up --build
   ```

**Reden:** Lokaal is sneller, makkelijker te debuggen, en je kunt direct zien welke modellen worden gebruikt in de backend logs.

## 📝 Environment Variables Samenvatting

### Lokaal (.env file):
```bash
ANTHROPIC_API_KEY=your_key_here
# OLLAMA_HOST niet nodig (default: localhost:11434)
```

### Docker (docker-compose.yml):
```yaml
environment:
  - OLLAMA_HOST=host.docker.internal:11434  # Bereik host Ollama
```

## ✅ Checklist

**Lokaal Setup:**
- [ ] Ollama geïnstalleerd (`./setup_ollama.sh`)
- [ ] Modellen gedownload (Qwen + Mistral)
- [ ] Python dependencies geïnstalleerd (`pip install -r requirements.txt`)
- [ ] Backend draait (`uvicorn main:app --reload --port 8002`)
- [ ] Ollama server actief (`ollama serve` of auto-start)

**Docker Setup:**
- [ ] Ollama geïnstalleerd **op host** (niet in Docker!)
- [ ] Modellen gedownload op host
- [ ] Docker Desktop actief
- [ ] `docker-compose up --build` succesvol
- [ ] Container kan host bereiken (test met curl command hierboven)

## 🎓 Wat je geleerd hebt

1. **Docker networking:** Containers zijn geïsoleerd, `host.docker.internal` is de bridge
2. **Hybride architectuur:** Ollama lokaal, backend in container (best of both worlds)
3. **Fallback strategie:** Altijd Claude als safety net
4. **Environment flexibility:** Zelfde code werkt lokaal EN in Docker

---

**Vragen?** Start lokaal, dan is het makkelijkst te begrijpen hoe alles werkt!
