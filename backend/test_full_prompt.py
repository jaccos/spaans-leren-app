#!/usr/bin/env python3
import anthropic
import os
from dotenv import load_dotenv
import json

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print("Testing met EXACTE backend prompt...\n")

dutch_word = "meloen"

client = anthropic.Anthropic(api_key=api_key)

prompt = f"""Je helpt een Nederlandse persoon (Jacco) Spaans te leren.

TAAK:
Vertaal het Nederlandse woord "{dutch_word}" naar Spaans en bedenk een VISUELE GEHEUGENSTEUN (mnemonic).

BELANGRIJKE REGELS voor de geheugensteun:
1. Maak een associatie tussen het SPAANSE woord en iets dat Nederlands/bekend klinkt
2. De visualisatie moet helpen het SPAANSE woord te onthouden
3. Gebruik woordspelingen, klanken, of grappige associaties
4. Maak het CONCREET en VISUEEL voorstelbaar

VOORBEELDEN van goede mnemonics:
- "la casa" (huis) → "Stel je een huis voor met een grote KASSA ervoor"
- "el perro" (hond) → "Een hond die PERROT (papegaai) achterna zit"
- "comer" (eten) → "Je KOMT ER aan om te eten"

CATEGORIEËN (kies de beste match):
- werkwoord: voor werkwoorden (lopen, eten, slapen)
- zelfstandig_naamwoord: voor zelfstandige naamwoorden (huis, kat, tafel)
- bijvoeglijk_naamwoord: voor bijvoeglijke naamwoorden (groot, mooi, snel)
- eten_drinken: voor eten en drinken (brood, wijn, appel)
- reizen: voor reizen (vliegtuig, hotel, strand)
- familie: voor familie (vader, moeder, kind)
- werk: voor werk (computer, vergadering, contract)
- algemeen: voor alles wat niet in bovenstaande past

Geef je antwoord in dit EXACTE JSON formaat (geen extra tekst):
{{
  "spanish": "het spaanse woord (met lidwoord)",
  "category": "de beste categorie uit de lijst hierboven",
  "mnemonic_text": "De geheugensteun uitleg in 1-2 zinnen",
  "visual_description": "Beschrijf in detail wat je zou ZIEN in een tekening"
}}"""

try:
    print(f"Woord: {dutch_word}\n")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    print("✅ API Response:")
    response_text = message.content[0].text.strip()
    print(response_text)
    print()
    
    # Parse JSON
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()
    
    result = json.loads(response_text)
    print("✅ Parsed result:")
    print(f"   Spanish: {result['spanish']}")
    print(f"   Category: {result['category']}")
    print(f"   Mnemonic: {result['mnemonic_text']}")
    print(f"   Visual: {result['visual_description'][:80]}...")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
