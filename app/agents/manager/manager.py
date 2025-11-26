"""
Agent Manager
Orchestre la création du plan d'histoire complet
"""
import json
from typing import List, Optional, Dict, Any
from manager import get_system_prompt, get_user_prompt

class ManagerAgent:
    """
    Agent Manager - Chef d'orchestre
    
    INPUT: {
        "age": int,
        "interests": [str],
        "peurs": [str],
        "keywords": str,
        "moral": str,
        "type_histoire": str,
        "duree_minutes": int,
        "personnage": str
    }
    
    OUTPUT: {
        "plan": {...},
        "chapitres": [...],
        "morale": {...},
        "personnages": [...],
        "elements_cles": {...}
    }
    """
    
    def __init__(self):
        self.name = "Agent Manager"
        self.model = GroqConfig.get_model("manager")
        self.params = GroqConfig.get_params("manager")
        self.client = GroqConfig.get_client()
        
        print(f"✅ {self.name} initialisé")
        print(f"   Modèle: {self.model}")
    
    def create_story_plan(
        self,
        age: int,
        interests: List[str],
        peurs: List[str],
        keywords: str,
        moral: str,
        type_histoire: str,
        duree_minutes: int,
        personnage: str,
        nom_enfant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Créer le plan complet de l'histoire
        
        Args:
            age: Âge de l'enfant (3-12)
            interests: Centres d'intérêt
            peurs: Peurs à éviter
            keywords: Mots-clés pour l'histoire
            moral: Morale souhaitée
            type_histoire: Type (aventure, conte, fantaisie, etc.)
            duree_minutes: Durée totale en minutes
            personnage: Personnage principal souhaité
            nom_enfant: Prénom de l'enfant (optionnel)
        
        Returns:
            Dict contenant le plan complet
        """
        
        print(f"\n{'='*70}")
        print(f"🧠 {self.name} - Création du plan d'histoire")
        print(f"{'='*70}")
        print(f"👤 Enfant: {nom_enfant or 'Anonyme'}, {age} ans")
        print(f"⭐ Intérêts: {', '.join(interests)}")
        print(f"😰 Peurs à éviter: {', '.join(peurs) if peurs else 'Aucune'}")
        print(f"📝 Mots-clés: {keywords}")
        print(f"💭 Morale: {moral}")
        print(f"📚 Type: {type_histoire}")
        print(f"⏱️  Durée: {duree_minutes} minutes")
        print(f"🎭 Personnage: {personnage}")
        
        # Construire les prompts
        system_prompt = get_system_prompt()
        user_prompt = get_user_prompt(
            age=age,
            interests=interests,
            peurs=peurs,
            keywords=keywords,
            moral=moral,
            type_histoire=type_histoire,
            duree_minutes=duree_minutes,
            personnage=personnage
        )
        
        try:
            print(f"\n🤖 Appel Groq ({self.model})...")
            
            # Appel à Groq avec JSON mode
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=self.params["temperature"],
                max_tokens=self.params["max_tokens"],
            )
            
            # Parser la réponse
            content = response.choices[0].message.content
            plan_data = json.loads(content)
            
            print("\n📩 Réponse brute du modèle :")
            print(content)
            # Validation basique
            self._validate_plan(plan_data)
            
            print(f"\n✅ {self.name} - Plan créé avec succès !")
            print(f"{'='*70}")
            print(f"📖 Titre: {plan_data['plan']['titre']}")
            print(f"📚 Chapitres: {len(plan_data['chapitres'])}")
            print(f"👥 Personnages: {len(plan_data['personnages'])}")
            print(f"💭 Morale: {plan_data['morale']['valeur_principale']}")
            print(f"{'='*70}\n")
            
            return plan_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Erreur de parsing JSON: {str(e)}"
            print(f"\n❌ {error_msg}")
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Erreur lors de la création du plan: {str(e)}"
            print(f"\n❌ {error_msg}")
            raise Exception(error_msg)
    
    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Valider que le plan généré est complet
        
        Args:
            plan: Dictionnaire du plan
        
        Returns:
            True si valide
        
        Raises:
            ValueError si invalide
        """
        required_keys = ["plan", "chapitres", "morale", "personnages", "elements_cles"]
        
        for key in required_keys:
            if key not in plan:
                raise ValueError(f"Clé manquante dans le plan: {key}")
        
        # Vérifier les sous-structures
        if "titre" not in plan["plan"]:
            raise ValueError("Titre manquant dans le plan")
        
        if len(plan["chapitres"]) == 0:
            raise ValueError("Aucun chapitre généré")
        
        if len(plan["personnages"]) == 0:
            raise ValueError("Aucun personnage défini")
        
        # Vérifier chaque chapitre
        for i, chapitre in enumerate(plan["chapitres"]):
            required_chapter_keys = ["numero", "titre", "resume", "duree_minutes"]
            for key in required_chapter_keys:
                if key not in chapitre:
                    raise ValueError(f"Clé manquante dans chapitre {i+1}: {key}")
        
        print("✅ Plan validé avec succès")
        return True
    
    def create_plan_from_json(self, input_json: str) -> str:
        """
        Créer un plan à partir d'un JSON string
        
        Args:
            input_json: JSON string avec tous les paramètres
        
        Returns:
            JSON string du plan créé
        """
        try:
            data = json.loads(input_json)
            
            plan = self.create_story_plan(
                age=data.get("age"),
                interests=data.get("interests", []),
                peurs=data.get("peurs", []),
                keywords=data.get("keywords", ""),
                moral=data.get("moral", ""),
                type_histoire=data.get("type_histoire", "aventure"),
                duree_minutes=data.get("duree_minutes", 10),
                personnage=data.get("personnage", ""),
                nom_enfant=data.get("nom_enfant")
            )
            
            return json.dumps(plan, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)

# Instance globale
manager_agent = ManagerAgent()