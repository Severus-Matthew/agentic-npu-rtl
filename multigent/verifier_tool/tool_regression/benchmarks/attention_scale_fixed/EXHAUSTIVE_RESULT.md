# Exhaustive attention-scale qualification result

Result: **PASS**

The final frozen run used:

```bash
.venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.attention_scale_fixed.qualify \
  --mutants all --workers 4 --random-cases 128 \
  --work-root /private/tmp/attention-scale-exhaustive-final \
  --json-out /private/tmp/attention-scale-exhaustive-final/qualification_summary.json
```

Evidence summary:

- code-owned coverage: 14/14 `attention_scale` bins, 0 missing;
- arithmetic domain: all 65,536 signed 16-bit inputs;
- additional generated stimulus: 145 pool cases / 870 score elements, including
  128 deterministic randomized tensor cases;
- total baseline comparisons: 66,406;
- temporal checks: decoupled empty-stage acceptance, output stall stability,
  accepted/output accounting, reset abort, no ghost or duplicate output;
- mutation catalog: 73 selected, 73 compile-valid, 73 killed, 0 invalid,
  0 survivors;
- deterministic seed: `0x5CA1E`;
- contract digest:
  `60bd76726ca97808b60ec051c29e370a19f717c99e7fc41ca815eac983b7f2eb`;
- RTL digest:
  `b33c17e2b3f2fbd8e8536ac29252212cb70169d362b3f7026d0ac68a6562ee35`;
- qualification runner digest:
  `9e30c78ac5961f664aff525d35b588a80b881c00a647473043f4d79cba466b3b`.

The excluded score-input bit flips 0..2 are not faults for this frozen `/8`
function: changing only those bits cannot change `floor(score/8)`.  They are
mathematically equivalent edits and are not misreported as surviving bugs.
Likewise, the logical-shift fault is modeled with premature narrowing, where it
actually changes signed output behavior; merely replacing a 32-bit arithmetic
shift with a logical shift and then discarding the upper 16 bits is equivalent
over the reachable product range.
