# Complete Implementation Examples

## Full Implementation Flow - Step by Step

### Phase 1: Database Migration

**Step 1.1: Create migration script**

Create `backend/migrate_add_srs.py`:

```python
"""
Migration: Add Spaced Repetition columns to words table
Run once: python3 migrate_add_srs.py
"""

import sqlite3
from datetime import datetime

def migrate():
    conn = sqlite3.connect('spaans_leren.db')
    cursor = conn.cursor()
    
    # Check if migration already done
    cursor.execute("PRAGMA table_info(words)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'next_review_date' in columns:
        print("⚠️  Migration already applied!")
        conn.close()
        return
    
    print("🔄 Starting migration...")
    
    # Add new columns
    migrations = [
        "ALTER TABLE words ADD COLUMN next_review_date DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE words ADD COLUMN repetition_count INTEGER DEFAULT 0",
        "ALTER TABLE words ADD COLUMN easiness_factor REAL DEFAULT 2.5",
        "ALTER TABLE words ADD COLUMN last_review_date DATETIME",
        "ALTER TABLE words ADD COLUMN total_reviews INTEGER DEFAULT 0",
        "ALTER TABLE words ADD COLUMN successful_reviews INTEGER DEFAULT 0",
        "ALTER TABLE words ADD COLUMN success_rate REAL DEFAULT 0.0",
    ]
    
    for migration in migrations:
        try:
            cursor.execute(migration)
            print(f"  ✅ {migration.split('ADD COLUMN')[1].split()[0]}")
        except sqlite3.OperationalError as e:
            print(f"  ❌ Error: {e}")
    
    # Create index for performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_next_review ON words(next_review_date)"
    )
    print("  ✅ Created index on next_review_date")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration complete!")
    print("\nVerify with: sqlite3 spaans_leren.db '.schema words'")

if __name__ == "__main__":
    migrate()
```

**Step 1.2: Run migration**

```bash
cd backend
python3 migrate_add_srs.py
```

**Step 1.3: Verify**

```bash
sqlite3 spaans_leren.db ".schema words"
```

Expected output should include:
```sql
next_review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
repetition_count INTEGER DEFAULT 0,
easiness_factor REAL DEFAULT 2.5,
...
```

---

### Phase 2: Backend Implementation

**Step 2.1: Copy SM-2 algorithm**

```bash
cp .claude/skills/spaced-repetition/scripts/sm2_algorithm.py backend/
```

**Step 2.2: Update database.py**

Add columns to the Word model:

```python
# backend/database.py

from datetime import datetime

class Word(Base):
    __tablename__ = "words"
    
    # Existing columns
    id = Column(Integer, primary_key=True, index=True)
    dutch_word = Column(Text, nullable=False)
    spanish_word = Column(Text, nullable=False)
    category = Column(Text)
    mnemonic_text = Column(Text)
    mnemonic_image = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # NEW: Spaced Repetition columns
    next_review_date = Column(DateTime, default=datetime.utcnow)
    repetition_count = Column(Integer, default=0)
    easiness_factor = Column(Float, default=2.5)
    last_review_date = Column(DateTime, nullable=True)
    total_reviews = Column(Integer, default=0)
    successful_reviews = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
```

**Step 2.3: Add endpoints to main.py**

```python
# backend/main.py

from datetime import datetime, timedelta
from sm2_algorithm import calculate_next_review, get_review_quality_from_simple_response

# NEW ENDPOINT 1: Get words due for review
@app.get("/api/words/due")
async def get_due_words(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get words that are due for review.
    
    Query params:
        limit: Maximum number of words to return (default: 20)
    """
    now = datetime.utcnow()
    
    due_words = db.query(Word).filter(
        Word.next_review_date <= now
    ).order_by(
        Word.next_review_date.asc()  # Oldest due first
    ).limit(limit).all()
    
    return {
        "count": len(due_words),
        "words": [
            {
                "id": word.id,
                "dutch_word": word.dutch_word,
                "spanish_word": word.spanish_word,
                "category": word.category,
                "mnemonic_text": word.mnemonic_text,
                "mnemonic_image": word.mnemonic_image,
                "repetition_count": word.repetition_count,
                "success_rate": word.success_rate
            }
            for word in due_words
        ]
    }


# NEW ENDPOINT 2: Submit review result
class ReviewResult(BaseModel):
    success: bool

@app.post("/api/words/{word_id}/review")
async def submit_review(
    word_id: int,
    result: ReviewResult,
    db: Session = Depends(get_db)
):
    """Submit review result and update scheduling"""
    
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Convert simple success/fail to quality score
    quality = get_review_quality_from_simple_response(result.success)
    
    # Calculate current interval for algorithm
    if word.last_review_date:
        previous_interval = (datetime.utcnow() - word.last_review_date).days
    else:
        previous_interval = 0
    
    # Calculate next review using SM-2
    updated_data = calculate_next_review(
        repetition_count=word.repetition_count,
        easiness_factor=word.easiness_factor,
        quality=quality,
        previous_interval_days=previous_interval
    )
    
    # Update word with new values
    word.repetition_count = updated_data['repetition_count']
    word.easiness_factor = updated_data['easiness_factor']
    word.next_review_date = updated_data['next_review_date']
    word.last_review_date = datetime.utcnow()
    word.total_reviews += 1
    
    if result.success:
        word.successful_reviews += 1
    
    # Recalculate success rate
    if word.total_reviews > 0:
        word.success_rate = (word.successful_reviews / word.total_reviews) * 100
    
    db.commit()
    db.refresh(word)
    
    return {
        "message": "Review recorded successfully",
        "next_review_date": word.next_review_date.isoformat(),
        "interval_days": updated_data['interval_days'],
        "success_rate": round(word.success_rate, 1),
        "repetition_count": word.repetition_count
    }


# NEW ENDPOINT 3: Review statistics
@app.get("/api/stats/reviews")
async def get_review_stats(db: Session = Depends(get_db)):
    """Get comprehensive review statistics"""
    from sqlalchemy import func
    
    now = datetime.utcnow()
    
    # Total words
    total_words = db.query(Word).count()
    
    # Words that have been reviewed at least once
    reviewed_words = db.query(Word).filter(Word.total_reviews > 0).count()
    
    # Words due today
    due_today = db.query(Word).filter(Word.next_review_date <= now).count()
    
    # Words due this week
    week_from_now = now + timedelta(days=7)
    due_this_week = db.query(Word).filter(
        Word.next_review_date <= week_from_now
    ).count()
    
    # Average success rate (only for reviewed words)
    avg_success_rate = db.query(func.avg(Word.success_rate)).filter(
        Word.total_reviews > 0
    ).scalar()
    
    if avg_success_rate is None:
        avg_success_rate = 0
    
    # Mature cards (repetition_count >= 5)
    mature_words = db.query(Word).filter(Word.repetition_count >= 5).count()
    
    return {
        "total_words": total_words,
        "reviewed_words": reviewed_words,
        "unreviewed_words": total_words - reviewed_words,
        "due_today": due_today,
        "due_this_week": due_this_week,
        "mature_words": mature_words,
        "average_success_rate": round(avg_success_rate, 1)
    }
```

**Step 2.4: Test endpoints**

```bash
# Get due words
curl http://localhost:8002/api/words/due

# Submit review (word_id=1, success)
curl -X POST http://localhost:8002/api/words/1/review \
  -H "Content-Type: application/json" \
  -d '{"success": true}'

# Get stats
curl http://localhost:8002/api/stats/reviews
```

---

### Phase 3: Frontend Implementation

**Step 3.1: Add Review Mode to index.html**

Add state for review mode:

```javascript
const [reviewMode, setReviewMode] = useState(false);
const [dueWords, setDueWords] = useState([]);
const [currentWordIndex, setCurrentWordIndex] = useState(0);
const [showAnswer, setShowAnswer] = useState(false);
const [reviewStats, setReviewStats] = useState(null);

// Fetch due words when entering review mode
useEffect(() => {
    if (reviewMode) {
        fetchDueWords();
        fetchReviewStats();
    }
}, [reviewMode]);

const fetchDueWords = async () => {
    const response = await fetch('http://localhost:8002/api/words/due?limit=20');
    const data = await response.json();
    setDueWords(data.words);
    setCurrentWordIndex(0);
    setShowAnswer(false);
};

const fetchReviewStats = async () => {
    const response = await fetch('http://localhost:8002/api/stats/reviews');
    const data = await response.json();
    setReviewStats(data);
};
```

**Step 3.2: Create Review UI Component**

```javascript
function ReviewMode() {
    if (dueWords.length === 0) {
        return (
            <div className="review-empty">
                <h2>🎉 All caught up!</h2>
                <p>No words due for review right now.</p>
                <button onClick={() => setReviewMode(false)}>
                    Back to Word List
                </button>
            </div>
        );
    }
    
    const currentWord = dueWords[currentWordIndex];
    
    const handleReview = async (success) => {
        await fetch(`http://localhost:8002/api/words/${currentWord.id}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ success })
        });
        
        // Move to next word
        if (currentWordIndex < dueWords.length - 1) {
            setCurrentWordIndex(currentWordIndex + 1);
            setShowAnswer(false);
        } else {
            // Finished all reviews!
            alert('🎉 Great job! All reviews complete!');
            setReviewMode(false);
            fetchReviewStats();
        }
    };
    
    return (
        <div className="review-container">
            {/* Progress bar */}
            <div className="review-progress">
                <div className="progress-bar">
                    <div 
                        className="progress-fill" 
                        style={{width: `${((currentWordIndex + 1) / dueWords.length) * 100}%`}}
                    />
                </div>
                <p>{currentWordIndex + 1} of {dueWords.length}</p>
            </div>
            
            {/* Review card */}
            <div className="review-card">
                {!showAnswer ? (
                    <>
                        <h2 className="dutch-word">{currentWord.dutch_word}</h2>
                        <p className="hint">
                            Category: {currentWord.category} | 
                            Reviews: {currentWord.repetition_count} | 
                            Success: {currentWord.success_rate.toFixed(0)}%
                        </p>
                        <button 
                            className="show-answer-btn"
                            onClick={() => setShowAnswer(true)}
                        >
                            Show Answer
                        </button>
                    </>
                ) : (
                    <>
                        <h2 className="spanish-word">{currentWord.spanish_word}</h2>
                        <p className="mnemonic-text">{currentWord.mnemonic_text}</p>
                        {currentWord.mnemonic_image && (
                            <img 
                                src={currentWord.mnemonic_image} 
                                alt="Mnemonic visualization"
                                className="mnemonic-image"
                            />
                        )}
                        
                        <div className="review-buttons">
                            <button 
                                className="review-btn incorrect"
                                onClick={() => handleReview(false)}
                            >
                                ❌ Incorrect
                            </button>
                            <button 
                                className="review-btn correct"
                                onClick={() => handleReview(true)}
                            >
                                ✅ Correct
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
```

**Step 3.3: Add Statistics Dashboard**

```javascript
function StatsDashboard() {
    const [stats, setStats] = useState(null);
    
    useEffect(() => {
        fetch('http://localhost:8002/api/stats/reviews')
            .then(res => res.json())
            .then(setStats);
    }, []);
    
    if (!stats) return <div>Loading stats...</div>;
    
    return (
        <div className="stats-dashboard">
            <h3>📊 Your Progress</h3>
            
            <div className="stats-grid">
                <div className="stat-card">
                    <span className="stat-label">Due Today</span>
                    <strong className="stat-value">{stats.due_today}</strong>
                </div>
                
                <div className="stat-card">
                    <span className="stat-label">Success Rate</span>
                    <strong className="stat-value">{stats.average_success_rate}%</strong>
                </div>
                
                <div className="stat-card">
                    <span className="stat-label">Total Words</span>
                    <strong className="stat-value">{stats.total_words}</strong>
                </div>
                
                <div className="stat-card">
                    <span className="stat-label">Mature Words</span>
                    <strong className="stat-value">{stats.mature_words}</strong>
                </div>
            </div>
            
            {stats.due_today > 0 && (
                <button 
                    className="start-review-btn"
                    onClick={() => setReviewMode(true)}
                >
                    Start Review Session ({stats.due_today} words)
                </button>
            )}
        </div>
    );
}
```

**Step 3.4: Add CSS Styling**

```css
.review-container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}

.review-progress {
    margin-bottom: 30px;
}

.progress-bar {
    width: 100%;
    height: 10px;
    background: #e0e0e0;
    border-radius: 5px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    transition: width 0.3s ease;
}

.review-card {
    background: white;
    padding: 40px;
    border-radius: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    text-align: center;
}

.dutch-word {
    font-size: 48px;
    color: #333;
    margin-bottom: 20px;
}

.spanish-word {
    font-size: 42px;
    color: #667eea;
    margin-bottom: 20px;
}

.mnemonic-text {
    font-size: 18px;
    color: #666;
    line-height: 1.6;
    margin: 20px 0;
}

.mnemonic-image {
    max-width: 100%;
    border-radius: 10px;
    margin: 20px 0;
}

.review-buttons {
    display: flex;
    gap: 20px;
    justify-content: center;
    margin-top: 30px;
}

.review-btn {
    padding: 15px 40px;
    font-size: 18px;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    transition: transform 0.2s;
}

.review-btn:hover {
    transform: scale(1.05);
}

.review-btn.correct {
    background: #4CAF50;
    color: white;
}

.review-btn.incorrect {
    background: #f44336;
    color: white;
}

.stats-dashboard {
    background: white;
    padding: 30px;
    border-radius: 20px;
    margin: 20px 0;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
}

.stat-label {
    display: block;
    font-size: 14px;
    opacity: 0.9;
    margin-bottom: 10px;
}

.stat-value {
    display: block;
    font-size: 32px;
    font-weight: bold;
}
```

---

### Phase 4: Testing Flow

**Test 1: Add new word**
```bash
curl -X POST http://localhost:8002/api/words/ \
  -H "Content-Type: application/json" \
  -d '{"dutch_word": "gato"}'

# Verify next_review_date is set to today
```

**Test 2: Check due words**
```bash
curl http://localhost:8002/api/words/due

# Should show the word we just added
```

**Test 3: Submit successful review**
```bash
curl -X POST http://localhost:8002/api/words/1/review \
  -H "Content-Type: application/json" \
  -d '{"success": true}'

# Check response - interval should be 1 day
```

**Test 4: Verify scheduling**
```bash
sqlite3 backend/spaans_leren.db \
  "SELECT dutch_word, next_review_date, repetition_count, easiness_factor FROM words WHERE id=1"

# Should show updated values
```

---

## Complete Working Example

See the full working example in `/Users/jaccostokx/projects/spaans-leren-app/` after implementation!

**To test the complete flow:**

1. Start backend: `./start.sh`
2. Add a word: Go to frontend, add "perro"
3. Check stats: Stats should show 1 word due
4. Start review: Click "Start Review Session"
5. Review word: Show answer, click ✅ or ❌
6. Check next review: Should schedule for tomorrow
7. Tomorrow: Word appears in due list again!

🎉 **Congratulations!** You now have a fully functional spaced repetition system!
