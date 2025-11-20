# core/mcp_protocol.py

import uuid
from datetime import datetime

# Types autorisés pour un message MCP
VALID_TYPES = {"request", "response", "error"}


def build_mcp_message(sender: str, receiver: str, payload: dict, type: str = "request"):
    """
    Construit un message MCP structuré.
    """
    if type not in VALID_TYPES:
        raise ValueError(f"Invalid MCP message type: {type}. Allowed: {VALID_TYPES}")

    return {
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "from": sender,
        "to": receiver,
        "type": type,
        "payload": payload,
    }


def validate_mcp_message(message: dict):
    """
    Vérifie la structure minimale d'un message MCP.
    Lève une erreur si un champ obligatoire est manquant.
    """
    required_fields = {"message_id", "timestamp", "from", "to", "type", "payload"}

    missing = required_fields - set(message.keys())
    if missing:
        raise ValueError(f"MCP message missing fields: {missing}")

    if message["type"] not in VALID_TYPES:
        raise ValueError(f"Invalid MCP message type: {message['type']}")

    return True


def is_response(message: dict) -> bool:
    """Retourne True si c'est une réponse."""
    return message.get("type") == "response"


def is_error(message: dict) -> bool:
    """Retourne True si c'est un message d'erreur."""
    return message.get("type") == "error"
