from engines.providers.provider_factory import get_ai_provider

ask_model = get_ai_provider()

MODEL_NAME = "qwen3"


def ask_model(prompt):
    answer = ask_model(prompt)