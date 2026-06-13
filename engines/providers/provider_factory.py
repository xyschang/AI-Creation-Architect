import os
from dotenv import load_dotenv

load_dotenv()


def get_ai_provider():
    provider = os.getenv("AI_PROVIDER", "ollama").lower()

    if provider == "claude":
        from engines.providers.claude_provider import ask_model
        return ask_model

    from engines.providers.ollama_provider import ask_model
    return ask_model