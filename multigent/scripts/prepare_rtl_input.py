"""Prepare the complete RTL Generator input from a minimal user request.

This script is intentionally deterministic. It does not ask another LLM to
reinterpret project policy. It combines:

1. the exact original user request,
2. fixed RTL/project constraints, and
3. the frozen Architect artifacts.

Example:

    python -m multigent.scripts.prepare_rtl_input --run-id dense-gemm-001
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from multigent.intake.request_builder import WORKSPACE_ROOT, build_rtl_context


def load_user_request(run_id: str) -> str:
    path = WORKSPACE_ROOT / "specs" / f"request-{run_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(
            f"Architect intake record not found: {path}. Run the Architect first or "
            "pass --request explicitly."
        )
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    request = value.get("user_request") if isinstance(value, dict) else None
    if not isinstance(request, str) or not request.strip():
        raise ValueError(f"No usable user_request found in {path}")
    return request.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic input context for the RTL Generator"
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--request",
        default=None,
        help="Override the recorded original user request",
    )
    parser.add_argument(
        "--architecture-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output YAML path; defaults to workspace/specs/derived/rtl-input-<run-id>.yaml",
    )
    args = parser.parse_args()

    request = args.request.strip() if args.request else load_user_request(args.run_id)
    context = build_rtl_context(
        user_request=request,
        architecture_dir=args.architecture_dir,
    )

    output = args.output or (
        WORKSPACE_ROOT / "specs" / "derived" / f"rtl-input-{args.run_id}.yaml"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(context, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()
