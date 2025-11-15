# 🇪🇸 Spaans Leren App

**AI-Powered Spanish Learning Application with Visual Mnemonics**

A full-stack web application that uses AI to help learn Spanish vocabulary through visual memory aids, automatic categorization, and SVG visualizations.

## ✨ Features

### 🤖 AI-Powered Learning
- **Automatic Translation**: Just enter a Dutch word, AI generates Spanish translation
- **Smart Categorization**: Automatically classifies words (verb, noun, food, family, etc.)
- **Creative Mnemonics**: Phonetic word associations between Spanish and Dutch
- **Visual SVG Illustrations**: Auto-generated 800x700px images with emojis
- **Example Sentences**: Contextual usage examples in both languages
- **Related Words**: Synonyms, antonyms, and word families

### 🎯 Spaced Repetition (SM-2 Algorithm)
- **Smart Review Scheduling**: Based on SuperMemo SM-2 algorithm
- **Performance Tracking**: Review history, success rates, easiness factors
- **Daily Goals**: Progress tracking with visual heatmap
- **Leitner Box System**: Queue management for optimal learning

### 🎓 Multiple Practice Modes
- **🎧 Listening Practice**: Text-to-speech audio with fuzzy matching
- **📝 Multiple Choice Quiz**: Random Dutch↔Spanish direction
- **⌨️ Type Mode**: Full keyboard input with spaced repetition tracking
- **🇪🇸 Spanish Character Helper**: On-screen buttons for á, é, í, ó, ú, ñ, ü, ¿, ¡

### 📊 Statistics & Analytics
- **Study Heatmap**: GitHub-style contribution graph
- **Current Streak**: Daily study tracking
- **Performance Metrics**: Cards reviewed, success rate, study time
- **Review History**: Complete learning journey visualization

## 🏗️ Tech Stack

### Backend
- **FastAPI** (Python 3.11+)
- **SQLAlchemy** ORM
- **SQLite** Database
- **Anthropic Claude API** (Sonnet 4.5)
- **Ollama** (Local LLM - in development)
- **gTTS** (Text-to-Speech)

### Frontend
- **React 18**
- **Tailwind CSS**
- **Vanilla JavaScript** (no complex state management)

### Infrastructure
- **Docker** / **OrbStack**
- **Nginx** (Reverse proxy)
- **macOS** (Apple Silicon M3 Pro optimized)

## 🚀 Getting Started

### Prerequisites
- Docker / OrbStack
- Python 3.11+
- Node.js 18+
- Anthropic API Key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/jaccostokx/spaans-leren-app.git
cd spaans-leren-app
```

2. **Set up environment variables**
```bash
cd backend
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

3. **Start the application**
```bash
# Using Docker Compose
docker-compose up -d

# Or manually:
# Backend
cd backend
bash start.sh

# Frontend
cd frontend
npm install
npm start
```

4. **Access the application**
- Frontend: http://localhost/ (or http://spaans.local via OrbStack)
- Backend API: http://localhost/api/
- API Docs: http://localhost/api/docs

## 📦 Project Structure

```
spaans-leren-app/
├── backend/
│   ├── main.py              # FastAPI server + AI integration
│   ├── database.py          # SQLAlchemy models
│   ├── ai_router.py         # Hybrid AI routing (Ollama + Claude)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── start.sh
│   └── stop.sh
├── frontend/
│   ├── index.html           # React SPA
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   └── nginx.conf           # Reverse proxy config
├── docker-compose.yml
├── CLAUDE.md                # Detailed project documentation
└── README.md
```

## 🔐 Security

- ✅ .env files excluded from git
- ✅ API keys in environment variables
- ✅ Database files gitignored
- ⚠️ No authentication (personal use only)
- ⚠️ Not intended for public deployment

## 👤 Author

**Jacco Stokx**
- Data Scientist
- Location: Goes, Netherlands
- Learning: Spanish 🇪🇸

## 📄 License

This is a personal learning project. Feel free to use for educational purposes.

---

**Note**: This app is designed for personal use. Remember to add your ANTHROPIC_API_KEY to backend/.env before running.
