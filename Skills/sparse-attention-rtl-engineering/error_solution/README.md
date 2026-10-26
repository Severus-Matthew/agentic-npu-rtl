# Error-solution record fields

`error_solution_rag.yaml` contains design context, error families, and incident records. Empty attempt or hypothesis lists mean none were documented. A supplied patch is described as supplied; execution and PASS are claimed only when the session records them.

For `status`, `validated` means the stated repair has a recorded successful check; `partially_validated` means a stated obligation remains open; `diagnosed_fix_provided` means the proposed repair lacks a recorded rerun; `validation_change_requires_review` means a PASS followed a changed acceptance criterion whose justification is not established.

```yaml
design_profiles:
  - design_id: Microarchitecture-based identifier, independent of contributor identity.
    family: Broad design family.
    selection: How keys or pages are selected.
    query_organization: Query dimensions and tiling.
    key_organization: Key dimensions, pages, and tiling.
    arithmetic: Numerical formats and computation.
    mask_semantics: Meaning and effect of the masks.
    storage: Memory organization and interfaces.
    functional_boundary: Stages implemented by this design.
    excluded_stages:
      - Stages outside its demonstrated scope.
    evidence_status:
      validation_milestone: Whether this milestone is confirmed, failed, or unverified.

error_families:
  - family_id: Broad error-family identifier.
    description: Failures grouped into this family.
    first_questions:
      - Initial questions that help identify the relevant failure mechanism.

records:
  - id: SA-EXAMPLE-001
    title: Short descriptive error title.
    applies_to:
      design_profiles: [relevant_design_id]
      architecture_traits: [relevant_structure_or_behavior]
    status: Recorded evidence outcome, using one of the four values explained above.
    error_family: Broad error family.
    error_type: Specific error class.
    subtype: Precise failure pattern.
    stage: Design or tool stage where the failure occurred.
    tool: Tool that exposed the failure.
    failing_layer: Source of the failure, such as RTL, testbench, build flow, or physical implementation.

    symptom_signatures:
      - Observable error message or failure behavior.

    preconditions:
      - Design state and environment required for this case to apply.

    action_trace:
      - step: 1
        status: observed_action
        action: Documented GPT analysis, supplied patch, executed change, or check, described according to what actually happened.
        observation_or_result: Evidence observed at that step, including an incomplete result when applicable.

    failed_or_insufficient_attempts:
      - status: attempted_insufficient
        action: An approach actually used in the recorded incident.
        result: What failed or which requirement remained unmet.

    rejected_by_evidence:
      - hypothesis_or_direction: An explanation or direction ruled out for this incident; not necessarily an attempted repair.
        evidence: The observation that contradicts it.

    root_cause:
      - Cause supported by the evidence, with any unresolved mechanism stated explicitly.

    resolution:
      actions:
        - Concrete corrective changes, preserving exact details where the source provides them.

    validation:
      - evidence: Recorded result supporting the repair.
        regression_scope: Tests and implementation stages actually covered.
        limitation: Optional boundary, missing rerun, or missing implementation detail in the supplied evidence.

    derived_guidance:
      - status: generalized_rule
        rule: Reusable lesson derived afterward; not claimed as an action performed in the incident.

    reuse_rule:
      - Conditions under which the precedent applies and differences that require a fresh investigation.
```
