---
name: spaced-repetition-algorithm
description: Implement spaced repetition learning algorithms (SuperMemo SM-2, Anki-style) for effective vocabulary memorization. Use when implementing flashcard review systems, scheduling algorithms, retention tracking, or when user asks to add spaced repetition to language learning apps.
---

# Spaced Repetition Algorithm Skill

## Overzicht

Deze skill helpt bij het implementeren van **Spaced Repetition** algoritmes voor effectief taal leren. Het gebruikt het bewezen **SuperMemo SM-2** algoritme dat zorgt voor optimale memorisatie door woorden op het juiste moment te herhalen.

**Wanneer deze skill gebruiken:**
- User vraagt om spaced repetition toe te voegen
- Flashcard review systemen implementeren
- Scheduling algoritmes voor herhaling
- Retention tracking en statistieken
- Optimale review timing berekenen

## Het SuperMemo SM-2 Algoritme

### Basis Principe

Het algoritme past de review interval aan op basis van hoe makkelijk je een woord onthoudt:
- **Goed onthouden** → langere interval (exponentiële groei)
- **Slecht onthouden** → reset naar korte interval

### Formule

```python
def calculate_next_review(easiness_factor, current_interval, quality_score):
    """
    SuperMemo SM-2 algoritme
    
    Parameters:
    - easiness_factor: float (1.3 - 2.5) - hoe makkelijk is dit woord
    - current_interval: int - huidige interval in dagen
    - quality_score: int (0-5) - hoe goed werd het onthouden
        5: Perfect
        4: Correct na aarzeling
        3: Correct met moeite
        2: Incorrect maar herinnerd
        1: Incorrect maar bekend
        0: Complete black-out
    
    Returns:
    - next_interval: int - dagen tot volgende review
    - new_easiness: float - nieuwe easiness factor
    """
    
    if quality_score >= 3:
        # Goed onthouden - verhoog interval
        if current_interval == 0:
            next_interval = 1
        elif current_interval == 1:
            next_interval = 6
        else:
            next_interval = round(current_interval * easiness_factor)
        
        # Pas easiness factor aan
        new_easiness = easiness_factor + (0.1 - (5 - quality_score) * (0.08 + (5 - quality_score) * 0.02))
        new_easiness = max(1.3, new_easiness)
    else:
        # Slecht onthouden - reset interval
        next_interval = 1
        new_easiness = easiness_factor
    
    return next_interval, new_easiness
```

## Database Schema voor Spaans Leren App

### Nieuwe Kolommen voor `words` tabel

Voeg deze kolommen toe aan je bestaande SQLAlchemy model:

```python
# In database.py - voeg toe aan Word class:

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime, timedelta

class Word(Base):
    __tablename__ = "words"
    
    # Bestaande kolommen...
    id = Column(Integer, primary_key=True, index=True)
    dutch_word = Column(Text, nullable=False)
    spanish_word = Column(Text, nullable=False)
    category = Column(Text)
    mnemonic_text = Column(Text)
    mnemonic_image = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # NIEUWE KOLOMMEN VOOR SPACED REPETITION:
    easiness_factor = Column(Float, default=2.5)  # Start waarde 2.5
    repetition_count = Column(Integer, default=0)  # Aantal keer geoefend
    interval_days = Column(Integer, default=0)  # Huidige interval
    next_review_date = Column(DateTime, default=datetime.utcnow)  # Wanneer opnieuw oefenen
    last_review_date = Column(DateTime, nullable=True)  # Laatst geoefend
    total_reviews = Column(Integer, default=0)  # Totaal aantal reviews
    successful_reviews = Column(Integer, default=0)  # Aantal correcte reviews
```

### Database Migratie

Aangezien je geen Alembic gebruikt, moet je de database opnieuw aanmaken:

```bash
# Backup oude database
cp backend/spaans_leren.db backend/spaans_leren.db.backup_$(date +%Y%m%d)

# Verwijder oude database
rm backend/spaans_leren.db

# Maak nieuwe database aan met updated schema
cd backend
python3 -c "from database import engine, Base; Base.metadata.create_all(engine)"
```

Of gebruik een SQL script om kolommen toe te voegen:

```sql
ALTER TABLE words ADD COLUMN easiness_factor REAL DEFAULT 2.5;
ALTER TABLE words ADD COLUMN repetition_count INTEGER DEFAULT 0;
ALTER TABLE words ADD COLUMN interval_days INTEGER DEFAULT 0;
ALTER TABLE words ADD COLUMN next_review_date DATETIME DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE words ADD COLUMN last_review_date DATETIME;
ALTER TABLE words ADD COLUMN total_reviews INTEGER DEFAULT 0;
ALTER TABLE words ADD COLUMN successful_reviews INTEGER DEFAULT 0;
```

## FastAPI Endpoints

### 1. Get Words Due for Review

```python
@app.get("/api/words/due")
async def get_due_words(db: Session = Depends(get_db)):
    """
    Haal alle woorden op die vandaag geoefend moeten worden.
    """
    now = datetime.utcnow()
    
    words = db.query(Word).filter(
        Word.next_review_date <= now
    ).order_by(Word.next_review_date).all()
    
    return {
        "count": len(words),
        "words": words
    }
```

### 2. Submit Review Result

```python
from pydantic import BaseModel
from datetime import datetime, timedelta

class ReviewResult(BaseModel):
    quality_score: int  # 0-5

@app.post("/api/words/{word_id}/review")
async def submit_review(
    word_id: int,
    result: ReviewResult,
    db: Session = Depends(get_db)
):
    """
    Verwerk review resultaat en bereken volgende review datum.
    """
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Bereken nieuwe interval en easiness
    next_interval, new_easiness = calculate_next_review(
        easiness_factor=word.easiness_factor,
        current_interval=word.interval_days,
        quality_score=result.quality_score
    )
    
    # Update word
    word.easiness_factor = new_easiness
    word.interval_days = next_interval
    word.last_review_date = datetime.utcnow()
    word.next_review_date = datetime.utcnow() + timedelta(days=next_interval)
    word.repetition_count += 1
    word.total_reviews += 1
    
    if result.quality_score >= 3:
        word.successful_reviews += 1
    
    db.commit()
    db.refresh(word)
    
    return {
        "message": "Review recorded",
        "next_review_in_days": next_interval,
        "next_review_date": word.next_review_date.isoformat(),
        "success_rate": round(word.successful_reviews / word.total_reviews * 100, 1) if word.total_reviews > 0 else 0
    }
```

### 3. Get Review Statistics

```python
@app.get("/api/stats/reviews")
async def get_review_stats(db: Session = Depends(get_db)):
    """
    Haal review statistieken op.
    """
    total_words = db.query(Word).count()
    words_due_today = db.query(Word).filter(
        Word.next_review_date <= datetime.utcnow()
    ).count()
    
    # Bereken gemiddelde success rate
    words_with_reviews = db.query(Word).filter(Word.total_reviews > 0).all()
    
    if words_with_reviews:
        avg_success_rate = sum(
            w.successful_reviews / w.total_reviews 
            for w in words_with_reviews
        ) / len(words_with_reviews) * 100
    else:
        avg_success_rate = 0
    
    return {
        "total_words": total_words,
        "due_today": words_due_today,
        "average_success_rate": round(avg_success_rate, 1),
        "total_reviews_completed": sum(w.total_reviews for w in words_with_reviews)
    }
```

## Frontend Integration (React)

### Oefenen Component met Review Knoppen

```javascript
function PracticeWithReview() {
    const [currentWord, setCurrentWord] = useState(null);
    const [showAnswer, setShowAnswer] = useState(false);
    const [stats, setStats] = useState(null);

    // Haal een woord op dat geoefend moet worden
    async function loadDueWord() {
        const response = await fetch('http://localhost:8002/api/words/due');
        const data = await response.json();
        
        if (data.words.length > 0) {
            setCurrentWord(data.words[0]);
            setShowAnswer(false);
        } else {
            alert('Geen woorden om te oefenen! 🎉');
        }
    }

    // Submit review met quality score
    async function submitReview(qualityScore) {
        await fetch(`http://localhost:8002/api/words/${currentWord.id}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quality_score: qualityScore })
        });
        
        // Laad volgend woord
        loadDueWord();
    }

    useEffect(() => {
        loadDueWord();
    }, []);

    if (!currentWord) return <div>Laden...</div>;

    return (
        <div className="practice-container">
            <h2>Oefen Woord</h2>
            
            {/* Toon Nederlands woord */}
            <div className="question">
                <h1>{currentWord.dutch_word}</h1>
                <p>Wat is dit in het Spaans?</p>
            </div>

            {/* Toon Antwoord knop */}
            {!showAnswer && (
                <button onClick={() => setShowAnswer(true)}>
                    Toon Antwoord
                </button>
            )}

            {/* Toon antwoord en review knoppen */}
            {showAnswer && (
                <div className="answer">
                    <h2>{currentWord.spanish_word}</h2>
                    <img src={currentWord.mnemonic_image} alt="Mnemonic" />
                    <p>{currentWord.mnemonic_text}</p>

                    <div className="review-buttons">
                        <h3>Hoe goed wist je het?</h3>
                        <button onClick={() => submitReview(5)} className="btn-perfect">
                            😃 Perfect! (5)
                        </button>
                        <button onClick={() => submitReview(4)} className="btn-good">
                            🙂 Goed (4)
                        </button>
                        <button onClick={() => submitReview(3)} className="btn-ok">
                            😐 Met moeite (3)
                        </button>
                        <button onClick={() => submitReview(2)} className="btn-hard">
                            😕 Fout maar bekend (2)
                        </button>
                        <button onClick={() => submitReview(0)} className="btn-forgot">
                            😞 Vergeten (0)
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
```

### Dashboard met Review Statistieken

```javascript
function ReviewDashboard() {
    const [stats, setStats] = useState(null);

    useEffect(() => {
        async function loadStats() {
            const response = await fetch('http://localhost:8002/api/stats/reviews');
            const data = await response.json();
            setStats(data);
        }
        loadStats();
    }, []);

    if (!stats) return <div>Laden...</div>;

    return (
        <div className="dashboard">
            <h2>Review Statistieken</h2>
            
            <div className="stat-card">
                <h3>{stats.due_today}</h3>
                <p>Woorden te oefenen vandaag</p>
            </div>

            <div className="stat-card">
                <h3>{stats.total_words}</h3>
                <p>Totaal woorden</p>
            </div>

            <div className="stat-card">
                <h3>{stats.average_success_rate}%</h3>
                <p>Gemiddeld succes percentage</p>
            </div>

            <div className="stat-card">
                <h3>{stats.total_reviews_completed}</h3>
                <p>Totaal reviews voltooid</p>
            </div>
        </div>
    );
}
```

## Best Practices

### 1. Initiële Review Direct Beschikbaar

Nieuwe woorden moeten direct geoefend kunnen worden:

```python
# Bij het aanmaken van een nieuw woord:
new_word.next_review_date = datetime.utcnow()  # Direct beschikbaar
new_word.easiness_factor = 2.5  # Standaard start waarde
new_word.interval_days = 0  # Nog niet geoefend
```

### 2. Review Queue Optimalisatie

Sorteer woorden op prioriteit:

```python
# Eerst woorden die lang geleden geoefend hadden moeten worden
words = db.query(Word).filter(
    Word.next_review_date <= datetime.utcnow()
).order_by(Word.next_review_date.asc()).limit(20).all()
```

### 3. Success Rate Tracking

Houd bij welke woorden moeilijk zijn:

```python
# Identificeer moeilijke woorden (success rate < 60%)
difficult_words = db.query(Word).filter(
    Word.total_reviews >= 5,
    Word.successful_reviews / Word.total_reviews < 0.6
).all()
```

### 4. Review Streaks

Motiveer gebruikers met streaks:

```python
# Check of gebruiker dagelijks oefent
def check_streak(user_id):
    # Implementeer streak tracking
    # Return aantal opeenvolgende dagen
    pass
```

## Testing

### Test het algoritme

```python
# Test SuperMemo SM-2 berekening
def test_spaced_repetition():
    # Test case 1: Perfect score
    interval, easiness = calculate_next_review(
        easiness_factor=2.5,
        current_interval=1,
        quality_score=5
    )
    assert interval == 6  # Eerste interval is altijd 6
    assert easiness > 2.5  # Easiness stijgt bij perfect score
    
    # Test case 2: Slecht score
    interval, easiness = calculate_next_review(
        easiness_factor=2.5,
        current_interval=10,
        quality_score=1
    )
    assert interval == 1  # Reset naar 1 dag
    assert easiness == 2.5  # Easiness blijft gelijk

    print("✅ Alle tests geslaagd!")

test_spaced_repetition()
```

## Veelgestelde Vragen

**Q: Wat als ik meerdere woorden op één dag wil oefenen?**
A: Het algoritme staat dit toe. Je kunt zelf kiezen hoeveel woorden je per dag wilt oefenen door het aantal te limiteren in de query.

**Q: Kan ik het algoritme aanpassen?**
A: Ja! De formule in `calculate_next_review()` kun je tweaken. Bijvoorbeeld:
- Langzamere groei: vermenigvuldig interval met een lager getal
- Snellere groei: verhoog de easiness factor sneller

**Q: Hoe reset ik de voortgang van een woord?**
A: Zet alle velden terug naar default:
```python
word.easiness_factor = 2.5
word.interval_days = 0
word.repetition_count = 0
word.next_review_date = datetime.utcnow()
```

## Wetenschappelijke Basis

Het SuperMemo SM-2 algoritme is ontwikkeld door Piotr Woźniak in 1987 en is bewezen effectief voor long-term memorisatie. Het is de basis voor populaire apps zoals Anki, Quizlet, en Duolingo.

**Key Research:**
- Woźniak, P. (1990). "SuperMemo SM-2 algorithm"
- Ebbinghaus Forgetting Curve (1885)
- Leitner System (1972)

**Effectiviteit:**
- 90%+ retention rate bij correct gebruik
- 10x efficiënter dan random review
- Optimaal voor long-term memorisatie

## Implementatie Checklist

Gebruik deze checklist bij implementatie:

- [ ] Database schema uitgebreid met nieuwe kolommen
- [ ] `calculate_next_review()` functie toegevoegd
- [ ] `/api/words/due` endpoint gemaakt
- [ ] `/api/words/{id}/review` endpoint gemaakt
- [ ] Frontend oefencomponent met quality buttons
- [ ] Statistics dashboard
- [ ] Nieuwe woorden krijgen default waarden
- [ ] Getest met test cases
- [ ] Success rate tracking werkend
- [ ] Review queue sorteerd op prioriteit

---

**Versie:** 1.0.0  
**Laatst bijgewerkt:** 2025-11-06  
**Voor vragen:** Check deze SKILL.md eerst, dan CLAUDE.md in project root
