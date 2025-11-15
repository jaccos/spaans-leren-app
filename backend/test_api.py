#!/usr/bin/env python3
import anthropic
import os
from dotenv import load_dotenv
import json

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"✓ API Key gevonden: {bool(api_key)}")
print(f"✓ API Key starts: {api_key[:20]}..." if api_key else "✗ No API key")
print()

try:
    client = anthropic.Anthropic(api_key=api_key)
    print("✓ Client aangemaakt")
    print()
    
    print("Testing API call met simpele prompt...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user", 
            "content": "Vertaal 'meloen' naar Spaans en geef dit in JSON: {\"spanish\": \"...\", \"category\": \"...\", \"mnemonic_text\": \"...\", \"visual_description\": \"...\"}"
        }]
    )
    
    print("✅ API call SUCCESVOL!")
    print()
    print("Response:")
    print(message.content[0].text)
    print()
    
    # Try to parse as JSON
    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()
    
    result = json.loads(response_text)
    print("✅ JSON parsing SUCCESVOL!")
    print(f"   Spanish: {result.get('spanish')}")
    print(f"   Category: {result.get('category')}")
    print(f"   Mnemonic: {result.get('mnemonic_text')}")
    
except anthropic.APIError as e:
    print(f"❌ Anthropic API Error: {e}")
    print(f"   Status: {e.status_code if hasattr(e, 'status_code') else 'unknown'}")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    print()
    print("Traceback:")
    traceback.print_exc()
