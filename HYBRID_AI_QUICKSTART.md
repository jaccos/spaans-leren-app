# 🚀 HYBRIDE AI SYSTEEM - QUICK START

## Wat is geïmplementeerd?

Je Spaanse leer-app gebruikt nu een **hybride AI systeem** dat slim kiest tussen lokale modellen en Claude API:

- **Qwen 2.5 14B** (lokaal, 70% van queries): Vertalingen & grammatica
- **Mistral 7B** (lokaal, 15% van queries): Creatieve mnemonics
- **Claude API** (cloud, 15% van queries): Validation & complexe cases

**Resultaat**: 85-95% kostenbesparing + snellere responses + offline capability

## 🎯 Installatie (Eenmalig)

### Stap 1: Installeer Ollama & download modellen

```bash
cd /Users/jaccostokx/projects/spaans-leren-app
./setup_ollama.sh
```

Dit script:
- ✅ Installeert Ollama
- ✅ Download Qwen 2.5 14B (~8GB)
- ✅ Download Mistral 7B Instruct (~4GB)
- ✅ Configureert optimale settings voor M3 Pro
- ✅ Test beide modellen

**Verwachte duur**: 15-20 minuten (afhankelijk van internet snelheid)

### Stap 2: Update Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

Dit installeert httpx voor Ollama API communicatie.

## 🧪 Testen

### Quick Test

```bash
./test_ollama.sh
```

Dit test:
- ✅ Of Ollama server actief is
- ✅ Of beide modellen beschikbaar zijn
- ✅ Qwen vertaling (NL → ES)
- ✅ Mistral mnemonic generatie
- ✅ Backend API statistics endpoint

### Full Workflow Test

```bash
# Start backend (in terminal 1)
cd backend
uvicorn main:app --reload --port 8002

# Test complete workflow (in terminal 2)
curl -X POST http://localhost:8002/api/words/add \
  -H "Content-Type: application/json" \
  -d '{"dutch_word": "bibliotheek"}'

# Check AI stats
curl http://localhost:8002/api/stats/ai | jq '.'
```

## 🎮 Gebruik

### Start de app (normale workflow)

```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload --port 8002

# Terminal 2: Start frontend
cd frontend
python3 -m http.server 3000

# Open browser: http://localhost:3000
```

De app werkt nu **automatisch met het hybride systeem**:
- Type Nederlands woord → Qwen vertaalt → Mistral maakt mnemonic → SVG wordt gegenereerd
- Alles gebeurt lokaal (gratis, snel, privacy)
- Bij errors: automatische fallback naar Claude

### Force Claude (voor maximale kwaliteit)

Je kunt nog steeds Claude forceren via de API:

```bash
curl -X POST http://localhost:8002/api/words/add \
  -H "Content-Type: application/json" \
  -d '{
    "dutch_word": "bibliotheek",
    "use_claude": true
  }'
```

## 📊 Monitoring

### AI Usage Statistics

Check welke modellen worden gebruikt:

```bash
curl http://localhost:8002/api/stats/ai | jq '.'
```

Voorbeeld output:
```json
{
  "qwen_calls": 150,
  "mistral_calls": 30,
  "claude_calls": 20,
  "qwen_fallbacks": 2,
  "mistral_fallbacks": 1,
  "total_calls": 200,
  "claude_percentage": 10.0,
  "cost_savings": {
    "actual_cost_usd": 0.09,
    "all_claude_cost_usd": 0.90,
    "savings_usd": 0.81,
    "savings_percentage": 90.0
  },
  "ollama_health": {
    "total_errors": 3,
    "qwen_fallback_rate": 1.3,
    "mistral_fallback_rate": 3.3
  }
}
```

### Ollama Server Status

```bash
# Check welke modellen actief zijn
ollama ps

# List alle geïnstalleerde modellen
ollama list

# Stop alle modellen (memory vrijmaken)
ollama stop -a
```

## 🔧 Troubleshooting

### "Ollama is niet actief"

```bash
# Start Ollama server handmatig
ollama serve

# In andere terminal, test:
curl http://localhost:11434/api/tags
```

### "Model not found"

```bash
# Download ontbrekend model
ollama pull qwen2.5:14b
ollama pull mistral:7b-instruct
```

### Backend errors "Failed to connect to Ollama"

1. Check of Ollama actief is: `ollama ps`
2. Restart Ollama server: `ollama serve`
3. Check firewall settings (Ollama gebruikt port 11434)

### Trage responses

Dit is normaal tijdens eerste gebruik:
- **Eerste call**: Model wordt geladen in memory (~5-10 sec)
- **Volgende calls**: Instant responses (1-3 sec)

Tip: Houd modellen geladen met `export OLLAMA_KEEP_ALIVE="1h"`

### Memory problemen

Je M3 Pro heeft 36GB, wat ruim voldoende is. Maar als je problemen ervaart:

```bash
# Check memory usage
ollama ps

# Stop ongebruikte modellen
ollama stop qwen2.5:14b

# Of stop alles
ollama stop -a
```

## 📈 Performance Expectations

Op jouw M3 Pro:

| Model | Response Tijd | Tokens/sec | Memory |
|-------|---------------|------------|--------|
| Qwen 14B | 2-3 sec | 15-20 | ~10GB |
| Mistral 7B | <1 sec | 40-60 | ~5GB |
| Claude API | 3-5 sec | variabel | 0GB |

**Beide modellen tegelijk**: ~15GB gebruikt, 21GB vrij

## 🎯 Wat verandert er voor jou?

### ✅ Niets! (alles werkt automatisch)

De frontend blijft exact hetzelfde. Het hybride systeem werkt transparant:

1. Type Nederlands woord in frontend
2. Backend kiest automatisch beste model
3. Bij errors: automatische fallback naar Claude
4. Resultaat komt terug zoals altijd

### 📊 Nieuwe mogelijkheden

Je kunt nu monitoren:
- Hoeveel queries lokaal vs cloud
- Kostenbesparing in real-time
- Model performance en fallback rates

### 🔄 Fallback gedrag

Het systeem heeft **3 fallback levels**:

1. **Qwen fails** → Try Claude
2. **Mistral fails** → Try Claude
3. **Ollama server down** → All Claude

Je merkt niets van errors, alleen dat responses soms iets langer duren (fallback naar Claude).

## 💰 Cost Savings Voorbeeld

Voor 1000 nieuwe woorden:

**Voorheen (100% Claude)**:
- 1000 woorden × 2 calls (translate + mnemonic)
- 2000 API calls × $0.004 = **$8.00/maand**

**Nu (Hybrid)**:
- 700 Qwen calls (translate): **$0.00**
- 150 Mistral calls (mnemonic): **$0.00**
- 150 Claude calls (validation): $0.60
- **TOTAAL: $0.60/maand (92.5% besparing)**

## 🚀 Volgende Stappen

1. ✅ **Test het systeem**: Run `./test_ollama.sh`
2. ✅ **Start de app**: Normal workflow (backend + frontend)
3. ✅ **Voeg woorden toe**: Alles werkt automatisch
4. ✅ **Check stats**: `curl http://localhost:8002/api/stats/ai`

## 📚 Meer Info

- **Ollama Docs**: https://ollama.ai/docs
- **Qwen 2.5**: https://qwenlm.github.io/blog/qwen2.5/
- **Mistral**: https://mistral.ai/news/mixtral-of-experts/

Implementatieplan: `/home/claude/hybrid-ai-implementation-plan.md`

---

**Questions?** Check de logs:
```bash
# Backend logs (terminal waar uvicorn draait)
# Je ziet welke modellen worden gebruikt per request

# Ollama logs
journalctl -u ollama -f  # (op systemen met systemd)
```
