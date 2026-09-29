# Shared repository handoff

## Canonical merge decisions

- The `agentic-npu-rtl` verifier implementation is the production baseline.
- Regressions, mutants, fixtures, benchmark runners, and fault injection belong
  under `multigent/verifier_tool/tool_regression/` and must not add
  qualification-only branches to production protocol drivers.
- Generated-TB validation is production code under `tb_validation/`; it is not
  part of the verifier-tool regression suite.
- Extension regressions are isolated under `tool_regression/extensions/` so an
  unsupported feature can be tested without mixing its implementation evidence
  into built-in protocol, lifecycle, or operation regressions.
- Historical reports and temporary checklists belong in the ignored
  `tool_regression/local_reports/` directory. Stable executable evidence stays
  in tests and qualification builders.
- Test names describe behavior, not project phases. Source and documentation
  must not contain author watermarks or non-English implementation comments.

## Removed compatibility workarounds

An earlier qualification branch injected AXI faults from the production
`axi4_outstanding` driver. That path was removed. Equivalent faults are now
installed by benchmark-local adapters and monkeypatch helpers so normal generated
TBs cannot accidentally observe a regression-only mode.

The previous `deterministic/review.py` and `deterministic/patch.py` files were
renamed to `tb_validation/validator.py` and `tb_validation/repair.py`. Their
public imports remain available through `multigent.verifier_tool`.

## Continuation prompt

Continue from the current shared branch without replacing production verifier
modules with an older qualification fork. Keep production behavior aligned with
the `agentic-npu-rtl` working tree and place every new test-only helper under
`multigent/verifier_tool/tool_regression/`. Before changing a built-in pool or
checker, reproduce the problem through the public verifier-tool API and add a
focused regression. Preserve the separation between protocol, lifecycle, and
operation extensions. Do not add phase-numbered filenames, author watermarks,
non-English code comments, checked-in generated reports, or fault switches in
production drivers. Run `python -m multigent.verifier_tool.tool_regression.run_all`
after changes and report any failure by exact feature ID and test path.
