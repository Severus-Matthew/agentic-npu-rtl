# Verifier tool

This directory contains the deterministic, code-owned part of `my_v` verification.
It is a library used by the Architect, Verifier, reviewer, and cocotb runtime; it is
not another LLM agent.

```text
verifier_tool/
├── role_pool/                 closed signal roles and interface semantics
├── coverage/
│   ├── protocol/              protocol coverpoints and obligation planning
│   ├── operation/             operation families, bins, and DUT sampling
│   ├── cocotb_model.py        cocotb-coverage objects
│   ├── runtime.py             sampling, bin hits, and coverage reports
│   └── stimulus.py            cumulative stimulus evidence
└── predefined_assertion/
    ├── protocol/              ready/valid protocol assertion generation
    ├── operation/             catalog-operation result assertion generation
    ├── instrumentation.py     assembles and inserts the generated TB block
    └── review.py              read-only assertion view for TB review
```

`role_pool` describes what a signal means. `coverage` records whether required
behavior was observed. `predefined_assertion` checks whether observed behavior is
legal. Known protocol and operation features use these code-owned definitions;
only features absent from the catalogs remain Verifier-authored extensions.
