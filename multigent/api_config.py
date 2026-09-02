"""Shared API endpoint configuration for the multi-agent runtime."""

from __future__ import annotations

import os
from urllib.parse import urlsplit


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def resolve_base_url() -> str:
    """Return a valid explicit API base URL.

    An empty ``OPENAI_BASE_URL=`` environment variable must not be passed through
    implicitly to the OpenAI SDK. Some SDK versions consult that environment
    variable themselves when ``base_url`` is omitted, which can lead to an
    ``UnsupportedProtocol`` error. We therefore always resolve and pass a concrete
    URL explicitly.
    """

    value = (os.getenv("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL).strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            "OPENAI_BASE_URL must be an absolute http(s) URL, e.g. "
            f"{DEFAULT_OPENAI_BASE_URL!r}; got {value!r}."
        )
    return value.rstrip("/")
