# Spaced Repetition - Voorbeelden & Referenties

## Real-World Voorbeelden

### Voorbeeld 1: Nederlands woord "huis" leren

**Dag 1 - Eerste keer zien:**
- Nederlands: "huis"
- Spaans: "la casa"  
- User ziet het woord voor het eerst
- Status: `interval_days=0`, `easiness_factor=2.5`, `next_review_date=now`

**Dag 1 - Eerste review:**
- User oefent: "huis" → moet "la casa" zeggen
- User klikt: **"Perfect! (5)"**
- Algoritme berekent: `interval=1 dag`, `easiness=2.6`
- Status: Morgen weer oefenen

**Dag 2 - Tweede review:**
- User oefent weer
- User klikt: **"Goed (4)"**
- Algoritme berekent: `interval=6 dagen`, `easiness=2.6`
- Status: Over 6 dagen weer oefenen

**Dag 8 - Derde review:**
- User oefent weer
- User klikt: **"Perfect! (5)"**
- Algoritme berekent: `interval=16 dagen` (6 * 2.6), `easiness=2.7`
- Status: Over 16 dagen weer oefenen

**Dag 24 - Vierde review:**
- User oefent weer
- User klikt: **"Met moeite (3)"**
- Algoritme berekent: `interval=43 dagen` (16 * 2.7), `easiness=2.6`
- Status: Over 43 dagen weer oefenen

**Dag 67 - User heeft het vergeten:**
- User oefent
- User klikt: **"Vergeten (0)"**
- Algoritme berekent: `interval=1 dag` (RESET!), `easiness=2.6`
- Status: Morgen weer vanaf begin

---

## Vergelijking met Andere Methoden

### Random Review (Zonder Spaced Repetition)

```
Woord A: dag 1, 3, 7, 9, 12, 15, 18, 20...
Woord B: dag 2, 5, 8, 11, 13, 16, 19...
Woord C: dag 1, 4, 6, 10, 14, 17...
```

❌ **Problemen:**
- Veel tijd verspild aan woorden die je al kent
- Te weinig aandacht aan moeilijke woorden
- Geen optimale timing
- Retention rate: ~50-60%

### Spaced Repetition (SuperMemo SM-2)

```
Moeilijk woord: dag 1, 2, 3, 4, 5, 7, 10, 15...
Makkelijk woord: dag 1, 2, 8, 24, 67, 180...
Gemiddeld woord: dag 1, 2, 8, 20, 50, 125...
```

✅ **Voordelen:**
- Focus op moeilijke woorden
- Makkelijke woorden komen zelden terug
- Optimale timing net voor je het vergeet
- Retention rate: ~90%+

---

## Complete SQL Queries

### 1. Woorden die VANDAAG geoefend moeten worden

```sql
SELECT * FROM words 
WHERE next_review_date <= datetime('now')
ORDER BY next_review_date ASC
LIMIT 20;
```

### 2. Moeilijke woorden identificeren

```sql
SELECT 
    dutch_word,
    spanish_word,
    total_reviews,
    successful_reviews,
    (successful_reviews * 100.0 / total_reviews) as success_rate
FROM words 
WHERE total_reviews >= 5
  AND (successful_reviews * 100.0 / total_reviews) < 60
ORDER BY success_rate ASC;
```

### 3. Woorden die al lang niet meer geoefend zijn

```sql
SELECT 
    dutch_word,
    spanish_word,
    last_review_date,
    julianday('now') - julianday(last_review_date) as days_since_review
FROM words 
WHERE last_review_date IS NOT NULL
ORDER BY days_since_review DESC
LIMIT 10;
```

### 4. Review statistieken per categorie

```sql
SELECT 
    category,
    COUNT(*) as total_words,
    AVG(successful_reviews * 100.0 / total_reviews) as avg_success_rate,
    SUM(total_reviews) as total_reviews_done
FROM words 
WHERE total_reviews > 0
GROUP BY category
ORDER BY avg_success_rate DESC;
```

---

## API Request/Response Voorbeelden

### POST /api/words/{id}/review

**Request:**
```json
{
  "quality_score": 4
}
```

**Response:**
```json
{
  "message": "Review recorded",
  "next_review_in_days": 16,
  "next_review_date": "2025-11-22T10:30:00",
  "success_rate": 85.7,
  "word": {
    "id": 42,
    "dutch_word": "huis",
    "spanish_word": "la casa",
    "easiness_factor": 2.6,
    "interval_days": 16,
    "repetition_count": 7,
    "total_reviews": 7,
    "successful_reviews": 6
  }
}
```

### GET /api/words/due

**Response:**
```json
{
  "count": 5,
  "words": [
    {
      "id": 1,
      "dutch_word": "kat",
      "spanish_word": "el gato",
      "next_review_date": "2025-11-05T08:00:00",
      "easiness_factor": 2.5,
      "interval_days": 1
    },
    {
      "id": 2,
      "dutch_word": "hond",
      "spanish_word": "el perro",
      "next_review_date": "2025-11-06T10:00:00",
      "easiness_factor": 2.3,
      "interval_days": 6
    }
  ]
}
```

---

## Quality Score Guidelines

Help gebruikers de juiste score te kiezen:

| Score | Label | Wanneer gebruiken | Effect |
|-------|-------|-------------------|--------|
| 5 | 😃 Perfect! | Direct geweten, geen aarzeling | Interval × 2.7, easiness +0.1 |
| 4 | 🙂 Goed | Kort nadenken, maar correct | Interval × 2.6, easiness +0.0 |
| 3 | 😐 Met moeite | Veel nadenken of bijna fout | Interval × 2.5, easiness -0.14 |
| 2 | 😕 Fout maar bekend | Fout antwoord maar je kent het woord | Reset interval, easiness blijft |
| 1 | 😟 Fout | Helemaal fout antwoord | Reset interval, easiness blijft |
| 0 | 😞 Vergeten | Complete black-out, geen idee | Reset interval, easiness blijft |

**Best Practice:**
- Wees eerlijk! Het algoritme werkt alleen als je eerlijk bent
- Twijfel tussen 4 en 5? Kies 4 (beter safe than sorry)
- Score < 3 betekent altijd reset naar 1 dag

---

## Wetenschappelijke Achtergrond

### Ebbinghaus Forgetting Curve (1885)

Hermann Ebbinghaus ontdekte dat mensen:
- Na 20 minuten: 58% vergeten
- Na 1 uur: 44% onthouden
- Na 1 dag: 33% onthouden
- Na 1 week: 25% onthouden
- Na 1 maand: 21% onthouden

**Conclusie:** Zonder herhaling vergeten we bijna alles!

### Leitner System (1972)

Sebastian Leitner bedacht een systeem met dozen:
- Doos 1: Review elke dag
- Doos 2: Review elke 3 dagen
- Doos 3: Review elke week
- Doos 4: Review elke maand
- Doos 5: Review elke 3 maanden

Goed → verplaats naar hogere doos
Fout → terug naar doos 1

**Probleem:** Vaste intervallen, niet adaptief per woord

### SuperMemo SM-2 (1987)

Piotr Woźniak verbeterde het Leitner systeem:
- Adaptieve intervallen per woord
- Easiness factor houdt rekening met moeilijkheid
- Exponentiële groei (niet lineair)
- Bewezen effectief met 90%+ retention

**Gebruikt door:**
- Anki (meest populaire flashcard app)
- Memrise
- Quizlet (gedeeltelijk)
- Duolingo (variant)

---

## Performance Optimalisatie Tips

### 1. Index voor snellere queries

```sql
CREATE INDEX idx_next_review_date ON words(next_review_date);
CREATE INDEX idx_success_rate ON words(successful_reviews, total_reviews);
```

### 2. Cache statistieken

In plaats van elke keer berekenen, cache statistieken:

```python
# Bereken 1x per dag
daily_stats = {
    "due_count": count_due_words(),
    "avg_success_rate": calculate_avg_success(),
    "cached_at": datetime.utcnow()
}
```

### 3. Batch updates

Bij veel woorden, gebruik batch updates:

```python
# In plaats van 100x UPDATE query:
for word in words:
    word.next_review_date = calculate_date(word)
    
db.bulk_update_mappings(Word, [
    {"id": w.id, "next_review_date": w.next_review_date}
    for w in words
])
```

---

## Troubleshooting

### Probleem: Te veel woorden per dag

**Symptoom:** 50+ woorden due op 1 dag

**Oorzaak:** Alle woorden tegelijk toegevoegd

**Oplossing:**
```python
# Spread nieuwe woorden over meerdere dagen
for i, word in enumerate(new_words):
    word.next_review_date = datetime.utcnow() + timedelta(hours=i)
```

### Probleem: Easiness factor te laag

**Symptoom:** easiness_factor < 1.5 voor veel woorden

**Oorzaak:** Te streng beoordeeld (alleen 0-2 scores)

**Oplossing:** Educatie gebruiker over quality scores

### Probleem: Interval te lang

**Symptoom:** Woorden komen pas na 6 maanden terug

**Oorzaak:** Te veel perfecte scores (5)

**Oplossing:**
```python
# Cap maximum interval op 90 dagen
next_interval = min(next_interval, 90)
```

---

## Toekomstige Uitbreidingen

### 1. Difficulty Levels

Woorden opdelen in moeilijkheidsgraden:

```python
def get_difficulty_level(easiness_factor, success_rate):
    if success_rate > 80 and easiness_factor > 2.3:
        return "Makkelijk"
    elif success_rate > 60:
        return "Gemiddeld"
    else:
        return "Moeilijk"
```

### 2. Learning Streaks

Motiveer met streaks:

```python
def calculate_streak(user_reviews):
    streak = 0
    for i in range(len(user_reviews) - 1, -1, -1):
        if user_reviews[i].date == today - timedelta(days=streak):
            streak += 1
        else:
            break
    return streak
```

### 3. Predictive Analytics

Voorspel welke woorden moeilijk worden:

```python
def predict_difficulty(word):
    # Features: lengte, aantal syllables, categorie, etc.
    # Machine learning model
    pass
```

---

**Bronnen:**

1. Woźniak, P. (1990). "SuperMemo SM-2 Algorithm"
2. Ebbinghaus, H. (1885). "Memory: A Contribution to Experimental Psychology"
3. Leitner, S. (1972). "So lernt man lernen"
4. Anki Manual: https://docs.ankiweb.net/
5. Gwern Branwen - Spaced Repetition: https://gwern.net/spaced-repetition
