# --------------------------------------------------------------
# dessinateur.py
# Génération d’image via l’API Modelslab (text‑to‑image)
# --------------------------------------------------------------

import os
import json
import base64
import io
from pathlib import Path
from PIL import Image
import requests
from dotenv import load_dotenv
# --------------------------------------------------------------
# Chargement des variables d’environnement (facultatif)
# --------------------------------------------------------------
# Si tu mets ton API‑key dans un fichier .env à la racine du projet,
# ajoute la ligne suivante dans .env :
#   MODEL_SLAB_KEY=ta_clef_api
load_dotenv()
API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")
# sinon utilise la clé en dur ci‑dessous

# ------------------------------------------------------------------
# Configuration de l’API
# ------------------------------------------------------------------
API_URL = "https://modelslab.com/api/v7/images/text-to-image"
HEADERS = {"Content-Type": "application/json"}

# --------------------------------------------------------------
# Fonction principale : génération d’image
# --------------------------------------------------------------
def generer_image(
    prompt: str,
    output_path: Path,
    model_id: str = "nano-banana-t2i",
    seed: int = 42,
) -> Path:
    """
    Envoie le prompt à Modelslab, récupère l’image (via URL) et la sauvegarde.

    Args:
        prompt: texte décrivant l’image à créer.
        output_path: chemin complet où écrire le PNG.
        model_id: identifiant du modèle (par défaut nano‑banana‑t2i).
        seed: graine aléatoire (facultatif, pour rendre le résultat reproductible).

    Returns:
        Le même `Path` passé en argument (convenance).
    """
    payload = {
        "prompt": prompt,
        "model_id": model_id,
        "key": API_KEY,
        "seed": seed,
    }

    # ------------------- appel API -------------------
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Erreur lors de l’appel API : {exc}") from exc

    # ------------------- décodage JSON -------------------
    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("Réponse non‑JSON reçue de l’API") from exc

    # L’API renvoie un tableau `output` contenant l’URL de l’image.
    # Si `output` n’existe pas, on regarde `proxy_links` (c’est le même lien).
    image_url = None
    if isinstance(data, dict):
        if "output" in data and isinstance(data["output"], list) and data["output"]:
            image_url = data["output"][0]
        elif "proxy_links" in data and isinstance(data["proxy_links"], list) and data["proxy_links"]:
            image_url = data["proxy_links"][0]

    if not image_url:
        raise RuntimeError(
            f"Réponse inattendue : {json.dumps(data, indent=2)}"
        )

    # ------------------- téléchargement de l’image -------------------
    try:
        img_resp = requests.get(image_url, timeout=60)
        img_resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Impossible de télécharger l’image depuis {image_url}: {exc}") from exc

    # ------------------- sauvegarde -------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_resp.content)

    print(f"✅ Image générée → {output_path.resolve()}")
    return output_path


# --------------------------------------------------------------
# Exemple d’utilisation (exécuté uniquement si le script est lancé directement)
# --------------------------------------------------------------
if __name__ == "__main__":
    # Prompt d’exemple – à remplacer par le texte que tu veux réellement.
    exemple_prompt = (
        "genere moi un dalmassien avec des grains de beauté et des lunettes rondes ."

    )

    # Chemin de sortie (dans le même dossier que ce script)
    sortie = Path(__file__).parent / "output.png"

    try:
        chemin_image = generer_image(
            prompt=exemple_prompt,
            output_path=sortie,
            model_id="nano-banana-t2i",
            seed=123,          # change la graine si tu veux une variante
        )
        # Affichage rapide (facultatif)
        Image.open(chemin_image).show()
    except Exception as e:
        print(f"❌ Échec de la génération : {e}")