"""API-backed independent Verifier Agent.

The Verifier creates a specification-derived Python reference model and cocotb
regression environment from the original request and frozen Architect artifacts.
Generated RTL is deliberately excluded from its context. Deterministic tool nodes
later compile the RTL and execute these tests.
"""

from __future__ import annotations

import argparse
import ast
import copy
import difflib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.verifier_tool import (
    AUDIT_BEGIN_MARKER,
    AUDIT_END_MARKER,
    BEGIN_MARKER,
    END_MARKER,
    OperationSamplingError,
    ReviewPatchPartialFailure,
    VerifierMetadataPatchError,
    apply_operation_coverage_metadata_edits,
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_feature_extension_manifest,
    build_interface_coverage_plan,
    canonical_operation_obligation_id,
    canonicalize_operation_obligation_claim,
    code_owned_obligations_for_supported_operations,
    coverage_obligation_mapping_diff,
    derive_interface_coverage_seed,
    effective_operation_coverage,
    extract_literal_coverage_obligations,
    extract_operation_sampling_bindings,
    extract_stimulus_coverage_intents,
    finding_scope,
    install_contract_generated_block,
    install_pipeline_generated_annotations,
    interface_vocabulary_extensions,
    merge_coverage_plans,
    normalize_operation_sampling_bindings,
    operation_plan_for_tests,
    render_extension_authoring_guide,
    render_requested_extension_worklist,
    render_interface_semantic_catalog,
    render_operation_coverage_catalog,
    render_operation_assertion_catalog,
    render_operation_sampling_catalog,
    render_signal_role_catalog,
    signals_with_coverage_tags,
    supported_code_owned_concepts,
    synthesize_code_owned_operation_coverage,
    synchronize_test_coverage_metadata,
    validate_architecture_operation_features,
    validate_contract_generated_block,
    validate_frozen_operation_scope,
    validate_interface_semantics,
    validate_interface_signal_roles,
    validate_operation_coverage,
    validate_verifier_authored_structure,
    validate_architect_extension_requests,
    validate_verifier_extension_bundles,
    with_verifier_extension_bundle_schema,
)
from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT


VERIFIER_OUTPUT_SCHEMA = SCHEMA_ROOT / "verifier_output.schema.json"
VERIFIER_SOURCE_REPAIR_SCHEMA = SCHEMA_ROOT / "verifier_source_repair.schema.json"
VERIFIER_REVISION_PATCH_SCHEMA = SCHEMA_ROOT / "deterministic_verifier_patch.schema.json"
_FORBIDDEN_IMPORT_ROOTS = {
    "os", "sys", "io", "builtins", "ctypes", "pickle", "shutil", "subprocess", "socket", "requests", "urllib", "http", "pathlib", "glob", "importlib"
}
_FORBIDDEN_CALL_NAMES = {"open", "exec", "eval", "compile", "__import__"}
_FORBIDDEN_CALL_ATTRIBUTES = {
    "system", "popen", "run", "call", "check_call", "check_output",
    "read_text", "read_bytes", "write_text", "write_bytes", "open", "glob", "rglob"
}


def _local_checker_run_calls(tree: ast.AST) -> set[ast.Call]:
    """Recognize direct calls to a locally defined, unmodified checker method.

    ``self.run()`` is a common cocotb observer entry point, not subprocess.run.
    Unknown receivers remain forbidden. This narrow exception does not relax
    import, dynamic execution, filesystem, or the method body's capability checks.
    """
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.Delete)):
            targets.extend(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets.append(node.target)
    if any(isinstance(target, ast.Attribute) and target.attr == 'run' for target in targets):
        return set()  # Do not exempt a rebound method.
    permitted = set()
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef) or cls.bases or cls.keywords or cls.decorator_list:
            continue
        methods = {node.name: node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        implementation = methods.get('run')
        if implementation is None or implementation.decorator_list or {'__getattr__', '__getattribute__'} & methods.keys():
            continue
        if any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'setattr'
               for node in ast.walk(cls)):
            continue
        for method in methods.values():
            arguments = method.args.posonlyargs + method.args.args
            if not arguments or method.decorator_list:
                continue
            receiver = arguments[0].arg
            if any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id == receiver
                   for node in ast.walk(method)):
                continue
            for node in ast.walk(method):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'run' and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == receiver):
                    continue
                owner = parents.get(node)
                while owner is not None and not isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    owner = parents.get(owner)
                if owner is method:
                    permitted.add(node)
    return permitted


class VerifierAgent(APIAgent):
    """Generate independent verification artifacts without reading generated RTL."""

    def __init__(self, *, model: str | None = None, api_mode: str | None = None) -> None:
        super().__init__(
            AgentConfig(
                name="verifier",
                role_skill="verifier",
                model=model or os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex"),
                api_mode=api_mode or os.getenv("NPU_AGENT_API_MODE", "responses"),
            )
        )
        self.last_generated_result: dict[str, Any] | None = None

    def load_instructions(self) -> str:
        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        return "# INDEPENDENT VERIFIER TECHNICAL SKILL\n\n" + self.role_skill_path.read_text(encoding="utf-8") + "\n"

    def load_output_schema(self, schema_path: Path) -> dict[str, Any]:
        schema = super().load_output_schema(schema_path)
        if schema_path.resolve() in {
            VERIFIER_OUTPUT_SCHEMA.resolve(),
            VERIFIER_SOURCE_REPAIR_SCHEMA.resolve(),
        }:
            return with_verifier_extension_bundle_schema(schema)
        return schema

    def run(
        self,
        context: Mapping[str, Any],
        *,
        workspace_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        self._validate_context(context)
        root = workspace_dir or WORKSPACE_ROOT
        reference_dir = root / "reference"
        tests_dir = root / "tests"
        verification_dir = root / "verification"
        for directory in (reference_dir, tests_dir, verification_dir):
            directory.mkdir(parents=True, exist_ok=True)

        self.last_generated_result = None
        self.last_addressed_findings = None
        review_draft = self._review_patch_draft(context)
        draft = self._source_repair_draft(context)
        if review_draft is not None:
            # Assertion/coverage review corrections preserve the accepted oracle,
            # metadata and unaffected TB source.  The model returns only exact
            # local source substitutions; deterministic validation still checks
            # the complete reconstructed verifier result below.
            self.last_generated_result = review_draft
            revision = self.run_structured(
                task=self._build_review_patch_task(context, review_draft),
                schema_path=VERIFIER_REVISION_PATCH_SCHEMA,
                log_name=f"verifier-{run_id}.json",
            )
            safe_run_id = "".join(
                char if char.isalnum() or char in {"-", "_"} else "_"
                for char in run_id
            )
            (verification_dir / f"verifier_revision_patch-{safe_run_id}.json").write_text(
                json.dumps(revision, indent=2) + "\n", encoding="utf-8"
            )
            try:
                result = self._apply_review_patch(context, review_draft, revision)
            except ReviewPatchPartialFailure as exc:
                # Keep whatever edits genuinely applied so the next retry only
                # has to cover the findings still outstanding, not redo work
                # a prior attempt in this same review round already got right.
                self.last_generated_result = exc.partial_result
                self.last_addressed_findings = exc.addressed_findings
                raise
            if result.get("status") == "VERIFICATION_READY":
                # The local patch round itself completed even if the subsequent
                # whole-artifact semantic validator exposes a different defect.
                # Preserve that distinction so orchestration starts a fresh
                # finding round instead of asking the model to replay edits that
                # are already present in this reconstructed draft.
                review = self._patch_review(context) or {}
                findings, _, _ = finding_scope(review)
                self.last_addressed_findings = set(range(len(findings)))
        elif draft is None:
            result = self.run_structured(
                task=self._build_task(context),
                schema_path=VERIFIER_OUTPUT_SCHEMA,
                log_name=f"verifier-{run_id}.json",
            )
        else:
            # This replaces one normal, counted graph correction; it does not
            # make an extra hidden generation/retry call. Reuse valid metadata
            # so the model can spend its response on executable function bodies.
            self.last_generated_result = draft
            sources = self.run_structured(
                task=self._build_source_repair_task(context, draft),
                schema_path=VERIFIER_SOURCE_REPAIR_SCHEMA,
                log_name=f"verifier-{run_id}.json",
            )
            result = self._merge_source_repair(draft, sources)
        # Keep a schema-valid draft available even when deterministic semantic
        # validation rejects it. The graph can return this verifier-owned source to
        # the same role for a targeted correction without repeating the code-owned
        # generated protocol block in the LLM prompt.
        self.last_generated_result = dict(result)
        return self.persist_validated_result(
            result=result, context=context, root=root
        )

    @staticmethod
    def _patch_review(context: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Return the one deterministic local-repair request, including old state."""

        for key in ("deterministic_validation_review", "assertion_definition_review"):
            review = context.get(key)
            if isinstance(review, Mapping):
                return review
        return None

    @staticmethod
    def _review_patch_draft(context: Mapping[str, Any]) -> dict[str, Any] | None:
        review = VerifierAgent._patch_review(context)
        if not isinstance(review, Mapping):
            return None
        draft = review.get("previous_verifier_output")
        if not isinstance(draft, Mapping) or draft.get("status") != "VERIFICATION_READY":
            return None
        if not draft.get("reference_files") or not draft.get("test_files"):
            return None
        return copy.deepcopy(dict(draft))

    @classmethod
    def _apply_review_patch(
        cls,
        context: Mapping[str, Any],
        draft: Mapping[str, Any],
        revision: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Apply exact, local verifier-owned source edits to a complete draft."""

        result = copy.deepcopy(dict(draft))
        status = revision.get("status")
        patches = list(revision.get("patches", []))
        metadata_edits = list(revision.get("metadata_edits", []))
        stimulus_intent_edits = list(revision.get("stimulus_intent_edits", []))
        conflict = revision.get("architecture_conflict")
        if status == "ARCHITECTURE_CONFLICT":
            if patches or metadata_edits or stimulus_intent_edits or not isinstance(conflict, Mapping):
                raise AgentRuntimeError(
                    "Verifier patch ARCHITECTURE_CONFLICT needs structured evidence and no edits"
                )
            result["status"] = "ARCHITECTURE_CONFLICT"
            result["summary"] = str(revision.get("summary", ""))
            result["architecture_conflict"] = copy.deepcopy(dict(conflict))
            result["known_verification_gaps"] = list(
                revision.get("known_verification_gaps", [])
            )
            result["reference_files"] = []
            result["test_files"] = []
            return result
        if (
            status != "PATCH_READY"
            or conflict is not None
            or not (patches or metadata_edits or stimulus_intent_edits)
        ):
            raise AgentRuntimeError(
                "Verifier review correction requires PATCH_READY, local edits, and no architecture conflict"
            )

        review = cls._patch_review(context) or {}
        findings, already_addressed, expected_findings = finding_scope(review)
        # A prior retry in this same review round may have already applied real
        # edits for some findings; only the remainder must be covered now.
        addressed_findings: set[int] = set()

        files: dict[str, dict[str, Any]] = {}
        for field, owner in (("reference_files", "reference"), ("test_files", "tests")):
            for item in result[field]:
                filename = cls._safe_python_filename(str(item["path"]), owned_root=owner)
                files[f"{owner}/{filename}"] = item

        # Collect every rejected patch instead of stopping at the first one: a
        # single-turn multi-patch response commonly has more than one defect
        # (e.g. several no-op patches), and reporting only the first forces one
        # wasted retry per defect instead of fixing them all in the next turn.
        patch_errors: list[str] = []
        for index, patch in enumerate(patches):
            finding_indices = set(patch.get("finding_indices", []))
            if (
                finding_indices
                and finding_indices <= already_addressed
                and not (finding_indices - set(range(len(findings))))
            ):
                # The prior attempt already applied these findings to the draft.
                # Ignore stale replays (including no-ops/old anchors) instead of
                # rejecting the genuinely new patches in the same response.
                continue
            raw_path = str(patch.get("path", ""))
            parts = Path(raw_path).parts
            if len(parts) != 2 or parts[0] not in {"reference", "tests"}:
                patch_errors.append(
                    f"patch {index} path must be reference/<file>.py or tests/<file>.py"
                )
                continue
            owner = parts[0]
            filename = cls._safe_python_filename(raw_path, owned_root=owner)
            path = f"{owner}/{filename}"
            if path not in files:
                patch_errors.append(f"patch {index} references unknown file {path!r}")
                continue
            old_text = str(patch.get("old_text", ""))
            new_text = str(patch.get("new_text", ""))
            occurrence_line = patch.get("occurrence_line")
            if occurrence_line is not None and (
                isinstance(occurrence_line, bool)
                or not isinstance(occurrence_line, int)
                or occurrence_line < 1
            ):
                patch_errors.append(
                    f"patch {index} occurrence_line must be null or a positive one-based integer"
                )
                continue
            if not old_text or old_text == new_text:
                patch_errors.append(
                    f"patch {index} (finding_indices={sorted(patch.get('finding_indices', []))}) "
                    "must make a non-empty exact substitution, not a no-op"
                )
                continue
            content = str(files[path]["content"])
            whole_file_append = (
                old_text == content
                and new_text.startswith(old_text)
                and len(new_text) > len(old_text)
                and any(
                    marker in str(finding.get("evidence", "")).lower()
                    for finding in findings
                    for marker in ("no executable", "incomplete", "truncated")
                )
            )
            if old_text.strip() == content.strip() and not whole_file_append:
                patch_errors.append(
                    f"patch {index} attempts to replace the entire file; use local edits"
                )
                continue
            occurrences = content.count(old_text)
            starts: list[int] = []
            search_start = content.find(old_text)
            while search_start != -1:
                starts.append(search_start)
                search_start = content.find(old_text, search_start + 1)
            selected_start: int | None = None
            if occurrences == 0:
                patch_errors.append(
                    f"patch {index} {cls._describe_patch_mismatch(old_text, content, path, occurrences)}"
                )
                continue
            if occurrences == 1:
                selected_start = starts[0]
                actual_line = content.count("\n", 0, selected_start) + 1
                if occurrence_line is not None and occurrence_line != actual_line:
                    patch_errors.append(
                        f"patch {index} occurrence_line={occurrence_line} does not match "
                        f"the unique old_text start line {actual_line} in {path}; use null "
                        "for a unique old_text or copy the exact reported line"
                    )
                    continue
            elif occurrence_line is None:
                patch_errors.append(
                    f"patch {index} {cls._describe_patch_mismatch(old_text, content, path, occurrences)}"
                )
                continue
            else:
                matching_starts = [
                    start for start in starts
                    if content.count("\n", 0, start) + 1 == occurrence_line
                ]
                if len(matching_starts) != 1:
                    available = [content.count("\n", 0, start) + 1 for start in starts]
                    patch_errors.append(
                        f"patch {index} occurrence_line={occurrence_line} does not select "
                        f"exactly one identical old_text in {path}; available start "
                        f"lines={available}"
                    )
                    continue
                selected_start = matching_starts[0]
            assert selected_start is not None
            if owner == "tests" and cls._patch_touches_generated_block(
                content, old_text, start=selected_start
            ):
                patch_errors.append(f"patch {index} may not edit pipeline-generated TB blocks")
                continue
            truly_unknown = finding_indices - set(range(len(findings)))
            usable = finding_indices & expected_findings
            if not finding_indices or truly_unknown:
                # A patch naming only already-addressed findings is still a real,
                # non-no-op edit and is applied below like any other; it just adds
                # nothing new to addressed_findings. Rejecting it outright would
                # block the model from genuinely refining a finding it already
                # patched earlier in this same round. Only reject a genuinely
                # empty or out-of-range finding_indices list.
                patch_errors.append(
                    f"patch {index} has invalid finding_indices={sorted(finding_indices)}"
                )
                continue
            addressed_findings.update(usable)
            files[path]["content"] = (
                content[:selected_start]
                + new_text
                + content[selected_start + len(old_text):]
            )

        # STIMULUS_COVERAGE_INTENTS is re-derived and re-rendered by the pipeline
        # at persist time (see _with_contract_generated_blocks), so a raw source
        # patch there is always rejected as an edit to a pipeline-generated block.
        # This is the sanctioned structured path to add a new declared intent: it
        # only appends here, and the persist step regenerates the audited block
        # and its # STIMULUS comment once a matching _contract_record_checked_
        # stimulus(..., label=...) call exists in the patched body above.
        for index, edit in enumerate(stimulus_intent_edits):
            finding_indices = set(edit.get("finding_indices", []))
            if (
                finding_indices
                and finding_indices <= already_addressed
                and not (finding_indices - set(range(len(findings))))
            ):
                continue
            op = edit.get("op")
            if op not in {"add", "add_targets"}:
                patch_errors.append(f"stimulus intent edit {index} must use op 'add' or 'add_targets'")
                continue
            label = str(edit.get("label", "")).strip()
            targets = [str(t) for t in edit.get("targets", [])]
            if not label or not targets:
                patch_errors.append(
                    f"stimulus intent edit {index} needs a non-empty label and targets"
                )
                continue
            truly_unknown = finding_indices - set(range(len(findings)))
            usable = finding_indices & expected_findings
            if not finding_indices or truly_unknown or not usable:
                stale = finding_indices & already_addressed
                patch_errors.append(
                    f"stimulus intent edit {index} has invalid finding_indices={sorted(finding_indices)}"
                    + (f" (already addressed in a prior retry: {sorted(stale)})" if stale else "")
                )
                continue
            target_path = next(
                (
                    path for path, item in files.items()
                    if path.startswith("tests/")
                    and "STIMULUS_COVERAGE_INTENTS" in str(item["content"])
                ),
                None,
            )
            if target_path is None:
                patch_errors.append(
                    f"stimulus intent edit {index} found no STIMULUS_COVERAGE_INTENTS declaration"
                )
                continue
            content = str(files[target_path]["content"])
            try:
                current_intents = extract_stimulus_coverage_intents(content)
            except ValueError as exc:
                patch_errors.append(f"stimulus intent edit {index}: {exc}")
                continue
            existing = next((item for item in current_intents if item["label"] == label), None)
            if op == "add":
                if existing is not None:
                    patch_errors.append(
                        f"stimulus intent edit {index} label {label!r} is already declared; "
                        "use op 'add_targets' to widen its existing targets instead"
                    )
                    continue
                updated_intents = current_intents + [{"label": label, "targets": targets}]
            else:
                if existing is None:
                    patch_errors.append(
                        f"stimulus intent edit {index} label {label!r} is not declared; "
                        "use op 'add' to declare it as a new intent instead"
                    )
                    continue
                merged_targets = list(existing["targets"])
                merged_targets += [t for t in targets if t not in merged_targets]
                if merged_targets == existing["targets"]:
                    patch_errors.append(
                        f"stimulus intent edit {index} adds no new target to {label!r}; "
                        "every listed target is already present"
                    )
                    continue
                updated_intents = [
                    {"label": label, "targets": merged_targets} if item["label"] == label else item
                    for item in current_intents
                ]
            tree = ast.parse(content)
            declaration = next(
                (
                    node for node in tree.body
                    if (
                        isinstance(node, ast.Assign)
                        and any(
                            isinstance(target, ast.Name)
                            and target.id == "STIMULUS_COVERAGE_INTENTS"
                            for target in node.targets
                        )
                    )
                    or (
                        isinstance(node, ast.AnnAssign)
                        and isinstance(node.target, ast.Name)
                        and node.target.id == "STIMULUS_COVERAGE_INTENTS"
                    )
                ),
                None,
            )
            if declaration is None:
                patch_errors.append(
                    f"stimulus intent edit {index} found no STIMULUS_COVERAGE_INTENTS assignment"
                )
                continue
            lines = content.splitlines()
            lines[declaration.lineno - 1 : declaration.end_lineno] = [
                f"STIMULUS_COVERAGE_INTENTS = {updated_intents!r}"
            ]
            files[target_path]["content"] = "\n".join(lines) + "\n"
            addressed_findings.update(usable)
        if patch_errors:
            raise ReviewPatchPartialFailure(
                "Verifier source patches rejected: " + "; ".join(patch_errors),
                partial_result=result,
                addressed_findings=already_addressed | addressed_findings,
            )

        metadata_finding_indices: set[int] = set()
        active_metadata_edits = []
        for index, edit in enumerate(metadata_edits):
            finding_indices = set(edit.get("finding_indices", []))
            if (
                finding_indices
                and finding_indices <= already_addressed
                and not (finding_indices - set(range(len(findings))))
            ):
                continue
            truly_unknown = finding_indices - set(range(len(findings)))
            usable = finding_indices & expected_findings
            if not finding_indices or truly_unknown:
                # As with patches: an edit naming only already-addressed findings
                # is a legitimate refinement, not an error; only reject a genuinely
                # empty or out-of-range finding_indices list.
                raise ReviewPatchPartialFailure(
                    f"Verifier metadata edit {index} has invalid finding_indices={sorted(finding_indices)}",
                    partial_result=result,
                    addressed_findings=already_addressed | addressed_findings,
                )
            metadata_finding_indices.update(usable)
            active_metadata_edits.append(edit)
        try:
            apply_operation_coverage_metadata_edits(
                result["operation_coverage"], active_metadata_edits,
            )
        except VerifierMetadataPatchError as exc:
            # Edits before the failing one may already be applied in-place above;
            # do not credit any metadata finding as addressed for this attempt.
            raise ReviewPatchPartialFailure(
                f"Invalid Verifier metadata edit: {exc}",
                partial_result=result,
                addressed_findings=already_addressed | addressed_findings,
            ) from exc
        addressed_findings.update(metadata_finding_indices)

        if addressed_findings != expected_findings:
            raise ReviewPatchPartialFailure(
                "Verifier source patches must address every review finding; "
                f"missing={sorted(expected_findings - addressed_findings)}",
                partial_result=result,
                addressed_findings=already_addressed | addressed_findings,
            )
        result["status"] = "VERIFICATION_READY"
        result["summary"] = str(revision.get("summary", ""))
        result["architecture_conflict"] = None
        result["known_verification_gaps"] = list(
            revision.get("known_verification_gaps", [])
        )
        return result

    @staticmethod
    def _patch_touches_generated_block(
        content: str, old_text: str, *, start: int | None = None
    ) -> bool:
        start = content.index(old_text) if start is None else start
        stop = start + len(old_text)
        for begin_marker, end_marker in (
            (BEGIN_MARKER, END_MARKER),
            (AUDIT_BEGIN_MARKER, AUDIT_END_MARKER),
        ):
            begin = content.find(begin_marker)
            end = content.find(end_marker)
            if begin < 0 or end < begin:
                continue
            end += len(end_marker)
            if start < end and stop > begin:
                return True
        return False

    @staticmethod
    def _describe_patch_mismatch(old_text: str, content: str, path: str, occurrences: int) -> str:
        """Give the next attempt concrete evidence instead of just a count.

        LLMs are unreliable at exact substring counting/matching over long
        files; re-asking the same model to "double check" its own old_text is
        just another fallible guess. Instead, compute the precise mismatch
        deterministically here so the next revision gets an anchor it can
        actually fix, not just a bare number.
        """

        def line_of(offset: int) -> int:
            return content.count("\n", 0, offset) + 1

        if occurrences == 0:
            matcher = difflib.SequenceMatcher(None, content, old_text, autojunk=False)
            match = matcher.find_longest_match(0, len(content), 0, len(old_text))
            if match.size == 0:
                return (
                    f"old_text was not found anywhere in {path} (0 characters of it "
                    "match); this is not a small anchor mismatch, re-copy old_text "
                    "directly from the supplied file content"
                )
            matched = old_text[match.b : match.b + match.size]
            expected_next = old_text[match.b + match.size : match.b + match.size + 40]
            actual_next = content[match.a + match.size : match.a + match.size + 40]
            return (
                f"old_text must occur exactly once in {path}; found 0. The longest "
                f"part of old_text that does match starts at line {line_of(match.a)}: "
                f"{matched[-60:]!r}. Right after that point old_text expects "
                f"{expected_next!r} but the file actually has {actual_next!r} there — "
                "copy old_text from the file exactly from that point on (check "
                "whitespace, quotes, and whether a prior edit in this same batch "
                "already changed this region)"
            )
        starts = []
        start = content.find(old_text)
        while start != -1:
            starts.append(start)
            start = content.find(old_text, start + 1)
        locations = ", ".join(f"line {line_of(s)}" for s in starts)
        return (
            f"old_text must occur exactly once in {path}; found {occurrences} "
            f"identical occurrences ({locations}). Either widen old_text with unique "
            "surrounding context, or keep this exact local old_text and set "
            "occurrence_line to the exact one-based start line of the ONE occurrence "
            "you mean. Do not guess a different label or add a placeholder call"
        )

    @classmethod
    def _build_review_patch_task(
        cls, context: Mapping[str, Any], draft: Mapping[str, Any]
    ) -> str:
        review = cls._patch_review(context)
        if not isinstance(review, Mapping):
            raise AgentRuntimeError("Verifier local patch requires deterministic findings")
        files = []
        for field, owner in (("reference_files", "reference"), ("test_files", "tests")):
            for item in draft[field]:
                filename = cls._safe_python_filename(str(item["path"]), owned_root=owner)
                files.append({"path": f"{owner}/{filename}", "content": item["content"]})
        findings, already_addressed, expected_findings = finding_scope(review)
        envelope = {
            "user_request": context["user_request"],
            "frozen_architecture": context["frozen_architecture"],
            "review_findings": [
                {"index": index, **dict(finding)}
                for index, finding in enumerate(findings)
                if index in expected_findings
            ],
            "already_applied_finding_indices": sorted(already_addressed),
            "patch_validation_error": review.get("patch_validation_error"),
            "operation_coverage": draft["operation_coverage"],
            "files": files,
        }
        coverage_feedback = context.get("coverage_closure_review")
        if isinstance(coverage_feedback, Mapping):
            feedback = {
                key: copy.deepcopy(coverage_feedback[key])
                for key in (
                    "missing_bins", "covered_bins", "bin_hits",
                    "missing_bin_definitions", "stimulus_summary",
                )
                if key in coverage_feedback
            }
            if {"runtime_report_missing", "invalid_runtime_report"} & set(
                map(str, feedback.get("missing_bins", []))
            ):
                envelope["coverage_report_failure"] = feedback
            else:
                envelope["coverage_hit_feedback"] = feedback
        if isinstance(review.get("runtime_evidence"), Mapping):
            envelope["runtime_failure_evidence"] = copy.deepcopy(
                review["runtime_evidence"]
            )
        declared_module_names = ", ".join(
            sorted(
                str(item["name"])
                for item in context["frozen_architecture"]["module_manifest"]["modules"]
            )
        ) or "none"
        return f"""Repair the reviewed verifier artifacts with local source patches.

The complete previously accepted oracle/TB is supplied below. Return only the
smallest exact old_text -> new_text source substitutions and, when coverage bins or
point fields change, leaf-level metadata_edits needed for the enumerated findings.
Do not regenerate or return a complete file or coverage catalog. Preserve all
unaffected source, metadata, valid stimulus and checks. Each old_text must occur
exactly once in its named file unless occurrence_line deterministically selects
one of several identical occurrences. Set occurrence_line=null when old_text is
unique. If patch_validation_error lists identical start lines, either widen the
anchor or keep the exact local old_text and set occurrence_line to exactly ONE of
those reported one-based start lines; never guess a different label or insert a
placeholder merely to make an anchor unique. Use a small stable anchor plus new
code to insert a helper. Test functions often share near-identical boilerplate lines (a common
closing assert, a common helper call): before submitting old_text, check whether
that exact snippet could plausibly appear verbatim at more than one call site in
the file (e.g. the same two lines closing two different @cocotb.test functions);
if so, widen old_text with a few more lines of that SAME occurrence's unique
surrounding context or set occurrence_line from the deterministic duplicate-line
error. Only the findings present in
review_findings remain open. Every listed finding index must be referenced by at
least one local edit. Indices in already_applied_finding_indices are historical
and must not appear in any edit.
If coverage_hit_feedback is present, treat its hit counts as the authoritative
result of the previous executed regression. Keep the already covered scenarios;
add real DUT-driven, checked stimulus for every missing bin, using
missing_bin_definitions to target the actual predicate and stimulus_summary to
avoid repeating unsuccessful schedules. Never claim or synthesize a hit. The
pipeline reruns the full TB after this local patch and repeats coverage closure
until every required bin is hit or the bounded Verifier budget is exhausted.
If coverage_report_failure is present, there are no trustworthy hit results:
repair only the report/instrumentation failure named by the findings. Do not
invent bin hits or add stimulus for the report-missing sentinel.
operation_coverage (operation names, coverpoints, bins, predicates, intents,
descriptions) is never literal text inside any source file, in any format,
including as an embedded YAML/JSON-looking block: it is supplied to you and
returned to the runtime purely as structured data. A finding that says a
coverpoint or bin definition is wrong (wrong bins, wrong predicate, wrong value
space, stale/impossible bin) is corrected only through metadata_edits, never
through a patches old_text/new_text substitution; a patches entry whose
old_text looks like coverage-catalog content will always fail to match any
real file and wastes the whole edit. Use a patches entry only to change actual
Python source text (stimulus, checkers, helper functions, comments).
One edit may address multiple findings. Use value_json for metadata scalar values,
one appended coverpoint, or one appended bin. Named selectors are stable and never
numeric indices:
/operation_coverage/operation_name=<name>/coverpoints/id=<id>/field to edit a
coverpoint's own field,
/operation_coverage/operation_name=<name>/coverpoints/id=<id>/bins/name=<bin-name>/field
to edit an EXISTING bin's non-identity field (predicate, intent, etc. — this is
the correct path to fix a bin whose meaning/predicate is wrong), or
/operation_coverage/operation_name=<name>/coverpoints/id=<id>/bins/- to append a
brand new bin object, or op "remove" on
/operation_coverage/operation_name=<name>/coverpoints/id=<id>/bins/name=<bin-name>
(no trailing field) to delete one existing bin outright — this is the correct
fix when a finding says a bin represents a value the contract makes impossible
to observe, not a relabel/patch. remove never targets a field beneath the
selector, and refuses to remove a coverpoint's last remaining bin (add its
replacement first, same batch or a prior one). Paths like bins/0/... or
bins/1/... are always rejected; a bin has no stable position, only its name.
A bin's own name/id can never be the edited field via add/replace, even via
the name=<bin-name> selector: to correct what a mislabeled-but-still-reachable
bin means, leave name unchanged and edit its sibling predicate/intent instead
of removing and re-adding it. A bin's predicate is itself an object
{{"op": ..., "args": [...]}}: you can never replace predicate or predicate/args
wholesale in one edit (each is a composite value, always rejected), only their
own scalar leaves — predicate/op (a string) and each existing predicate/args/<i>
(a numeric index into that array, one scalar per edit; args cannot grow or
shrink). predicate/op must be one of exactly these literal strings — no others
are recognized, and there is no boolean/nested-condition combinator: "eq",
"neq", "lt", "lte", "gt", "gte" (each takes exactly 1 arg), "between", "mod_eq",
"mod_ne" (each takes exactly 2 args), "one_of" (1 or more args — this is the op
for "value is one of a set", not "in_set" or "or"), "truthy", "falsy" (each
takes 0 args). A new bin you add via bins/- must use one of these too. Do not
replace operation, point, bin, or entire source-file sections wholesale.
A coverpoint's existing bin names, and an operation's existing coverpoint ids,
are already listed in operation_coverage below: before appending a new one via
bins/- or coverpoints/-, check it is not already present under that exact
name/id. Appending a duplicate name/id is always rejected; if a review finding
says an existing bin's predicate is wrong, that is a 'replace' on its predicate
fields (or a 'remove' of the one bin plus a differently-named 'add', never both
an 'add' of the same name and a later fix attempt on it in the same or a later
round). A review finding's prose (e.g. "includes a negative/minimum bin") is a
paraphrased description of a problem, not a literal name: before writing any
name=<x>/id=<x> selector, find that exact bin/coverpoint in the operation_coverage
listed below and copy its real declared name/id character-for-character — never
infer, guess, or reuse a word from the finding text itself as a selector. If no
bin in the current operation_coverage actually matches what the finding
describes (e.g. it already only has non-negative bins), the finding is likely
already satisfied by a prior edit; do not keep guessing a nonexistent name — use
metadata_edits addressing only what genuinely still needs to change, or a
smaller predicate/intent refinement, referencing this finding's index.

Every bare `assert` you add or leave in a patched region needs a feature comment
on the line immediately above it, in exactly this literal form:
`# LLM-GENERATED OPERATION ASSERTION [feature]` — this is the only comment the
runtime recognizes for a Verifier-authored assert, including one that checks a
protocol/signal-level concept (reset behavior, error behavior, channel
handshake/stall state, illegal-command recovery timing, and similar): the
bracketed feature is a free-form label naming what the assert checks, not
restricted to an operation-catalog id. No other comment text satisfies this —
not `# FEATURE: x`, not `# PROTOCOL ASSERTION [x]`, not a plain description —
only this exact bracketed form. Adding an assert without also adding its
comment in the same patch, or resubmitting one you already tried without
fixing its wording, wastes the edit.

Do not edit either PIPELINE-GENERATED VERIFIER ANNOTATIONS or CONTRACT-GENERATED
PROTOCOL MONITOR blocks with a source patch; code owns them, and the runtime
rebuilds both after your edits apply. STIMULUS_COVERAGE_INTENTS itself is never
a metadata_edits target (metadata_edits only ever targets /operation_coverage/...;
a path starting /stimulus_coverage_intents/... is always rejected) and never a
source patch target either — both are always rejected as edits to a
pipeline-rebuilt declaration. It has its own two structured edits instead. To add
a brand new stimulus label (a MISSING_STIMULUS finding that needs one), use
stimulus_intent_edits with op "add", the new label, and its targets, and
separately add the actual stimulus construction plus a
_contract_record_checked_stimulus(..., label="<same label>") call to the test body
via a normal source patch. The runtime appends your declared label and re-derives
its # STIMULUS comment from that call once both land together. "add" is rejected
if that label is already declared. To make an EXISTING label also cover one or
more additional obligation targets (e.g. a finding says an existing stimulus
should also exercise/validate a target it does not yet list), use
stimulus_intent_edits with op "add_targets", that same existing label, and only
the new target(s) to add — it merges them into the label's existing targets list
and is rejected if the label is not already declared or if every listed target
is already present. Neither op can remove a label or a target, or rename one.
Do not weaken existing assertions or
coverage. Change stimulus only when a MISSING_STIMULUS or
INVALID_STIMULUS_MAPPING finding requires it. A response/output limit, patch-format
problem, Python problem, or coverage implementation choice is a Verifier defect,
never an architecture conflict. Return ARCHITECTURE_CONFLICT only for a genuine
unresolved contradiction in externally observable frozen semantics. If you do,
architecture_conflict.affected_modules must contain only exact names from
module_manifest.modules[].name. The declared modules for this contract are:
{declared_module_names}. Never put a test or reference file name/path there.

After applying your patches, the runtime reparses and validates the complete source,
then sends it through the independent review again before simulation.

FROZEN INPUT, FINDINGS, AND EXISTING SOURCES
""" + yaml.safe_dump(envelope, sort_keys=False, default_flow_style=False)

    @staticmethod
    def _with_contract_generated_blocks(
        result: Mapping[str, Any], context: Mapping[str, Any]
    ) -> dict[str, Any]:
        prepared = copy.deepcopy(dict(result))
        prepared.setdefault("feature_extensions", [])
        if prepared.get("status") != "VERIFICATION_READY":
            return prepared
        interface_plan = build_interface_coverage_plan(
            context["frozen_architecture"]["interface_contract"]
        )
        operation_metadata = build_architect_operation_metadata(
            context["frozen_architecture"]["architecture_contract"],
            context["frozen_architecture"]["interface_contract"],
        )
        supported = supported_code_owned_concepts(operation_metadata)
        campaign_support = automatic_campaign_support(
            operation_metadata,
            context["frozen_architecture"]["architecture_contract"],
        )
        automatic_campaign_supported = bool(campaign_support["supported"])
        # Embedding the executable campaign test is safe to relax to "at
        # least one operation qualifies": the campaign's own per-operation
        # loop (orchestration/campaign.py) skips any operation that
        # individually fails automatic_campaign_support's checks, so a
        # contract with a mix of known and unknown protocols/lifecycles still
        # gets automatic driving for the operations that do qualify.
        any_operation_campaign_supported = bool(campaign_support["any_operation_supported"])
        # synthesize_code_owned_operation_coverage is per-concept, not
        # per-operation or all-or-nothing: it generates deterministic
        # coverpoints only for concepts supported_code_owned_concepts marks
        # code-owned and preserves the LLM's own supplied points for every
        # other concept untouched (see its own per-concept "code_owned"/
        # "preserved" split) -- so it is safe, and correct, to call
        # unconditionally rather than gate it on every operation qualifying.
        try:
            prepared["operation_coverage"] = (
                synthesize_code_owned_operation_coverage(
                    list(prepared.get("operation_coverage", [])),
                    context["frozen_architecture"]["architecture_contract"],
                    operation_metadata,
                )
            )
        except ValueError as exc:
            raise AgentRuntimeError(
                f"Cannot synthesize code-owned operation coverage: {exc}"
            ) from exc
        operation_points = [
            (
                str(spec.get("operation_name", "")),
                str(point.get("id", "")),
                str(point.get("concept", "")),
            )
            for spec in prepared.get("operation_coverage", [])
            for point in spec.get("coverpoints", [])
        ]
        # Use the canonical helper directly because local point IDs may already
        # contain the operation prefix after a prior model revision.
        code_owned_ids = {
            canonical_operation_obligation_id(operation_name, point.get("id"))
            for spec in prepared.get("operation_coverage", [])
            for operation_name in [str(spec.get("operation_name", ""))]
            for point in spec.get("coverpoints", [])
            if str(point.get("concept", ""))
            in supported.get(operation_name, set())
        }
        all_points_code_owned = bool(operation_points) and len(code_owned_ids) == len(operation_points)
        try:
            minimum_randomized = int(
                context.get("verification_policy", {}).get(
                    "randomized_transactions_minimum", 0
                )
            )
            for index, item in enumerate(prepared["test_files"]):
                item["content"] = normalize_operation_sampling_bindings(
                    str(item["content"]),
                    code_owned_ids=code_owned_ids,
                    all_points_code_owned=all_points_code_owned,
                )
                if "STIMULUS_COVERAGE_INTENTS" in str(item["content"]):
                    item["content"] = install_pipeline_generated_annotations(
                        str(item["content"])
                    )
                item["content"] = install_contract_generated_block(
                    str(item["content"]),
                    interface_plan,
                    context["frozen_architecture"]["architecture_contract"],
                    include_automatic_campaign=(
                        any_operation_campaign_supported and index == 0
                    ),
                    randomized_transactions_minimum=minimum_randomized,
                )
        except (SyntaxError, ValueError) as exc:
            raise AgentRuntimeError(
                f"Cannot install contract-generated TB monitor: {exc}"
            ) from exc
        return prepared

    @staticmethod
    def _source_repair_draft(context: Mapping[str, Any]) -> dict[str, Any] | None:
        # Any semantic-validation failure with a valid, still-VERIFICATION_READY
        # previous draft goes through this targeted correction (previous content
        # shown, told the exact validator_error, told to change only what is
        # implicated) instead of the full from-scratch _build_task prompt, which
        # has no memory of the previous attempt or what specifically broke it.
        review = context.get("semantic_validation_review")
        if not isinstance(review, Mapping):
            return None
        draft = review.get("previous_verifier_output")
        if not isinstance(draft, Mapping) or draft.get("status") != "VERIFICATION_READY":
            return None
        if not draft.get("reference_files") or not draft.get("test_files"):
            return None
        if validate_operation_coverage(
            context["frozen_architecture"]["architecture_contract"],
            draft.get("operation_coverage", []),
        ) or validate_frozen_operation_scope(
            context["frozen_architecture"]["architecture_contract"],
            draft.get("operation_coverage", []),
        ):
            return None  # Invalid metadata still needs the normal full correction.
        # Operation metadata and the frozen scope were checked above.  Any
        # remaining obligation mismatch is therefore confined to the test-file
        # metadata/source pair and is safe for the local source-repair path.
        return copy.deepcopy(dict(draft))

    @classmethod
    def _merge_source_repair(
        cls, draft: Mapping[str, Any], sources: Mapping[str, Any],
    ) -> dict[str, Any]:
        result = copy.deepcopy(dict(draft))
        result["status"] = sources["status"]
        result["architecture_conflict"] = sources["architecture_conflict"]
        result["known_verification_gaps"] = list(sources["known_verification_gaps"])
        if "feature_extensions" in sources:
            result["feature_extensions"] = copy.deepcopy(
                list(sources["feature_extensions"])
            )
        if sources["status"] == "ARCHITECTURE_CONFLICT":
            if sources["files"]:
                raise AgentRuntimeError("ARCHITECTURE_CONFLICT must not emit source files")
            result["reference_files"] = []
            result["test_files"] = []
            return result
        expected = {}
        for field, owner in (("reference_files", "reference"), ("test_files", "tests")):
            for item in result[field]:
                filename = cls._safe_python_filename(item["path"], owned_root=owner)
                expected[f"{owner}/{filename}"] = item
        emitted = {}
        for item in sources["files"]:
            path = item["path"]
            if path in emitted:
                raise AgentRuntimeError(f"Source completion duplicates file: {path}")
            emitted[path] = item["content"]
        missing, unknown = sorted(expected.keys() - emitted.keys()), sorted(emitted.keys() - expected.keys())
        if missing or unknown:
            raise AgentRuntimeError(
                f"Source completion must replace exactly the planned files; missing={missing}, unknown={unknown}"
            )
        for path, item in expected.items():
            item["content"] = emitted[path]
        try:
            result = synchronize_test_coverage_metadata(result)
        except (SyntaxError, ValueError) as exc:
            raise AgentRuntimeError(str(exc)) from exc
        result["summary"] = "Verifier source completion; deterministic validation and simulation remain authoritative."
        return result

    @classmethod
    def _build_source_repair_task(cls, context: Mapping[str, Any], draft: Mapping[str, Any]) -> str:
        envelope = {key: context[key] for key in (
            "user_request", "verification_policy", "frozen_architecture",
            "execution_configuration", "provenance",
        ) if key in context}
        envelope["verification_plan"] = draft["verification_plan"]
        envelope["operation_coverage"] = draft["operation_coverage"]
        envelope["feature_extensions"] = draft.get("feature_extensions", [])
        try:
            envelope["operation_sampling_bindings"] = extract_operation_sampling_bindings(
                [item["content"] for item in draft["test_files"]]
            )
        except OperationSamplingError:
            # previous_content itself may be exactly what is broken (e.g. the
            # rejected prior draft that made this repair round happen in the
            # first place). This field is supplementary context only; a raw
            # extraction failure here must never crash task construction, since
            # validator_error below already tells the model the real defect and
            # previous_content still lets it see and fix the actual bindings.
            envelope["operation_sampling_bindings"] = []
        envelope["interface_coverage_plan"] = build_interface_coverage_plan(
            context["frozen_architecture"]["interface_contract"]
        )
        review = context.get("semantic_validation_review")
        envelope["validator_error"] = (
            review.get("validator_error") if isinstance(review, Mapping) else None
        )
        envelope["planned_files"] = [
            {**{key: value for key, value in item.items() if key != "content"},
             "path": f"{owner}/{cls._safe_python_filename(item['path'], owned_root=owner)}",
             "previous_content": item["content"]}
            for field, owner in (("reference_files", "reference"), ("test_files", "tests"))
            for item in draft[field]
        ]
        declared_module_names = ", ".join(
            sorted(
                str(item["name"])
                for item in context["frozen_architecture"]["module_manifest"]["modules"]
            )
        ) or "none"
        return """Complete the missing executable sources in one counted Verifier correction.

validator_error names the exact defect that made previous_content invalid; every
planned_files entry's previous_content is otherwise a working file. Reproduce each
file's previous_content byte-for-byte and change only what validator_error requires
you to fix. Do not rewrite, reformat, restructure, or regenerate code that
validator_error does not implicate, even though the schema still requires you to
return each file's complete content.

Exception: if a specific file's previous_content is itself genuinely incomplete or
truncated independent of validator_error — it ends mid-statement, or ends cleanly
but is missing an actual required test body (e.g. only helper/observer functions
are defined, with no real @cocotb.test implementation) — byte-for-byte preservation
of that one file is impossible by construction. In that case only, write a fresh
complete replacement for that file (reusing its still-valid helpers, stimulus, and
structure where you can) while still reproducing every OTHER file's previous_content
byte-for-byte except for validator_error's own fix. This is a normal, expected
correction here, never a reason to return ARCHITECTURE_CONFLICT: Architect has no
artifact that repairs the Verifier's own prior incomplete generation.

If validator_error says a stimulus needs a "# STIMULUS [label]" comment, do not
just insert that comment line: the runtime strips every such comment and
regenerates it only next to a `_contract_record_checked_stimulus(..., label="...")`
call whose label is a literal string constant at that exact call site. A shared
helper that receives label as a parameter and forwards it with `label=label` can
never get its comment restored, no matter how many times you add it. Fix this by
passing the literal label string directly at each `_contract_record_checked_stimulus`
call site (inline the call at each case, or add a small per-case wrapper that
passes the literal), not by editing comments.

If validator_error says the Verifier must not duplicate a pipeline-owned catalog
assertion, the fix is to delete that redundant `assert` statement entirely (and
its now-orphaned comment above it), not to relabel, strip, or reword the comment.
Catalog operation assertions (the required_properties/feature_checks already
defined for this operation's family, e.g. accumulation or post_processing) are
generated and checked by the pipeline itself; the Verifier must never author its
own assert for a concept the catalog already owns. Only taxonomy-missing features
(behavior with no catalog entry) may carry a Verifier-authored
`# LLM-GENERATED OPERATION ASSERTION [feature]` assert. Removing just the comment
while leaving the assert in place, or renaming its label, does not resolve this
error and produces the opposite "assert needs a feature comment" error instead —
the assert itself must go.

Return only status, files (path and complete content), architecture_conflict,
known_verification_gaps, and feature_extensions when the validator error implicates
that field. Otherwise omit feature_extensions and the previous bundle is preserved.
Metadata is reused by the runtime; coverage plans, catalogs, and ordinary test
metadata must not be regenerated. Return every planned file in full. JSON content strings are
executed verbatim; there is no later delivery step.
Imports/declarations/comments alone are invalid: emit actual async test functions.
Choose your oracle, helpers and stimulus code independently from the frozen
semantics. No RTL/source-derived evidence is present. Do not weaken any checks.
The regression uses declared parameter defaults without overrides. Verifier owns
custom observer implementations and scheduling; exact unpromised cycle timing and missing
prior TB are not architecture conflicts. Genuine unresolved external contradictions
may still return ARCHITECTURE_CONFLICT with exact evidence and no files.
""" + f"""If you do, architecture_conflict.affected_modules must contain only exact
names from module_manifest.modules[].name. The declared modules for this contract
are: {declared_module_names}. Never put a test or reference file name/path there.
""" + """
Use cocotb 2.x and one free-running Clock per test. Use finite literal timeout_time
and timeout_unit in every @cocotb.test decorator, with @contract_coverage() directly
below it (import from multigent.verifier_tool). Drive on the inactive clock edge,
settle/sample ready/valid/payload before the active edge, then commit that recorded
handshake. Never infer transfer from post-edge signals. Hold presented valid/payload
until transfer; optional idle delays before presentation are legal. Use independent
producers for channels that can interleave, and one owner per driven signal. Keep
ReadOnly observers separate from active drivers. Observe/check completion and error
each cycle concurrently with traffic, not only after producer tasks finish.

Implement the requested reference math and serialization with independent analytical
sanity checks. Generate directed boundaries plus the policy's seeded randomized
transaction minimum. Count outputs on handshakes, compare all against the reference,
check framing/reset/illegal-command behavior, and drive real protocol scenarios for
the supplied interface obligations. Declare each file's coverage_obligations exactly
in its module-level literal COVERAGE_OBLIGATIONS. Copy IDs byte-for-byte.

After each complete DUT job, call the code-inserted
_contract_record_checked_stimulus(kind, actual_inputs, expected_outputs,
observed_outputs, operations=(exact_operation_name, ...), label=...) with full,
equally structured JSON-serializable expected and observed outputs. It applies the
taxonomy-owned assertions for catalog features and records the stimulus only after
they pass. The inserted helper also links every listed operation to that checked
stimulus; do not import or call sample_operation or raw record_stimulus yourself.
Every selected bin must be deliberately exercised by
real submitted and checked traffic. Never fabricate hits or sample synthetic jobs.
Use no filesystem, subprocess, network or dynamic import capabilities. Keep prose
minimal; spend output on working source bodies and include useful failure context.
Do not emit names beginning _contract_generated_, _contract_record_, or CONTRACT_.
Code adds the frozen protocol assertions, catalog-operation assertion wrapper, and
single-snapshot monitor as a visibly marked final block after your response.
Declare one statically resolvable
STIMULUS_COVERAGE_INTENTS list of {"label": "case_id", "targets":
["exact.obligation.id", ...]} entries. Across all test files the targets must cover
every supplied interface and operation obligation. Code normalizes this metadata
into a literal and adds the stimulus section and ``# STIMULUS [case_id]`` comments;
do not spend output writing those comments. Use the same literal case_id as each
_contract_record_checked_stimulus label.
The exact ``# === LLM-GENERATED OPERATION ASSERTIONS ===`` section is only for
features absent from the selected taxonomy family. Put
``# LLM-GENERATED OPERATION ASSERTION [feature]`` immediately above each such
custom assert and include useful input/expected/observed/signal context in its
failure message. Do not reimplement catalog-feature assertions. Review will compare
actual stimulus code with these claims.
Preserve supplied operation_sampling_bindings only for unknown/novel points as a
literal module-level OPERATION_SAMPLING_BINDINGS list. Known points listed in
architect_operation_metadata are assembled and classified by verifier_tool and
must not get an LLM binding. The remaining bindings are static DUT connections,
not coverage values: the trusted observer samples their points. Every remaining
point needs a reusable binding or custom observer(values, state). Preserve
or implement its local synchronous function and helpers in the test module. Runtime
reads the fields and invokes it; None means no observation, a scalar is evaluated
by the normal coverage predicates. Never try to hit coverage from driver values.
The generated wrapper's internal sample_operation only links the checked job; it
is not a Verifier-authored sampling API call.

FROZEN INPUT AND REUSED GENERATION PLAN
""" + yaml.safe_dump(envelope, sort_keys=False, default_flow_style=False)

    def persist_validated_result(
        self,
        *,
        result: Mapping[str, Any],
        context: Mapping[str, Any],
        root: Path,
    ) -> dict[str, Any]:
        """Validate and persist an already generated structured verifier result."""

        result = self._with_contract_generated_blocks(result, context)
        try:
            result = synchronize_test_coverage_metadata(result)
        except (SyntaxError, ValueError) as exc:
            raise AgentRuntimeError(str(exc)) from exc
        # If validation exposes a different defect, local-repair callers must
        # continue from this normalized candidate, not stale duplicate metadata.
        self.last_generated_result = copy.deepcopy(result)
        self._validate_context(context)
        self._validate_prepared_result(result=result, context=context)
        reference_dir = root / "reference"
        tests_dir = root / "tests"
        verification_dir = root / "verification"
        for directory in (reference_dir, tests_dir, verification_dir):
            directory.mkdir(parents=True, exist_ok=True)
        if result["status"] == "VERIFICATION_READY":
            for directory in (reference_dir, tests_dir):
                for stale in directory.glob("*.py"):
                    stale.unlink()
            for item in result["reference_files"]:
                self._write_python(reference_dir, item, owned_root="reference")
            for item in result["test_files"]:
                self._write_python(tests_dir, item, owned_root="tests")
            (verification_dir / "verification_plan.yaml").write_text(
                yaml.safe_dump(result["verification_plan"], sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
            coverage_plan = build_interface_coverage_plan(
                context["frozen_architecture"]["interface_contract"]
            )
            (verification_dir / "interface_coverage_plan.yaml").write_text(
                yaml.safe_dump(coverage_plan, sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
            operation_plan = operation_plan_for_tests(
                result["operation_coverage"], [item["content"] for item in result["test_files"]],
                context["frozen_architecture"]["architecture_contract"],
                context["frozen_architecture"]["interface_contract"],
            )
            (verification_dir / "operation_sampling_bindings.yaml").write_text(
                yaml.safe_dump(extract_operation_sampling_bindings([item["content"] for item in result["test_files"]]), sort_keys=False),
                encoding="utf-8",
            )
            (verification_dir / "operation_coverage_plan.yaml").write_text(
                yaml.safe_dump(operation_plan, sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
            (verification_dir / "feature_extensions.yaml").write_text(
                yaml.safe_dump(
                    result.get("feature_extensions", []),
                    sort_keys=False,
                    default_flow_style=False,
                ),
                encoding="utf-8",
            )
            extension_manifest = build_feature_extension_manifest(
                context["frozen_architecture"]["architecture_contract"],
                result.get("feature_extensions", []),
                source_files=[*result["reference_files"], *result["test_files"]],
                interface=context["frozen_architecture"]["interface_contract"],
            )
            (verification_dir / "feature_extension_manifest.yaml").write_text(
                yaml.safe_dump(
                    extension_manifest,
                    sort_keys=False,
                    default_flow_style=False,
                ),
                encoding="utf-8",
            )
            (verification_dir / "combined_coverage_plan.yaml").write_text(
                yaml.safe_dump(
                    merge_coverage_plans(coverage_plan, operation_plan),
                    sort_keys=False,
                    default_flow_style=False,
                ),
                encoding="utf-8",
            )
            (verification_dir / "verifier_result.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
        return result

    def run_from_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        context = state.get("verification_context")
        if not isinstance(context, Mapping) or not context:
            user_request = state.get("user_request")
            if not isinstance(user_request, str) or not user_request.strip():
                raise AgentRuntimeError("Verifier node requires verification_context or user_request")
            context = build_verification_context(
                user_request=user_request,
                architecture_dir=Path(state.get("architecture_dir", WORKSPACE_ROOT / "architecture")),
            )

        run_id = str(state.get("run_id", "langgraph"))
        architecture_version = int(state.get("architecture_version", 0))
        architecture_revision = int(state.get("architecture_revision", 0))
        repair_iteration = int(state.get("repair_iteration", 0))
        verifier_revision = int(state.get("verifier_revision", 0))
        result = self.run(
            context,
            run_id=(
                f"{run_id}-verify-av{architecture_version}-ar{architecture_revision}"
                f"-r{repair_iteration}-v{verifier_revision}"
            ),
        )
        return {
            "verifier_status": result["status"],
            "verifier_result": result,
            "verification_plan": result["verification_plan"],
            "architecture_conflict": result["architecture_conflict"],
            "verification_context": dict(context),
        }

    @staticmethod
    def _validate_context(context: Mapping[str, Any]) -> None:
        required = {"user_request", "verification_policy", "frozen_architecture", "provenance"}
        missing = sorted(required - set(context))
        if missing:
            raise AgentRuntimeError(f"Verifier context missing required fields: {missing}")
        provenance = context["provenance"]
        if not isinstance(provenance, Mapping):
            raise AgentRuntimeError("Verifier provenance must be a mapping")
        if provenance.get("includes_generated_rtl") is not False:
            raise AgentRuntimeError("Independent Verifier context must exclude generated RTL")
        if provenance.get("includes_rtl_generator_output") is not False:
            raise AgentRuntimeError("Independent Verifier context must exclude RTL Generator output")
        frozen = context["frozen_architecture"]
        if not isinstance(frozen, Mapping):
            raise AgentRuntimeError("Verifier frozen_architecture must be a mapping")
        needed = {"architecture_contract", "interface_contract", "module_manifest", "acceptance_criteria"}
        missing_artifacts = sorted(needed - set(frozen))
        if missing_artifacts:
            raise AgentRuntimeError(f"Verifier context missing frozen artifacts: {missing_artifacts}")
        extension_errors = validate_architect_extension_requests(
            frozen["architecture_contract"], frozen["interface_contract"]
        )
        try:
            role_extensions, semantic_extensions = interface_vocabulary_extensions(
                frozen["architecture_contract"]
            )
        except ValueError:
            role_extensions, semantic_extensions = {}, {}
        role_errors = validate_interface_signal_roles(
            frozen["interface_contract"], role_extensions=role_extensions
        )
        semantic_errors = validate_interface_semantics(
            frozen["interface_contract"],
            role_extensions=role_extensions,
            semantic_class_extensions=semantic_extensions,
        )
        operation_errors = validate_architecture_operation_features(
            frozen["architecture_contract"]
        )
        if role_errors or semantic_errors or operation_errors or extension_errors:
            raise AgentRuntimeError(
                "Verifier received an invalid taxonomy contract: "
                + "; ".join(
                    role_errors + semantic_errors + operation_errors + extension_errors
                )
            )

    @staticmethod
    def _safe_python_filename(raw: str, *, owned_root: str | None = None) -> str:
        path = Path(str(raw))
        if path.is_absolute() or ".." in path.parts:
            raise AgentRuntimeError(f"Unsafe verification Python path: {raw!r}")
        parts = path.parts
        if len(parts) == 1:
            filename = parts[0]
        elif len(parts) == 2 and owned_root is not None and parts[0] == owned_root:
            filename = parts[1]
        else:
            expected = f"{owned_root}/<file>.py" if owned_root else "<file>.py"
            raise AgentRuntimeError(f"Verification Python path {raw!r} is outside its owned root; expected {expected}")
        normalized = Path(filename)
        if normalized.suffix != ".py" or normalized.name.startswith("."):
            raise AgentRuntimeError(f"Invalid verification Python filename: {raw!r}")
        return normalized.name

    @staticmethod
    def _canonical_test_module(raw: str) -> str:
        """Normalize verifier plan references to a cocotb Python module stem.

        Accepted forms include ``test_core``, ``test_core.py``,
        ``tests/test_core.py``, ``tests.test_core``, and pytest-style selectors such
        as ``tests/test_core.py::test_backpressure``. Cocotb's runner consumes test
        *modules*, so any ``::...`` selector is intentionally reduced to its owning
        module. The generated test file remains the authority for which cocotb tests
        exist inside that module.
        """

        value = str(raw).strip()
        if not value:
            raise AgentRuntimeError("Empty verification test module reference")

        if "::" in value:
            module_part, selector = value.split("::", 1)
            if not module_part.strip() or not selector.strip():
                raise AgentRuntimeError(
                    f"Malformed verification test selector: {raw!r}"
                )
            value = module_part.strip()

        if value.startswith("tests."):
            value = value[len("tests."):]

        if "/" in value or "\\" in value:
            value = value.replace("\\", "/")
            filename = VerifierAgent._safe_python_filename(value, owned_root="tests")
            value = Path(filename).stem
        elif value.endswith(".py"):
            if Path(value).name != value:
                raise AgentRuntimeError(f"Unsafe verification test module reference: {raw!r}")
            value = Path(value).stem

        if not value.isidentifier():
            raise AgentRuntimeError(
                f"Verification test module reference {raw!r} is not a flat importable Python module"
            )
        return value

    @classmethod
    def _write_python(cls, target: Path, item: Mapping[str, Any], *, owned_root: str) -> None:
        filename = cls._safe_python_filename(str(item["path"]), owned_root=owned_root)
        content = str(item["content"])
        (target / filename).write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")

    @classmethod
    def _normalize_plan_test_modules(cls, plan: Mapping[str, Any]) -> None:
        """Canonicalize test-module references before semantic validation/write.

        ``test_modules`` itself must contain unique modules. Regression groups may
        enumerate individual pytest-style selectors from the same generated file;
        those collapse to a single owning cocotb module while preserving first-seen
        order. Every group is constrained to declared ``test_modules``.
        """

        if not isinstance(plan, dict):
            raise AgentRuntimeError("verification_plan must be a mutable mapping")

        modules = [cls._canonical_test_module(item) for item in plan["test_modules"]]
        if len(modules) != len(set(modules)):
            raise AgentRuntimeError("verification_plan.test_modules contains duplicate module references")
        plan["test_modules"] = modules
        declared = set(modules)

        groups = plan.get("regression_groups")
        if not isinstance(groups, dict):
            raise AgentRuntimeError("verification_plan.regression_groups must be a mapping")
        for group_name in ("smoke", "targeted", "full"):
            normalized: list[str] = []
            seen: set[str] = set()
            for item in groups[group_name]:
                module = cls._canonical_test_module(item)
                if module not in seen:
                    normalized.append(module)
                    seen.add(module)
            unknown = sorted(seen - declared)
            if unknown:
                raise AgentRuntimeError(
                    f"verification_plan.regression_groups.{group_name} references undeclared test modules: {unknown}"
                )
            groups[group_name] = normalized

    @classmethod
    def _validate_result(cls, *, result: Mapping[str, Any], context: Mapping[str, Any]) -> None:
        cls._validate_prepared_result(
            result=cls._with_contract_generated_blocks(result, context),
            context=context,
        )

    @classmethod
    def _validate_prepared_result(
        cls, *, result: Mapping[str, Any], context: Mapping[str, Any]
    ) -> None:
        status = result["status"]
        references = list(result["reference_files"])
        tests = list(result["test_files"])
        plan = result["verification_plan"]
        operation_coverage = list(result["operation_coverage"])
        conflict = result["architecture_conflict"]
        manifest = context["frozen_architecture"]["module_manifest"]
        top = str(manifest["top"])
        module_names = {str(item["name"]) for item in manifest["modules"]}

        if status == "ARCHITECTURE_CONFLICT":
            if references or tests:
                raise AgentRuntimeError("ARCHITECTURE_CONFLICT must not emit verification Python files")
            if not isinstance(conflict, Mapping):
                raise AgentRuntimeError("ARCHITECTURE_CONFLICT requires structured conflict details")
            self_invalidating = " ".join(
                str(conflict.get(field, "")).lower()
                for field in ("category", "issue", "evidence", "requested_architect_decision")
            )
            if any(phrase in self_invalidating for phrase in (
                "statements agree", "these statements agree", "no contradiction exists",
                "no conflict exists", "no conflict actually exists", "no ambiguity exists",
                "no architectural decision", "withdraw escalation",
                "regenerate verification instead of escalating",
                "output capacity", "response capacity", "token limit",
                "cannot be completed within this response",
                "verifier_delivery_failure", "artifacts could not be represented",
                "contract itself is consistent",
            )) or (
                (decision := str(conflict.get("requested_architect_decision", "")).strip().lower())
                in {"none", "none."} or decision.startswith(("none;", "none,"))
            ):
                raise AgentRuntimeError(
                    "Verifier ARCHITECTURE_CONFLICT invalidates itself by concluding "
                    "that the contract agrees, needs no Architect decision, or only "
                    "encountered a Verifier-owned response-capacity problem"
                )
            if any(phrase in self_invalidating for phrase in (
                "previous_content", "prior test file content", "prior source",
                "planned_file", "planned file",
            )) and any(
                phrase in self_invalidating
                for phrase in ("truncat", "incomplete", "not available")
            ):
                raise AgentRuntimeError(
                    "Verifier ARCHITECTURE_CONFLICT escalates a defect in the Verifier's "
                    "own prior generated output (previous_content reported as truncated "
                    "or incomplete), not a frozen-contract question; Architect has no "
                    "artifact that fixes this. Emit a fresh, complete replacement for "
                    "the affected file(s) instead of escalating."
                )
            if any(phrase in self_invalidating for phrase in (
                "input_evidence_mismatch",
                "patch_context_mismatch",
                "artifact_mismatch",
                "actual current file snapshot",
                "exact current on-disk artifact",
                "precise validator-flagged region",
                "updated findings",
                "patch_validation_error",
            )):
                raise AgentRuntimeError(
                    "Verifier ARCHITECTURE_CONFLICT describes a Verifier patch/input/"
                    "validator evidence mismatch, not an unresolved frozen hardware "
                    "semantic. Architect cannot provide or repair Verifier-owned file "
                    "snapshots. Continue from previous_verifier_output and correct only "
                    "the remaining deterministic findings."
                )
            if "operation_sampling_bindings" in self_invalidating or "operation sampling bindings" in self_invalidating:
                raise AgentRuntimeError(
                    "OPERATION_SAMPLING_BINDINGS is never a frozen architecture artifact "
                    "and Architect never supplies it: it is a module-level literal list "
                    "that the Verifier itself declares in its own test file content, "
                    "binding each operation coverage point already in operation_coverage "
                    "to a reusable template or custom observer. A missing or invalid "
                    "entry is always a Verifier defect to fix directly, never an "
                    "architecture conflict to escalate."
                )
            if any(phrase in self_invalidating for phrase in (
                "operation obligation id",
                "operation-obligation id",
                "operation coverage id namespace",
                "operation-obligation id namespace",
                "authoritative operation-obligation",
                "verifier-defined operation id namespace",
            )):
                raise AgentRuntimeError(
                    "Operation coverage obligation IDs are generated by the deterministic "
                    "Verifier taxonomy from the frozen operation metadata; they are not "
                    "an Architect-owned interface namespace. Copy the exact IDs supplied "
                    "in the current operation_coverage/coverage findings and correct the "
                    "Verifier files locally instead of escalating an architecture conflict."
                )
            unknown = sorted(set(conflict["affected_modules"]) - module_names)
            if unknown:
                raise AgentRuntimeError(
                    f"Verifier conflict references undeclared modules: {unknown}; "
                    f"affected_modules must use exact names from module_manifest.modules[].name, "
                    f"never a test/reference file name. Declared modules are: {sorted(module_names)}"
                )
            return

        if status != "VERIFICATION_READY":
            raise AgentRuntimeError(f"Unknown verifier status: {status!r}")
        if conflict is not None:
            raise AgentRuntimeError("VERIFICATION_READY cannot also contain architecture_conflict")
        if not references or not tests:
            raise AgentRuntimeError("VERIFICATION_READY requires reference model and cocotb tests")
        extension_errors = validate_verifier_extension_bundles(
            context["frozen_architecture"]["architecture_contract"],
            result.get("feature_extensions", []),
            source_files=[*references, *tests],
            interface=context["frozen_architecture"]["interface_contract"],
        )
        if extension_errors:
            raise AgentRuntimeError(
                "Invalid Verifier feature extensions: " + "; ".join(extension_errors)
            )
        if str(plan["top_module"]) != top:
            raise AgentRuntimeError(f"Verification plan top={plan['top_module']!r} does not match manifest top={top!r}")

        reference_names: set[str] = set()
        for item in references:
            name = cls._safe_python_filename(str(item["path"]), owned_root="reference")
            if name in reference_names:
                raise AgentRuntimeError(f"Duplicate reference filename: {name}")
            reference_names.add(name)
            cls._validate_python_content(name, str(item["content"]), cocotb_required=False)

        test_names: set[str] = set()
        test_modules: set[str] = set()
        test_contents: list[str] = []
        implemented_obligations: set[str] = set()
        minimum_randomized = int(
            context.get("verification_policy", {}).get(
                "randomized_transactions_minimum", 0
            )
        )
        automatic_metadata = build_architect_operation_metadata(
            context["frozen_architecture"]["architecture_contract"],
            context["frozen_architecture"]["interface_contract"],
        )
        automatic_campaign_report = automatic_campaign_support(
            automatic_metadata,
            context["frozen_architecture"]["architecture_contract"],
        )
        # See _with_contract_generated_blocks: obligation bookkeeping stays
        # gated on every operation qualifying (no mixed code-owned/LLM-owned
        # mode yet), but embedding the executable campaign test is safe to
        # relax to "at least one operation qualifies" -- the campaign's own
        # per-operation loop skips whichever operations do not.
        automatic_campaign_supported = bool(automatic_campaign_report["supported"])
        any_operation_campaign_supported = bool(automatic_campaign_report["any_operation_supported"])
        for test_index, item in enumerate(tests):
            name = cls._safe_python_filename(str(item["path"]), owned_root="tests")
            if name in test_names:
                raise AgentRuntimeError(f"Duplicate test filename: {name}")
            test_names.add(name)
            test_modules.add(Path(name).stem)
            if "full" not in set(item["regression_groups"]):
                raise AgentRuntimeError(f"Initial verifier test file {name} must belong to full regression")
            content = str(item["content"])
            try:
                validate_contract_generated_block(
                    content,
                    build_interface_coverage_plan(
                        context["frozen_architecture"]["interface_contract"]
                    ),
                    context["frozen_architecture"]["architecture_contract"],
                    include_automatic_campaign=(
                        any_operation_campaign_supported and test_index == 0
                    ),
                    randomized_transactions_minimum=minimum_randomized,
                )
            except (SyntaxError, ValueError) as exc:
                raise AgentRuntimeError(
                    f"Generated test file {name} has invalid protocol instrumentation: {exc}"
                ) from exc
            cls._validate_python_content(name, content, cocotb_required=True)
            raw_obligations = list(map(str, item["coverage_obligations"]))
            if len(raw_obligations) != len(set(raw_obligations)):
                raise AgentRuntimeError(
                    f"Generated test file {name} coverage_obligations contains duplicates"
                )
            declared_obligations = set(raw_obligations)
            code_obligations = cls._extract_coverage_obligations(name, content)
            if declared_obligations != code_obligations:
                difference = coverage_obligation_mapping_diff(
                    declared_obligations, code_obligations
                )
                raise AgentRuntimeError(
                    f"Generated test file {name} coverage_obligations must match its "
                    "module-level COVERAGE_OBLIGATIONS constant; "
                    f"missing_in_source_constant={difference['missing_in_source_constant']}, "
                    f"unexpected_in_source_constant={difference['unexpected_in_source_constant']}. "
                    "Update only the stale side so both preserve the frozen deterministic plan."
                )
            implemented_obligations.update(declared_obligations)
            test_contents.append(content)

        try:
            operation_plan = operation_plan_for_tests(
                operation_coverage, test_contents,
                context["frozen_architecture"]["architecture_contract"],
                context["frozen_architecture"]["interface_contract"],
            )
        except OperationSamplingError as exc:
            raise AgentRuntimeError(f"Invalid operation sampling bindings: {exc}") from exc
        operation_errors = validate_operation_coverage(
            context["frozen_architecture"]["architecture_contract"],
            effective_operation_coverage(operation_coverage, operation_plan),
        )
        operation_errors.extend(
            validate_frozen_operation_scope(
                context["frozen_architecture"]["architecture_contract"],
                effective_operation_coverage(operation_coverage, operation_plan),
            )
        )
        if operation_errors:
            raise AgentRuntimeError(
                "Invalid operation coverage: " + "; ".join(operation_errors)
            )

        cls._normalize_plan_test_modules(plan)
        normalized_plan_modules = set(map(str, plan["test_modules"]))
        if normalized_plan_modules != test_modules:
            raise AgentRuntimeError(
                "verification_plan.test_modules must reference exactly the generated test files"
            )

        policy = context["verification_policy"]
        minimum_randomized = int(policy.get("randomized_transactions_minimum", 0))
        if int(plan["randomized_test_count"]) < minimum_randomized:
            raise AgentRuntimeError(
                f"Verifier randomized_test_count={plan['randomized_test_count']} is below policy minimum {minimum_randomized}"
            )
        minimum_wall_timeout = int(policy.get("regression_wall_timeout_seconds_minimum", 1))
        if int(plan["timeout_seconds"]) < minimum_wall_timeout:
            raise AgentRuntimeError(
                f"Verifier timeout_seconds={plan['timeout_seconds']} is below full-regression wall-clock policy minimum {minimum_wall_timeout}"
            )
        if set(map(str, plan["regression_groups"]["full"])) != test_modules:
            raise AgentRuntimeError("Initial full regression group must contain every generated test module")

        interface_plan = build_interface_coverage_plan(
            context["frozen_architecture"]["interface_contract"]
        )
        deterministic_plan = merge_coverage_plans(
            interface_plan,
            operation_plan,
        )
        required_obligations = {
            str(item["id"]) for item in deterministic_plan["obligations"]
        }
        # Lifecycle/protocol/operation obligations that the automatic campaign
        # actually drives are deliberately not assigned to LLM-authored
        # COVERAGE_OBLIGATIONS bookkeeping -- per operation and, for a shared
        # protocol channel, only when every operation on it qualifies (see
        # code_owned_obligations_for_supported_operations's docstring for why
        # a wrong attribution here fails loudly at simulation time rather
        # than silently under-covering).
        supported_operation_names = {
            name
            for name, info in automatic_campaign_report["operations"].items()
            if info.get("known_scope_campaign_supported", info["supported"])
        }
        # Wider than supported_operation_names: an operation blocked only on
        # arithmetic still gets real protocol/lifecycle traffic from
        # _run_arithmetic_blocked_operation_smoke, so its own channel/
        # command/status obligations close the same way a fully-supported
        # operation's do (see code_owned_obligations_for_supported_operations's
        # docstring). scope=="operation" obligations stay gated on the
        # narrower set regardless -- only this widens.
        protocol_lifecycle_ready_names = {
            name
            for name, info in automatic_campaign_report["operations"].items()
            if info["protocol_lifecycle_supported"]
        }
        reset_signal = next(
            (
                str(item.get("name", ""))
                for item in context["frozen_architecture"]["interface_contract"].get("signals", [])
                if isinstance(item, dict) and item.get("role") == "reset"
            ),
            None,
        )
        code_owned_runtime_obligations = code_owned_obligations_for_supported_operations(
            deterministic_plan["obligations"],
            automatic_metadata,
            supported_operation_names,
            reset_signal_name=reset_signal,
            protocol_lifecycle_ready_operations=protocol_lifecycle_ready_names,
        )
        operation_names = [
            str(item["operation_name"]) for item in operation_coverage
        ]
        implemented_obligations = {
            canonicalize_operation_obligation_claim(item, operation_names)
            for item in implemented_obligations
        }
        implemented_obligations.update(code_owned_runtime_obligations)
        missing_obligations = sorted(required_obligations - implemented_obligations)
        unknown_obligations = sorted(implemented_obligations - required_obligations)
        if missing_obligations or unknown_obligations:
            raise AgentRuntimeError(
                "Verifier coverage-obligation mapping does not match the deterministic "
                f"plan; missing={missing_obligations}, unknown={unknown_obligations}. "
                "The test artifact coverage_obligations list and its matching "
                "module-level COVERAGE_OBLIGATIONS constant are already required to "
                "be identical: add every missing ID to both and remove every unknown "
                "ID from both. Do not alter the frozen deterministic plan."
            )

        if not automatic_campaign_supported:
            try:
                validate_verifier_authored_structure(
                    test_contents,
                    required_obligations,
                    context["frozen_architecture"]["architecture_contract"],
                    context["frozen_architecture"]["interface_contract"],
                    randomized_transactions_minimum=minimum_randomized,
                    code_owned_obligations=code_owned_runtime_obligations,
                )
            except (SyntaxError, ValueError) as exc:
                raise AgentRuntimeError(
                    f"Verifier TB review structure is invalid: {exc}"
                ) from exc

        # Ready/valid correctness is temporal, not a property of Python loop
        # nesting or variable spelling. The generated TB assertion checks the
        # actual sampled valid/payload history during simulation instead.
        cls._validate_cocotb_phase_safety(test_contents)
        if not automatic_campaign_supported:
            cls._validate_runtime_coverage_instrumentation(test_contents, context)
            cls._validate_required_signal_coverage(test_contents, context)
            cls._validate_operation_coverage_sampling(
                test_contents, operation_coverage,
            )

    @staticmethod
    def _validate_python_content(filename: str, content: str, *, cocotb_required: bool) -> None:
        if not content.strip():
            raise AgentRuntimeError(f"Generated Python file {filename} is empty")
        if "```" in content:
            raise AgentRuntimeError(f"Generated Python file {filename} contains Markdown fences")
        normalized_content = content.lower()
        placeholder_markers = (
            "full source omitted",
            "source omitted",
            "implementation omitted",
            "executable omitted",
            "omitted here",
            "placeholder removed",
            "actual artifact generation",
        )
        if any(marker in normalized_content for marker in placeholder_markers):
            raise AgentRuntimeError(
                f"Generated Python file {filename} contains omitted/placeholder source"
            )
        try:
            tree = ast.parse(content, filename=filename, mode="exec")
        except SyntaxError as exc:
            raise AgentRuntimeError(f"Generated Python file {filename} has syntax error: {exc.msg}") from exc

        if cocotb_required and any(isinstance(node, ast.Raise) for node in tree.body):
            raise AgentRuntimeError(
                f"Generated test file {filename} contains a top-level raise instead of executable tests"
            )

        imported_cocotb = False
        cocotb_module_aliases: set[str] = set()
        local_checker_calls = _local_checker_run_calls(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    imported_cocotb = imported_cocotb or root == "cocotb"
                    if root == "cocotb":
                        cocotb_module_aliases.add(alias.asname or root)
                    if root in _FORBIDDEN_IMPORT_ROOTS:
                        raise AgentRuntimeError(f"Generated verification file {filename} imports forbidden capability {root}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".", 1)[0]
                imported_cocotb = imported_cocotb or root == "cocotb"
                if root in _FORBIDDEN_IMPORT_ROOTS:
                    raise AgentRuntimeError(f"Generated verification file {filename} imports forbidden capability {root}")
                if module == "cocotb.result" and any(alias.name == "SimTimeoutError" for alias in node.names):
                    raise AgentRuntimeError(
                        f"Generated test file {filename} uses obsolete cocotb 2.x API: import SimTimeoutError from cocotb.triggers, not cocotb.result"
                    )
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CALL_NAMES:
                    raise AgentRuntimeError(f"Generated verification file {filename} calls forbidden capability {node.func.id}")
                if isinstance(node.func, ast.Attribute) and node.func.attr in _FORBIDDEN_CALL_ATTRIBUTES and node not in local_checker_calls:
                    raise AgentRuntimeError(f"Generated verification file {filename} calls forbidden capability {node.func.attr}")
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in cocotb_module_aliases
                    and node.func.attr == "start"
                ):
                    raise AgentRuntimeError(
                        f"Generated test file {filename} uses obsolete cocotb API cocotb.start(); use cocotb.start_soon()"
                    )
        if cocotb_required and not imported_cocotb:
            raise AgentRuntimeError(f"Generated test file {filename} does not import cocotb")
        if cocotb_required and not any(
            isinstance(node, ast.AsyncFunctionDef)
            and any(
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id in cocotb_module_aliases
                and decorator.func.attr == "test"
                for decorator in node.decorator_list
            )
            for node in tree.body
        ):
            raise AgentRuntimeError(
                f"Generated test file {filename} contains no executable async "
                "@cocotb.test() functions; imports, coverage declarations and "
                "comments are not test bodies. Return complete executable source "
                "now, not a description of future runtime delivery."
            )

    @staticmethod
    def _extract_coverage_obligations(filename: str, content: str) -> set[str]:
        """Read a literal module-level traceability declaration from generated tests."""
        try:
            return extract_literal_coverage_obligations(filename, content)
        except (SyntaxError, ValueError) as exc:
            raise AgentRuntimeError(str(exc)) from exc

    @staticmethod
    def _validate_runtime_coverage_instrumentation(
        test_contents: list[str], context: Mapping[str, Any]
    ) -> None:
        """Require every cocotb test to run the generated TB snapshot monitor."""

        clock_name = str(
            context["frozen_architecture"]["interface_contract"].get("clock", "")
        )
        for content in test_contents:
            tree = ast.parse(content, mode="exec")
            imported = any(
                isinstance(node, ast.ImportFrom)
                and node.module == "multigent.verifier_tool"
                and any(alias.name == "contract_coverage" for alias in node.names)
                for node in tree.body
            )
            cocotb_tests = []
            for node in ast.walk(tree):
                if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    continue
                cocotb_decorators = [
                    decorator
                    for decorator in node.decorator_list
                    if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id in {"cocotb", "_contract_cocotb"}
                    and decorator.func.attr == "test"
                    )
                ]
                if not cocotb_decorators:
                    continue
                cocotb_tests.append(node.name)
                keywords = {
                    keyword.arg
                    for keyword in cocotb_decorators[0].keywords
                    if keyword.arg is not None
                }
                if not {"timeout_time", "timeout_unit"} <= keywords:
                    raise AgentRuntimeError(
                        f"Cocotb test {node.name} must declare timeout_time and "
                        "timeout_unit in @cocotb.test()"
                    )
                coverage_decorators = [
                    decorator
                    for decorator in node.decorator_list
                    if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "contract_coverage"
                    )
                ]
                if not coverage_decorators:
                    raise AgentRuntimeError(
                        f"Cocotb test {node.name} must use @contract_coverage()"
                    )
                if len(coverage_decorators) != 1 or any(
                    decorator.args or decorator.keywords
                    for decorator in coverage_decorators
                ):
                    raise AgentRuntimeError(
                        f"Cocotb test {node.name} must call @contract_coverage() "
                        "with no positional or keyword arguments; coverage obligations "
                        "are installed by the deterministic tool"
                    )
            if not cocotb_tests:
                raise AgentRuntimeError(
                    "Every generated test file must contain at least one @cocotb.test()"
                )
            if not imported:
                raise AgentRuntimeError(
                    "Generated cocotb tests must import contract_coverage from "
                    "multigent.verifier_tool"
                )
            direct_clock_drives = {
                target.value.attr
                for assignment in ast.walk(tree)
                if isinstance(assignment, (ast.Assign, ast.AnnAssign))
                for target in (
                    assignment.targets
                    if isinstance(assignment, ast.Assign)
                    else [assignment.target]
                )
                if isinstance(target, ast.Attribute)
                and target.attr == "value"
                and isinstance(target.value, ast.Attribute)
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "dut"
                and target.value.attr == clock_name
            }
            if direct_clock_drives:
                raise AgentRuntimeError(
                    f"Generated cocotb tests must run {clock_name} with a free-running "
                    "cocotb Clock; direct test writes to the monitored clock can deadlock"
                )

    @staticmethod
    def _validate_operation_coverage_sampling(
        test_contents: list[str], operation_coverage: list[Mapping[str, Any]],
    ) -> None:
        """Require exact checked-job ledger hooks, not test-authored coverage values."""

        required_operations = {str(item.get("operation_name")) for item in operation_coverage}
        if not required_operations:
            return
        recorder_calls = 0
        raw_recorder_calls = 0
        checked_operations: set[str] = set()
        sampled: set[str] = set()
        unlinked_samples = 0
        for content in test_contents:
            tree = ast.parse(content, mode="exec")
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "record_stimulus"
                ):
                    raw_recorder_calls += 1
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "_contract_record_checked_stimulus"
                ):
                    recorder_calls += 1
                    operation_nodes = [
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg == "operations"
                    ]
                    try:
                        operations = ast.literal_eval(operation_nodes[0])
                    except (IndexError, TypeError, ValueError, SyntaxError) as exc:
                        raise AgentRuntimeError(
                            "Every _contract_record_checked_stimulus call needs one "
                            "literal operations tuple"
                        ) from exc
                    if (
                        not isinstance(operations, (list, tuple))
                        or not operations
                        or not all(isinstance(item, str) for item in operations)
                    ):
                        raise AgentRuntimeError(
                            "_contract_record_checked_stimulus operations must be a "
                            "non-empty literal string tuple"
                        )
                    checked_operations.update(operations)
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "sample_operation"
                    and len(node.args) >= 3
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    continue
                has_stimulus_id = len(node.args) >= 4 or any(
                    keyword.arg == "stimulus_id" for keyword in node.keywords
                )
                if not has_stimulus_id:
                    unlinked_samples += 1
                operation_name = node.args[0].value
                sampled.add(operation_name)
        if raw_recorder_calls:
            raise AgentRuntimeError(
                "Generated operation tests must use the code-inserted "
                "_contract_record_checked_stimulus helper, not raw record_stimulus"
            )
        if recorder_calls == 0:
            raise AgentRuntimeError(
                "Generated operation tests must call "
                "_contract_record_checked_stimulus so catalog operation assertions "
                "run before stimulus evidence is persisted"
            )
        if unlinked_samples:
            raise AgentRuntimeError(
                "Every sample_operation call must reference the stimulus_id returned "
                "by _contract_record_checked_stimulus as its fourth argument"
            )
        missing_checks = sorted(required_operations - checked_operations)
        unknown_checks = sorted(checked_operations - required_operations)
        if missing_checks or unknown_checks:
            raise AgentRuntimeError(
                "Catalog operation checks must name the exact contract operations; "
                f"missing={missing_checks}, unknown={unknown_checks}"
            )

    @staticmethod
    def _validate_cocotb_phase_safety(test_contents: list[str]) -> None:
        """Do not mix DUT writes and ReadOnly waits in one coroutine.

        A coroutine resumes in the simulator ReadOnly phase after ``await ReadOnly()``.
        A loop that then returns to a DUT assignment fails at runtime before the next
        edge. Keeping active drivers and ReadOnly monitors in separate coroutines is a
        simple, statically enforceable discipline that prevents this class of failure.
        """

        for content in test_contents:
            tree = ast.parse(content, mode="exec")
            for function in (
                node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
            ):
                has_read_only_wait = any(
                    isinstance(node, ast.Await)
                    and isinstance(node.value, ast.Call)
                    and (
                        (
                            isinstance(node.value.func, ast.Name)
                            and node.value.func.id == "ReadOnly"
                        )
                        or (
                            isinstance(node.value.func, ast.Attribute)
                            and node.value.func.attr == "ReadOnly"
                        )
                    )
                    for node in ast.walk(function)
                )
                if not has_read_only_wait:
                    continue
                writes_dut = any(
                    isinstance(target, ast.Attribute)
                    and target.attr == "value"
                    and isinstance(target.value, ast.Attribute)
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == "dut"
                    for assignment in ast.walk(function)
                    if isinstance(assignment, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                    for target in (
                        assignment.targets
                        if isinstance(assignment, ast.Assign)
                        else [assignment.target]
                    )
                )
                if writes_dut:
                    raise AgentRuntimeError(
                        f"Generated cocotb coroutine {function.name} both drives DUT "
                        "signals and awaits ReadOnly(); separate the active driver from "
                        "ReadOnly monitoring to avoid writes during the ReadOnly phase. "
                        "For a post-RisingEdge sample that must remain in this driving "
                        "coroutine, replace ReadOnly() with a small Timer before reading; "
                        "do not remove the settling wait and do not add another ReadOnly()"
                    )

    @staticmethod
    def _dut_aliases(tree: ast.AST) -> set[str]:
        """Recognize explicit DUT aliases, without guessing signal roles by name.

        This is a presence check, not proof that a signal was exercised or checked.
        Runtime coverage and assertions remain responsible for that evidence.
        """

        aliases = {"dut"}
        functions = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assignments = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]
        changed = True
        while changed:
            changed = False
            for assignment in assignments:
                value = assignment.value
                if not isinstance(value, (ast.Name, ast.Attribute)):
                    continue
                if ast.unparse(value) not in aliases:
                    continue
                targets = (
                    assignment.targets if isinstance(assignment, ast.Assign)
                    else [assignment.target]
                )
                for target in targets:
                    if isinstance(target, (ast.Name, ast.Attribute)):
                        name = ast.unparse(target)
                        if name not in aliases:
                            aliases.add(name)
                            changed = True
            for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
                if not isinstance(call.func, ast.Name) or call.func.id not in functions:
                    continue
                function = functions[call.func.id]
                parameters = list(function.args.posonlyargs) + list(function.args.args)
                for argument, parameter in zip(call.args, parameters):
                    if isinstance(argument, (ast.Name, ast.Attribute)) and ast.unparse(argument) in aliases:
                        if parameter.arg not in aliases:
                            aliases.add(parameter.arg)
                            changed = True
                by_name = {parameter.arg: parameter for parameter in parameters}
                for keyword in call.keywords:
                    if keyword.arg not in by_name:
                        continue
                    if isinstance(keyword.value, (ast.Name, ast.Attribute)) and ast.unparse(keyword.value) in aliases:
                        if keyword.arg not in aliases:
                            aliases.add(keyword.arg)
                            changed = True
        return aliases

    @classmethod
    def _validate_required_signal_coverage(
        cls, test_contents: list[str], context: Mapping[str, Any]
    ) -> None:
        interface = context["frozen_architecture"]["interface_contract"]
        policy = context["verification_policy"]
        signals = list(interface.get("signals", []))

        referenced: set[str] = set()
        for content in test_contents:
            tree = ast.parse(content, mode="exec")
            dut_aliases = cls._dut_aliases(tree)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, (ast.Name, ast.Attribute))
                    and ast.unparse(node.value) in dut_aliases
                ):
                    referenced.add(node.attr)
                elif (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "getattr"
                    and len(node.args) >= 2
                    and isinstance(node.args[0], (ast.Name, ast.Attribute))
                    and ast.unparse(node.args[0]) in dut_aliases
                    and isinstance(node.args[1], ast.Constant)
                    and isinstance(node.args[1].value, str)
                ):
                    referenced.add(node.args[1].value)

        required: set[str] = set()
        if policy.get("require_completion_behavior_tests_when_defined"):
            required |= signals_with_coverage_tags(signals, {"completion"})
        if policy.get("require_error_behavior_tests_when_defined"):
            required |= signals_with_coverage_tags(signals, {"error"})

        missing = sorted(required - referenced)
        if missing:
            raise AgentRuntimeError(
                "Verifier claims readiness without referencing required role-tagged completion/error signals: "
                + ", ".join(missing)
            )

    @staticmethod
    def _build_task(context: Mapping[str, Any]) -> str:
        serialized = yaml.safe_dump(dict(context), sort_keys=False, default_flow_style=False)
        signal_roles = render_signal_role_catalog()
        interface_semantics = render_interface_semantic_catalog()
        coverage_seed = yaml.safe_dump(
            derive_interface_coverage_seed(
                context["frozen_architecture"]["interface_contract"]
            ),
            sort_keys=False,
            default_flow_style=False,
        )
        coverage_plan = yaml.safe_dump(
            build_interface_coverage_plan(
                context["frozen_architecture"]["interface_contract"]
            ),
            sort_keys=False,
            default_flow_style=False,
        )
        operation_catalog = (
            render_operation_coverage_catalog()
            + "\n"
            + render_operation_assertion_catalog()
        )
        sampling_catalog = render_operation_sampling_catalog()
        operation_metadata = build_architect_operation_metadata(
            context["frozen_architecture"]["architecture_contract"],
            context["frozen_architecture"]["interface_contract"],
        )
        unrepresentable_operations = list(operation_metadata.get("unrepresentable_operations", []))
        campaign_support = automatic_campaign_support(
            operation_metadata,
            context["frozen_architecture"]["architecture_contract"],
        )
        # synthesize_code_owned_operation_coverage is per-concept, not
        # per-operation: called with no prior LLM specs, it emits
        # deterministic coverpoints for exactly the concepts
        # supported_code_owned_concepts already says are code-owned (which
        # is an arithmetic/classifier question, independent of whether this
        # operation's protocol or lifecycle also qualifies) and silently
        # omits everything else -- safe to compute unconditionally, in the
        # fully-supported case and the partial one alike, since a concept it
        # cannot yet own just does not appear in the seed.
        code_owned_coverage_seed = yaml.safe_dump(
            synthesize_code_owned_operation_coverage(
                [],
                context["frozen_architecture"]["architecture_contract"],
                operation_metadata,
            ),
            sort_keys=False,
            default_flow_style=False,
        )
        if campaign_support["supported"]:
            automatic_ownership_text = f"""
CODE-OWNED AUTOMATIC CAMPAIGN (OVERRIDES GENERAL MANUAL-TB RULES BELOW)
---------------------------------------------------------------------
- This frozen contract is fully supported by verifier_tool. Python code owns the
  known operation golden model, directed and randomized vectors, ready/valid
  traffic, exact short/long input and output stalls, command legality, reset at
  every external job phase, abort/recovery, lifecycle assertions, and runtime
  coverage sampling. The pipeline appends the real executable cocotb test after
  your structured response.
- Do not duplicate that work in LLM source. Do not write another golden model,
  ready/valid driver, output collector, reset sequence, illegal-command test,
  backpressure loop, directed-vector loop, randomized loop, operation sampler,
  lifecycle checker, or manual coverage-intent ledger for the known scope.
- The response schema still requires one reference file and one test file. Emit a
  compact reference ownership marker and a compact test host containing exactly a
  module-level literal ``COVERAGE_OBLIGATIONS = set()``. No manual ``@cocotb.test``
  is needed: code installs the executable campaign before source validation.
- The response schema also still requires ``operation_coverage``. Copy the
  deterministic seed below for clarity. Code rebuilds all known points from the
  frozen feature list, so these declarations are not an LLM decision. Add source,
  observers, stimulus, or coverage only if the frozen Architect contract contains
  a genuinely non-code-owned feature; this contract contains none.
- Set verification_plan.randomized_test_count to at least the policy minimum and
  list the compact test host in every selected regression group. The generated
  runtime, not this declared number, proves that the randomized jobs executed.
- Later general rules about manually authored stimulus, bindings, checked-stimulus
  calls, status-signal references, and per-test ``@contract_coverage`` decorators
  apply only when this section says a feature is LLM-owned.

DETERMINISTIC CODE-OWNED OPERATION_COVERAGE SEED
{code_owned_coverage_seed}
"""
        elif campaign_support["any_operation_supported"]:
            supported_ops = sorted(
                name for name, info in campaign_support["operations"].items() if info["supported"]
            )
            arithmetic_only_blocked_ops = sorted(
                name for name, info in campaign_support["operations"].items()
                if not info["supported"]
                and info["protocol_lifecycle_supported"]
                and info["arithmetic_reasons"]
                and not info.get("lifecycle_extension_fields")
            )
            contract_extension_ops = sorted(
                name for name, info in campaign_support["operations"].items()
                if info.get("lifecycle_extension_fields")
                and info.get("known_scope_campaign_supported")
            )
            fully_blocked_lines = "\n".join(
                f"  - {name}: {'; '.join(info['reasons'])}"
                for name, info in sorted(campaign_support["operations"].items())
                if not info["supported"]
                and not info["protocol_lifecycle_supported"]
                # Operations that did not compile have their own section below.
                and not info.get("compile_blocked")
            )
            arithmetic_only_blocked_lines = "\n".join(
                f"  - {name}: {'; '.join(info['arithmetic_reasons'])}"
                for name, info in sorted(campaign_support["operations"].items())
                if name in arithmetic_only_blocked_ops
            )
            automatic_ownership_text = f"""
LLM-EXTENSION CAMPAIGN (PARTIAL -- PER-OPERATION BREAKDOWN BELOW IS EXACT)
--------------------------------------------------------------------------
- This contract has a mix of operations across three buckets, not just two.
  Use this exact breakdown; do not re-derive it yourself by re-reading the
  contract.
- Fully code-owned (do not write driving code, a golden model, a stimulus
  loop, or coverage bookkeeping for these -- the generated campaign already
  drives, checks, and samples coverage for them):
  {supported_ops}
- Arithmetic-blocked only -- protocol and lifecycle are still fully
  code-owned for these (reasons below name only ``operation_profile_not_executable``
  or ``llm_extension_features``, never protocol/lifecycle/shape): the
  generated campaign already drives real traffic through these operations'
  own channels and command/status signals and samples their
  channel/command/status coverage, exactly like a fully code-owned
  operation's -- do not write a protocol/lifecycle driver or declare their
  channel/command/status obligations. What you *do* still own for these:
  the golden model/correctness check itself (still reuse
  ``_contract_generate_operation_stimulus``/
  ``_contract_generate_random_operation_stimuli`` for stimulus and expected
  values if useful, but nothing here checks them automatically) and this
  operation's own arithmetic-concept coverage
  (``operation_coverage``/``COVERAGE_OBLIGATIONS`` for its ``scope ==
  "operation"`` obligations specifically):
{arithmetic_only_blocked_lines or "  (none)"}
- Contract-local lifecycle extension only -- the generated campaign preserves
  and executes every safe known sibling feature for these operations. Implement
  only the listed missing lifecycle policy fields through the exact extension
  worklist and feature_extensions bundle below; do not replace their existing
  protocol driver, arithmetic golden model, or unrelated lifecycle checks:
  {[(name, campaign_support['operations'][name]['lifecycle_extension_fields']) for name in contract_extension_ops] or '(none)'}
- Fully blocked -- protocol, lifecycle, or shape itself is the problem, so
  nothing here is automatic, including driving: own everything for these,
  exactly as the general manual-TB rules below describe:
{fully_blocked_lines or "  (none)"}
- ``operation_coverage`` for the code-owned concepts above (both the fully
  code-owned bucket and the arithmetic-only-blocked bucket's non-arithmetic
  obligations) is already synthesized for you -- copy the seed below; it
  silently omits any operation or concept this tool cannot yet own, so it
  never conflicts with what you add yourself. Do not hand-author
  ``operation_coverage`` entries duplicating what the seed already gives
  you, and do not declare the omitted ones in a test file's
  ``COVERAGE_OBLIGATIONS`` constant either -- the deterministic plan and
  this breakdown are the only source of truth for which IDs still need your
  bookkeeping.

DETERMINISTIC CODE-OWNED OPERATION_COVERAGE SEED (for the operations listed as fully code-owned above only)
{code_owned_coverage_seed}
"""
        else:
            automatic_ownership_text = """
LLM-EXTENSION CAMPAIGN
----------------------
The frozen operation set is not completely executable by verifier_tool. Follow
the general manual-TB rules below only for the unsupported operation/features;
reuse every generated protocol/assertion/coverage helper that does apply.
"""
        if unrepresentable_operations:
            unrepresentable_lines = "\n".join(
                f"  - {item['name']} [{item.get('reason_code', 'unclassified')}; "
                f"{item.get('category', 'unclassified')}; owner={item.get('owner', 'unknown')}]: "
                f"{item['reason']}\n      resolution: {item.get('resolution_hint', 'n/a')}\n"
                f"      required lifecycle/operation features it blocks: "
                f"{', '.join(item.get('affected_feature_ids', [])) or 'none listed'}"
                for item in unrepresentable_operations
            )
            automatic_ownership_text += f"""
OPERATIONS THAT COULD NOT BE COMPILED (DISTINCT FROM "FULLY BLOCKED" ABOVE)
-------------------------------------------------------------------------------
- These operations could not be compiled into architect_operation_metadata, so
  nothing else in this section applies to them, even if it says "fully supported"
  above: no code-owned driver, checker, or coverage sampler exists for them.
- Each entry names its defect (reason_code), its category and who owns the fix.
  contract_error: the frozen contract is at fault and only the Architect can correct
  it -- you cannot fix it and must not work around it. tool_capability: the contract is
  valid but verifier_tool has no automatic path for it (an engineer adds support to
  verifier_tool; you never invent a lifecycle policy or protocol behavior on the
  tool's behalf).
- Their contract-required lifecycle obligations REMAIN in the deterministic plan
  (the operation.<name>.* IDs). They are not code-owned, so the deterministic
  comparison expects them in COVERAGE_OBLIGATIONS, and they are required: a bin nothing
  hits fails the run, reported under the blocker named in each entry. Their bins are
  sampled only by tool-owned monitors for compiled operations and no public API
  records hits for them from Verifier-authored code, so do not fabricate coverage or
  edit tool-owned code to close them; list the gap in known_verification_gaps.
- Author everything else for these operations by hand -- golden model, protocol
  driver, lifecycle checks -- exactly as the general manual-TB rules below describe,
  with zero code-owned help. Do not assume any generated protocol/lifecycle/coverage
  helper applies to these operations' own channels or status signals just because it
  applies to other operations sharing the same interface.
{unrepresentable_lines}
"""
        policy = context["verification_policy"]
        interface_signals = context["frozen_architecture"]["interface_contract"].get(
            "signals", []
        )
        required_status_signals: set[str] = set()
        if policy.get("require_completion_behavior_tests_when_defined"):
            required_status_signals |= signals_with_coverage_tags(
                interface_signals, {"completion"}
            )
        if policy.get("require_error_behavior_tests_when_defined"):
            required_status_signals |= signals_with_coverage_tags(
                interface_signals, {"error"}
            )
        required_status_text = ", ".join(sorted(required_status_signals)) or "none"
        declared_module_names = ", ".join(
            sorted(
                str(item["name"])
                for item in context["frozen_architecture"]["module_manifest"]["modules"]
            )
        ) or "none"
        extension_authoring = render_extension_authoring_guide()
        extension_worklist = render_requested_extension_worklist(
            context["frozen_architecture"]["architecture_contract"],
            context["frozen_architecture"]["interface_contract"],
        )
        return f"""Create an independent executable verification environment for the frozen hardware contract.

{automatic_ownership_text}

{extension_authoring}

EXACT CONTRACT-LOCAL EXTENSION WORKLIST
---------------------------------------
{extension_worklist}

FIRST-CANDIDATE COMPLETENESS CHECK
----------------------------------
- Make the initial test source executable and auditable, not a plan to finish later.
  Pair every STIMULUS_COVERAGE_INTENTS label with a real
  _contract_record_checked_stimulus call using that exact literal label after
  actually checked DUT traffic. Code adds a # STIMULUS comment only at a matching
  call; declaring an unexecuted intent is an error, not a formatting shortcut.
  Every intent entry needs at least one exact obligation ID in its targets;
  never include a convenient case with targets=[] merely to record it.
- Keep expected outputs derived from the independent oracle and observed outputs
  derived from accepted DUT transfers/status. Never pass the same constructed
  mapping as both expected and observed or copy planned configuration into an
  observed transaction without reading the accepted configuration handshake.
- Give every Verifier-authored bare assert its required feature comment before
  returning the first source. Pipeline-owned protocol/catalog assertions and their
  comments are inserted by code; do not duplicate them.
- Build the external transaction checker before recording a job: enforce the
  contract's accepted phase/count/order, persistent extra-stream-output rejection,
  and completion/error/reset association where the frozen contract requires them.
  A producer-generated beat count is not proof that no forbidden or extra DUT
  transfer occurred. Observe all accepted transfers and status pulses continuously
  across loading, compute, output, completion, idle and next-job boundaries.
- Explicitly read and assert each required completion/error role signal through
  dut.<exact signal name> or literal getattr(dut, "<exact signal name>") in the
  first TB. Dynamic tuple-driven getattr names do not establish that the correct
  required signal was ever checked.
- For packed command/configuration fields, calculate the active slice width and
  legality bound from the frozen default parameter values for this regression;
  do not silently reuse a GEMM-like fixed 4-bit nibble/8-bound convention when
  the selected contract has different parameter defaults.
- For unknown/novel points not handled by architect_operation_metadata, emit
  OPERATION_SAMPLING_BINDINGS as an inert module-level literal list (or an
  alias to inert literal containers). Spell out each entry. Do not build that
  list with a for-comprehension, function call, mutation, or runtime loop, even
  when the iterable happens to be a fixed tuple; the safe source extractor does
  not execute Python to discover bindings.
- Every binding's "point" must be the exact same literal coverpoint id string
  you declared for that point in operation_coverage; never invent, abbreviate,
  reformat, or re-derive a spelling in OPERATION_SAMPLING_BINDINGS. Copy it
  character-for-character from where you declared the coverpoint. This applies
  to every template, including channel_stall: declare the coverpoint in
  operation_coverage first, then bind it; a binding with no matching declared
  coverpoint is rejected even though the sampled data itself is code-owned.
- Each checked stimulus call must show label="<case_id>" as a literal directly
  in _contract_record_checked_stimulus(...). Do not hide its label behind a helper
  parameter or `label=label`: that prevents code from installing and auditing the
  per-case # STIMULUS comment even if the helper's callers pass literal strings.
- Do not define operation coverpoints with constant True/1 observers or with
  result-transfer presence as a proxy for arithmetic stage order, overflow,
  pre-activation sign, or accepted shape. Bind accepted operands/configuration
  and actual output state where the feature needs transaction evidence.
- Before claiming a stimulus label targets a channel-stall bin or operation
  boundary, construct the actual presented-valid plus not-ready overlap and the
  actual accepted values that make that target reachable. Otherwise narrow the
  label's target list and supply another directed case for the uncovered IDs.

INDEPENDENCE BOUNDARY
---------------------
- The envelope contains the original request, fixed verification policy, and frozen
  Architect artifacts only. Generated RTL and RTL Generator output are absent.
- Do not ask for RTL or infer expected behavior from implementation conventions.
- Generated Python may not use filesystem, subprocess, dynamic-import, or network
  capabilities. Deterministic Verilator/cocotb nodes execute your artifacts later.

DECISION OWNERSHIP
------------------
- Architect owns externally observable behavior: accepted commands, framing,
  arithmetic, output ordering, reset/error semantics, and any promised latency.
- Verifier owns coverage field names/types, predicates, reachable bin selection,
  helpers, stimulus distributions, and test scheduling. You must choose these from
  the frozen semantics; Architect need not supply an executable coverage schema.
  Map each mandated feature/concept to your own concrete transaction fields.
  For runtime-bound operation points (rule 18), Verifier selects static DUT
  connections; code owns value reads, type decoding and effective bin construction.
  Use separate dimension points for each relevant axis (for example M, N and K),
  not one M-only point claiming all dimension coverage. A matched feature name
  alone never establishes the correct observation source or numeric semantics.
- A handshake-driven test needs event ordering and transfer rules, not a fully
  specified cycle-by-cycle ready/arbitration schedule. Test the contract's partial
  order, count/order outputs on handshakes, and use finite watchdogs for deadlock.
  A test budget is not an invented exact latency promise. Do not assert an exact
  completion offset unless the contract promises one. Observe completion/error
  concurrently with traffic so a pulse is not missed while joining producers.
- The deterministic regression uses default elaboration: no compile-time parameter
  overrides. Declared parameter default expressions are the active bounds/config
  for this run; configurable parameters do not make their declared defaults
  ambiguous. Parameter sweeps are additional experiments, not implicit requirements
  of this run. Use ``execution_configuration`` when supplied for run provenance.
- Contract widths may be literal integers or symbolic SystemVerilog expressions.
  In generated cocotb, obtain an elaborated signal width with ``len(dut.signal)``;
  never pass a symbolic contract expression such as a parameter name or ``$clog2``
  expression to Python ``int()``.
- Apply legality rules to values representable by the declared encoding. Generate
  illegal encodable values when error behavior is defined; do not request behavior
  for values outside the physical port width unless an encoding defines them.
  For an unsigned field of width w, its encodings are 0..(2**w-1). If the default
  legal bound is smaller than that upper encoding, the over-bound illegal cases
  are representable: generate them. Never label your own proof of representability
  as ARCHITECTURE_CONFLICT or ask Architect to restate the same arithmetic.
  If a criterion says to exercise each over-bound value per dimension, vary one
  dimension at a time with the others legal. Do not infer a Cartesian product of
  all illegal combinations unless the contract explicitly requires it; that
  test-volume choice is Verifier-owned, not an Architect behavior conflict.
- Command acceptance and command legality are distinct: a handshake can accept an
  illegal command and lead to an error instead of creating a pending legal job.
  Read explicit transition rules together; a pending-legal-job rule does not cancel
  an explicitly defined accepted-illegal-command rule.
- If you return ARCHITECTURE_CONFLICT, architecture_conflict.affected_modules must
  contain only exact names from module_manifest.modules[].name. The declared
  modules for this contract are: {declared_module_names}. Never put a test or
  reference file name/path there.
- Return ARCHITECTURE_CONFLICT only for an external behavior that genuinely needs
  an Architect choice to define expected results. Cite the exact conflicting or
  missing contract statements and the two incompatible observable outcomes. Do
  not escalate verifier-owned field names, prior-TB absence, helper structure,
  unpromised exact cycle timing, unrepresentable stimulus values, or limitations
  of this verification runtime's coverage/observer API. A per-point observer may
  independently reconstruct a complete job from clock-bound external signals
  and its own state; shared observer state or a new Architect job identifier is
  not required. If the current TB cannot do that, repair its bindings/observer
  or report a Verifier-owned gap, never ask Architect to change the DUT contract.
  Check arithmetic for any claimed exact-cycle contradiction: if your evidence
  concludes that the schedule and formula agree, do not emit a conflict. Genuine
  functional/protocol contradictions must still be reported; never invent them
  away merely to produce VERIFICATION_READY.

OUTPUT RULES
------------
1. Return VERIFICATION_READY with reference/test contents and a complete plan, or
   ARCHITECTURE_CONFLICT when an executable oracle requires a new Architect decision.
   If VERIFIER CONTEXT contains architect_resolution, treat it as Architect's
   authoritative answer to the cited prior question. Do not repeat that question;
   implement the resolved existing contract unless a distinct contradiction remains.
2. Reference paths may be foo.py or reference/foo.py; test paths may be bar.py or
   tests/bar.py. No nested/cross-owned paths.
   Every ``content`` field must contain the complete executable source. A comment,
   outline, summary, ellipsis, top-level placeholder exception, or promise of
   omitted code is invalid. Never mention omitted/placeholder test code in
   ``known_verification_gaps``: output the executable test instead.
   Response length, token budget, delivery format, or lack of prior source is never an
   architecture conflict. Keep helpers and prose compact, but emit every executable
   source file in full.
   The JSON source strings are saved verbatim and executed; no later agent fills
   in missing bodies. Prioritize compact complete test functions and helpers over
   coverage prose. Imports plus COVERAGE_OBLIGATIONS alone are never a test suite.
3. verification_plan.test_modules and regression_groups identify generated cocotb
   Python modules. Bare module names are preferred. If a pytest-style ``::test``
   selector is emitted, the runtime canonicalizes it to its owning cocotb module.
4. Full regression contains every generated test module and meets the randomized
   transaction minimum with a deterministic seed.
5. verification_plan.timeout_seconds is the wall-clock budget for the whole
   regression and must satisfy the policy minimum; tests need separate simulation
   timeouts/bounded waits.
6. Use cocotb 2.x APIs: cocotb.start_soon(), and SimTimeoutError from cocotb.triggers.
   Start the contract clock once per test with a free-running
   ``cocotb.clock.Clock(...).start()`` task. Do not implement a tick helper by
   writing the DUT clock directly because the trusted coverage monitor observes the
   same edge. Every ``@cocotb.test`` decorator must include finite literal
   ``timeout_time`` and ``timeout_unit`` arguments.
7. For ready/valid input sources, randomized throttling may delay presenting a beat,
   but once valid=1 for a beat, keep valid=1 and payload stable until ready&&valid.
   Deasserting valid after a recorded handshake is legal, including inside a loop;
   dropping it while a presented beat is still stalled is illegal.
   Respect cocotb scheduling phases when checking a synchronous transfer: drive
   ready/valid during the inactive half-cycle and snapshot valid/ready/payload in a
   stable pre-active-edge phase. With the rising-edge contract clock, use
   ``FallingEdge`` to drive, then a small sub-half-cycle ``Timer`` to settle/sample,
   then ``RisingEdge`` to commit that recorded transfer. Keep values stable from
   the pre-edge snapshot through the active edge. ``RisingEdge`` alone is not a
   portable pre-evaluation snapshot in Verilator. A coroutine that writes any
   ``dut.<signal>.value`` must not
   also await ``ReadOnly()``; keep active drivers and ReadOnly monitors in separate
   coroutines. Use ``ReadOnly`` in a read-only observer, or a small sub-cycle Timer
   in a driver, to inspect registered outputs caused by
   that transfer. Never decide whether a handshake occurred from post-edge values,
   because a compliant registered producer may already have cleared valid. Do not
   write DUT inputs while in the ReadOnly phase.
   If a coroutine first discovers ``valid`` only after the current FallingEdge (for
   example after a Timer or ReadOnly observation), it is too late to change
   ``ready`` for that same upcoming active edge. Hold the existing ready value
   through the rising edge and schedule the release immediately after the next
   awaited FallingEdge. Never create a stall-release handshake by writing ready in
   the middle of a half-cycle; the contract-generated TB block intentionally
   captures the pre-active-edge transaction state once for assertions and coverage.
   When a test assigns a DUT input and also needs a local expected/held value, retain
   the Python value that was assigned (or explicitly settle before reading it back);
   do not assume an immediate simulator-handle read reflects a same-delta write.
   Also derive cross-channel consumption order from the frozen scheduling and channel
   ordering contracts. If the DUT may alternate readiness between two input streams
   in one phase, never await all beats of stream A before starting stream B: either
   launch independent producer coroutines with ``cocotb.start_soon`` and await both,
   or drive the exact interleaved contract order. A sequential all-A-then-all-B
   driver can deadlock even when each individual ready/valid helper is correct.
   A sequence of separate memory-mapped reads is not an atomic snapshot unless the
   contract explicitly says so. A job may complete between legal reads; validate
   each transfer against the lifecycle state observable for that transfer rather
   than requiring all independently read registers to show one historical version.
8. Treat each signal's explicit ``role``, ``semantic_class``, and ``channel`` plus
   each channel's ``protocol_profile`` as authoritative. Do not classify signals by
   spelling or fuzzy matching. Combine taxonomy coverage tags to derive generic
   protocol obligations; use contract semantic text for design-specific behavior.
9. If completion/error behavior is defined and required by policy, generated tests
   must actually reference and check the signals carrying those roles. For this
   contract the exact required status signal names are: {required_status_text}.
   Test code must read and assert each one through ``dut.<exact_name>`` or a literal
   ``getattr(dut, "<exact_name>")`` (explicit aliases such as ``self.dut = dut``
   are supported); mentioning it only in prose is insufficient.
10. Each test file must declare the obligation IDs it implements in both its
    structured ``coverage_obligations`` field and exactly one module-level literal
    ``COVERAGE_OBLIGATIONS`` collection. Across all test files, implement every ID
    from the DETERMINISTIC INTERFACE COVERAGE PLAN plus every ID created by your
    ``operation_coverage`` entries, and claim no other ID. Copy generated IDs
    byte-for-byte: ``operation.`` is a required prefix and must never be shortened
    to ``op.`` or otherwise paraphrased.
11. Use only contract-declared top-level signals and preserve verifier independence.
12. Import ``contract_coverage`` from ``multigent.verifier_tool`` and decorate
    every cocotb test with ``@contract_coverage()`` directly below
    ``@cocotb.test()``. Code appends one immutable, visibly marked block to each
    saved TB after your response. It snapshots every declared interface signal once,
    executes taxonomy-owned protocol assertions, supplies the catalog-operation
    result assertion wrapper, and passes that same snapshot to cocotb-coverage.
    Do not define names beginning ``_contract_generated_``, ``_contract_record_``,
    or ``CONTRACT_`` and do not create another coverage clock observer. Tests must
    drive traffic that hits every
    required bin. Do not call tracker internals or declare hits manually. A zero-hit
    required bin makes regression fail.
13. Populate ``operation_coverage`` for every frozen contract operation. For a
    taxonomy feature, the feature selection and resulting cocotb-coverage object
    are code-enforced; supply only the contract-specific observed field, reachable
    bins, and static DUT binding needed to instantiate it. For a feature absent
    from the taxonomy, add a ``llm_extension`` point and its custom observer.
    When an operation's
    ``kind`` exactly matches a catalog alias, use that family. When Architect used
    a generic kind such as ``compute``, infer the closest family from the frozen
    operation semantics. If Architect declared a novel family, preserve that exact
    family and implement every explicit contract feature.
    Implement every ``features`` concept with source ``baseline`` and every
    ``feature_extensions`` concept with source ``architect_extension``. Implement
    every selected known family's baseline concept exactly
    once or with multiple useful coverpoints; never downgrade a baseline concept
    to ``llm_extension``. Add further design-specific points with source
    ``llm_extension`` whenever the frozen semantics, dimensions, modes, numeric
    behavior, or acceptance criteria expose an important case absent from the
    baseline. Bins use only the schema's declarative ``op`` plus ``args``
    predicates: one arg for comparisons, two for between/modulo, one or more for
    one_of, and an empty array for truthy/falsy. Every bin must be reachable by at
    least one legal concrete transaction under the frozen contract and the test
    suite must intentionally generate it. Never create placeholder, inapplicable,
    impossible, or deliberately unsampled bins. Catalog starter-bin labels are
    examples, not a checklist: do not copy a starter bin merely because it appears
    in the catalog. When a mandatory baseline concept is fixed rather than
    configurable in this contract (for example, every lane is always active because
    there is no predication control), represent that concept with exactly one
    meaningful reachable bin for the fixed behavior; do not invent none/some modes,
    duplicate predicates under different names, or list the absent modes as known
    gaps. If mathematical overflow is impossible under the contract's numeric
    bounds, cover reachable accumulator magnitude boundaries instead. Baseline
    concept names are mandatory, but catalog starter-bin labels and counts are not.
    For a selected catalog optional concept, use its starter bins only when they are
    reachable. Its result checking is supplied by the code-owned catalog assertion
    wrapper. If the frozen
    semantics expose an important feature absent from the optional pool, retain the
    Architect extension and design an equivalent explicit check rather than dropping
    it.
    Before returning source, ensure each exact required stall-duration bin has a
    directed witness, including a one-cycle stall; randomized ready deassertion is
    not proof that valid overlapped it for the required duration.
14. Do not import or call ``sample_operation`` or raw ``record_stimulus``; the
    generated wrapper owns both ledger operations. After each real accelerator job has
    completed, and before moving to the next job, call the helper inserted by code:
    ``stimulus_id = _contract_record_checked_stimulus(
    "directed" | "randomized",
    {{<all submitted input operands/configuration>: ...}},
    {{<complete independently expected external transaction>: ...}},
    {{<complete actually observed external transaction>: ...}},
    operations=("<exact contract operation name>", ...),
    label="<useful case name>")``.
    Expected and observed must have the same complete structure, including accepted
    input streams/counts when relevant, transferred output values in contract order,
    framing, completion count, and error/status events. The code-owned wrapper
    performs the taxonomy-feature comparison before it records anything. The three
    mappings must be JSON-serializable and contain concrete values used or observed
    for that checked job; do not store only category labels, seeds, or coverage
    fields. For functional jobs, key accepted operands by the exact ``data_object``
    names shown in ``architect_operation_metadata`` (legacy short aliases are only
    a compatibility path). For a code-owned known operation, obtain numeric vectors
    from ``_contract_generate_operation_stimulus(operation_name, concept, bin_name)``
    and randomized jobs from
    ``_contract_generate_random_operation_stimuli(operation_name, count, seed=...)``.
    These return canonical ``stimulus`` and ``expected`` mappings already checked
    against the same classifier; drive their stimulus through the real protocol,
    independently capture DUT outputs, and pass literal top-level dicts whose values
    come from those mappings into the checked-stimulus call. Do not copy or rewrite
    the GEMM arithmetic merely to choose known-feature vectors. A reported
    ``unreachable`` bin is not a coverage target; ``metadata_missing`` requires a
    contract correction and ``llm_extension_required`` is the explicit fallback for
    novel semantics. The inserted helper validates transaction completeness,
    assembles the canonical job, computes known-feature evidence, and links every
    participating operation to the checked stimulus. Do not import or call
    ``sample_operation`` or raw ``record_stimulus`` yourself. The operation names
    tuple and case label must be
    literals in source; mapping values and the stimulus-kind value may be runtime
    expressions. The coverage runtime accepts only ``directed`` or
    ``randomized`` labels. The kind used by a sample must match its recorded
    stimulus. It enforces the policy minimum from actual randomized stimulus ledger
    records, not from the number of operation hooks (one composed job can have many
    operation hooks). Execute at least the policy's randomized transaction minimum.
    Do not emit synthetic coverage-only samples or record a stimulus that did not
    pass the code-owned comparison. Every operation point is sampled
    by the same clock observer through reusable or custom observation code; see rule 18.
    A composed accelerator job may contain several contract operations without
    exposing a separate handshake for each internal stage. In that case, the
    accepted external job is the real transaction for all of those operations;
    list every participating exact operation name in the helper's literal tuple.
    Absence of internal stage handshakes is not
    an architecture conflict and does not require new top-level signals.
15. When ``coverage_closure_review`` is present, use its ``covered_bins``,
    ``missing_bins``, ``bin_hits``, ``missing_bin_definitions``, and
    ``stimulus_summary`` together. Preserve valid
    prior checks, add new legal cases that target the missing bins, and avoid simply
    replaying the same stimulus distribution. Exact prior inputs and expected values
    are intentionally not included in the prompt; use the existing generator source,
    seed/count metadata, and summarized operation-field distributions. Never edit hit
    counts or claim a hit without DUT traffic.
16. Collect the selected taxonomy family's behavioral evidence for the code-owned
    comparison, not merely coverage labels. Count actual accepted operands and
    outputs; producer loop counts alone cannot detect forbidden-phase or extra input
    consumption. Keep observed output accounting active after the expected final
    beat through completion/idle/next-job boundaries, subject to the frozen reset or
    abort semantics. Put those actual observations into the observed transaction
    passed to ``_contract_record_checked_stimulus``. The code-owned protocol monitor
    separately checks reusable protocol properties. Only a contract feature absent
    from the taxonomy may require a Verifier-authored custom assertion. Never use an
    always-True fallback when required observed evidence is absent.
17. When ``assertion_definition_review`` is present, repair its concrete coverage
    or assertion findings using the complete previous_verifier_output. Preserve
    valid checks and stimulus constructions; fix any specifically invalid or
    unreachable stimulus-intent mapping or producer sequence identified by the
    review, without redesigning unrelated stimulus. Wire in the corrected
    checker. The review does not assess actual
    bin hits or traffic activation. Additional points within an existing taxonomy
    class and pool-missing llm_extension points are allowed. Genuine unresolved
    external semantics may still return ARCHITECTURE_CONFLICT with exact evidence;
    missing observer association or coverage helper structure is not external
    semantics and must stay in Verifier repair.
18. ``architect_operation_metadata`` identifies known concepts whose adapter,
    canonical-job assembler, and classifier are owned by verifier_tool. Do not
    declare ``OPERATION_SAMPLING_BINDINGS`` or custom observers for those concepts;
    the checked-stimulus helper supplies their evidence after the central golden
    comparison passes. For every remaining unknown or novel operation coverage
    point, declare literal module-level ``OPERATION_SAMPLING_BINDINGS`` connection
    metadata. Do not implement its own
    clock/task observer or call a sampler for these points: @contract_coverage starts the
    trusted observer. Each binding references an existing operation coverpoint;
    reusable template generates effective bins; a custom observer retains your
    feature-specific bin predicates. Keep the point's concept/source and coverage ID.
    Example for the dimension named M packed in an accepted command:
    OPERATION_SAMPLING_BINDINGS = [{{
      "operation": "<exact operation name>", "point": "<local coverpoint id>",
      "template": "dimension", "event": "transfer", "channel": "<command channel>",
      "fields": {{"value": {{"signal": "<declared command signal>", "lsb": 0, "width": 3}}}},
      "dimension": "<exact contract dimension name>"
    }}]
    These names/bit locations are examples, never fixed architecture conventions.
    Field sources may alternatively use {{"channel": "<channel>", "role": "payload"}}
    plus optional lsb/width. Event=transfer uses declared valid/ready roles;
    For integer_operand, omit fields only if that channel has exactly one payload
    whose literal width and signedness exactly match the named contract data_type;
    code binds that whole signal by role. For boolean_mode, omit fields only for
    exactly one unsigned one-bit whole payload. Otherwise declare the exact
    signal/slice yourself: code never guesses packed fields or symbolic widths.
    event=clock observes an explicitly clock-sampled/combinational interface and
    must omit channel. Optional guards are [{{"field": <field source>, "equals":
    <contract encoding>}}] for selecting the intended operation on a shared channel.
    Choose sources, mode encodings, types and tile parameters from frozen semantics.
    For tile_shape, fields maps exact dimension names to sources and tile_parameters
    maps those names to declared positive-literal-default tile parameters.
    For integer_operand, data_type references a contract integer type and the selected
    field width must match it. For integer_add_overflow, fields has a/b, operand_types
    maps a/b to declared types, and result_type names the declared result type; it
    covers an input scenario, never asserts correct result/flag handling.
    boolean_mode/discrete_mode use legal_values containing applicable contract
    encodings; do not invent a disabled mode when only enabled is possible.
    channel_stall needs a top-level "channel" key and no "fields" or "observer" key:
    {{"operation": "<exact operation name>", "point": "<local coverpoint id>",
    "template": "channel_stall", "channel": "<declared channel>"}}. There is no
    per-binding "observer" key for this template, as a string or as an object: the
    runtime's own trusted stall tracker measures actual stalls through release
    directly from the named channel, not planned ready delays and not a
    Verifier-supplied function. Only template="custom" ever takes an "observer" key.
    For any feature/encoding without an appropriate reusable template, use
    template="custom", observer="observe_name",
    event/channel/guards and fields describing actual DUT observations. Implement
    a local synchronous def observe_name(values, state) with exactly two arguments,
    no decorators/defaults, no awaits, no drivers and no hit/coverage API calls.
    Runtime passes a read-only mapping of actual bound fields and a per-point state
    dictionary, reset at test/reset boundaries. Return a finite scalar observation
    or None until the relevant observed event/job is complete. Optional field_types
    maps field names to contract integer types for signed decoding. Pure local
    helper functions are allowed; derive observations only from supplied DUT values,
    prior observed state and contract constants, never planned stimulus or a claimed
    True label. Use clock events with explicitly bound valid/ready/config/completion
    fields to track multi-channel or composed jobs; you need not invent internal ports.
    When a feature needs A/B/bias/shape and result association, bind all necessary
    external fields to that point's clock event and maintain its own accepted-job
    state. Multiple points may independently track the same job; do not require
    a shared state between points or a contract-visible job-ID signal.
    Your custom value classification and bins remain generated and definition-reviewed.
    New features/families require no runtime registry edit and are not prohibited.
    The generated checked-stimulus wrapper owns operation-ledger linkage.
    Definitions/connection metadata are reviewed before simulation; actual hits
    remain a simulation outcome. Catalog operation assertions are pipeline-owned;
    only taxonomy-missing feature assertions are Verifier-authored.
19. Make stimulus intent and Verifier-owned assertions auditable in the saved TB.
    Declare one statically resolvable ``STIMULUS_COVERAGE_INTENTS`` list per test
    file whose entries contain exactly
    ``label`` and ``targets``. Across all files, the targets must contain every exact
    interface and operation obligation at least once and no unknown ID. Pipeline
    code emits the literal, stimulus section, and ``# STIMULUS [case_id]`` comments
    into the saved TB; do not write those comments yourself. Pass case_id as a
    literal ``_contract_record_checked_stimulus(..., label="case_id")``. Keep the
    exact ``# === LLM-GENERATED OPERATION ASSERTIONS ===`` section even when it is
    empty. Use it only for taxonomy-missing features: put
    ``# LLM-GENERATED OPERATION ASSERTION [feature]`` immediately above each custom
    ``assert`` and give it a failure message containing the relevant concrete
    inputs/configuration, expected and observed values, and DUT signal names. Never
    duplicate a catalog-feature assertion. The review receives actual stimulus source and rejects omitted
    features or mappings that cannot exercise the claimed bins/assertions. Comments
    and metadata never count as a hit; simulation remains authoritative.

SIGNAL ROLE TAXONOMY
--------------------
{signal_roles}

INTERFACE SEMANTICS AND PROTOCOL PROFILES
-----------------------------------------
{interface_semantics}

DETERMINISTIC INTERFACE COVERAGE SEED
-------------------------------------
The following tags were computed by code from the frozen taxonomy fields. Cover
applicable tags and explain any inapplicable tag in ``known_verification_gaps``.

{coverage_seed}

DETERMINISTIC INTERFACE COVERAGE PLAN
-------------------------------------
{coverage_plan}

OPERATION COVERAGE FAMILY CATALOG
---------------------------------
These are minimum concepts for recognized common accelerators. You must instantiate
them with contract-specific fields and bins, then add llm_extension points where the
contract requires more coverage.

{operation_catalog}

RUNTIME OPERATION SAMPLING TEMPLATES
-----------------------------------
Use these supported observation templates instead of planned stimulus values or
self-declared behavior labels. Static bindings do not include stimulus payloads.

{sampling_catalog}

VERIFIER CONTEXT
----------------
{serialized}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the independent Verifier Agent")
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--architecture-dir", type=Path, default=WORKSPACE_ROOT / "architecture")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-mode", choices=["responses", "chat_completions"], default=None)
    args = parser.parse_args()
    context = build_verification_context(
        user_request=args.request,
        architecture_dir=args.architecture_dir,
    )
    result = VerifierAgent(model=args.model, api_mode=args.api_mode).run(context, run_id=args.run_id)
    print(json.dumps({
        "status": result["status"],
        "top_module": result["verification_plan"].get("top_module"),
        "test_modules": result["verification_plan"].get("test_modules", []),
        "randomized_test_count": result["verification_plan"].get("randomized_test_count", 0),
        "architecture_conflict": result["architecture_conflict"],
    }, indent=2))


if __name__ == "__main__":
    main()
