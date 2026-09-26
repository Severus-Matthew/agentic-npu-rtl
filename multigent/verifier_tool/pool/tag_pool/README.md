# Verification Tag Pool

`verification_tags.yaml` is the single closed vocabulary for capability tags
shared by Protocol, Lifecycle, and Operation verification. A tag is a stable
machine-readable concept such as `handshake`, `reset`, `lifecycle`, or
`mathematical_correctness`; it is not an assertion, coverage bin, or stimulus
implementation by itself.

All consumers load the registry through `registry.py`. They must not parse the
YAML independently or maintain a second list of tag names. The registry validates
every tag already referenced by the built-in signal-role, semantic-class, and
protocol-profile pools.

## Domain use

- Protocol derives tags from the selected protocol profile and from the roles and
  semantic classes of the concrete signals in a channel. This lets a custom
  protocol that reuses built-in `valid`, `ready`, and `payload` roles reuse the
  existing handshake, backpressure, and stall helpers without an LLM recreating
  them.
- Lifecycle feature matching remains policy- and role-based. Resolved lifecycle
  features are additionally tagged with exact concepts such as `lifecycle`,
  `completion`, `error`, `busy`, and `reset`, so an extension can identify and
  preserve applicable built-in sibling behavior.
- Operation feature matching remains family/concept- and arithmetic-based.
  Resolved known features carry `operation_feature` and
  `mathematical_correctness`, so a novel residual operation feature can reuse the
  existing golden-model, coverage-classifier, and stimulus infrastructure where
  its contract still matches known mathematics.

Tags therefore aid matching and reuse; they never replace exact protocol fields,
lifecycle policy values, operation formula/DAG metadata, or signal bindings.

## Contract-local vocabulary

When the closed pool cannot represent a required feature, Architect may declare
plural, contract-local vocabulary under
`architecture_contract.verification_vocabulary`:

```yaml
verification_vocabulary:
  tags:
    - name: retry_window
      definition:
        description: A contract-local retry eligibility window.
        domains: [protocol]
        allowed_scopes: [signal, channel]
        required_observations: [retry_token]
  signal_roles:
    - name: retry_token
      definition:
        description: A token authorizing one retry.
        category: channel_flow_control
        channel_binding: required
        direction_relation: same_as_channel
        allowed_directions: [input, output]
        semantic_class_binding: forbidden
        coverage_tags: [retry_window]
```

An extension request then references either a built-in or local tag explicitly:

```yaml
match:
  tags:
    - {source: contract_local, name: retry_window}
  required_roles: [retry_token]
  required_protocol_profiles: [custom]
```

Validation rejects collisions with built-in names, unknown references, unused
local declarations, and domain/scope mismatches. Contract-local entries remain in
the frozen contract and are never written into this pool. Qualification,
mutation, promotion, and automatic promotion are deliberately not implemented.
