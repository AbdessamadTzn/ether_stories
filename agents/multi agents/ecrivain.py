from groq import Groq
import dotenv
import os
import typing
import time

# Charger les variables d'environnement depuis .env
dotenv.load_dotenv()

_API_KEY = os.environ.get("GROQ_API_KEY")
if not _API_KEY:
  print("[ecrivain] WARNING: GROQ_API_KEY not set in environment (.env?).", flush=True)
client = Groq(api_key=_API_KEY)


def generer_chapitre(prompt: str, temperature: float = 1.0, max_tokens: int = 2048, retries: int = 1) -> str:
    attempt = 0
    while True:
        attempt += 1
        pieces = []
        try:
            print(f"[ecrivain] generer_chapitre start (attempt {attempt})", flush=True)
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=True,
                stop=None,
            )

            for chunk in completion:
                # structure: chunk.choices[0].delta.content when streaming
                try:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", None) or (
                        delta.get("content") if isinstance(delta, dict) else None
                    )
                except Exception:
                    # fallback generic access
                    try:
                        content = chunk.choices[0].delta.content
                    except Exception:
                        content = None

                if content:
                    pieces.append(content)

            result = "".join(pieces).strip()
            print(f"[ecrivain] generer_chapitre finished, {len(result)} chars", flush=True)
            return result

        except Exception as exc:
            print(f"[ecrivain] Exception during generation: {exc}", flush=True)
            if attempt > retries:
                print("[ecrivain] Exhausted retries, raising.", flush=True)
                raise
            print("[ecrivain] Retrying...", flush=True)
            time.sleep(0.5)
            continue


if __name__ == "__main__":
    prompt_ex = (
        "You are a talented writer. Write a short scene where a tired blacksmith meets a mysterious traveler at dusk. "
        "Keep it ~250 words."
    )
    texte = generer_chapitre(prompt_ex, max_tokens=512)
    print(texte)
