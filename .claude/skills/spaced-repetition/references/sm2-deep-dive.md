# SuperMemo SM-2 Algorithm - Deep Dive

## History & Background

The SuperMemo SM-2 algorithm was developed by Piotr Woźniak in 1987 as part of his research on optimal learning intervals. It's the foundation for:
- Anki (most popular flashcard app)
- Mnemosyne
- SuperMemo itself
- Countless other spaced repetition systems

**Why SM-2?** It's the sweet spot between:
- ✅ Simplicity (easy to implement)
- ✅ Effectiveness (proven retention rates)
- ✅ Resource efficiency (minimal computational overhead)

## Core Concepts

### 1. The Forgetting Curve

Without review, memory retention follows an exponential decay:
```
Retention = 100% → 58% → 44% → 36% → 33% ...
Time:      0 days  1 day   2 days  7 days  30 days
```

**SM-2 Strategy:** Review just before you forget!

### 2. Optimal Intervals

The algorithm calculates intervals that maximize:
- **Retention:** Keep success rate ~90%
- **Efficiency:** Minimize total review time
- **Spacing Effect:** Longer intervals = stronger memories

### 3. Individual Difficulty

Not all words are equally difficult. The `easiness_factor` personalizes intervals:
- Easy word (EF = 2.5): Intervals grow fast (1d → 6d → 15d → 38d)
- Hard word (EF = 1.3): Intervals grow slow (1d → 6d → 8d → 10d)

## The Formula Explained

### Interval Calculation

```python
if quality < 3:
    interval = 1 day  # Reset on failure
elif repetition == 1:
    interval = 1 day  # First review
elif repetition == 2:
    interval = 6 days  # Second review
else:
    interval = previous_interval * easiness_factor
```

**Why 1 and 6 days?**
- Day 1: Initial consolidation period
- Day 6: Optimal spacing for second review (research-based)
- After: Exponential growth based on individual performance

### Easiness Factor Update

```python
new_EF = old_EF + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
new_EF = max(1.3, new_EF)  # Never too easy
```

**Quality Impact on EF:**
```
Quality 5 → EF +0.10  (word becomes easier)
Quality 4 → EF +0.00  (no change)
Quality 3 → EF -0.14  (slightly harder)
Quality 2 → EF -0.32  (much harder)
```

**Example: Learning "mesa" (table)**

| Review | Quality | EF Before | EF After | Interval | Next Review |
|--------|---------|-----------|----------|----------|-------------|
| 1      | 4       | 2.50      | 2.50     | 1 day    | Tomorrow    |
| 2      | 4       | 2.50      | 2.50     | 6 days   | 1 week      |
| 3      | 4       | 2.50      | 2.50     | 15 days  | 2 weeks     |
| 4      | 5       | 2.50      | 2.60     | 39 days  | 1 month     |
| 5      | 2       | 2.60      | 2.28     | 1 day    | RESET       |
| 6      | 4       | 2.28      | 2.28     | 1 day    | Tomorrow    |
| 7      | 4       | 2.28      | 2.28     | 6 days   | 1 week      |

## Quality Scale Deep Dive

### 5-Point Scale (Anki Standard)

**Quality 5 - Perfect Response:**
- Instant recall, no hesitation
- Feels "too easy"
- **Effect:** Accelerates learning (EF increases)

**Quality 4 - Correct Response:**
- Slight hesitation (< 3 seconds)
- Recalled with confidence
- **Effect:** Maintains current difficulty

**Quality 3 - Difficult Correct:**
- Significant hesitation (> 5 seconds)
- Required mental effort
- **Effect:** Slows progression (EF decreases slightly)

**Quality 2 - Incorrect:**
- Remembered after seeing answer
- "Oh right, I knew that!"
- **Effect:** Resets interval, reduces EF

**Quality 0-1 - Blackout:**
- No recognition
- Completely forgotten
- **Effect:** Hard reset

### Simplified 2-Button Scale (Recommended for Spaans App)

**✅ Success → Quality 4**
- Pros: Simple UX, keeps users engaged
- Cons: Less granular data

**❌ Failure → Quality 2**
- Pros: Clear "need to review" signal
- Cons: Might be too harsh for near-misses

**Why this works:** Most users struggle with 5-point decisions. Binary keeps them moving.

## Common Pitfalls & Solutions

### Pitfall 1: "Easiness Hell"
**Problem:** EF drops to 1.3, word stuck in short intervals forever

**Solution:** Reset EF to 2.0 after 10 consecutive successes
```python
if repetition_count >= 10 and easiness_factor < 2.0:
    easiness_factor = 2.0
```

### Pitfall 2: "Review Pileup"
**Problem:** 200 words due same day, user overwhelmed

**Solution:** Spread due dates slightly
```python
# Add ±12 hour jitter to due dates
import random
jitter_hours = random.randint(-12, 12)
next_review_date += timedelta(hours=jitter_hours)
```

### Pitfall 3: "Fresh Word Spam"
**Problem:** User sees same new word 5 times in one session

**Solution:** Separate "new words" from "reviews"
```python
# Limit new words per session
MAX_NEW_WORDS_PER_DAY = 10
```

## Optimization Tips

### Database Indexing
```sql
CREATE INDEX idx_next_review ON words(next_review_date);
CREATE INDEX idx_repetition ON words(repetition_count);
```

### Query Optimization
```python
# Bad: Load all words, filter in Python
all_words = db.query(Word).all()
due_words = [w for w in all_words if w.next_review_date <= now]

# Good: Filter in SQL
due_words = db.query(Word).filter(
    Word.next_review_date <= now
).limit(50).all()  # Limit prevents overwhelming user
```

### Caching
```python
# Cache "due count" for dashboard (update every 5 minutes)
@lru_cache(maxsize=1)
def get_due_count_cached():
    return db.query(Word).filter(
        Word.next_review_date <= datetime.utcnow()
    ).count()
```

## Research & Further Reading

**Original Paper:**
- Woźniak, P. (1990). "Application of a computer to improve the results obtained in working with the SuperMemo method"
- Available: https://www.supermemo.com/en/blog/application-of-a-computer-to-improve-the-results-obtained-in-working-with-the-supermemo-method

**Modern Implementations:**
- Anki Algorithm: https://faqs.ankiweb.net/what-spaced-repetition-algorithm.html
- Anki 2.1+ uses FSRS (alternative to SM-2)

**Academic Research:**
- Cepeda et al. (2006): "Distributed practice in verbal recall tasks"
- Karpicke & Roediger (2008): "The critical importance of retrieval for learning"

## When to Modify SM-2

**Keep it if:**
- ✅ You have < 1000 words
- ✅ Users are casual learners (30 min/day)
- ✅ Simple is better for your UX

**Consider FSRS if:**
- ⚠️ You have 10,000+ words
- ⚠️ Users are hardcore (2+ hours/day)
- ⚠️ You have data scientists on team

**For Spaans Leren App:** SM-2 is perfect! Keep it simple. 🎯

## Success Metrics to Track

Monitor these to ensure algorithm is working:

1. **Retention Rate:** Should be ~90%
   ```python
   retention_rate = successful_reviews / total_reviews
   ```

2. **Daily Review Count:** Should be manageable (< 50/day)
   ```python
   avg_daily_reviews = total_reviews / days_since_start
   ```

3. **Mature Card Ratio:** Words with repetition_count > 5
   ```python
   mature_ratio = words_with_reps_over_5 / total_words
   ```

4. **Average EF:** Should stabilize around 2.3-2.5
   ```python
   avg_ef = sum(all_easiness_factors) / word_count
   ```

---

**TL;DR:** SM-2 is battle-tested, simple, and perfect for language learning. Don't overthink it! 🚀
