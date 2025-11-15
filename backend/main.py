from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import re
import anthropic
import os
from datetime import datetime, timedelta, date
import base64
import json
from dotenv import load_dotenv
from gtts import gTTS
import io
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

# Load environment variables
load_dotenv()

# Configure logging with sensitive data filter
class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from logs"""
    def filter(self, record):
        if isinstance(record.msg, str):
            # Redact API keys
            record.msg = re.sub(
                r'sk-ant-[a-zA-Z0-9\-]+',
                'sk-ant-***REDACTED***',
                record.msg
            )
            # Redact other potential secrets (Bearer tokens, etc.)
            record.msg = re.sub(
                r'Bearer\s+[a-zA-Z0-9\-\._~\+\/]+',
                'Bearer ***REDACTED***',
                record.msg
            )
        return True

# Apply filter to root logger
logging.basicConfig(level=logging.INFO)
for handler in logging.root.handlers:
    handler.addFilter(SensitiveDataFilter())

from database import get_db, Word, ReviewHistory, StudySession, init_db
from ai_router import ai_router

app = FastAPI(title="Spaans Leren API")

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Whitelist only trusted origins
# For production, replace with your actual domain
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:80",
    "https://spaans.local",
    "https://spaans.orb.local",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],  # Explicit methods only
    allow_headers=["Content-Type", "Authorization"],  # Explicit headers only
)

# Initialize database
@app.on_event("startup")
def startup_event():
    init_db()

# Pydantic models with validation
class WordCreate(BaseModel):
    dutch_word: str = Field(..., min_length=1, max_length=100, description="Dutch word to translate")

    @validator('dutch_word')
    def validate_dutch_word(cls, v):
        """Validate and sanitize Dutch word input"""
        # Strip whitespace
        v = v.strip()

        # Check length after stripping
        if len(v) < 1:
            raise ValueError('Word cannot be empty')
        if len(v) > 100:
            raise ValueError('Word too long (max 100 characters)')

        # Allow letters (including accented), spaces, hyphens, apostrophes
        # This regex supports Dutch, Spanish, and international characters
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\']+$', v):
            raise ValueError('Word contains invalid characters (only letters, spaces, hyphens, and apostrophes allowed)')

        # Prevent excessive whitespace
        if '  ' in v:
            v = re.sub(r'\s+', ' ', v)

        return v

class WordResponse(BaseModel):
    id: int
    dutch_word: str
    spanish_word: str
    category: str
    mnemonic_text: Optional[str]
    mnemonic_image: Optional[str]
    conjugations: Optional[dict]  # Werkwoordvervoegingen
    forms: Optional[dict]  # Meervoud/geslacht vormen
    # Learning enhancement fields
    example_sentences: Optional[List[dict]] = None  # [{"spanish": "...", "dutch": "..."}]
    related_words: Optional[dict] = None  # {"synonyms": [...], "antonyms": [...], "family": [...]}
    video_url: Optional[str] = None  # YouTube embed URL
    created_at: datetime
    # Spaced repetition fields
    review_count: int = 0
    correct_count: int = 0
    easiness_factor: float = 2.5
    interval: int = 0
    repetitions: int = 0
    last_reviewed: Optional[datetime] = None
    next_review: Optional[datetime] = None
    leitner_box: int = 0  # Leitner box 0-5 (calculated)
    # Duplicate detection
    is_duplicate: bool = False

    class Config:
        from_attributes = True


class ReviewSubmit(BaseModel):
    word_id: int = Field(..., gt=0, description="Word ID must be positive")
    quality: int = Field(..., ge=0, le=5, description="Quality rating 0-5")

    @validator('quality')
    def validate_quality(cls, v):
        """Ensure quality is one of the allowed values"""
        if v not in [0, 3, 4, 5]:
            raise ValueError('Quality must be 0, 3, 4, or 5')
        return v


class ReviewHistoryResponse(BaseModel):
    id: int
    word_id: int
    reviewed_at: datetime
    quality: int
    interval_before: Optional[int]
    interval_after: Optional[int]
    easiness_factor_after: Optional[float]

    class Config:
        from_attributes = True


class ReviewStatsResponse(BaseModel):
    due_today: int
    learning: int  # interval < 21 days
    mastered: int  # interval >= 21 days
    total_reviews_today: int


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_review_date: Optional[date]


class HeatmapEntry(BaseModel):
    date: date
    reviews: int


def word_to_response(word: Word) -> WordResponse:
    """Convert Word database model to WordResponse with parsed JSON fields"""
    conjugations = None
    forms = None
    example_sentences = None
    related_words = None

    if word.conjugations:
        try:
            conjugations = json.loads(word.conjugations)
        except (json.JSONDecodeError, TypeError):
            pass

    if word.forms:
        try:
            forms = json.loads(word.forms)
        except (json.JSONDecodeError, TypeError):
            pass

    if word.example_sentences:
        try:
            example_sentences = json.loads(word.example_sentences)
        except (json.JSONDecodeError, TypeError):
            pass

    if word.related_words:
        try:
            related_words = json.loads(word.related_words)
        except (json.JSONDecodeError, TypeError):
            pass

    return WordResponse(
        id=word.id,
        dutch_word=word.dutch_word,
        spanish_word=word.spanish_word,
        category=word.category,
        mnemonic_text=word.mnemonic_text,
        mnemonic_image=word.mnemonic_image,
        conjugations=conjugations,
        forms=forms,
        example_sentences=example_sentences,
        related_words=related_words,
        video_url=word.video_url,
        created_at=word.created_at,
        review_count=word.review_count,
        correct_count=word.correct_count,
        easiness_factor=word.easiness_factor,
        interval=word.interval,
        repetitions=word.repetitions,
        last_reviewed=word.last_reviewed,
        next_review=word.next_review,
        leitner_box=get_leitner_box(word)
    )


def get_leitner_box(word: Word) -> int:
    """
    Calculate Leitner box (0-5) based on word performance.

    Box system:
    - Box 0: New cards (never reviewed)
    - Box 1: Learning (struggling, low EF or few repetitions)
    - Box 2: Familiar (making progress)
    - Box 3: Good (solid understanding)
    - Box 4: Strong (high confidence)
    - Box 5: Mastered (expert level)

    Args:
        word: Word with spaced repetition stats

    Returns:
        int: Box number 0-5
    """
    # Box 0: New cards (never reviewed)
    if word.review_count == 0:
        return 0

    # Use easiness factor and repetitions to determine box
    ef = word.easiness_factor
    reps = word.repetitions

    # Box 1: Learning (EF < 2.0 or low repetitions)
    if ef < 2.0 or reps < 3:
        return 1

    # Box 2: Familiar (EF 2.0-2.3, or reps 3-4)
    if ef < 2.3 or reps < 5:
        return 2

    # Box 3: Good (EF 2.3-2.6, or reps 5-7)
    if ef < 2.6 or reps < 8:
        return 3

    # Box 4: Strong (EF 2.6-2.8, or reps 8-9)
    if ef < 2.8 or reps < 10:
        return 4

    # Box 5: Mastered (EF >= 2.8 and reps >= 10)
    return 5


def calculate_sm2_interval(word: Word, quality: int) -> tuple[float, int, int, datetime]:
    """
    Calculate next review interval using SM-2 algorithm.

    Args:
        word: Current word state
        quality: User rating 0-5 (0=Again, 3=Hard, 4=Good, 5=Easy)

    Returns:
        tuple: (new_easiness_factor, new_interval, new_repetitions, next_review_date)
    """
    ef = word.easiness_factor
    interval = word.interval
    repetitions = word.repetitions

    # SM-2 formula: EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    # Simplified: EF' = EF - 0.8 + 0.28*q - 0.02*q*q
    new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    # Easiness factor must stay >= 1.3
    if new_ef < 1.3:
        new_ef = 1.3

    # Calculate new interval based on quality
    if quality < 3:
        # Failed - restart
        new_repetitions = 0
        new_interval = 1  # Review tomorrow
    else:
        # Passed
        if repetitions == 0:
            new_interval = 1
            new_repetitions = 1
        elif repetitions == 1:
            new_interval = 6
            new_repetitions = 2
        else:
            # For subsequent reviews: interval = previous_interval * EF
            new_interval = round(interval * new_ef)
            new_repetitions = repetitions + 1

    # Calculate next review date
    next_review = datetime.utcnow() + timedelta(days=new_interval)

    return new_ef, new_interval, new_repetitions, next_review


async def generate_translation_and_mnemonic(dutch_word: str, use_claude: bool = False) -> dict:
    """
    Generate translation and mnemonic using hybrid AI system
    
    HYBRID WORKFLOW:
    1. Translation & Grammar: Qwen 2.5 14B (fast, multilingual expert)
    2. Creative Mnemonic: Mistral 7B (creative content specialist)
    3. Optional validation: Claude API (quality assurance)
    
    Args:
        dutch_word: Dutch word to translate
        use_claude: Force use of Claude API instead of Ollama (default: False)
    
    Returns:
        dict with keys: spanish, category, mnemonic_text, visual_description, 
                       conjugations, forms, models_used
    """
    print(f"\n{'='*60}")
    print(f"🚀 HYBRIDE AI SYSTEEM - Vertaling: '{dutch_word}'")
    print(f"{'='*60}")
    
    try:
        # PHASE 1: Translation with Qwen (or Claude if forced)
        print(f"\n📝 FASE 1: Vertaling en grammatica")
        translation_data = await ai_router.translate_with_grammar(
            dutch_word=dutch_word,
            use_claude=use_claude
        )
        
        spanish_word = translation_data.get("spanish", "")
        category = translation_data.get("category", "algemeen")
        conjugations = translation_data.get("conjugations")
        forms = translation_data.get("forms")
        
        print(f"   ✓ Spaans: {spanish_word}")
        print(f"   ✓ Categorie: {category}")
        print(f"   ✓ Model: {'Claude' if use_claude else 'Qwen'}")
        
        # PHASE 2: Mnemonic generation with Mistral (or Claude if forced)
        print(f"\n🎨 FASE 2: Mnemonic generatie")
        mnemonic_data = await ai_router.generate_mnemonic(
            spanish_word=spanish_word,
            dutch_word=dutch_word,
            use_claude=use_claude
        )
        
        mnemonic_text = mnemonic_data.get("mnemonic_text", "")
        visual_description = mnemonic_data.get("visual_description", "")
        
        print(f"   ✓ Mnemonic: {mnemonic_text[:60]}...")
        print(f"   ✓ Visual: {visual_description[:60]}...")
        print(f"   ✓ Model: {'Claude' if use_claude else 'Mistral'}")
        
        # Combine results
        result = {
            "spanish": spanish_word,
            "category": category,
            "mnemonic_text": mnemonic_text,
            "visual_description": visual_description,
            "conjugations": conjugations,
            "forms": forms,
            "models_used": {
                "translation": "claude" if use_claude else "qwen",
                "mnemonic": "claude" if use_claude else "mistral"
            }
        }
        
        print(f"\n{'='*60}")
        print(f"✅ HYBRIDE WORKFLOW COMPLEET")
        print(f"{'='*60}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR in hybride workflow: {str(e)}")
        print(f"🔄 Falling back to pure Claude API...")
        
        # Complete fallback to original Claude API method
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY niet gevonden en Ollama gefaald")
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Use original comprehensive prompt
        prompt = f"""Je helpt een Nederlandse persoon (Jacco) Spaans te leren.

TAAK:
Vertaal het Nederlandse woord "{dutch_word}" naar Spaans en bedenk een VISUELE GEHEUGENSTEUN (mnemonic).

[... rest of original prompt remains the same ...]

Geef je antwoord in dit EXACTE JSON formaat (geen extra tekst):
{{
  "spanish": "het spaanse woord (met lidwoord zoals la/el)",
  "category": "de beste categorie",
  "mnemonic_text": "De geheugensteun uitleg (kort en bondig!)",
  "visual_description": "SCENE|ELEMENTEN|KLEUREN|ACTIE formaat",
  "conjugations": {{...}} (ALLEEN voor werkwoorden),
  "forms": {{...}} (voor naamwoorden of bijvoeglijke naamwoorden)
}}
"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text.strip()
        
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        result = json.loads(response_text)
        result["models_used"] = {"translation": "claude_fallback", "mnemonic": "claude_fallback"}
        
        return result


async def generate_learning_enhancements(spanish_word: str, dutch_word: str, category: str) -> dict:
    """
    Generate example sentences and related words for enhanced learning.
    Called separately after main translation to enrich word data.

    Returns:
        dict with keys: example_sentences, related_words
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️ No API key for learning enhancements, skipping...")
        return {"example_sentences": [], "related_words": {}}

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Generate learning enhancements for Spanish word "{spanish_word}" (Dutch: "{dutch_word}", Category: {category}).

PROVIDE:
1. **3 Example Sentences** - Show the word in natural context:
   - Vary difficulty (basic → intermediate)
   - Include both Spanish sentence AND Dutch translation
   - Keep sentences practical and conversational

2. **Related Words** for memory connections:
   - Synonyms (2-3 Spaanse woorden met gelijke betekenis)
   - Antonyms (1-2 tegenovergestelden, if applicable)
   - Word Family (verwante woorden zoals trabajo → trabajar, trabajador)

Return ONLY valid JSON (no markdown):
{{
  "example_sentences": [
    {{"spanish": "El gato come pescado.", "dutch": "De kat eet vis."}},
    {{"spanish": "Mi gato es muy cariñoso.", "dutch": "Mijn kat is erg aanhankelijk."}},
    {{"spanish": "¿Has visto al gato del vecino?", "dutch": "Heb je de kat van de buur gezien?"}}
  ],
  "related_words": {{
    "synonyms": ["minino", "felino"],
    "antonyms": [],
    "family": ["gatito (kitten)", "gatuno (feline)", "gatera (cat lover)"]
  }}
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # Clean markdown if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)
        print(f"✅ Learning enhancements generated: {len(result.get('example_sentences', []))} sentences")
        return result

    except Exception as e:
        print(f"❌ Error generating learning enhancements: {str(e)}")
        return {"example_sentences": [], "related_words": {}}


def validate_svg(svg_code: str) -> tuple[bool, str]:
    """
    Strict SVG validation for security.
    Protects against XSS, XXE, and malicious content injection.
    Returns (is_valid, error_message)
    """
    import re
    from xml.etree import ElementTree

    if not svg_code or len(svg_code.strip()) == 0:
        return False, "SVG is empty"

    svg_lower = svg_code.lower()

    # SECURITY CHECK 1: Block script tags (XSS protection)
    if re.search(r'<script', svg_code, re.IGNORECASE):
        return False, "Scripts not allowed in SVG (security risk)"

    # SECURITY CHECK 2: Block external resources (data exfiltration prevention)
    if re.search(r'xlink:href\s*=\s*["\']https?://', svg_code, re.IGNORECASE):
        return False, "External resources not allowed (security risk)"

    # SECURITY CHECK 3: Block DOCTYPE and entities (XXE attack prevention)
    if '<!DOCTYPE' in svg_code or '<!ENTITY' in svg_code:
        return False, "DOCTYPE/entities not allowed (XXE protection)"

    # SECURITY CHECK 4: Block event handlers (onclick, onload, etc.)
    event_handlers = ['onclick', 'onload', 'onmouseover', 'onerror', 'onmouseenter']
    for handler in event_handlers:
        if handler in svg_lower:
            return False, f"Event handlers not allowed: {handler} (XSS protection)"

    # SECURITY CHECK 5: Block JavaScript URLs
    if 'javascript:' in svg_lower:
        return False, "JavaScript URLs not allowed (XSS protection)"

    # SECURITY CHECK 6: Block data URLs with scripts
    if re.search(r'data:[^,]*script', svg_code, re.IGNORECASE):
        return False, "Script data URLs not allowed (XSS protection)"

    # Check for required tags
    if "<svg" not in svg_lower:
        return False, "Missing <svg> opening tag"
    if "</svg>" not in svg_lower:
        return False, "Missing </svg> closing tag"

    # Check for basic structure
    if 'width=' not in svg_lower or 'height=' not in svg_lower:
        return False, "Missing width or height attributes"

    # Check for tag balance
    if svg_code.count("<svg") != svg_code.count("</svg>"):
        return False, "Mismatched svg tags"

    # Check if it looks like an error message
    if "error" in svg_lower[:100] or "sorry" in svg_lower[:100]:
        return False, "SVG appears to be an error message"

    # SECURITY CHECK 7: Validate as well-formed XML
    try:
        ElementTree.fromstring(svg_code)
    except ElementTree.ParseError as e:
        return False, f"Invalid XML structure: {str(e)}"

    # SECURITY CHECK 8: Whitelist allowed SVG tags only
    allowed_tags = {
        'svg', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon',
        'path', 'text', 'g', 'defs', 'linearGradient', 'radialGradient',
        'stop', 'filter', 'feGaussianBlur', 'feOffset', 'feComponentTransfer',
        'feFuncA', 'feMerge', 'feMergeNode', 'image', 'use', 'clipPath',
        'mask', 'pattern', 'marker', 'symbol', 'foreignObject'
    }

    try:
        tree = ElementTree.fromstring(svg_code)
        for elem in tree.iter():
            # Remove namespace prefix if present
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag not in allowed_tags:
                return False, f"Disallowed SVG tag: <{tag}> (security restriction)"
    except Exception as e:
        return False, f"Error parsing SVG tags: {str(e)}"

    return True, "Valid"


async def generate_svg_with_claude(description: str, spanish_word: str, dutch_word: str, retry: int = 0) -> str:
    """Use Claude to generate custom SVG based on visual description"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback to simple visualization
        return None

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Je bent een SVG illustrator voor educatieve flashcards. Genereer een RIJKE, VISUELE SVG illustratie (800x700px).

CONTEXT:
- Nederlands woord: {dutch_word}
- Spaans woord: {spanish_word}
- Visuele beschrijving: {description}

De visuele beschrijving is gestructureerd als "SCENE: ... | ELEMENTEN: ... | KLEUREN: ... | ACTIE: ..."
Parse deze structuur en VISUALISEER alle elementen!

LAYOUT STRUCTUUR (verplicht):
1. Canvas: 800x700px met gradient achtergrond (purple #667eea → violet #764ba2 → pink #f093fb)
2. Scene area (top): Y 50-350 - teken hier de VOLLEDIGE scene met ALLE objecten
3. Spanish word: Y 370 - groot, wit, bold (72px)
4. Dutch word: Y 420 - kleiner, wit, semi-transparent (38px)
5. Mnemonic box: Y 460-680 - witte box met de mnemonic tekst

SVG ELEMENTEN VOOR RIJKE SCENES:

**SPEECH BUBBLES** (voor "roepen", "zeggen", etc.):
```xml
<!-- Speech bubble met tekst -->
<g>
  <!-- Bubble achtergrond -->
  <ellipse cx="300" cy="150" rx="80" ry="40" fill="white" stroke="#333" stroke-width="2"/>
  <!-- Pointer/tail -->
  <polygon points="280,180 270,200 290,185" fill="white" stroke="#333" stroke-width="2"/>
  <!-- Tekst in bubble -->
  <text x="300" y="160" text-anchor="middle" font-size="20" font-weight="bold" fill="#333">TEKST!</text>
</g>
```

**MEERDERE OBJECTEN** (bijv. ei in nest met andere eieren):
- Teken elk element AFZONDERLIJK op verschillende posities
- Gebruik layering: achtergrond objecten eerst, voorgrond objecten later
- Voorbeelden:
  * Nest: <ellipse> met brown fill, sticks met <line> elementen
  * Eieren: meerdere <ellipse> op verschillende (cx, cy) posities
  * Characters: circle voor hoofd + rect voor body + circles voor ogen

**ACTIONS/BEWEGING**:
- **Motion lines**: <line> elementen met opacity 0.5 achter bewegend object
- **Pijlen**: <polygon> of <path> met arrow marker
- **Richting**: positioneer objecten met implicit movement (links → rechts)
- **Expressies**: extra circles/ellipses voor ogen, gebogen lijnen voor mond

KLEUREN (gebruik de kleuren uit KLEUREN: sectie):
- Heldere, contrastrijke kleuren
- Consistente kleurpaletten per scene
- Witte/lichte accents voor highlights

CRITICAL RULES:
1. TEKEN ALLES met SVG shapes - GEEN emoji/unicode tekst (behalve in speech bubbles)
2. Parse de ELEMENTEN: sectie en teken ELK element dat genoemd wordt
3. Als ACTIE: "roept/zegt" → gebruik speech bubble
4. Als ACTIE: "beweegt/rent/komt" → gebruik motion lines of pijlen
5. Meerdere objecten? Teken ze ALLEMAAL op verschillende posities
6. Gebruik <g> groups om gerelateerde elementen te groeperen
7. Voeg shadows toe met filters voor depth
8. Background objects: opacity 0.3-0.7 voor depth

RESPONSIVE TEXT:
- Text moet gecentreerd zijn (text-anchor="middle")
- Spanish word: x="400" y="370" font-size="72" (altijd)
- Dutch word: x="400" y="420" font-size="38" (altijd)

VOORBEELD voor "ei roept HOEVEEL naar andere eieren in nest":
```xml
<svg width="800" height="700" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#667eea"/>
      <stop offset="50%" stop-color="#764ba2"/>
      <stop offset="100%" stop-color="#f093fb"/>
    </linearGradient>
    <filter id="shadow">
      <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
      <feOffset dx="0" dy="3"/>
      <feComponentTransfer><feFuncA type="linear" slope="0.3"/></feComponentTransfer>
      <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="800" height="700" fill="url(#bg)" rx="40"/>

  <!-- SCENE: Nest onderaan met eieren -->
  <!-- Nest (brown ellipse met sticks) -->
  <ellipse cx="400" cy="280" rx="180" ry="60" fill="#8B4513" opacity="0.7"/>
  <line x1="300" y1="250" x2="280" y2="290" stroke="#654321" stroke-width="4"/>
  <line x1="500" y1="250" x2="520" y2="290" stroke="#654321" stroke-width="4"/>

  <!-- Achtergrond eieren (andere eieren) -->
  <ellipse cx="320" cy="270" rx="30" ry="40" fill="#FFF8DC" stroke="#DDD" stroke-width="2" opacity="0.8"/>
  <ellipse cx="480" cy="270" rx="30" ry="40" fill="#FFF8DC" stroke="#DDD" stroke-width="2" opacity="0.8"/>
  <ellipse cx="380" cy="290" rx="28" ry="38" fill="#FFF8DC" stroke="#DDD" stroke-width="2" opacity="0.8"/>

  <!-- MAIN EI (voorgrond, groter) -->
  <ellipse cx="400" cy="240" rx="45" ry="60" fill="#FFFACD" stroke="#FFD700" stroke-width="3" filter="url(#shadow)"/>
  <!-- Ei gezicht (ogen) -->
  <circle cx="390" cy="230" r="5" fill="#333"/>
  <circle cx="410" cy="230" r="5" fill="#333"/>
  <!-- Mond (open voor roepen) -->
  <ellipse cx="400" cy="245" rx="8" ry="12" fill="#333"/>

  <!-- SPEECH BUBBLE: "HOEVEEL!" -->
  <ellipse cx="520" cy="150" rx="90" ry="45" fill="white" stroke="#333" stroke-width="3" filter="url(#shadow)"/>
  <polygon points="480,180 450,220 490,190" fill="white" stroke="#333" stroke-width="3"/>
  <text x="520" y="160" text-anchor="middle" font-size="24" font-weight="bold" fill="#E74C3C">HOEVEEL!</text>

  <!-- Spanish word -->
  <text x="400" y="370" text-anchor="middle" font-size="72" font-weight="900" fill="white" filter="url(#shadow)">el huevo</text>

  <!-- Dutch word -->
  <text x="400" y="420" text-anchor="middle" font-size="38" font-weight="600" fill="white" opacity="0.9">ei</text>

  <!-- Mnemonic box -->
  <rect x="40" y="460" width="720" height="200" fill="white" opacity="0.95" rx="30" filter="url(#shadow)"/>
  <text x="70" y="510" font-size="48">💡</text>
  <text x="400" y="520" text-anchor="middle" font-size="20" fill="#333">Een groot wit ei in een nest dat met zijn bek wijd open</text>
  <text x="400" y="550" text-anchor="middle" font-size="20" fill="#333">'HOEVEEL, HOEVEEL!' roept naar andere eieren die om hem heen liggen</text>
</svg>
```

Nu, genereer de SVG voor de gegeven beschrijving. Geef ALLEEN de SVG code, geen uitleg!"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,  # Verhoogd voor complexere SVG's
            messages=[{"role": "user", "content": prompt}]
        )

        svg_code = message.content[0].text.strip()

        # Remove markdown code blocks if present
        if svg_code.startswith("```"):
            svg_code = svg_code.split("```")[1]
            if svg_code.startswith("xml") or svg_code.startswith("svg"):
                svg_code = "\n".join(svg_code.split("\n")[1:])

        svg_code = svg_code.strip()

        # Validate the generated SVG
        is_valid, error_msg = validate_svg(svg_code)

        if not is_valid:
            print(f"❌ SVG Validation failed for '{dutch_word}': {error_msg}")
            print(f"Generated SVG preview: {svg_code[:300]}...")

            # Retry once with more explicit instructions
            if retry < 1:
                print(f"🔄 Retrying SVG generation for '{dutch_word}' (attempt {retry + 2})...")
                return await generate_svg_with_claude(description, spanish_word, dutch_word, retry + 1)

            print(f"⚠️  SVG generation failed after {retry + 1} attempts, falling back to simple visualization")
            return None

        # Success!
        print(f"✅ SVG generated successfully for '{dutch_word}' (attempt {retry + 1})")
        return svg_code

    except Exception as e:
        print(f"❌ Exception generating SVG with Claude for '{dutch_word}': {e}")
        import traceback
        print(traceback.format_exc())

        # Retry once on exception
        if retry < 1:
            print(f"🔄 Retrying after exception for '{dutch_word}' (attempt {retry + 2})...")
            return await generate_svg_with_claude(description, spanish_word, dutch_word, retry + 1)

        return None


def generate_svg_visualization(description: str, spanish_word: str, dutch_word: str) -> str:
    """Generate modern SVG visualization"""

    import base64  # Import altijd bovenaan zodat het voor alle cases beschikbaar is

    # Speciale case voor tafel - teken een echte tafel!
    if dutch_word.lower() == "tafel" or "mesa" in spanish_word.lower():
        # Wrap tekst netjes
        words = description.split()
        lines = []
        current_line = ""
        max_chars = 65
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_chars:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # Maak text elements - GECENTREERD zoals de rest van de SVG
        text_y = 490
        text_elements = ""
        for i, line in enumerate(lines[:5]):  # Max 5 regels
            text_elements += f'<text x="400" y="{text_y + (i * 32)}" font-family="Poppins, Arial, sans-serif" font-size="20" font-weight="500" fill="#1F2937" text-anchor="middle">{line}</text>\n    '
        
        svg = f"""<svg width="800" height="700" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
            <stop offset="50%" style="stop-color:#764ba2;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#f093fb;stop-opacity:1" />
        </linearGradient>
        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="4"/>
            <feOffset dx="0" dy="4"/>
            <feComponentTransfer><feFuncA type="linear" slope="0.3"/></feComponentTransfer>
            <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
    </defs>
    
    <!-- Gradient achtergrond -->
    <rect width="800" height="700" fill="url(#bgGrad)" rx="40"/>
    
    <!-- Decoratieve cirkels -->
    <circle cx="120" cy="120" r="80" fill="white" opacity="0.1"/>
    <circle cx="680" cy="600" r="100" fill="white" opacity="0.1"/>
    <circle cx="700" cy="150" r="60" fill="white" opacity="0.15"/>
    <circle cx="100" cy="550" r="70" fill="white" opacity="0.1"/>
    
    <!-- TAFEL TEKENING als "emoji" -->
    <g transform="translate(400, 140)" filter="url(#shadow)">
        <!-- Tafelblad (perspective view) -->
        <ellipse cx="0" cy="0" rx="150" ry="30" fill="#654321" opacity="0.3"/>
        <rect x="-150" y="-15" width="300" height="30" rx="10" fill="#8B4513"/>
        <rect x="-150" y="-15" width="300" height="10" rx="10" fill="#A0522D"/>
        
        <!-- Vier tafelpoten (perspective) -->
        <rect x="-130" y="15" width="18" height="100" fill="#654321"/>
        <rect x="112" y="15" width="18" height="100" fill="#654321"/>
        <rect x="-80" y="15" width="15" height="90" fill="#5D4E37"/>
        <rect x="65" y="15" width="15" height="90" fill="#5D4E37"/>
        
        <!-- Borden op tafel (beter verdeeld) -->
        <ellipse cx="-70" cy="5" rx="30" ry="10" fill="white" opacity="0.95"/>
        <ellipse cx="0" cy="0" rx="30" ry="10" fill="white" opacity="0.95"/>
        <ellipse cx="70" cy="5" rx="30" ry="10" fill="white" opacity="0.95"/>
        
        <!-- Extra detail: bestek -->
        <line x1="-85" y1="3" x2="-85" y2="12" stroke="#C0C0C0" stroke-width="2"/>
        <line x1="-55" y1="3" x2="-55" y2="12" stroke="#C0C0C0" stroke-width="2"/>
    </g>
    
    <!-- Spaans woord -->
    <text x="400" y="330" font-family="Poppins, Arial, sans-serif" font-size="72" font-weight="900" 
          fill="white" text-anchor="middle" filter="url(#shadow)">{spanish_word}</text>
    
    <!-- Nederlands woord -->
    <text x="400" y="390" font-family="Poppins, Arial, sans-serif" font-size="38" font-weight="600"
          fill="white" text-anchor="middle" opacity="0.9">{dutch_word}</text>
    
    <!-- Geheugensteun box -->
    <rect x="40" y="440" width="720" height="220" fill="white" opacity="0.95" rx="30" filter="url(#shadow)"/>
    
    <!-- Lampje emoji -->
    <text x="70" y="500" font-size="48">💡</text>
    
    <!-- Geheugensteun tekst -->
    {text_elements}
</svg>"""
        # Encode naar base64
        svg_base64 = base64.b64encode(svg.encode()).decode()
        return f"data:image/svg+xml;base64,{svg_base64}"
    
    # Extract emoji's uit description voor andere woorden
    import re
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map
        u"\U0001F700-\U0001F77F"  # alchemical
        u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        u"\U0001FA00-\U0001FA6F"  # Chess Symbols
        u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        u"\U00002702-\U000027B0"  # Dingbats
        "]+", flags=re.UNICODE)
    
    emojis = emoji_pattern.findall(description)
    emoji_display = " ".join(emojis[:6]) if emojis else "💡✨"
    
    # Moderne gradient kleuren
    svg = f"""<svg width="800" height="700" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <!-- Moderne gradient achtergrond -->
        <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
            <stop offset="50%" style="stop-color:#764ba2;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#f093fb;stop-opacity:1" />
        </linearGradient>
        
        <!-- Shadow filter -->
        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="4"/>
            <feOffset dx="0" dy="4" result="offsetblur"/>
            <feComponentTransfer>
                <feFuncA type="linear" slope="0.3"/>
            </feComponentTransfer>
            <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        
        <!-- Glow effect -->
        <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    
    <!-- Gradient achtergrond -->
    <rect width="800" height="700" fill="url(#bgGrad)" rx="40"/>
    
    <!-- Decoratieve cirkels met opacity -->
    <circle cx="120" cy="120" r="80" fill="white" opacity="0.1"/>
    <circle cx="680" cy="600" r="100" fill="white" opacity="0.1"/>
    <circle cx="700" cy="150" r="60" fill="white" opacity="0.15"/>
    <circle cx="100" cy="550" r="70" fill="white" opacity="0.1"/>
    
    <!-- Groot emoji centrum met glow -->
    <text x="400" y="200" font-size="140" text-anchor="middle" filter="url(#glow)">{emoji_display}</text>
    
    <!-- Spaans woord - extra groot en prominent met shadow -->
    <text x="400" y="330" font-family="Poppins, Arial, sans-serif" font-size="72" font-weight="900" 
          fill="white" text-anchor="middle" filter="url(#shadow)">{spanish_word}</text>
    
    <!-- Nederlands woord -->
    <text x="400" y="390" font-family="Poppins, Arial, sans-serif" font-size="38" font-weight="600"
          fill="white" text-anchor="middle" opacity="0.9">{dutch_word}</text>
    
    <!-- Geheugensteun box - wit met rounded corners -->
    <rect x="40" y="440" width="720" height="220" fill="white" opacity="0.95" rx="30" filter="url(#shadow)"/>
    
    <!-- Lampje emoji -->
    <text x="70" y="500" font-size="48">💡</text>
"""
    
    # Wrap tekst netjes over meerdere regels met meer ruimte
    words = description.split()
    lines = []
    current_line = ""
    max_chars = 65  # Meer karakters per regel
    
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    # Maximaal 5 regels voor betere leesbaarheid
    y_start = 490
    line_height = 32
    
    for i, line in enumerate(lines[:5]):  # Max 5 regels
        y_pos = y_start + (i * line_height)
        svg += f'    <text x="400" y="{y_pos}" font-family="Poppins, Arial, sans-serif" font-size="20" font-weight="500" fill="#1F2937" text-anchor="middle">{line}</text>\n'
    
    svg += "</svg>"
    
    svg_base64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{svg_base64}"


@app.post("/api/words/", response_model=WordResponse)
@limiter.limit("10/minute")  # Max 10 new words per minute (expensive AI operation)
async def create_word(request: Request, word_data: WordCreate, db: Session = Depends(get_db)):
    # Check of het woord al bestaat (case-insensitive)
    existing_word = db.query(Word).filter(
        Word.dutch_word.ilike(word_data.dutch_word)
    ).first()

    if existing_word:
        # Woord bestaat al, geef de bestaande entry terug met is_duplicate flag
        response = word_to_response(existing_word)
        response.is_duplicate = True
        return response
    
    try:
        # Force Claude for speed (skip slow Ollama timeouts)
        ai_result = await generate_translation_and_mnemonic(word_data.dutch_word, use_claude=True)
    except Exception as e:
        import traceback
        error_detail = f"AI generatie fout: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(status_code=500, detail=f"AI generatie fout: {str(e)}")
    
    # Try Claude-generated SVG first, fallback to simple visualization
    svg_image = await generate_svg_with_claude(
        ai_result.get("visual_description", ""),
        ai_result["spanish"],
        word_data.dutch_word
    )

    if not svg_image:
        # Fallback to simple SVG
        svg_image = generate_svg_visualization(
            ai_result.get("visual_description", ""),
            ai_result["spanish"],
            word_data.dutch_word
        )
    else:
        # Encode Claude-generated SVG to base64
        import base64
        svg_base64 = base64.b64encode(svg_image.encode()).decode()
        svg_image = f"data:image/svg+xml;base64,{svg_base64}"

    # Generate learning enhancements (example sentences + related words)
    print(f"\n📚 Generating learning enhancements...")
    enhancements = await generate_learning_enhancements(
        spanish_word=ai_result["spanish"],
        dutch_word=word_data.dutch_word,
        category=ai_result.get("category", "algemeen")
    )

    # Extract conjugations and forms from AI result
    conjugations_json = None
    forms_json = None
    example_sentences_json = None
    related_words_json = None

    if "conjugations" in ai_result and ai_result["conjugations"]:
        conjugations_json = json.dumps(ai_result["conjugations"])

    if "forms" in ai_result and ai_result["forms"]:
        forms_json = json.dumps(ai_result["forms"])

    if enhancements.get("example_sentences"):
        example_sentences_json = json.dumps(enhancements["example_sentences"])

    if enhancements.get("related_words"):
        related_words_json = json.dumps(enhancements["related_words"])

    db_word = Word(
        dutch_word=word_data.dutch_word,
        spanish_word=ai_result["spanish"],
        category=ai_result.get("category", "algemeen"),
        mnemonic_text=ai_result["mnemonic_text"],
        mnemonic_image=svg_image,
        conjugations=conjugations_json,
        forms=forms_json,
        example_sentences=example_sentences_json,
        related_words=related_words_json
    )
    
    db.add(db_word)
    db.commit()
    db.refresh(db_word)

    return word_to_response(db_word)


@app.get("/api/words/", response_model=List[WordResponse])
def get_all_words(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Word)

    if category:
        # Sanitize category to prevent injection
        category = category.strip()[:50]
        query = query.filter(Word.category == category)

    if search:
        # SECURITY: Sanitize search input to prevent SQL injection and DoS
        # Remove special SQL LIKE characters and limit length
        search = search.strip()[:100]  # Limit length
        search = re.sub(r'[%_\\]', '', search)  # Remove wildcard characters
        if search:  # Only search if there's something left after sanitization
            search_term = f"%{search}%"
            query = query.filter(
                (Word.dutch_word.like(search_term)) |
                (Word.spanish_word.like(search_term))
            )

    words = query.offset(skip).limit(limit).all()
    return [word_to_response(word) for word in words]


# IMPORTANT: Define /words/due BEFORE /words/{word_id} to avoid route conflict
@app.get("/api/words/due", response_model=List[WordResponse])
def get_due_words(db: Session = Depends(get_db)):
    """
    Get all words that are due for review with smart priority sorting.

    Priority order:
    1. Most overdue first (next_review earliest = longest waiting)
    2. Lower Leitner box = higher priority (struggling words first)
    3. Lower easiness factor = harder words first
    """
    now = datetime.utcnow()
    due_words = db.query(Word).filter(
        Word.next_review <= now
    ).order_by(
        Word.next_review.asc(),      # Most overdue first
        Word.repetitions.asc(),       # Fewer reps = lower box = higher priority
        Word.easiness_factor.asc()    # Lower EF = struggling = higher priority
    ).all()
    return [word_to_response(word) for word in due_words]


@app.get("/api/words/{word_id}", response_model=WordResponse)
def get_word(word_id: int, db: Session = Depends(get_db)):
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Woord niet gevonden")
    return word_to_response(word)


@app.delete("/api/words/{word_id}")
def delete_word(word_id: int, db: Session = Depends(get_db)):
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Woord niet gevonden")

    db.delete(word)
    db.commit()
    return {"message": "Woord verwijderd"}


@app.get("/api/words/{word_id}/audio")
def get_word_audio(word_id: int, db: Session = Depends(get_db)):
    """
    Generate Spanish pronunciation audio for a word using Google Text-to-Speech.
    Returns base64 encoded MP3 as data URL.
    """
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Woord niet gevonden")

    try:
        # Generate Spanish audio with gTTS
        tts = gTTS(text=word.spanish_word, lang='es', slow=False)

        # Save to in-memory bytes buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        # Convert to base64
        audio_base64 = base64.b64encode(audio_buffer.read()).decode('utf-8')

        # Return as data URL
        return {
            "word_id": word_id,
            "spanish_word": word.spanish_word,
            "audio_data": f"data:audio/mp3;base64,{audio_base64}"
        }

    except Exception as e:
        print(f"❌ Error generating audio for word {word_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij genereren audio: {str(e)}")


@app.post("/api/words/{word_id}/regenerate", response_model=WordResponse)
@limiter.limit("5/minute")  # Max 5 regenerations per minute
async def regenerate_word(request: Request, word_id: int, db: Session = Depends(get_db)):
    """
    Regenerate visualization for a single word.
    This will create a NEW mnemonic and visualization using the improved prompts.
    """
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Woord niet gevonden")

    try:
        print(f"\n{'='*60}")
        print(f"🔄 Regenerating word: '{word.dutch_word}' (ID: {word_id})")
        print(f"{'='*60}")

        # Generate new translation and mnemonic
        ai_result = await generate_translation_and_mnemonic(word.dutch_word)

        # Try Claude-generated SVG first
        svg_image = await generate_svg_with_claude(
            ai_result.get("visual_description", ""),
            ai_result["spanish"],
            word.dutch_word
        )

        if not svg_image:
            # Fallback to simple SVG
            print(f"⚠️  Using fallback visualization for '{word.dutch_word}'")
            svg_image = generate_svg_visualization(
                ai_result.get("visual_description", ""),
                ai_result["spanish"],
                word.dutch_word
            )
        else:
            # Encode Claude-generated SVG to base64
            import base64
            svg_base64 = base64.b64encode(svg_image.encode()).decode()
            svg_image = f"data:image/svg+xml;base64,{svg_base64}"

        # Update word with new data
        word.spanish_word = ai_result["spanish"]
        word.category = ai_result.get("category", "algemeen")
        word.mnemonic_text = ai_result["mnemonic_text"]
        word.mnemonic_image = svg_image

        # Update conjugations and forms if present
        if "conjugations" in ai_result and ai_result["conjugations"]:
            word.conjugations = json.dumps(ai_result["conjugations"])
        if "forms" in ai_result and ai_result["forms"]:
            word.forms = json.dumps(ai_result["forms"])

        db.commit()
        db.refresh(word)

        print(f"✅ Successfully regenerated '{word.dutch_word}'")
        print(f"{'='*60}\n")

        return word_to_response(word)

    except Exception as e:
        import traceback
        error_detail = f"Regeneratie fout: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"Regeneratie fout: {str(e)}")


class RegenerateAllResponse(BaseModel):
    total_words: int
    regenerated: int
    failed: int
    failed_words: List[str]


@app.post("/api/words/regenerate-all", response_model=RegenerateAllResponse)
@limiter.limit("1/hour")  # Max 1 batch regeneration per hour (very expensive!)
async def regenerate_all_words(request: Request, db: Session = Depends(get_db)):
    """
    Regenerate visualizations for ALL words in the database.
    This will update all words with new mnemonics and visualizations.

    WARNING: This can take a while and use significant API credits!
    Rate limited to 1 word per 2 seconds to avoid API throttling.
    """
    import asyncio

    words = db.query(Word).all()
    total = len(words)
    regenerated = 0
    failed = 0
    failed_words = []

    print(f"\n{'='*60}")
    print(f"🚀 Starting batch regeneration for {total} words")
    print(f"{'='*60}\n")

    for i, word in enumerate(words, 1):
        try:
            print(f"[{i}/{total}] Regenerating '{word.dutch_word}'...")

            # Generate new content
            ai_result = await generate_translation_and_mnemonic(word.dutch_word)

            # Generate SVG
            svg_image = await generate_svg_with_claude(
                ai_result.get("visual_description", ""),
                ai_result["spanish"],
                word.dutch_word
            )

            if not svg_image:
                svg_image = generate_svg_visualization(
                    ai_result.get("visual_description", ""),
                    ai_result["spanish"],
                    word.dutch_word
                )
            else:
                svg_base64 = base64.b64encode(svg_image.encode()).decode()
                svg_image = f"data:image/svg+xml;base64,{svg_base64}"

            # Update word
            word.spanish_word = ai_result["spanish"]
            word.category = ai_result.get("category", "algemeen")
            word.mnemonic_text = ai_result["mnemonic_text"]
            word.mnemonic_image = svg_image

            if "conjugations" in ai_result and ai_result["conjugations"]:
                word.conjugations = json.dumps(ai_result["conjugations"])
            if "forms" in ai_result and ai_result["forms"]:
                word.forms = json.dumps(ai_result["forms"])

            db.commit()
            regenerated += 1
            print(f"✅ Successfully regenerated '{word.dutch_word}'")

            # Rate limiting: 2 second pause between words
            if i < total:
                await asyncio.sleep(2)

        except Exception as e:
            failed += 1
            failed_words.append(word.dutch_word)
            print(f"❌ Failed to regenerate '{word.dutch_word}': {e}")
            continue

    print(f"\n{'='*60}")
    print(f"📊 Batch regeneration complete:")
    print(f"   Total: {total}")
    print(f"   Regenerated: {regenerated}")
    print(f"   Failed: {failed}")
    if failed_words:
        print(f"   Failed words: {', '.join(failed_words)}")
    print(f"{'='*60}\n")

    return RegenerateAllResponse(
        total_words=total,
        regenerated=regenerated,
        failed=failed,
        failed_words=failed_words
    )


@app.get("/api/categories/")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Word.category).distinct().all()
    return [cat[0] for cat in categories]


@app.get("/api/stats/")
def get_stats(db: Session = Depends(get_db)):
    total_words = db.query(Word).count()
    categories = db.query(Word.category).distinct().count()

    return {
        "total_words": total_words,
        "total_categories": categories
    }


@app.get("/api/stats/ai")
def get_ai_stats():
    """
    Get AI usage statistics and cost savings
    
    Returns:
        - Model usage counts (Qwen, Mistral, Claude)
        - Fallback statistics
        - Cost savings estimate
        - Ollama health metrics
    """
    return ai_router.get_stats()


# ============ SPACED REPETITION ENDPOINTS ============

@app.post("/api/reviews/", response_model=WordResponse)
def submit_review(review: ReviewSubmit, db: Session = Depends(get_db)):
    """
    Submit a review for a word and update its scheduling.

    Quality mapping:
    - 0 = Again (complete fail)
    - 3 = Hard (difficult but got it)
    - 4 = Good (normal recall)
    - 5 = Easy (instant recall)
    """
    # Validate quality
    if review.quality not in [0, 3, 4, 5]:
        raise HTTPException(status_code=400, detail="Quality must be 0, 3, 4, or 5")

    # Get the word
    word = db.query(Word).filter(Word.id == review.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    # Store old values for history
    old_interval = word.interval

    # Calculate new scheduling using SM-2
    new_ef, new_interval, new_repetitions, next_review = calculate_sm2_interval(word, review.quality)

    # Easiness hell fix: Reset EF after 10 consecutive successes if still low
    # This prevents words from getting permanently stuck with low EF
    if review.quality >= 3 and new_repetitions >= 10 and new_ef < 2.0:
        print(f"🔧 Easiness hell fix for '{word.dutch_word}': Resetting EF from {new_ef:.2f} to 2.5")
        new_ef = 2.5

    # Update word
    word.review_count += 1
    if review.quality >= 3:
        word.correct_count += 1
    word.easiness_factor = new_ef
    word.interval = new_interval
    word.repetitions = new_repetitions
    word.last_reviewed = datetime.utcnow()
    word.next_review = next_review

    # Create review history entry
    history = ReviewHistory(
        word_id=word.id,
        quality=review.quality,
        interval_before=old_interval,
        interval_after=new_interval,
        easiness_factor_after=new_ef
    )
    db.add(history)

    # Update or create study session for today
    today = date.today()
    session = db.query(StudySession).filter(StudySession.session_date == today).first()
    if session:
        session.cards_reviewed += 1
    else:
        session = StudySession(session_date=today, cards_reviewed=1)
        db.add(session)

    db.commit()
    db.refresh(word)

    return word_to_response(word)


@app.get("/api/stats/reviews", response_model=ReviewStatsResponse)
def get_review_stats(db: Session = Depends(get_db)):
    """Get review statistics: due today, learning, mastered"""
    now = datetime.utcnow()

    # Due today
    due_today = db.query(Word).filter(Word.next_review <= now).count()

    # Learning (interval < 21 days)
    learning = db.query(Word).filter(Word.interval < 21).count()

    # Mastered (interval >= 21 days)
    mastered = db.query(Word).filter(Word.interval >= 21).count()

    # Total reviews today
    today = date.today()
    session = db.query(StudySession).filter(StudySession.session_date == today).first()
    total_reviews_today = session.cards_reviewed if session else 0

    return ReviewStatsResponse(
        due_today=due_today,
        learning=learning,
        mastered=mastered,
        total_reviews_today=total_reviews_today
    )


@app.get("/api/stats/streak", response_model=StreakResponse)
def get_streak(db: Session = Depends(get_db)):
    """Calculate current streak and longest streak"""
    sessions = db.query(StudySession).order_by(StudySession.session_date.desc()).all()

    if not sessions:
        return StreakResponse(current_streak=0, longest_streak=0, last_review_date=None)

    # Current streak
    current_streak = 0
    today = date.today()
    check_date = today

    for session in sessions:
        if session.session_date == check_date:
            current_streak += 1
            check_date -= timedelta(days=1)
        elif session.session_date < check_date:
            # Gap found
            break

    # Longest streak
    longest_streak = 0
    temp_streak = 0
    prev_date = None

    for session in reversed(sessions):
        if prev_date is None or session.session_date == prev_date + timedelta(days=1):
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1
        prev_date = session.session_date

    return StreakResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        last_review_date=sessions[0].session_date if sessions else None
    )


@app.get("/api/stats/heatmap", response_model=List[HeatmapEntry])
def get_heatmap(days: int = 30, db: Session = Depends(get_db)):
    """Get review counts per day for heatmap (last N days)"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    sessions = db.query(StudySession).filter(
        StudySession.session_date >= start_date,
        StudySession.session_date <= end_date
    ).all()

    # Create dict for quick lookup
    session_dict = {s.session_date: s.cards_reviewed for s in sessions}

    # Fill in all dates (including zeros)
    result = []
    current_date = start_date
    while current_date <= end_date:
        result.append(HeatmapEntry(
            date=current_date,
            reviews=session_dict.get(current_date, 0)
        ))
        current_date += timedelta(days=1)

    return result


@app.get("/api/words/{word_id}/history", response_model=List[ReviewHistoryResponse])
def get_word_history(word_id: int, db: Session = Depends(get_db)):
    """Get review history for a specific word"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    history = db.query(ReviewHistory).filter(
        ReviewHistory.word_id == word_id
    ).order_by(ReviewHistory.reviewed_at.desc()).all()

    return history


# ===========================
# LEARNING MODES ENDPOINTS
# ===========================

class ListeningChallengeResponse(BaseModel):
    word_id: int
    audio_data: str  # Base64 encoded audio
    dutch_word: str  # For showing after answer
    category: str

class ListeningAnswerSubmit(BaseModel):
    word_id: int
    user_answer: str

class ListeningAnswerResponse(BaseModel):
    correct: bool
    user_answer: str
    correct_answer: str
    dutch_word: str
    similarity_score: float  # 0-100
    message: str


@app.get("/api/practice/listening", response_model=ListeningChallengeResponse)
def get_listening_challenge(db: Session = Depends(get_db)):
    """
    Get a random word for listening practice.
    Returns audio and word info (but not the Spanish word - user must guess).
    """
    # Get random word from database
    import random
    words = db.query(Word).all()
    if not words:
        raise HTTPException(status_code=404, detail="Geen woorden gevonden")

    word = random.choice(words)

    # Generate audio on-the-fly
    try:
        from gtts import gTTS
        import io

        tts = gTTS(text=word.spanish_word, lang='es', slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        audio_base64 = base64.b64encode(audio_buffer.read()).decode('utf-8')
        audio_data = f"data:audio/mp3;base64,{audio_base64}"

        return ListeningChallengeResponse(
            word_id=word.id,
            audio_data=audio_data,
            dutch_word=word.dutch_word,
            category=word.category
        )

    except Exception as e:
        print(f"❌ Error generating listening challenge: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij genereren audio: {str(e)}")


@app.post("/api/practice/listening/check", response_model=ListeningAnswerResponse)
def check_listening_answer(answer: ListeningAnswerSubmit, db: Session = Depends(get_db)):
    """
    Check user's listening comprehension answer.
    Uses fuzzy matching to allow for minor spelling mistakes.
    """
    word = db.query(Word).filter(Word.id == answer.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Woord niet gevonden")

    # Normalize answers (lowercase, strip whitespace)
    user_answer_clean = answer.user_answer.lower().strip()
    correct_answer_clean = word.spanish_word.lower().strip()

    # Calculate similarity using Levenshtein distance (same as type mode)
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, user_answer_clean, correct_answer_clean).ratio() * 100

    # Determine if correct (>= 80% similarity)
    is_correct = similarity >= 80

    # Generate feedback message
    if similarity >= 95:
        message = "🎉 Perfect! Uitstekend gehoord!"
    elif similarity >= 80:
        message = "✅ Bijna goed! Kleine spelfout, maar je hebt het goed gehoord."
    elif similarity >= 60:
        message = "⚠️ Dichtbij! Probeer nog eens goed te luisteren."
    else:
        message = f"❌ Niet helemaal. Het correcte antwoord is: {word.spanish_word}"

    return ListeningAnswerResponse(
        correct=is_correct,
        user_answer=answer.user_answer,
        correct_answer=word.spanish_word,
        dutch_word=word.dutch_word,
        similarity_score=round(similarity, 1),
        message=message
    )


# =============================================================================
# MULTIPLE CHOICE QUIZ ENDPOINTS
# =============================================================================

class MultipleChoiceQuestion(BaseModel):
    """Multiple choice question with 4 options"""
    word_id: int
    question_type: str  # "dutch_to_spanish" or "spanish_to_dutch"
    question: str  # The word to translate
    options: List[str]  # 4 options including correct answer
    correct_answer: str  # The correct translation
    dutch_word: str  # For showing after answer
    spanish_word: str  # For showing after answer

class MultipleChoiceAnswer(BaseModel):
    """User's answer to a multiple choice question"""
    word_id: int
    selected_answer: str
    correct_answer: str

class MultipleChoiceResult(BaseModel):
    """Result of answering a multiple choice question"""
    correct: bool
    selected_answer: str
    correct_answer: str
    dutch_word: str
    spanish_word: str
    message: str


@app.get("/api/practice/quiz", response_model=MultipleChoiceQuestion)
def get_multiple_choice_question(db: Session = Depends(get_db)):
    """
    Generate a multiple choice question.
    Randomly selects Dutch->Spanish or Spanish->Dutch direction.
    Creates 3 plausible distractors from other words in database.
    """
    import random
    import time

    # Ensure proper randomization by seeding with current time
    random.seed(time.time())

    # Get all words
    all_words = db.query(Word).all()
    if len(all_words) < 4:
        raise HTTPException(
            status_code=400,
            detail="Minimaal 4 woorden nodig voor multiple choice quiz"
        )

    # Pick a random word as the correct answer
    correct_word = random.choice(all_words)

    # Randomly choose question direction (50/50 split)
    question_type = random.choice(["dutch_to_spanish", "spanish_to_dutch"])

    if question_type == "dutch_to_spanish":
        question = correct_word.dutch_word
        correct_answer = correct_word.spanish_word

        # Get 3 random Spanish words as distractors (excluding correct answer)
        other_words = [w for w in all_words if w.id != correct_word.id]
        distractors = random.sample(other_words, min(3, len(other_words)))
        distractor_answers = [w.spanish_word for w in distractors]

    else:  # spanish_to_dutch
        question = correct_word.spanish_word
        correct_answer = correct_word.dutch_word

        # Get 3 random Dutch words as distractors (excluding correct answer)
        other_words = [w for w in all_words if w.id != correct_word.id]
        distractors = random.sample(other_words, min(3, len(other_words)))
        distractor_answers = [w.dutch_word for w in distractors]

    # Combine correct answer with distractors and shuffle
    options = [correct_answer] + distractor_answers
    random.shuffle(options)

    return MultipleChoiceQuestion(
        word_id=correct_word.id,
        question_type=question_type,
        question=question,
        options=options,
        correct_answer=correct_answer,
        dutch_word=correct_word.dutch_word,
        spanish_word=correct_word.spanish_word
    )


@app.post("/api/practice/quiz/check", response_model=MultipleChoiceResult)
def check_multiple_choice_answer(answer: MultipleChoiceAnswer, db: Session = Depends(get_db)):
    """Check user's answer to a multiple choice question and update statistics"""
    word = db.query(Word).filter(Word.id == answer.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Woord niet gevonden")

    is_correct = answer.selected_answer.strip() == answer.correct_answer.strip()

    # Update word statistics (similar to review mode)
    # Map quiz result to quality score (5 for correct, 0 for wrong)
    quality = 5 if is_correct else 0

    # Store interval before update
    interval_before = word.interval

    # Update spaced repetition using existing update_spaced_repetition function
    from datetime import datetime
    word.last_reviewed = datetime.utcnow()
    word.review_count += 1

    if quality >= 3:  # Correct answer
        word.correct_count += 1
        word.repetitions += 1
        word.easiness_factor = max(1.3, word.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

        if word.repetitions == 1:
            word.interval = 1
        elif word.repetitions == 2:
            word.interval = 6
        else:
            word.interval = round(word.interval * word.easiness_factor)
    else:  # Wrong answer
        word.repetitions = 0
        word.interval = 1
        word.easiness_factor = max(1.3, word.easiness_factor - 0.2)

    # Calculate next review date
    from datetime import timedelta
    word.next_review = datetime.utcnow() + timedelta(days=word.interval)

    # Create review history entry
    history_entry = ReviewHistory(
        word_id=word.id,
        reviewed_at=datetime.utcnow(),
        quality=quality,
        interval_before=interval_before,
        interval_after=word.interval,
        easiness_factor_after=word.easiness_factor
    )
    db.add(history_entry)

    # Update study session
    from datetime import date
    today = date.today()
    session = db.query(StudySession).filter(StudySession.session_date == today).first()
    if not session:
        session = StudySession(session_date=today, cards_reviewed=0, session_duration_minutes=0)
        db.add(session)
    session.cards_reviewed += 1

    db.commit()

    if is_correct:
        message = "🎉 Correct! Goed gedaan!"
    else:
        message = f"❌ Helaas, het juiste antwoord is: {answer.correct_answer}"

    return MultipleChoiceResult(
        correct=is_correct,
        selected_answer=answer.selected_answer,
        correct_answer=answer.correct_answer,
        dutch_word=word.dutch_word,
        spanish_word=word.spanish_word,
        message=message
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
