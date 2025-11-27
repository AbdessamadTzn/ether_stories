import json
import math
from pathlib import Path
from groq import Groq
from app.core.config import settings
from app.agents.manager.state import ManagerState

# Load text files
BASE_DIR = Path(__file__).parent
SYSTEM_CONTEXT = (BASE_DIR / "context_manager.txt").read_text(encoding="utf-8")
PROMPT_TEMPLATE = (BASE_DIR / "prompt.txt").read_text(encoding="utf-8")

client = Groq(api_key=settings.GROQ_API_KEY.strip() if settings.GROQ_API_KEY else None)
print(f"DEBUG: GROQ_API_KEY loaded: {settings.GROQ_API_KEY[:4]}...{settings.GROQ_API_KEY[-4:] if settings.GROQ_API_KEY else 'None'}")

def sanitize_text(text: str) -> str:
    if not isinstance(text, str): return str(text)
    # Basic injection protection
    return text.replace("{", "(").replace("}", ")").replace("<", "[").replace(">", "]")

# --- NPUT GUARD ---
def input_guard_node(state: ManagerState) -> ManagerState:
    raw_input = state["user_input"]
    
    # Calculate chapters logic
    duration = int(raw_input.get("duree_minutes", 2))
    nb_chapitres = max(2, min(5, math.ceil(duration / 3)))
    
    # Sanitize everything
    safe_data = {
        "age": str(raw_input.get("age", 5)),
        "nom_enfant": sanitize_text(raw_input.get("nom_enfant", "L'enfant")),
        "interests": sanitize_text(", ".join(raw_input.get("interests", []))),
        "peurs": sanitize_text(", ".join(raw_input.get("peurs", []))),
        "keywords": sanitize_text(raw_input.get("keywords", "")),
        "moral": sanitize_text(raw_input.get("moral", "")),
        "type_histoire": sanitize_text(raw_input.get("type_histoire", "aventure")),
        "personnage": sanitize_text(raw_input.get("personnage", "")),
        "duree_minutes": str(duration),
        "nb_chapitres": str(nb_chapitres)
    }
    
    # Inject into template
    prompt = PROMPT_TEMPLATE
    for key, value in safe_data.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", value)
        
    return {"sanitized_input": safe_data, "prompt_text": prompt}

# --- NODE 2: PLANNER (LLM) ---
def planner_node(state: ManagerState) -> ManagerState:
    print("--- PLANNER NODE ---")
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_CONTEXT},
                {"role": "user", "content": state["prompt_text"]}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
        print(f"LLM Response: {content[:100]}...") # Log first 100 chars
        return {"raw_llm_response": content, "error": None} # Clear previous errors
    except Exception as e:
        print(f"LLM Error: {e}")
        return {"error": f"LLM Call Failed: {str(e)}"}

# --- NODE 3: VALIDATOR ---
def validator_node(state: ManagerState) -> ManagerState:
    print("--- VALIDATOR NODE ---")
    # If previous step failed, pass it through (or handle retry logic in graph)
    if state.get("error"):
        return {"retry_count": state.get("retry_count", 0) + 1}

    raw = state.get("raw_llm_response", "")
    
    # Security check for refusal
    if "content violation" in raw.lower():
        return {"error": "Content violation detected."}
        
    try:
        plan = json.loads(raw)
        
        # Check if LLM returned an error response (content rejected, format violation, etc.)
        if plan.get("error") == True:
            error_type = plan.get("error_type", "UNKNOWN")
            user_message = plan.get("message", "Contenu inapproprié détecté.")
            print(f"LLM rejected content: {error_type}")
            # Return user-friendly message directly
            return {"error": user_message}
        
        # Structural Validation
        required = ["plan", "chapitres", "personnages"]
        if not all(key in plan for key in required):
            raise ValueError("Missing required JSON keys")
            
        if len(plan["chapitres"]) < 1:
            raise ValueError("No chapters generated")
            
        return {"final_plan": plan, "error": None}
        
    except Exception as e:
        current_retries = state.get("retry_count", 0)
        return {"error": f"Validation Failed: {str(e)}", "retry_count": current_retries + 1}