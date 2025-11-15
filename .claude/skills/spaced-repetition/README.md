# Spaced Repetition Skill

Een complete skill voor het implementeren van **Spaced Repetition** in je Spaans leren app.

## 🎯 Wat doet deze skill?

Deze skill helpt Claude Code om perfect spaced repetition te implementeren in je app met:
- ✅ SuperMemo SM-2 algoritme (wetenschappelijk bewezen)
- ✅ Database schema voor tracking
- ✅ FastAPI endpoints
- ✅ React frontend voorbeelden
- ✅ Kant-en-klare Python code

## 📁 Inhoud

```
spaced-repetition/
├── SKILL.md                    # Hoofddocumentatie (Claude leest dit)
├── README.md                   # Dit bestand (voor jou)
├── scripts/
│   └── sm2_algorithm.py        # Kant-en-klare Python implementatie
└── references/
    └── examples.md             # Voorbeelden en extra documentatie
```

## 🚀 Hoe te gebruiken

### 1. Herstart Claude Code

Sluit Claude Code af en start opnieuw op. De skill wordt automatisch geladen.

### 2. Vraag Claude om spaced repetition

Voorbeelden van wat je kunt vragen:

```
"Implementeer spaced repetition in mijn Spaans app"

"Voeg database kolommen toe voor spaced repetition"

"Maak een FastAPI endpoint voor due words"

"Hoe maak ik review buttons in React?"

"Test het SuperMemo algoritme"
```

### 3. Claude laadt automatisch de skill

Claude ziet dat je vraag over spaced repetition gaat en laadt deze skill.
Je hoeft de skill **niet** handmatig te noemen!

## 🧪 Test de skill

Test of de skill werkt:

```bash
cd /Users/jaccostokx/projects/spaans-leren-app/.claude/skills/spaced-repetition/scripts
python3 sm2_algorithm.py
```

Je zou moeten zien:
```
🧪 Testing SuperMemo SM-2 Algorithm

Test 1: Perfect score (5) op nieuw woord
  ✅ Next interval: 1 days (verwacht: 1)
  ✅ New easiness: 2.6 (verwacht: > 2.5)

...

✅ Alle tests geslaagd!
```

## 📚 Wat is SuperMemo SM-2?

Het is een bewezen algoritme dat bepaalt WANNEER je een woord opnieuw moet oefenen:

- Goed onthouden? → Langere tijd tot volgende review (exponentieel)
- Slecht onthouden? → Korte tijd tot volgende review (reset)

**Resultaat:** 90%+ retention rate (vs 50-60% bij random review)

## 🔧 Quick Start Implementatie

### Stap 1: Database Update

```python
# In database.py - voeg toe aan Word class:
easiness_factor = Column(Float, default=2.5)
repetition_count = Column(Integer, default=0)
interval_days = Column(Integer, default=0)
next_review_date = Column(DateTime, default=datetime.utcnow)
last_review_date = Column(DateTime, nullable=True)
total_reviews = Column(Integer, default=0)
successful_reviews = Column(Integer, default=0)
```

### Stap 2: Import Algoritme

```python
# In main.py - bovenaan:
from scripts.sm2_algorithm import calculate_next_review
```

### Stap 3: Maak Endpoint

```python
@app.post("/api/words/{word_id}/review")
async def submit_review(word_id: int, quality_score: int):
    word = db.query(Word).filter(Word.id == word_id).first()
    
    # Bereken nieuwe interval
    next_interval, new_easiness = calculate_next_review(
        word.easiness_factor,
        word.interval_days,
        quality_score
    )
    
    # Update word
    word.easiness_factor = new_easiness
    word.interval_days = next_interval
    word.next_review_date = datetime.utcnow() + timedelta(days=next_interval)
    
    db.commit()
    return {"next_review_in_days": next_interval}
```

### Stap 4: Frontend Buttons

```javascript
<button onClick={() => submitReview(5)}>😃 Perfect!</button>
<button onClick={() => submitReview(4)}>🙂 Goed</button>
<button onClick={() => submitReview(3)}>😐 Met moeite</button>
<button onClick={() => submitReview(0)}>😞 Vergeten</button>
```

## ❓ Veelgestelde Vragen

**Q: Moet ik de skill handmatig activeren?**
A: Nee! Claude laadt hem automatisch als je vraagt over spaced repetition.

**Q: Kan ik het algoritme aanpassen?**
A: Ja! Edit `scripts/sm2_algorithm.py` en pas de formule aan.

**Q: Werkt dit ook buiten Claude Code?**
A: Ja! De Python code werkt gewoon in je app. De skill is alleen om Claude te helpen.

**Q: Moet ik de database opnieuw maken?**
A: Ja, je moet kolommen toevoegen. Maak eerst een backup!

## 🎓 Meer Informatie

- Check `SKILL.md` voor volledige documentatie
- Check `references/examples.md` voor real-world voorbeelden
- Check `scripts/sm2_algorithm.py` voor code commentaar

## 📞 Support

Bij vragen: vraag Claude in Claude Code!

```
"Leg uit hoe spaced repetition werkt"
"Hoe test ik het algoritme?"
"Maak een dashboard voor review statistieken"
```

---

**Versie:** 1.0.0  
**Gemaakt:** 2025-11-06  
**Voor:** Spaans Leren App (Jacco Stokx)
