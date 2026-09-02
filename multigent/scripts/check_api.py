"""Check that the configured university/OpenAI-compatible API is reachable.

Run from the repository root:

    python -m multigent.scripts.check_api

Optional:

    python -m multigent.scripts.check_api --list-models
"""

from __future__ import annotations

import argparse
import os

from openai import OpenAI, OpenAIError


def build_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set your key."
        )

    kwargs = {"api_key": api_key, "timeout": 60.0}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url.rstrip("/") + "/"
    return OpenAI(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the configured agent API")
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Also ask the provider for its visible model IDs when supported",
    )
    args = parser.parse_args()

    model = os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex")
    mode = os.getenv("NPU_AGENT_API_MODE", "responses")
    base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"

    print(f"Base URL : {base_url}")
    print(f"API mode : {mode}")
    print(f"Model    : {model}")

    client = build_client()

    if args.list_models:
        try:
            models = client.models.list()
            ids = sorted(item.id for item in models.data)
            print("\nVisible models:")
            for model_id in ids:
                print(f"  - {model_id}")
        except OpenAIError as exc:
            print(f"\nModel listing is not supported or failed: {exc}")

    try:
        if mode == "responses":
            response = client.responses.create(
                model=model,
                input="Reply with exactly API_OK and nothing else.",
                store=False,
            )
            output = response.output_text.strip()
        elif mode == "chat_completions":
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": "Reply with exactly API_OK and nothing else.",
                    }
                ],
            )
            output = (response.choices[0].message.content or "").strip()
        else:
            raise RuntimeError(
                "NPU_AGENT_API_MODE must be 'responses' or 'chat_completions'."
            )
    except OpenAIError as exc:
        raise RuntimeError(
            f"API request failed for mode={mode!r}, model={model!r}: {exc}\n"
            "If your university gateway does not implement /responses, set "
            "NPU_AGENT_API_MODE=chat_completions and retry."
        ) from exc

    print(f"\nProvider response: {output}")
    if output != "API_OK":
        print("Connection succeeded, but the model did not follow the exact test text.")
    else:
        print("API connection is working.")


if __name__ == "__main__":
    main()
