#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_dir"
python_bin="$repo_dir/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin="$(command -v python3)"; fi
# Delta's packaged Verilator is optional; other machines use their normal PATH.
if [[ -d "$HOME/.local/verilator-env/bin" ]]; then
  export PATH="$HOME/.local/verilator-env/bin:$PATH"
  export MAKEFLAGS="${MAKEFLAGS:-} CXX=g++ LINK=g++ AR=ar"
fi
if [[ -d "$repo_dir/.venv/bin" ]]; then export PATH="$repo_dir/.venv/bin:$PATH"; fi
exec "$python_bin" -m multigent.ui.server "$@"
