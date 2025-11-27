import os
import requests
from pathlib import Path
from app.core.config import settings

API_URL = "https://modelslab.com/api/v7/images/text-to-image"

def generate_image(prompt: str, chapter_num: int) -> str:
    """
    Generates an image for the chapter and saves it.
    Returns the relative path to the image.
    """
    if not settings.STABLE_DIFFUSION_API_KEY:
        print("Warning: No Stable Diffusion API Key. Skipping image generation.")
        return ""

    payload = {
        "prompt": prompt,
        "model_id": "nano-banana-t2i",
        "key": settings.STABLE_DIFFUSION_API_KEY,
        "width": 512,
        "height": 512,
        "samples": 1
    }
    
    try:
        resp = requests.post(API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        image_url = None
        if "output" in data and data["output"]:
            image_url = data["output"][0]
        
        if not image_url:
            return ""
            
        # Download and save
        img_resp = requests.get(image_url, timeout=60)
        img_resp.raise_for_status()
        
        # Save to static/images
        output_dir = Path("app/static/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"chapter_{chapter_num}_{os.urandom(4).hex()}.png"
        file_path = output_dir / filename
        
        with open(file_path, "wb") as f:
            f.write(img_resp.content)
            
        return f"/static/images/{filename}"
        
    except Exception as e:
        print(f"Painter Error: {e}")
        return ""
