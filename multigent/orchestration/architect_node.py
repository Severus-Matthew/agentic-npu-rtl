"""LangGraph node adapter for initial and feedback-driven Architect runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import json

from jsonschema import Draft202012Validator

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA, ArchitectAgent, ContractValidationError
from multigent.agents.base import AgentRuntimeError
from multigent.intake.request_builder import (
    WORKSPACE_ROOT,
    build_architect_intake,
    build_rtl_context,
    build_verification_context,
    persist_intake,
)

from .state import HardwareDesignState
from .architect_revision_patch import apply_architect_revision_patch, RevisionPatchError


ARCHITECT_REVISION_PATCH_SCHEMA = ARCHITECT_OUTPUT_SCHEMA.with_name(
    "architect_revision_patch.schema.json"
)


def _run_architect_revision(
    agent: ArchitectAgent,
    *,
    user_request: str,
    feedback: Mapping[str, Any],
    output_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    """Run Architect with downstream technical evidence without changing user input."""

    previous_path = output_dir / "architect_result.json"
    if previous_path.is_file():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
    else:
        previous = feedback.get("candidate_contract")
    if not isinstance(previous, Mapping) or not all(
        key in previous for key in (
            "architecture_contract", "interface_contract", "module_manifest",
            "acceptance_criteria",
        )
    ):
        raise AgentRuntimeError("Architect revision requires the previous complete contract")

    intake = build_architect_intake(user_request)
    intake["downstream_revision_feedback"] = dict(feedback)
    intake["previous_contract"] = dict(previous)
    intake["provenance"]["runtime_injected_fields"].append(
        "downstream_revision_feedback"
    )
    intake["provenance"]["runtime_injected_fields"].append("previous_contract")

    intake_dir = output_dir.parent / "specs"
    persist_intake(intake, run_id=run_id, output_dir=intake_dir)
    task = agent._build_architecture_task(intake) + """

ARCHITECTURE REVISION FEEDBACK
------------------------------
``previous_contract`` is the exact frozen candidate being amended.
``downstream_revision_feedback`` is technical evidence, not a new user requirement.
Return ONLY a local patch, not a complete replacement design. Each edit has a JSON
pointer path into one previous_contract artifact, an operation add/replace/remove,
the new value serialized as JSON in value_json, and a brief reason tied to the
feedback. Correct only a wrong, missing, or ambiguous rule implicated by feedback.
If the existing contract already gives one unique externally observable answer,
return CONTRACT_CONFIRMED with no edits and use issue to cite the exact existing
contract paths and resolution. The Verifier's question is evidence, not authority;
do not invent a contract change merely because it asked. Return PATCH_READY only
when Architect decides that an actual contract amendment is required.
Use replace on existing scalar leaves and add only to a missing scalar field or the
end of a scalar list; never replace a section, list, module, operation, channel,
signal, data type, or parameter object. Preserve all unrelated decisions byte-for-
byte after JSON parsing, including names, feature pools and module decomposition.
For lists of named objects, select the object with a stable ``name=<exact name>``
path segment; for pipeline stages use ``stage=<exact stage>``. Never use a numeric
index for either collection. Examples are
``/interface_contract/signals/name=completion/semantic`` and
``/module_manifest/modules/name=gemm_bias_relu_npu/ports/name=completion/semantics``
and ``/architecture_contract/pipeline/stage=FINALIZE/responsibility``.
Numeric indices are allowed only for scalar lists such as acceptance criteria.
The runtime applies your edits to previous_contract and validates the resulting
complete contract. The prior generic design instruction does not authorize full
regeneration on a revision. If the evidence requires a materially new design rather
than a local repair, return SPEC_CONFLICT with a concise issue and no edits.
Never ask RTL Generator to silently work around an unresolved external defect.
"""
    patch = agent.run_structured(
        task=task,
        schema_path=ARCHITECT_REVISION_PATCH_SCHEMA,
        log_name=f"architect-{run_id}.json",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    agent._write_json(output_dir / f"revision_patch-{run_id}.json", patch)

    # The response schema cannot express these status-conditional rules (OpenAI
    # structured outputs reject allOf/if/then), so they are enforced here instead.
    if patch["status"] == "PATCH_READY" and not patch["edits"]:
        raise AgentRuntimeError(
            "Architect revision status PATCH_READY requires at least one edit"
        )
    if patch["status"] in {"CONTRACT_CONFIRMED", "SPEC_CONFLICT"}:
        if patch["edits"]:
            raise AgentRuntimeError(
                f"Architect revision status {patch['status']} must not include edits"
            )
        if not patch["issue"].strip():
            raise AgentRuntimeError(
                f"Architect revision status {patch['status']} requires a non-empty issue"
            )

    if patch["status"] == "SPEC_CONFLICT":
        result = {"status": "SPEC_CONFLICT", "conflicts": [patch["issue"]]}
        agent._write_json(output_dir / "spec_conflict.json", result)
        return result
    if patch["status"] == "CONTRACT_CONFIRMED":
        result = json.loads(json.dumps(previous))
    else:
        try:
            result = apply_architect_revision_patch(previous, feedback, patch)
        except RevisionPatchError as exc:
            raise ContractValidationError(f"Architect local patch rejected: {exc}", previous) from exc
    schema = json.loads(ARCHITECT_OUTPUT_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(result))
    if errors:
        message = "; ".join(error.message for error in errors[:3])
        raise ContractValidationError(
            f"Architect local patch produced schema-invalid contract: {message}", result
        )

    agent._validate_contract_references(result)
    agent._write_yaml(
        output_dir / "architecture_contract.yaml", result["architecture_contract"]
    )
    agent._write_yaml(
        output_dir / "interface_contract.yaml", result["interface_contract"]
    )
    agent._write_json(output_dir / "module_manifest.json", result["module_manifest"])
    agent._write_yaml(
        output_dir / "acceptance_criteria.yaml", result["acceptance_criteria"]
    )
    agent._write_json(output_dir / "architect_result.json", result)
    return result


def make_architect_node(agent: ArchitectAgent | None = None):
    """Return an Architect node suitable for ``StateGraph.add_node``."""

    runtime = agent or ArchitectAgent()

    def architect_node(state: HardwareDesignState) -> dict[str, Any]:
        user_request = state.get("user_request")
        if not isinstance(user_request, str) or not user_request.strip():
            raise AgentRuntimeError("Architect LangGraph node requires user_request")

        output_dir = Path(
            state.get("architecture_dir", str(WORKSPACE_ROOT / "architecture"))
        )
        current_version = int(state.get("architecture_version", 0))
        feedback = state.get("architecture_conflict")
        is_revision = isinstance(feedback, Mapping)
        next_version = current_version + 1
        base_run_id = str(state.get("run_id", "langgraph"))
        node_run_id = f"{base_run_id}-arch-v{next_version}"
        if is_revision:
            node_run_id += f"-r{int(state.get('architecture_revision', 0)) + 1}"

        try:
            if is_revision:
                result = _run_architect_revision(
                    runtime,
                    user_request=user_request.strip(),
                    feedback=feedback,
                    output_dir=output_dir,
                    run_id=node_run_id,
                )
                revision = int(state.get("architecture_revision", 0)) + 1
            else:
                result = runtime.run(
                    user_request.strip(),
                    output_dir=output_dir,
                    run_id=node_run_id,
                )
                revision = int(state.get("architecture_revision", 0))
        except ContractValidationError as exc:
            # Preserve the rejected candidate and precise evidence. Only contract
            # validation failures take this route; API/tool/programming errors do not.
            revision = int(state.get("architecture_revision", 0)) + int(is_revision)
            evidence = {
                "category": "CONTRACT_REFERENCE_VALIDATION_FAILURE",
                "issue": str(exc), "candidate_contract": exc.candidate,
                "original_revision_feedback": dict(feedback) if is_revision else None,
                "requested_architect_decision": "Correct the reported local patch/references while preserving unaffected contract fields.",
            }
            runtime._write_json(output_dir / f"rejected_contract_v{next_version}_r{revision}.json", evidence)
            return {
                "architecture_status": "SEMANTIC_VALIDATION_FAILED",
                "architecture_conflict": evidence,
                "architecture_revision": revision,
                "history": [{"stage": "architect", "status": "SEMANTIC_VALIDATION_FAILED",
                             "architecture_version": next_version, "revision": revision,
                             "validation_error": str(exc)}],
            }

        update: dict[str, Any] = {
            "architecture_status": result["status"],
            "contract_review_status": "PENDING",
            "contract_review_hashes": {},
            "architecture_dir": str(output_dir),
            "architecture_revision": revision,
            "history": [
                {
                    "stage": "architect",
                    "status": result["status"],
                    "architecture_version": next_version,
                    "revision": is_revision,
                }
            ],
        }

        if result["status"] == "READY":
            revision_patch = None
            contract_confirmed = False
            if is_revision:
                patch_path = output_dir / f"revision_patch-{node_run_id}.json"
                if not patch_path.is_file():
                    raise AgentRuntimeError("Architect revision did not persist its contract patch")
                revision_patch = json.loads(patch_path.read_text(encoding="utf-8"))
                contract_confirmed = revision_patch.get("status") == "CONTRACT_CONFIRMED"
            assigned_version = current_version if contract_confirmed else next_version
            rtl_context = build_rtl_context(
                user_request=user_request.strip(),
                architecture_dir=output_dir,
            )
            preserve_existing_rtl = (
                is_revision
                and state.get("rtl_status") == "RTL_GENERATED"
                and bool(state.get("rtl_files"))
            )
            history_entry = update["history"][0]
            history_entry["architecture_version"] = assigned_version
            history_entry["architect_decision"] = (
                "CONTRACT_CONFIRMED" if contract_confirmed else "CONTRACT_PATCHED" if is_revision else "INITIAL_CONTRACT"
            )
            history_entry["rtl_preserved"] = preserve_existing_rtl
            if preserve_existing_rtl:
                history_entry["rtl_contract_version"] = int(
                    state.get("rtl_contract_version", current_version)
                )
            update.update(
                {
                    "architecture_version": assigned_version,
                    "architecture_artifacts": {
                        "architecture_contract": str(
                            output_dir / "architecture_contract.yaml"
                        ),
                        "interface_contract": str(
                            output_dir / "interface_contract.yaml"
                        ),
                        "module_manifest": str(output_dir / "module_manifest.json"),
                        "acceptance_criteria": str(
                            output_dir / "acceptance_criteria.yaml"
                        ),
                    },
                    "architecture_conflict": None,
                    "architecture_revision_patch": revision_patch,
                    "rtl_context": rtl_context,
                    "verification_context": {},
                    "verifier_status": "PENDING",
                    "verifier_review_status": "PENDING",
                    "verifier_review_result": None,
                    "verifier_review_hashes": {},
                    "verification_plan": {},
                    "verification_status": "PENDING",
                    "verification_evidence": None,
                    "synthesis_result": None,
                    "best_candidate": None,
                    "optimization_plan": None,
                    "ppa_status": "PENDING",
                }
            )
            if contract_confirmed:
                verification_context = build_verification_context(
                    user_request=user_request.strip(), architecture_dir=output_dir
                )
                verification_context["architect_resolution"] = {
                    "decision": "CONTRACT_CONFIRMED",
                    "verifier_question": dict(feedback),
                    "resolution": str(revision_patch.get("issue", "")),
                }
                update["verification_context"] = verification_context
            if not preserve_existing_rtl:
                update.update(
                    {
                        "rtl_task_type": "INITIAL_GENERATION",
                        "rtl_status": "PENDING",
                        "rtl_result": {},
                        "rtl_files": [],
                        "rtl_contract_version": 0,
                        "rtl_feedback": None,
                    }
                )
            else:
                # A changed contract is first reconciled locally; a confirmed
                # unchanged contract can reuse the prior RTL directly. Any real
                # mismatch still needs deterministic simulation evidence.
                update.update(
                    {
                        "rtl_task_type": (
                            "CONTRACT_UNCHANGED" if contract_confirmed else "CONTRACT_FIXED"
                        ),
                        "rtl_status": "RTL_GENERATED",
                        "rtl_result": dict(state.get("rtl_result", {})),
                        "rtl_files": list(state.get("rtl_files", [])),
                        "rtl_contract_version": int(
                            state.get("rtl_contract_version", current_version)
                        ),
                        "rtl_feedback": {
                            "source": (
                                "architect_contract_confirmation"
                                if contract_confirmed
                                else "architect_contract_patch"
                            ),
                            "previous_contract_version": current_version,
                            "current_contract_version": assigned_version,
                            "contract_patch": revision_patch,
                        },
                    }
                )
        return update

    return architect_node
