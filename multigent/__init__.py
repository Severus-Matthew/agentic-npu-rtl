"""Autonomous multi-agent NPU RTL engineering runtime."""

from pathlib import Path

from dotenv import load_dotenv


# Local developer credentials/configuration live in the repository-root .env file.
# override=False preserves explicitly exported shell/cluster environment variables.
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env", override=False)
