# Move the combined blackhole branch to another cluster

The `blackhole` branch contains the current LangGraph flow, role skills, tests and UI,
the original `multigent/workspace/` artifacts, and the newer `multigent/runs/` artifacts.
`migration/merge-inventory.json` records the combination. Saved results are historical
evidence, including failed and timed-out runs; they are not all passing designs.

## Fresh setup

```bash
git clone --branch blackhole git@github.com:Severus-Matthew/agentic-npu-rtl.git
cd agentic-npu-rtl
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r multigent/requirements.txt
```

The validated Python version and package versions are recorded in
`migration/validated-python-packages.json` for reference. Install/load Verilator,
a C++ compiler, and make on the destination cluster. The original validation used
Verilator 5.050 and cocotb 2.1; check compatibility with the destination tools.
Recreate `.env` privately using the configuration described in `multigent/README.md`
and `.env.example` if present. Actual `.env` files, virtual environments, credentials,
and Python caches are not part of this migration. Do not commit API keys.

```bash
python -m pytest multigent/tests -q
bash multigent/scripts/start_ui.sh --port 8766
```

From your laptop, replace USER and CLUSTER with the new login details:

```bash
ssh -L 8766:127.0.0.1:8766 USER@CLUSTER
```

Open the full private session URL printed by the UI server, including its `#` token.
Keep the server and SSH tunnel running. Start a new run to test the new machine.

## Existing artifacts and limitations

Historical reports/checkpoints may contain absolute paths from Delta. Preserve these
as evidence; they are not automatically relocated/resumable checkpoints. Rebuild
simulators on the new cluster rather than executing saved Delta/aarch64 binaries.
The old workspace is a historical GEMM example, not a freshly validated result of
the current flow. Current UI runs live under `multigent/runs/`.

Vivado installation, FPGA target selection and real PPA validation remain deferred.
The exhaustive-test stimulus-ledger performance issue is still present: evidence
recording rewrites the growing ledger and can cause long simulations/timeouts.
This migration does not claim that the performance problem has been fixed.

## Validation of this combined branch

On Delta, the full repository suite passed: **422 tests in 33.93 seconds**.
All 5,551 source-artifact entries checked across the two input folders were present
byte-for-byte in the combined tracked tree (overlapping entries counted for each input).
The content audit covered 3,991 tracked files, approximately 104 MB, and found no
tracked environment paths, credential-pattern matches, or files above 95 MiB.
This pattern scan is a pre-push check, not a guarantee that arbitrary text can never
contain sensitive information. Historical generated artifacts retain their original
formatting and evidence; they have not been rewritten to clean whitespace.
