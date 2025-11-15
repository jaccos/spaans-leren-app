# Spaanse Leer-App - Project Specificaties voor Claude Code

## 📋 Project Overview

**Eigenaar:** Jacco Stokx  
**Doel:** Persoonlijke applicatie voor het leren van Spaans met visuele geheugensteuntjes  
**Ontwikkelperiode:** November 2025  
**Status:** Productie-klaar, volledig functioneel

### Korte Beschrijving
Een full-stack web applicatie die AI gebruikt om Nederlands-Spaanse woordenschat te leren via visuele mnemonics, automatische categorisatie, en SVG visualisaties. De gebruiker voert simpelweg een Nederlands woord in, en de AI genereert automatisch:
- Spaanse vertaling
- Grammaticale uitleg en vervoegingen
- Creatieve geheugensteuntjes (mnemonics)
- Visuele SVG illustraties met emoji's
- Woordcategorie classificatie

---

## 🏗️ Architectuur

### Tech Stack
- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React 18 met Tailwind CSS
- **Database:** SQLite
- **AI:** Anthropic Claude API (Sonnet 4.5) + Ollama (in ontwikkeling)
- **Deployment:** OrbStack containers
- **OS:** macOS (Apple Silicon M3 Pro geoptimaliseerd)

### Project Structuur
```
spaans-leren-app/
├── backend/
│   ├── main.py              # FastAPI server + AI integratie
│   ├── ai_router.py         # Hybride AI routing (Ollama + Claude)
│   ├── database.py          # SQLAlchemy models
│   ├── Dockerfile           # Backend container image
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # Environment vars (ANTHROPIC_API_KEY)
├── frontend/
│   ├── index.html           # Single-page React app (CDN-based)
│   └── Dockerfile           # Nginx container image
├── nginx/
│   └── nginx.conf           # Reverse proxy configuratie
├── docker-compose.yml       # Orchestratie van alle services
├── .claude/
│   └── skills/
│       └── spaced-repetition/  # SuperMemo SM-2 algoritme skill
├── README.md                # Gebruikersdocumentatie
├── DEPLOYMENT.md            # Technische deployment docs
└── CLAUDE.md                # Dit bestand

```

### Docker Architecture (13 Nov 2025)
```
Browser → http://localhost:80 (of https://spaans.local)
    ↓
  Nginx Container (spaans)
    ├─→ / (frontend static files)
    └─→ /api/* → Backend Container (spaans-leren-backend:8002)
            ├─→ Ollama Container (spaans-leren-ollama:11434)
            └─→ Claude API (fallback)
```

### Deployment URLs
- **Primair:** https://spaans.local (OrbStack custom domain)
- **Alternatief:** http://localhost (direct)
- **Fallback:** https://spaans.orb.local (default OrbStack)
- **Backend Direct:** Niet beschikbaar (alleen via Nginx reverse proxy)

---

## ✨ Belangrijkste Features

### 1. AI-Powered Vertaling & Categorisatie
**Gebruiker voert Nederlands woord in** → AI genereert automatisch:
- Spaanse vertaling met meerdere betekenissen (bijv. "mesa" = tafel, plateau, bestuur)
- Woordcategorie (werkwoord, zelfstandig naamwoord, bijwoord, voedsel, familie, werk, etc.)
- Grammaticale details (vervoegingen, meervoud/enkelvoud, geslacht)
- Voorbeeldzinnen met context

### 2. Creatieve Mnemonics (Geheugensteuntjes)
**AI genereert visuele associaties** tussen Spaans geluid en Nederlands concept:
- "sandía" (watermeloen) → "SAND en DÍA (dag)" → watermeloen eten op warme zandstrand
- "trabajar" (werken) → "TRAceren met je BAnen = JARenlang werken"
- "mesa" (tafel) → "MESA = MEt SAus op tafel"

Mnemonics bevatten:
- Fonetische woordspelingen
- Levendige beeldvorming
- Culturele context waar relevant
- Meerdere betekenissen tussen haakjes

### 3. SVG Visualisaties
**Automatische generatie van 800x700px SVG afbeeldingen:**
- Gradient achtergrond (purple/pink)
- Grote emoji (140px) bovenaan gecentreerd
- Spaans woord (72px, wit, bold)
- Nederlandse vertaling (38px, wit)
- Witte informatiebox (40,440, 720x220) met:
  - 💡 emoji
  - Mnemonic tekst (max 4 regels, 65 tekens per regel)
  - Font-size: 20px, line-height: 32px
  - Gecentreerde tekst (x=400, text-anchor="middle")

**Speciale visualisaties:**
- Sommige woorden krijgen custom SVG tekeningen (bijv. "tafel" krijgt een getekende tafel ipv emoji)

### 4. Moderne UI/UX
- **Zoekbare woordenlijst:** Alfabetisch gesorteerd, real-time zoeken
- **Flashcard Modus:** Random presentatie voor effectief oefenen
- **Modal Windows:** Klikbare visualisaties voor vergroot beeld
- **Progress Tracking:** Telt aantal geoefende woorden
- **Clean Table Design:** Compacte weergave met alle details

### 5. Hybride AI Systeem (in ontwikkeling)
**AI Router (`ai_router.py`)** schakelt intelligent tussen:
- **Qwen 2.5:14b** (Ollama) → Vertaling + grammatica (70% van queries)
- **Mistral 7b** (Ollama) → Creatieve mnemonics (15%)
- **Claude Sonnet 4.5** (API) → Validation + fallback (15%)

**Voordelen:**
- ~$0.0045 kostenbesparing per lokale call
- Offline capabilities
- Automatische fallback bij fouten
- Cost tracking en statistieken

---

## 📚 Ontwikkelgeschiedenis & Opgeloste Bugs

### Fase 1: Conceptontwikkeling (3-4 Nov 2025)
**Begonnen met:** Basisidee voor visuele Spaanse woordenschat app
- Eerste visualisaties met mindmaps en mnemonics
- Handmatige vertaling en geheugensteuntjes
- Focus op Nederlands-Spaans woordenparen

### Fase 2: Full-Stack Development (5 Nov 2025)
**Opgebouwd:**
- FastAPI backend met Claude AI integratie
- React frontend met Tailwind CSS
- SQLite database voor persistentie
- Automatische AI-gedreven vertaling en categorisatie

**Iteraties:**
1. Card-based layout → Table layout (op verzoek gebruiker)
2. Manuele categorie selectie → Automatische AI categorisatie
3. Sequentiële flashcards → Random presentatie
4. File:// protocol → HTTP server (CORS issue fix)

### Fase 3: Bugfixes & Optimalisaties (5 Nov avond)

#### Bug #1: SVG Tekst Positionering ("tafel" woord)
**Probleem:** Beschrijvende tekst compleet misaligned met visualisatie
**Oorzaak:** Tekst gebruikte x="140" (links uitgelijnd) terwijl rest gecentreerd was op x="400"
**Oplossing:** 
- Tekst gecentreerd met `text-anchor="middle"` en `x="400"`
- Font-size geoptimaliseerd naar 20px
- Line-height verhoogd naar 32px voor leesbaarheid

#### Bug #2: UnboundLocalError voor "vivo"
**Probleem:** Crash bij genereren van woorden anders dan "tafel"
```python
UnboundLocalError: local variable 'base64' referenced before assignment
```
**Oorzaak:** `base64` import alleen binnen special case "tafel", niet beschikbaar voor andere woorden
**Oplossing:** `import base64` naar top van `generate_svg_visualization()` functie verplaatst

#### Bug #3: Duplicate Woorden in Database
**Probleem:** Zelfde Nederlands woord kon meerdere keren toegevoegd worden
**Oorzaak:** Geen duplicate check in `create_word` endpoint
**Oplossing:** 
- Case-insensitive check toegevoegd voor bestaande Nederlandse woorden
- Returnt bestaande entry als woord al bestaat
- Database opgeschoond (duplicaten "klein" en "wonen" verwijderd)

```python
existing_word = db.query(Word).filter(
    func.lower(Word.dutch_word) == dutch_word.lower()
).first()
if existing_word:
    return existing_word
```

#### Bug #4: Emoji Mapping Inconsistentie
**Probleem:** "tafel" kreeg 🪑 (stoel emoji) ipv tafel representatie
**Oorzaak:** Emoji rules mappede zowel "tafel" als "stoel" naar zelfde emoji
**Oplossing:**
- Special case voor "tafel" met custom SVG tekening
- Tafel getekend met houten textuur, 4 poten, en borden erop
- Base64 encoded SVG als data URI in parent SVG

#### Bug #5: Meerdere Betekenissen Ontbraken
**Probleem:** "mesa" werd alleen als "tafel" vertaald, andere betekenissen gemist
**Oorzaak:** AI gaf niet alle betekenissen in eerste instantie
**Oplossing:**
- Prompt aangepast om meerdere betekenissen te vragen
- Mnemonics nu met context: "mesa (tafel, plateau, bestuur)"
- Gebruiker krijgt vollediger begrip van Spaanse woorden

### Fase 4: Lokale AI Integratie (12 Nov 2025)
**Doel:** Vervangen Anthropic API met lokale Ollama modellen voor kostenreductie
**Hardware:** MacBook Pro M3 Pro, 36GB RAM (geschikt voor 13B-70B modellen)
**Implementatie:**
- `ai_router.py` gebouwd met intelligente routing
- Ollama modellen: Qwen2.5:14b en Mistral 7b
- Timeout handling (60s)
- Automatische fallback naar Claude bij fouten
- Cost tracking en statistieken endpoint

**Status:** Volledig geïmplementeerd, modellen aan het downloaden

---

## 🔧 API Endpoints

### Base URL
`http://localhost:8002` of `https://backend.spaans-leren-app.orb.local`

### Health Check
```bash
GET /health
Response: {"status": "healthy"}
```

### Create/Get Word
```bash
POST /api/words/
Content-Type: application/json
Body: {"dutch_word": "tafel"}

Response: {
  "id": 1,
  "dutch_word": "tafel",
  "spanish_word": "mesa",
  "category": "noun",
  "mnemonic": "MESA = MEt SAus op tafel",
  "explanation": "Zelfstandig naamwoord, vrouwelijk (la mesa)...",
  "svg_visualization": "<svg>...</svg>",
  "created_at": "2025-11-05T20:30:00"
}
```

**Belangrijk:** Duplicate check is case-insensitive, retourneert bestaand woord indien al aanwezig.

### List All Words
```bash
GET /api/words/
Response: [
  {
    "id": 1,
    "dutch_word": "tafel",
    "spanish_word": "mesa",
    "category": "noun",
    "mnemonic": "...",
    ...
  },
  ...
]
```
**Sortatie:** Alfabetisch op `dutch_word` (case-insensitive)

### Get AI Statistics (Hybride Systeem)
```bash
GET /api/stats/ai
Response: {
  "qwen_calls": 45,
  "mistral_calls": 12,
  "claude_calls": 8,
  "total_ollama_errors": 2,
  "total_calls": 65,
  "claude_percentage": 12.3,
  "cost_savings": {
    "actual_cost_usd": 0.036,
    "all_claude_cost_usd": 0.2925,
    "savings_usd": 0.2565,
    "savings_percentage": 87.7
  }
}
```

---

## 🗄️ Database Schema

### SQLite Database: `spaans_leren.db`

```sql
CREATE TABLE words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dutch_word TEXT NOT NULL UNIQUE COLLATE NOCASE,
    spanish_word TEXT NOT NULL,
    category TEXT NOT NULL,
    mnemonic TEXT NOT NULL,
    explanation TEXT NOT NULL,
    svg_visualization TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Veldtypen
- **id:** Auto-increment primary key
- **dutch_word:** Case-insensitive unique constraint (COLLATE NOCASE)
- **spanish_word:** Kan meerdere varianten bevatten (bijv. "montar en bicicleta / pedalear")
- **category:** Waarden zoals "verb", "noun", "adjective", "food", "family", "work", etc.
- **mnemonic:** Creatieve geheugensteun met fonetische woordspeling
- **explanation:** Uitgebreide grammaticale details, vervoegingen, voorbeelden
- **svg_visualization:** Volledige SVG string (800x700px)
- **created_at:** Automatische timestamp

### Database Operaties

**Duplicaat Check:**
```python
from sqlalchemy import func
existing = db.query(Word).filter(
    func.lower(Word.dutch_word) == dutch_word.lower()
).first()
```

**Verwijderen Woord:**
```bash
sqlite3 spaans_leren.db "DELETE FROM words WHERE dutch_word='tafel';"
```

**Database Reset:**
```bash
rm spaans_leren.db
# Backend herstart maakt nieuwe database aan met schema
```

---

## 🎨 SVG Visualisatie Specificaties

### Standaard SVG Structuur (800x700px)

```svg
<svg width="800" height="700" xmlns="http://www.w3.org/2000/svg">
  <!-- Gradient Background -->
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8B5CF6"/>    <!-- Purple -->
      <stop offset="100%" stop-color="#EC4899"/>  <!-- Pink -->
    </linearGradient>
  </defs>
  
  <!-- Background Rectangle -->
  <rect width="800" height="700" fill="url(#bg-gradient)"/>
  
  <!-- Emoji (centered top, 140px font-size) -->
  <text x="400" y="150" font-size="140" text-anchor="middle">🍉</text>
  
  <!-- Spanish Word (centered, 72px bold white) -->
  <text x="400" y="280" font-size="72" font-weight="bold" 
        fill="white" text-anchor="middle">sandía</text>
  
  <!-- Dutch Translation (centered, 38px white) -->
  <text x="400" y="340" font-size="38" fill="white" 
        text-anchor="middle">watermeloen</text>
  
  <!-- White Info Box (x=40, y=440, width=720, height=220) -->
  <rect x="40" y="440" width="720" height="220" 
        fill="white" rx="20" opacity="0.95"/>
  
  <!-- Light Bulb Emoji (in box) -->
  <text x="70" y="480" font-size="32">💡</text>
  
  <!-- Mnemonic Text (multi-line, centered in box) -->
  <!-- Line 1 -->
  <text x="400" y="490" font-size="20" text-anchor="middle" 
        fill="#333">SAND + DÍA = Watermeloen eten op een warme</text>
  
  <!-- Line 2 -->
  <text x="400" y="522" font-size="20" text-anchor="middle" 
        fill="#333">zandstrand op een hete dag!</text>
  
  <!-- Line 3 (indien nodig) -->
  <text x="400" y="554" font-size="20" text-anchor="middle" 
        fill="#333">Spaanse 'día' klinkt als 'day' in Engels</text>
  
  <!-- Line 4 (max 4 regels, 65 chars per regel) -->
  <text x="400" y="586" font-size="20" text-anchor="middle" 
        fill="#333">(meerdere betekenissen indien relevant)</text>
</svg>
```

### Belangrijke SVG Positionering Regels

1. **Tekst Centreren:** ALTIJD `text-anchor="middle"` met `x="400"` (center van 800px)
2. **Line-height:** 32px tussen tekstregels (y-coordinaat verschil)
3. **Font-sizes:**
   - Emoji: 140px (top)
   - Spaans: 72px bold (wit)
   - Nederlands: 38px (wit)
   - Mnemonic: 20px (donkergrijs #333)
4. **Witte Box:** Start op y=440, hoogte 220px, opacity 0.95 voor lichte transparantie
5. **Max Tekst:** 4 regels van max 65 karakters elk

### Emoji Mapping Logica (in `main.py`)

```python
def get_emoji_for_word(spanish_word: str, dutch_word: str, category: str) -> str:
    emoji_map = {
        "hola": "👋", "adiós": "👋", "buenos días": "☀️",
        "gato": "🐱", "perro": "🐶", "pez": "🐠",
        "manzana": "🍎", "naranja": "🍊", "plátano": "🍌",
        "sandía": "🍉", "piña": "🍍", "melocotón": "🍑",
        "casa": "🏠", "coche": "🚗", "bicicleta": "🚲",
        "libro": "📚", "lápiz": "✏️", "papel": "📄",
        "mesa": "🍽️",  # NIET 🪑!
        "silla": "🪑",
        # ... meer mappings
    }
    
    # Fallback based on category
    category_emojis = {
        "food": "🍽️", "drink": "🥤", "fruit": "🍎",
        "animal": "🐾", "verb": "▶️", "adjective": "✨",
        "family": "👨‍👩‍👧‍👦", "work": "💼", "house": "🏠",
        # ... meer categorieën
    }
    
    return emoji_map.get(spanish_word.lower()) or 
           emoji_map.get(dutch_word.lower()) or 
           category_emojis.get(category, "📝")
```

### Special SVG Cases

**Woord "tafel" (mesa):**
- Krijgt GEEN emoji maar custom SVG tekening
- Functie: `generate_table_svg()` in `main.py`
- Tekent houten tafel met 4 poten en borden erop
- Gebruikt base64 encoded SVG als data URI
- Wordt ingevoegd in hoofdvisualisatie op y=100

```python
if dutch_word.lower() == "tafel":
    table_drawing = generate_table_svg()
    # Voeg table_drawing toe als <image> element in SVG
```

---

## 🚀 Development Workflow (Docker-Only sinds 13 Nov 2025)

**BELANGRIJK:** Applicatie draait volledig in Docker. Lokale scripts (start.sh/stop.sh) zijn verwijderd.

### Volledige Setup Starten
```bash
cd /Users/jaccostokx/projects/spaans-leren-app
docker-compose up -d
```

**Eerste keer opstarten:**
- Ollama downloadt automatisch Qwen 2.5:14b (~9GB) en Mistral 7b (~4GB)
- Dit duurt 10-15 minuten, app blijft bereikbaar via Claude fallback

### Services Stoppen
```bash
docker-compose down
```

### Development Mode met Volume Mounts

**✅ Huidige setup (Optie 1): Development mode met hot-reload**

De applicatie gebruikt **bind mounts** voor real-time development:

```yaml
# docker-compose.yml
backend:
  volumes:
    - ./backend:/app              # Lokale code → Container
    - spaans-db:/app/data         # Database persistent volume

nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./frontend/index.html:/usr/share/nginx/html/index.html:ro
```

**Voordelen:**
- ✅ Backend code wijzigingen → uvicorn auto-reload (geen rebuild)
- ✅ Frontend HTML wijzigingen → refresh browser (geen rebuild)
- ✅ .env file lokaal aanpasbaar
- ✅ Debugging en ontwikkeling makkelijk
- ⚠️ Lokale directories moeten blijven bestaan

**Hoe het werkt:**
1. Edit `/backend/main.py` lokaal
2. Uvicorn detecteert wijziging in container
3. Server herstart automatisch (~2s)
4. Refresh browser of test API opnieuw

**Frontend wijzigingen:**
1. Edit `/frontend/index.html` lokaal
2. Nginx serveert direct nieuwe versie
3. Refresh browser (Cmd+R of F5)

### Container Beheer

**Status checken:**
```bash
docker-compose ps
# Verwachte output:
# spaans                 (nginx, port 80)
# spaans-leren-backend   (FastAPI, intern)
# spaans-leren-ollama    (LLM models, port 11434)
```

**Logs bekijken:**
```bash
docker-compose logs -f nginx          # Nginx access/error logs
docker-compose logs -f backend        # Python logs + AI debug info
docker-compose logs -f ollama         # Ollama model loading

# Laatste 50 regels:
docker-compose logs --tail 50 backend
```

**Services herstarten:**
```bash
docker-compose restart backend        # Alleen backend herstarten
docker-compose restart nginx          # Nginx config reload
docker-compose restart                # Alle services
```

### API Testen (via Nginx Reverse Proxy)

```bash
# Health check (via stats endpoint, geen /health)
curl -s https://spaans.local/api/stats/ | python3 -m json.tool

# Woord toevoegen
curl -s -X POST https://spaans.local/api/words/ \
  -H "Content-Type: application/json" \
  -d '{"dutch_word":"fiets"}' | python3 -m json.tool

# Alle woorden ophalen
curl -s https://spaans.local/api/words/ | python3 -m json.tool

# AI Stats ophalen
curl -s https://spaans.local/api/stats/ai | python3 -m json.tool
```

### Database Beheer

**Database bevindt zich in Docker volume:**
```bash
# Backup maken
docker cp spaans-leren-backend:/app/data/spaans_leren.db ./backup-$(date +%Y%m%d).db

# Database queries uitvoeren
docker exec -it spaans-leren-backend sqlite3 /app/data/spaans_leren.db "SELECT COUNT(*) FROM words;"

# Interactieve SQLite sessie
docker exec -it spaans-leren-backend sqlite3 /app/data/spaans_leren.db

# Database reset (DESTRUCTIEF!)
docker-compose down
docker volume rm spaans-leren-db
docker-compose up -d
```

**Na schema changes:**
- Database schema wijzigingen vereisen volume verwijdering (zie boven)
- Huidige data gaat verloren
- Maak eerst backup!

### Debugging

**Container internals inspecteren:**
```bash
# Bash shell in backend container
docker exec -it spaans-leren-backend bash

# Check environment vars
docker exec spaans-leren-backend env | grep OLLAMA

# Check file permissions
docker exec spaans-leren-backend ls -la /app
```

**Ollama status:**
```bash
# Check welke modellen geladen zijn
docker exec spaans-leren-ollama ollama list

# Model handmatig pullen
docker exec spaans-leren-ollama ollama pull qwen2.5:14b

# Ollama logs
docker logs spaans-leren-ollama --tail 100
```

**Network debugging:**
```bash
# Test backend van binnen nginx container
docker exec spaans curl -s http://backend:8002/api/stats/

# Check exposed poorten
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

### Rebuilding

**Na Dockerfile wijzigingen:**
```bash
# Rebuild specifieke service
docker-compose build backend
docker-compose build nginx

# Rebuild alles zonder cache
docker-compose build --no-cache

# Rebuild en herstart
docker-compose up -d --build
```

**Image cleanup:**
```bash
# Verwijder oude unused images
docker image prune -a

# Check disk usage
docker system df
```

### Belangrijke Notes

**✅ Wat WEL werkt:**
- Backend hot-reload (uvicorn --reload detecteert file changes)
- Frontend instant updates (Nginx serveert direct van disk)
- Database persistence (blijft na docker-compose down)
- Ollama models persistence (13GB blijft cached)

**⚠️ Let op:**
- Backend poort 8002 is NIET exposed naar host (alleen intern)
- Alle API calls gaan via Nginx op poort 80
- .env file MOET in `/backend/.env` staan (wordt gemount in container)
- Database staat in Docker volume, niet in lokale directory

**❌ Niet meer beschikbaar:**
- Lokale start.sh/stop.sh scripts (verwijderd)
- Direct localhost:8002 toegang (gebruik localhost:80/api/)
- npm start voor frontend (geen Node.js meer nodig)

---

## 📦 Dependencies

### Backend (Python)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
anthropic>=0.7.0
pydantic>=2.0.0
requests>=2.31.0
```

### Frontend (React)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "devDependencies": {
    "tailwindcss": "^3.3.0"
  }
}
```

### Ollama Models (lokaal)
```bash
# Vertaling & Grammatica
ollama pull qwen2.5:14b

# Creatieve Mnemonics
ollama pull mistral:7b
```

---

## ⚠️ Known Issues & Workarounds

### Issue #1: Ollama Download Duurt Lang
**Symptoom:** Eerste keer Ollama gebruiken duurt 10-15 minuten  
**Oorzaak:** Modellen zijn 8-14GB groot  
**Workaround:** AI Router gebruikt automatisch Claude fallback tijdens download  
**Status:** Werkt zoals ontworpen ✅

### Issue #2: Sommige Vervoegingen Ontbreken
**Symptoom:** Niet alle werkwoordvervoegingen worden gegenereerd  
**Oorzaak:** AI output soms onvolledig  
**Workaround:** Voeg specifiekere prompts toe voor volledige conjugatie tabel  
**Status:** Te verbeteren 🔧

### Issue #3: Frontend CORS bij File Protocol
**Symptoom:** `file:///index.html` kan niet communiceren met backend  
**Oorzaak:** CORS policy blokkeert cross-origin requests  
**Oplossing:** ALTIJD frontend via `npm start` draaien (niet file:// openen)  
**Status:** Opgelost ✅

### Issue #4: Emoji Consistency
**Symptoom:** Sommige woorden krijgen vreemde emoji's  
**Oorzaak:** Fallback emoji logic niet perfect  
**Workaround:** Voeg specifieke mappings toe aan `emoji_map` dict  
**Status:** Ongoing verbetering 🔧

---

## 🎯 Roadmap & Toekomstige Features

### Kort Termijn (Q4 2025)
- [x] Hybride AI systeem (Ollama + Claude)
- [x] Cost tracking & statistieken
- [ ] Volledige Ollama integratie testen
- [ ] Spaced Repetition algoritme implementeren (SuperMemo SM-2)
- [ ] Audio uitspraak toevoegen (Text-to-Speech)
- [ ] Progress tracking per woord (geleerd/oefenen/moeilijk)

### Middellange Termijn (Q1 2026)
- [ ] User accounts & authentication
- [ ] Flashcard algoritme met moeilijkheidsgraad
- [ ] Export functionaliteit (CSV, PDF)
- [ ] Mobile-responsive design optimalisatie
- [ ] Dark mode support

### Lange Termijn (2026+)
- [ ] Mobile app (React Native?)
- [ ] Grammatica oefeningen generator
- [ ] Conversatie practice met AI
- [ ] Gamification (punten, badges, streaks)
- [ ] Community features (gedeelde woordenlijsten)

---

## 🤖 Instructies voor Claude Code

### Wanneer Te Gebruiken

**Gebruik deze app VOOR:**
- Nieuwe Nederlandse woorden toevoegen via API
- Bugs fixen in backend/frontend
- Database queries uitvoeren
- SVG visualisaties aanpassen
- AI prompts optimaliseren
- Ollama integratie testen

**NIET gebruiken VOOR:**
- Productie deployment (blijft lokaal)
- Gevoelige data opslag (alleen leer-content)
- Real-time collaboration features

### Belangrijke Commando's (Docker-Only)

**Project Status Checken:**
```bash
# Container status
docker-compose ps

# Backend health check (via Nginx)
curl -s https://spaans.local/api/stats/ | python3 -m json.tool

# Alle woorden tellen (in container)
docker exec spaans-leren-backend sqlite3 /app/data/spaans_leren.db "SELECT COUNT(*) FROM words;"

# Recente woorden bekijken (in container)
docker exec spaans-leren-backend sqlite3 /app/data/spaans_leren.db "SELECT dutch_word, spanish_word, category FROM words ORDER BY created_at DESC LIMIT 10;"

# AI statistieken (via Nginx)
curl -s https://spaans.local/api/stats/ai | python3 -m json.tool

# Ollama modellen check
docker exec spaans-leren-ollama ollama list
```

**Veelgebruikte Acties:**
```bash
# Volledige herstart
docker-compose restart

# Alleen backend herstart (na code wijziging, maar auto-reload zou moeten werken)
docker-compose restart backend

# Database backup
docker cp spaans-leren-backend:/app/data/spaans_leren.db ./backup-$(date +%Y%m%d).db

# Database reset (DESTRUCTIEF!)
docker-compose down
docker volume rm spaans-leren-db
docker-compose up -d

# Logs bekijken
docker-compose logs -f backend
docker-compose logs --tail 50 nginx

# Container shell (debugging)
docker exec -it spaans-leren-backend bash
```

### Claude Code Context

**Bij Vragen Over:**
- **SVG Issues:** Lees eerst sectie "SVG Visualisatie Specificaties"
- **Emoji Problemen:** Check `emoji_map` in `main.py` en "Special SVG Cases"
- **Database Errors:** Zie "Database Schema" en "Database Operaties"
- **AI Router Issues:** Check `ai_router.py` en "Hybride AI Systeem"
- **Docker Setup:** Zie "Development Workflow (Docker-Only)" sectie
- **Deployment:** Gebruik https://spaans.local (OrbStack) of http://localhost

**Code Aanpassingen Workflow (Docker):**
1. Maak wijziging in lokale file (`backend/main.py`, `frontend/index.html`, etc.)
2. Backend: uvicorn detecteert wijziging en herstart automatisch (~2s)
3. Frontend: refresh browser (geen rebuild nodig)
4. Test met curl/browser via https://spaans.local
5. Bij problemen: check logs met `docker-compose logs -f backend`
6. Verifieer fix met nieuwe test
7. **GEEN** handmatige restart nodig (tenzij Dockerfile wijzigt)

**Prompt Engineering Tips:**
- Vraag expliciet om ALLE betekenissen van Spaanse woorden
- Specificeer max lijnlengte (65 chars) voor mnemonics
- Vraag om fonetische woordspelingen in Nederlands context
- Gebruik "JSON zonder markdown" om parsing errors te voorkomen

---

## 📝 Belangrijke Design Beslissingen

### Waarom SQLite?
- **Pro:** Simpel, geen aparte database server nodig, perfect voor persoonlijke app
- **Con:** Niet geschikt voor multi-user scenarios
- **Beslissing:** Blijft SQLite, app is voor persoonlijk gebruik

### Waarom Hybride AI (Ollama + Claude)?
- **Pro:** Kostenreductie (~88%), offline capabilities, sneller voor simpele queries
- **Con:** Extra complexiteit, grotere dependency footprint
- **Beslissing:** Claude fallback garandeert betrouwbaarheid

### Waarom Custom SVG ipv Afbeeldingen?
- **Pro:** Schaalbaar, aanpasbaar, geen external dependencies, consistent design
- **Con:** Complexer om te genereren dan simpele images
- **Beslissing:** Betere controle over visuele leer-ervaring

### Waarom React Zonder State Management Library?
- **Pro:** Simpeler, minder dependencies, voldoende voor app scope
- **Con:** Moeilijker te schalen als app complexer wordt
- **Beslissing:** Built-in useState/useEffect voldoende voor nu

---

## 🧠 Lessons Learned

### Technisch
1. **SVG Tekst Centrering:** ALTIJD `text-anchor="middle"` gebruiken voor gecentreerde tekst, niet alleen x-coordinaat
2. **Import Scope:** Base64 en andere imports moeten op function-level staan, niet in conditional blocks
3. **Database Case Sensitivity:** Gebruik `COLLATE NOCASE` en `func.lower()` voor case-insensitive queries
4. **Backend Hot Reload:** FastAPI's `--reload` werkt niet betrouwbaar, altijd volledige restart
5. **CORS in Development:** File protocol werkt niet met CORS, gebruik altijd HTTP server

### Product Design
1. **Minder Input = Beter UX:** Automatische categorisatie werkt beter dan manuele selectie
2. **Random > Sequential:** Flashcards zijn effectiever met random presentatie
3. **Visual Memory:** Emoji + mnemonic + SVG geeft sterker geheugen dan alleen tekst
4. **Multiple Meanings Matter:** Spaanse woorden hebben vaak meerdere betekenissen die allemaal relevant zijn

### AI Integration
1. **Fallback Strategy Essentieel:** Lokale AI kan falen, Claude backup voorkomt user frustration
2. **Prompt Specificity:** Hoe specifieker de prompt, hoe consistenter de output
3. **JSON Parsing:** Vraag expliciet om "geen markdown" om parsing errors te vermijden
4. **Context in Mnemonics:** Nederlandse context maakt mnemonics veel effectiever dan generieke associaties

---

## 👤 Credits & Context

**Ontwikkelaar:** Jacco Stokx  
**Rol:** Data Scientist, binnenkort met pensioen  
**Locatie:** Nederland (Goes, Zeeland)  
**Talen:** Nederlands (native), Engels, Spaans (lerende)  
**Tech Stack Expertise:** Python, SQL, PowerBI, FastAPI, React

**Project Motivatie:**
- Persoonlijke tool voor Spaans leren
- Praktijkervaring met AI integratie
- Experimenten met lokale LLMs (Ollama)
- Portfolio project voor vibe coding

**Ontwikkeling Aanpak:**
- Iteratieve development met snelle feedback loops
- AI-first benadering (laat Claude het zware werk doen)
- Pragmatisch: functionaliteit boven perfectie
- Focus op persoonlijke leer-ervaring, niet commercieel product

---

## 📚 Referenties & Resources

### Documentatie
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/
- Tailwind CSS: https://tailwindcss.com/
- Anthropic API: https://docs.anthropic.com/
- Ollama: https://ollama.ai/

### Gerelateerde Skills
- **Spaced Repetition:** `.claude/skills/spaced-repetition/SKILL.md`
  - SuperMemo SM-2 algoritme
  - Optimale herhalingsintervallen
  - Moeilijkheidsgraad tracking

### Inspiratie & Methodologie
- SuperMemo SM-2 Algorithm (1987)
- Visual Memory Techniques (Tony Buzan)
- Mnemonic Major System
- Duolingo's gamification approach

---

## 🔐 Security & Privacy

**Huidige Status:**
- Geen authentication/authorization
- Lokaal gebruik only (niet exposed naar internet)
- API keys in environment variables (`.env` file)
- Database niet encrypted (persoonlijke leer-data)

**Voor Productie (indien ooit):**
- Implementeer user authentication (OAuth2)
- HTTPS verplicht stellen
- Rate limiting op API endpoints
- Database encryptie overwegen
- API keys in secure vault (AWS Secrets Manager, etc.)

---

## 📊 Project Metrics (Stand 12 Nov 2025)

**Code:**
- Backend: ~800 regels Python
- Frontend: ~400 regels React/JavaScript
- Total: ~1200 regels applicatie code
- Config/Scripts: ~100 regels

**Database:**
- Woorden opgeslagen: ~25-30 (groeiend)
- Avg response time: <2s (Claude), <1s (Ollama target)
- Database size: ~500KB

**AI Usage:**
- Claude API calls: ~65 totaal tijdens development
- Geschatte kosten: ~$0.30 (excl. development chats)
- Target savings met Ollama: 85-90%

---

## 🎓 Voor Claude Code Gebruikers

**Dit Bestand Gebruiken:**
```bash
# In Claude Code terminal
cat CLAUDE.md  # Overzicht krijgen

# Of specifieke secties zoeken
grep -A 10 "API Endpoints" CLAUDE.md
grep -A 20 "SVG Visualisatie" CLAUDE.md
```

**Veelgestelde Vragen:**

**Q: Hoe voeg ik een nieuw woord toe?**
A: POST naar `https://spaans.local/api/words/` met `{"dutch_word": "jouw_woord"}`, AI doet de rest!

**Q: SVG ziet er verkeerd uit?**
A: Check "SVG Visualisatie Specificaties" sectie, vooral text-anchor en x-coordinaten.

**Q: Database is corrupt?**
A: Backup maken via `docker cp`, dan `docker-compose down`, `docker volume rm spaans-leren-db`, `docker-compose up -d`.

**Q: Ollama werkt niet?**
A: Check `docker exec spaans-leren-ollama ollama list`, AI Router valt automatisch terug naar Claude.

**Q: Hoe test ik zonder UI?**
A: Gebruik curl commands via `https://spaans.local/api/...` (zie "API Testen" sectie).

**Q: Moet ik backend/frontend directories behouden?**
A: Ja! Deze zijn gemount in Docker containers voor hot-reload development. Zie "Development Mode met Volume Mounts".

---

**Laatst Bijgewerkt:** 13 November 2025
**Versie:** 2.0 (Docker-only deployment)
**Status:** ✅ Productie-klaar, volledig Docker-based

---

*Dit document is bedoeld voor gebruik met Claude Code en bevat alle technische specificaties, ontwikkelgeschiedenis, en instructies voor het werken met de Spaanse leer-app. Voor vragen of updates, zie de corresponderende chat history in het "Leer spaans" project.*