# Verifier tool

This directory contains the deterministic, code-owned verification components.
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
    ├── operation/             catalog-operation assertions and property guidance
    ├── instrumentation.py     assembles and inserts the generated TB block
    └── review.py              read-only assertion view for TB review
```

`role_pool` describes signal meaning. `coverage` records observed bin hits.
`predefined_assertion` generates code-owned checks. The Verifier still writes
stimulus, the reference model, and operation-specific connections or observers
where the contract cannot be bound deterministically.
