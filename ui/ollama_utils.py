"""
Utility functions for interacting with Ollama.

Provides functions to detect available models and check Ollama status.
"""

from ollama import Client


def get_available_models() -> list[str]:
    """Get list of available Ollama models.

    Returns:
        List of model names (e.g., ["llama3:latest", "deepseek-r1:8b"]).
        Returns empty list if Ollama is not running.
    """
    try:
        client = Client()
        response = client.list()
        return [m.model for m in response.models] if response.models else []
    except Exception:
        return []


def is_ollama_running() -> bool:
    """Check if Ollama service is available.

    Returns:
        True if Ollama is running and responding, False otherwise.
    """
    try:
        client = Client()
        client.list()
        return True
    except Exception:
        return False
