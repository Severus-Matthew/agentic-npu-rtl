"""Check that the configured university/OpenAI-compatible API is reachable.

Run from the repository root:

    python -m multigent.scripts.check_api

Optional:

    python -m multigent.scripts.check_api --list-models

The checker diagnoses malformed cluster proxy variables before attempting an API
request. By default the NPU runtime ignores inherited proxy variables because
HPC/login environments often inject proxies that are invalid for Python HTTPX.
Set NPU_AGENT_TRUST_ENV=true only when the cluster explicitly requires its proxy
for outbound HTTPS.
"""

from __future__ import annotations

import argparse
import os
from urllib.parse import urlsplit

from openai import DefaultHttpx2Client, OpenAI, OpenAIError


PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def trust_env_enabled() -> bool:
    value = os.getenv("NPU_AGENT_TRUST_ENV", "false").strip().lower()
    return value not in {"0", "false", "no", "off"}


def proxy_diagnostics() -> list[str]:
    """Return human-readable warnings without exposing proxy credentials."""

    warnings: list[str] = []
    for name in PROXY_VARIABLES:
        value = os.getenv(name)
        if not value:
            continue
        parsed = urlsplit(value)
        if not parsed.scheme:
            warnings.append(
                f"{name} is set but has no URL scheme (expected e.g. "
                "http://proxy.example.edu:PORT)."
            )
        elif parsed.scheme not in {"http", "https", "socks5", "socks5h"}:
            warnings.append(f"{name} uses unexpected proxy scheme {parsed.scheme!r}.")
    return warnings


def build_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set your key."
        )

    kwargs = {
        "api_key": api_key,
        "timeout": 60.0,
        "http_client": DefaultHttpx2Client(trust_env=trust_env_enabled()),
    }
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
    trust_env = trust_env_enabled()

    print(f"Base URL : {base_url}")
    print(f"API mode : {mode}")
    print(f"Model    : {model}")
    print(f"Trust env: {trust_env}")

    warnings = proxy_diagnostics()
    if trust_env and warnings:
        print("\nProxy environment problem detected:")
        for warning in warnings:
            print(f"  - {warning}")
        print(
            "\nThis can cause HTTPX/OpenAI to fail before contacting the API.\n"
            "Either fix/unset the malformed proxy variable(s), or set:\n\n"
            "    NPU_AGENT_TRUST_ENV=false\n"
        )
        raise SystemExit(2)

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
            "If the transport connects successfully but the provider rejects the "
            "endpoint, then try NPU_AGENT_API_MODE=chat_completions."
        ) from exc

    print(f"\nProvider response: {output}")
    if output != "API_OK":
        print("Connection succeeded, but the model did not follow the exact test text.")
    else:
        print("API connection is working.")


if __name__ == "__main__":
    main()
