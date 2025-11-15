"""
AI Router - Hybride systeem met Ollama (lokaal) + Claude API (strategisch)

Models:
- Qwen 2.5 14B: Nederlands-Spaans vertaling, grammatica, voorbeelden (70% queries)
- Mistral 7B: Creatieve mnemonics, SVG visualisaties (15% queries)
- Claude Sonnet 4.5: Fine-tuning, validation, complexe cases (15% queries)
"""

import httpx
import anthropic
import json
import os
from typing import Literal, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ModelType(Enum):
    """Available AI models"""
    QWEN = "qwen2.5:14b"
    MISTRAL = "mistral:7b-instruct"
    CLAUDE = "claude-sonnet-4-20250514"


class AIRouter:
    """
    Smart routing between local Ollama models and Claude API
    """
    
    def __init__(self):
        # Support both local and Docker environments
        ollama_host = os.getenv("OLLAMA_HOST", "localhost:11434")
        self.ollama_url = f"http://{ollama_host}/api/generate"
        self.claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        print(f"🔧 AI Router initialized with Ollama: {self.ollama_url}")
        
        # Statistics tracking
        self.stats = {
            "qwen_calls": 0,
            "mistral_calls": 0,
            "claude_calls": 0,
            "qwen_fallbacks": 0,
            "mistral_fallbacks": 0,
            "total_ollama_errors": 0
        }
    
    async def call_ollama(self, model: str, prompt: str, temperature: float = 0.7) -> str:
        """
        Generic Ollama API call with timeout and error handling
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "top_p": 0.9,
                            "num_predict": 1000
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama HTTP {response.status_code}: {response.text}")
                
                result = response.json()
                return result.get("response", "").strip()
                
        except httpx.TimeoutException:
            raise Exception(f"Ollama timeout voor model {model}")
        except httpx.ConnectError:
            raise Exception("Kan geen verbinding maken met Ollama (is het gestart?)")
        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}")
    
    async def call_qwen(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call Qwen 2.5 14B for translation and grammar tasks
        Fallback to Claude on error
        """
        self.stats["qwen_calls"] += 1
        try:
            print(f"🔄 Calling Qwen for translation/grammar...")
            result = await self.call_ollama(ModelType.QWEN.value, prompt, temperature)
            print(f"✅ Qwen response received ({len(result)} chars)")
            return result
        except Exception as e:
            print(f"⚠️ Qwen error: {e}")
            print(f"🔄 Falling back to Claude...")
            self.stats["qwen_fallbacks"] += 1
            self.stats["total_ollama_errors"] += 1
            return await self.call_claude(prompt, temperature)
    
    async def call_mistral(self, prompt: str, temperature: float = 0.8) -> str:
        """
        Call Mistral 7B for creative content (mnemonics, stories)
        Fallback to Claude on error
        """
        self.stats["mistral_calls"] += 1
        try:
            print(f"🎨 Calling Mistral for creative content...")
            result = await self.call_ollama(ModelType.MISTRAL.value, prompt, temperature)
            print(f"✅ Mistral response received ({len(result)} chars)")
            return result
        except Exception as e:
            print(f"⚠️ Mistral error: {e}")
            print(f"🔄 Falling back to Claude...")
            self.stats["mistral_fallbacks"] += 1
            self.stats["total_ollama_errors"] += 1
            return await self.call_claude(prompt, temperature)
    
    async def call_claude(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call Claude API for complex tasks or fallback
        """
        self.stats["claude_calls"] += 1
        print(f"☁️ Calling Claude API...")
        
        try:
            message = self.claude_client.messages.create(
                model=ModelType.CLAUDE.value,
                max_tokens=1000,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            result = message.content[0].text.strip()
            print(f"✅ Claude response received ({len(result)} chars)")
            return result
        except Exception as e:
            print(f"❌ Claude API error: {e}")
            raise Exception(f"Claude API failed: {str(e)}")
    
    async def translate_with_grammar(self, dutch_word: str, use_claude: bool = False) -> Dict[str, Any]:
        """
        Translate Dutch to Spanish with grammar info
        Uses Qwen by default, Claude if requested or on fallback
        
        Returns dict with: spanish, category, conjugations, forms, explanation
        """
        prompt = f"""Vertaal het Nederlandse woord '{dutch_word}' naar Spaans.

TAAK:
- Vertaal naar Spaans (met lidwoord el/la waar nodig)
- Bepaal de categorie
- Geef grammatica info (vervoegingen voor werkwoorden, enkelvoud/meervoud voor zelfstandige naamwoorden)
- Korte uitleg in Nederlands

CATEGORIEËN:
werkwoord, zelfstandig_naamwoord, bijvoeglijk_naamwoord, eten_drinken, reizen, familie, werk, algemeen

Geef antwoord in EXACT dit JSON formaat (geen extra tekst, geen markdown):
{{
  "spanish": "spaans woord (met el/la als nodig)",
  "category": "categorie",
  "explanation": "korte uitleg in Nederlands (1 zin)",
  "conjugations": {{"yo": "...", "tú": "...", "él/ella": "...", "nosotros": "...", "vosotros": "...", "ellos/ellas": "..."}} (alleen voor werkwoorden, anders null),
  "forms": {{"singular": "el/la woord", "plural": "los/las woorden"}} (voor zelfstandig naamwoord) of {{"masculine": "...", "feminine": "..."}} (voor bijvoeglijk naamwoord) of null
}}"""

        if use_claude:
            response = await self.call_claude(prompt, temperature=0.5)
        else:
            response = await self.call_qwen(prompt, temperature=0.5)
        
        # Parse JSON response
        return self._parse_json_response(response)
    
    async def generate_mnemonic(self, spanish_word: str, dutch_word: str, 
                               use_claude: bool = False) -> Dict[str, str]:
        """
        Generate creative mnemonic using Mistral (or Claude fallback)
        
        Returns dict with: mnemonic_text, visual_description
        """
        prompt = f"""Maak een VISUELE GEHEUGENSTEUN (mnemonic) voor:
Spaans: {spanish_word}
Nederlands: {dutch_word}

REGELS:
1. Associatie tussen SPAANS woord en iets Nederlands/bekend
2. CONCREET en VISUEEL met ACTIE
3. Gebruik woordspelingen of klanken
4. Als het woord MEERDERE betekenissen heeft, vermeld dit kort

VISUELE BESCHRIJVING - BELANGRIJK:
Gebruik het SCENE|ELEMENTEN|KLEUREN|ACTIE formaat voor SVG illustratie!

VOORBEELD FORMAAT:
"SCENE: [hoofdscene met posities] | ELEMENTEN: [lijst alle elementen met vorm-hints, gescheiden door ;] | KLEUREN: [kleuren per element] | ACTIE: [wat gebeurt, inclusief spraak]"

VOORBEELD:
Voor "el huevo" (ei):
"SCENE: Een wit ei in het midden van een bruin nest | ELEMENTEN: groot wit ei (ovaal) met gezicht; bruin nest (ovaal met stokjes); 3 kleinere eieren rondom; speech bubble rechtsboven met 'HOEVEEL!' | KLEUREN: hoofdei=wit met goud, nest=bruin, andere eieren=gebroken wit, bubble=wit met rood | ACTIE: Hoofdei roept 'HOEVEEL!' naar andere eieren"

Geef antwoord in EXACT dit JSON formaat:
{{
  "mnemonic_text": "korte geheugensteun uitleg (1-2 zinnen, max 65 karakters per regel)",
  "visual_description": "SCENE|ELEMENTEN|KLEUREN|ACTIE formaat zoals voorbeeld"
}}"""

        if use_claude:
            response = await self.call_claude(prompt, temperature=0.8)
        else:
            response = await self.call_mistral(prompt, temperature=0.8)
        
        # Parse JSON response
        return self._parse_json_response(response)
    
    async def claude_validate(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Claude to validate Ollama-generated content
        
        Returns: {is_valid: bool, score: int, issues: list, suggestions: list}
        """
        content_str = json.dumps(content, indent=2, ensure_ascii=False)
        
        prompt = f"""Valideer deze AI-gegenereerde vertaling en mnemonic:

{content_str}

Controleer:
1. Correctheid vertaling Nederlands→Spaans
2. Kwaliteit van de mnemonic (is het memorabel?)
3. Grammatica informatie (juist en compleet?)

Geef antwoord in dit JSON formaat:
{{
  "is_valid": true/false,
  "score": 0-10,
  "issues": ["lijst van problemen"],
  "suggestions": ["verbetervoorstellen"]
}}"""

        response = await self.call_claude(prompt, temperature=0.3)
        return self._parse_json_response(response)
    
    async def claude_refine(self, content: str, instruction: str) -> str:
        """
        Use Claude to refine/improve Ollama output
        """
        prompt = f"""Instructie: {instruction}

Te verbeteren content:
{content}

Verbeterde versie:"""
        
        return await self.call_claude(prompt, temperature=0.7)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks
        """
        # Remove markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            print(f"Response was: {response[:200]}...")
            raise Exception(f"Kon geen JSON parsen uit response: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Return usage statistics and cost savings estimate
        """
        total_calls = sum([
            self.stats["qwen_calls"],
            self.stats["mistral_calls"],
            self.stats["claude_calls"]
        ])
        
        # Claude pricing estimate (input ~500 tokens, output ~200 tokens per call)
        claude_cost_per_call = (0.5 * 0.003) + (0.2 * 0.015)  # $0.0045 per call
        
        actual_cost = self.stats["claude_calls"] * claude_cost_per_call
        all_claude_cost = total_calls * claude_cost_per_call
        savings = all_claude_cost - actual_cost
        
        return {
            **self.stats,
            "total_calls": total_calls,
            "claude_percentage": round((self.stats["claude_calls"] / total_calls * 100), 1) if total_calls > 0 else 0,
            "cost_savings": {
                "actual_cost_usd": round(actual_cost, 4),
                "all_claude_cost_usd": round(all_claude_cost, 4),
                "savings_usd": round(savings, 4),
                "savings_percentage": round((savings / all_claude_cost * 100), 1) if all_claude_cost > 0 else 0
            },
            "ollama_health": {
                "total_errors": self.stats["total_ollama_errors"],
                "qwen_fallback_rate": round((self.stats["qwen_fallbacks"] / self.stats["qwen_calls"] * 100), 1) if self.stats["qwen_calls"] > 0 else 0,
                "mistral_fallback_rate": round((self.stats["mistral_fallbacks"] / self.stats["mistral_calls"] * 100), 1) if self.stats["mistral_calls"] > 0 else 0
            }
        }


# Global singleton instance
ai_router = AIRouter()
