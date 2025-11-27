"""
Context Loader Utility for Ether Stories Agents

This module provides secure loading of context files for AI agents.
Context files contain system prompts with security hardening against
prompt injection and social engineering attacks.
"""

from pathlib import Path
from functools import lru_cache


# Base directory for agents
AGENTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=10)
def load_context(agent_name: str) -> str:
    """
    Load context file for a specific agent.
    
    Args:
        agent_name: Name of the agent (manager, moderator, writer, translator)
    
    Returns:
        Content of the context file as string
    
    Raises:
        FileNotFoundError: If context file doesn't exist
    """
    context_paths = {
        "manager": AGENTS_DIR / "manager" / "context_manager.txt",
        "moderator": AGENTS_DIR / "narrative" / "context_moderator.txt",
        "writer": AGENTS_DIR / "narrative" / "context_writer.txt",
        "translator": AGENTS_DIR / "translator" / "context_translator.txt",
    }
    
    if agent_name not in context_paths:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(context_paths.keys())}")
    
    context_path = context_paths[agent_name]
    
    if not context_path.exists():
        raise FileNotFoundError(f"Context file not found: {context_path}")
    
    return context_path.read_text(encoding="utf-8")


def wrap_user_input(user_input: str) -> str:
    """
    Wrap user input in XML tags for input isolation.
    This helps the AI distinguish between instructions and user data.
    
    Args:
        user_input: Raw user input string
    
    Returns:
        Wrapped input with XML tags
    """
    # Escape any existing XML-like tags in user input to prevent injection
    sanitized = user_input.replace("<", "&lt;").replace(">", "&gt;")
    return f"<user_input>\n{sanitized}\n</user_input>"


def wrap_content_for_moderation(content: str, context: dict) -> tuple[str, str]:
    """
    Wrap content and context for moderator agent.
    
    Args:
        content: Text content to moderate
        context: Story context dictionary
    
    Returns:
        Tuple of (wrapped_content, wrapped_context)
    """
    sanitized_content = content.replace("<", "&lt;").replace(">", "&gt;")
    
    # Convert context dict to safe string representation
    context_str = str(context).replace("<", "&lt;").replace(">", "&gt;")
    
    wrapped_content = f"<content_to_verify>\n{sanitized_content}\n</content_to_verify>"
    wrapped_context = f"<story_context>\n{context_str}\n</story_context>"
    
    return wrapped_content, wrapped_context


def wrap_chapter_instructions(instructions: str, context: str) -> tuple[str, str]:
    """
    Wrap chapter instructions for writer agent.
    
    Args:
        instructions: Chapter writing instructions
        context: Story context
    
    Returns:
        Tuple of (wrapped_instructions, wrapped_context)
    """
    sanitized_inst = instructions.replace("<", "&lt;").replace(">", "&gt;")
    sanitized_ctx = context.replace("<", "&lt;").replace(">", "&gt;")
    
    wrapped_inst = f"<chapter_instructions>\n{sanitized_inst}\n</chapter_instructions>"
    wrapped_ctx = f"<story_context>\n{sanitized_ctx}\n</story_context>"
    
    return wrapped_inst, wrapped_ctx


def wrap_translation_input(source_text: str, target_language: str) -> tuple[str, str]:
    """
    Wrap input for translator agent.
    
    Args:
        source_text: Text to translate
        target_language: Target language name
    
    Returns:
        Tuple of (wrapped_source, wrapped_language)
    """
    sanitized_text = source_text.replace("<", "&lt;").replace(">", "&gt;")
    sanitized_lang = target_language.replace("<", "&lt;").replace(">", "&gt;")
    
    wrapped_source = f"<source_text>\n{sanitized_text}\n</source_text>"
    wrapped_lang = f"<target_language>{sanitized_lang}</target_language>"
    
    return wrapped_source, wrapped_lang


# User-friendly error messages (not exposing internal details)
ERROR_MESSAGES = {
    "CONTENT_REJECTED": "Ce thème n'est pas adapté pour une histoire pour enfants. Essayez avec un autre sujet! 🌟",
    "FORMAT_VIOLATION": "Format de demande invalide. Veuillez réessayer.",
    "MODERATION_FAILED": "Nous ne pouvons pas créer cette histoire. Le contenu demandé n'est pas approprié pour les enfants. 🚫",
    "GENERATION_ERROR": "Une erreur s'est produite lors de la création. Veuillez réessayer. 🔄",
    "TRANSLATION_ERROR": "Erreur de traduction. Veuillez réessayer.",
}


def get_user_friendly_error(error_type: str) -> str:
    """
    Get user-friendly error message without exposing internal details.
    
    Args:
        error_type: Internal error type identifier
    
    Returns:
        User-friendly error message in French
    """
    return ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["GENERATION_ERROR"])
