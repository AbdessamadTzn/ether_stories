"""
Interface Streamlit pour la création d'histoires pour enfants
Utilise les agents S2T et Manager
"""
import os
import json
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# Load .env explicitly (ensure this runs before any os.getenv() calls)
dotenv_path = Path(__file__).resolve().parents[1] / ".env"  # ether_stories/.env
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()  # fallback to current working directory

# Configuration de la page
st.set_page_config(
    page_title="🎭 Créateur d'Histoires pour Enfants",
    page_icon="📚",
    layout="wide"
)

# Import des agents (after loading env)
try:
    from agents.speech_to_text.seepch_to_text import s2t_agent
    from agents.manager.manager import manager_agent
    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
    st.error(f"❌ Erreur d'import des agents: {e}")

# Titre principal
st.title("🎭 Créateur d'Histoires pour Enfants")
st.markdown("### 🎤 Enregistre ta voix ou décris ton histoire, et laisse la magie opérer !")

# Vérification de la clé API
if not os.getenv("GROQ_API_KEY"):
    st.error("⚠️ GROQ_API_KEY non trouvée dans les variables d'environnement!")
    st.info("Ajoute ta clé dans un fichier .env : `GROQ_API_KEY=ta_clé_ici`")
    st.stop()

# Sidebar - Paramètres de l'enfant
st.sidebar.header("👤 Profil de l'enfant")

nom_enfant = st.sidebar.text_input("Prénom de l'enfant", "")
age = st.sidebar.slider("Âge", 3, 12, 7)

st.sidebar.subheader("🎨 Centres d'intérêt")
interests_input = st.sidebar.text_area(
    "Liste les centres d'intérêt (un par ligne)",
    "dragons\nmagie\naventure"
)
interests = [i.strip() for i in interests_input.split("\n") if i.strip()]

st.sidebar.subheader("😰 Peurs à éviter")
peurs_input = st.sidebar.text_area(
    "Liste les peurs (un par ligne)",
    "noir\nmonstres"
)
peurs = [p.strip() for p in peurs_input.split("\n") if p.strip()]

# Sidebar - Paramètres de l'histoire
st.sidebar.header("📖 Paramètres de l'histoire")

type_histoire = st.sidebar.selectbox(
    "Type d'histoire",
    ["aventure", "fantaisie", "conte", "science-fiction", "mystère", "comédie"]
)

duree_minutes = st.sidebar.slider("Durée (minutes)", 5, 30, 10, step=5)

moral = st.sidebar.text_input(
    "Morale souhaitée",
    "courage et amitié"
)

personnage = st.sidebar.text_input(
    "Personnage principal (optionnel)",
    ""
)

# Zone principale - Deux onglets
tab1, tab2 = st.tabs(["🎤 Depuis Audio", "✍️ Depuis Texte"])

# ==================== TAB 1: AUDIO ====================
with tab1:
    st.header("🎤 Crée une histoire depuis un enregistrement audio")
    
    # Upload audio
    audio_file = st.file_uploader(
        "📁 Télécharge un fichier audio (MP3, WAV, M4A...)",
        type=["mp3", "wav", "m4a", "ogg", "flac"]
    )
    
    if audio_file:
        st.audio(audio_file, format=f"audio/{audio_file.name.split('.')[-1]}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            transcribe_only = st.button("🎤 Transcrire uniquement", use_container_width=True)
        
        with col2:
            create_story = st.button("📖 Créer l'histoire complète", use_container_width=True, type="primary")
        
        # Transcription seule
        if transcribe_only and AGENTS_AVAILABLE:
            with st.spinner("🎤 Transcription en cours..."):
                try:
                    result = s2t_agent.transcribe_audio(audio_file)
                    
                    if result["success"]:
                        st.success("✅ Transcription réussie !")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.subheader("📝 Transcription brute")
                            st.write(result["transcription_raw"])
                        
                        with col_b:
                            st.subheader("🔑 Mots-clés extraits")
                            st.write(result["keywords"])
                        
                        st.info(f"🎯 Confiance: {result['confidence']}")
                    else:
                        st.error(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de la transcription: {str(e)}")
        
        # Création histoire complète
        if create_story and AGENTS_AVAILABLE:
            with st.spinner("🎭 Création de l'histoire en cours... Cela peut prendre quelques secondes..."):
                try:
                    result = s2t_agent.transcribe_and_create_story(
                        audio_file=audio_file,
                        age=age,
                        interests=interests,
                        peurs=peurs,
                        moral=moral,
                        type_histoire=type_histoire,
                        duree_minutes=duree_minutes,
                        personnage=personnage,
                        nom_enfant=nom_enfant if nom_enfant else None
                    )
                    
                    if result["success"]:
                        st.success("✅ Histoire créée avec succès ! 🎉")
                        
                        # Affichage transcription
                        with st.expander("🎤 Voir la transcription"):
                            st.write(f"**Transcription:** {result['transcription']['transcription_raw']}")
                            st.write(f"**Mots-clés:** {result['transcription']['keywords']}")
                            st.write(f"**Confiance:** {result['transcription']['confidence']}")
                        
                        # Le plan est maintenant directement dans result["story_plan"]
                        plan = result["story_plan"]
                        
                        st.markdown("---")
                        st.header(f"📚 {plan['plan']['titre']}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("🎯 Type", plan['plan']['type_histoire'])
                        with col2:
                            st.metric("⏱️ Durée", f"{plan['plan']['duree_estimee']} min")
                        with col3:
                            st.metric("👶 Âge cible", f"{plan['plan']['age_cible']} ans")
                        
                        st.subheader("🎭 Personnage principal")
                        st.write(plan['plan']['personnage_principal'])
                        
                        st.subheader("📖 Chapitres")
                        for chapitre in plan['chapitres']:
                            with st.expander(f"Chapitre {chapitre['numero']}: {chapitre['titre']} ({chapitre['duree_minutes']} min)"):
                                st.write(chapitre['resume'])
                        
                        st.subheader("💡 Morale")
                        st.info(f"**Valeur:** {plan['morale']['valeur_principale']}")
                        st.write(f"**Message:** {plan['morale']['message']}")
                        st.write(f"**Intégration:** {plan['morale']['integration']}")
                        
                        st.subheader("👥 Personnages")
                        for perso in plan['personnages']:
                            st.markdown(f"**{perso['nom']}** ({perso['role']})")
                            st.write(perso['description'])
                        
                        # Téléchargement JSON
                        st.download_button(
                            label="📥 Télécharger le plan (JSON)",
                            data=json.dumps(plan, ensure_ascii=False, indent=2),
                            file_name=f"plan_histoire_{plan['plan']['titre'].replace(' ', '_')}.json",
                            mime="application/json"
                        )
                    
                    else:
                        st.error(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de la création: {str(e)}")
                    st.exception(e)

# ==================== TAB 2: TEXTE ====================
with tab2:
    st.header("✍️ Crée une histoire depuis des mots-clés textuels")
    
    keywords_input = st.text_area(
        "🔑 Entre tes mots-clés (séparés par des virgules)",
        "dragon, princesse, château magique, épée enchantée",
        height=100
    )
    
    if st.button("📖 Créer l'histoire", use_container_width=True, type="primary"):
        if not keywords_input.strip():
            st.warning("⚠️ Merci d'entrer des mots-clés !")
        elif AGENTS_AVAILABLE:
            with st.spinner("🎭 Création de l'histoire en cours..."):
                try:
                    # create_story_plan retourne maintenant directement le plan
                    plan = manager_agent.create_story_plan(
                        age=age,
                        interests=interests,
                        peurs=peurs,
                        keywords=keywords_input,
                        moral=moral,
                        type_histoire=type_histoire,
                        duree_minutes=duree_minutes,
                        personnage=personnage,
                        nom_enfant=nom_enfant if nom_enfant else None
                    )
                    
                    st.success("✅ Histoire créée avec succès ! 🎉")
                    
                    st.markdown("---")
                    st.header(f"📚 {plan['plan']['titre']}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🎯 Type", plan['plan']['type_histoire'])
                    with col2:
                        st.metric("⏱️ Durée", f"{plan['plan']['duree_estimee']} min")
                    with col3:
                        st.metric("👶 Âge cible", f"{plan['plan']['age_cible']} ans")
                    
                    st.subheader("🎭 Personnage principal")
                    st.write(plan['plan']['personnage_principal'])
                    
                    st.subheader("📖 Chapitres")
                    for chapitre in plan['chapitres']:
                        with st.expander(f"Chapitre {chapitre['numero']}: {chapitre['titre']} ({chapitre['duree_minutes']} min)"):
                            st.write(chapitre['resume'])
                    
                    st.subheader("💡 Morale")
                    st.info(f"**Valeur:** {plan['morale']['valeur_principale']}")
                    st.write(f"**Message:** {plan['morale']['message']}")
                    st.write(f"**Intégration:** {plan['morale']['integration']}")
                    
                    st.subheader("👥 Personnages")
                    for perso in plan['personnages']:
                        st.markdown(f"**{perso['nom']}** ({perso['role']})")
                        st.write(perso['description'])
                    
                    # Téléchargement JSON
                    st.download_button(
                        label="📥 Télécharger le plan (JSON)",
                        data=json.dumps(plan, ensure_ascii=False, indent=2),
                        file_name=f"plan_histoire_{plan['plan']['titre'].replace(' ', '_')}.json",
                        mime="application/json"
                    )
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de la création: {str(e)}")
                    st.exception(e)

# Footer
st.markdown("---")
st.markdown("🎨 **Créateur d'Histoires pour Enfants** - Propulsé par Groq & Whisper")