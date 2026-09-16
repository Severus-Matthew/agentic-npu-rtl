"""Explicit model choices shared by the CLI, UI and API smoke check."""
MODELS = {
    'gpt-5.3-codex': 'GPT-5.3 Codex',
    'gpt-5.6-sol': 'GPT-5.6 Sol',
    'gpt-6-astra': 'GPT-6 Astra',
}
DEFAULT_MODEL = 'gpt-5.3-codex'


def validate_model(model):
    if model not in MODELS:
        raise ValueError(f'Choose one of: {", ".join(MODELS)}')
    return model
