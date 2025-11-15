# Spaans Leren - Backend

FastAPI backend met AI-powered vertaling en geheugensteun generatie.

## Setup

1. **Installeer dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Maak .env bestand:**
   ```bash
   cp .env.example .env
   ```
   
   Vul je Anthropic API key in:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

3. **Start de server:**
   ```bash
   python main.py
   ```
   
   Of met uvicorn:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## API Endpoints

- `POST /api/words/` - Voeg Nederlands woord toe (AI genereert Spaans + mnemonic)
- `GET /api/words/` - Haal alle woorden op (met filters)
- `GET /api/words/{id}` - Haal specifiek woord op
- `DELETE /api/words/{id}` - Verwijder woord
- `GET /api/categories/` - Haal categorieën op
- `GET /api/stats/` - Statistieken

## Wat doet de AI?

1. Vertaalt Nederlands → Spaans
2. Bedenkt een creatieve geheugensteun (mnemonic)
3. Genereert een visuele beschrijving
4. Maakt een SVG afbeelding

## Database

SQLite database (`spaans_leren.db`) wordt automatisch aangemaakt.
