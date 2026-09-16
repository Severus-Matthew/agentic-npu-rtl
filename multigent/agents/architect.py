"""API-backed generic Hardware Architect Agent.

The user-facing input is intentionally minimal natural language. A deterministic
intake layer adds only fixed technical policy. The Architect chooses unspecified
microarchitecture details and freezes them into contracts for independent RTL
generation and verification. The Architect never writes RTL.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.verifier_tool.coverage.operation.plan import (
    render_operation_coverage_catalog,
    validate_architecture_operation_features,
)
from multigent.verifier_tool.predefined_assertion.operation import (
    render_operation_assertion_catalog,
)
from multigent.intake.request_builder import build_architect_intake, persist_intake
from multigent.verifier_tool.role_pool.interface_semantics import (
    render_interface_semantic_catalog,
    validate_interface_semantics,
)
from multigent.verifier_tool.role_pool.signal_roles import (
    render_signal_role_catalog,
    validate_interface_signal_roles,
)

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT, WORKSPACE_ROOT


ARCHITECT_OUTPUT_SCHEMA = SCHEMA_ROOT / "architect_output.schema.json"


class ContractValidationError(AgentRuntimeError):
    """A schema-valid candidate needs an Architect correction, not a tool retry."""

    def __init__(self, message: str, candidate: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.candidate = dict(candidate)


class ArchitectAgent(APIAgent):
    """Produce frozen architecture contracts from minimal hardware intent."""

    def __init__(self, *, model: str | None = None, api_mode: str | None = None) -> None:
        super().__init__(
            AgentConfig(
                name="architect",
                role_skill="architect",
                model=model or os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex"),
                api_mode=api_mode or os.getenv("NPU_AGENT_API_MODE", "responses"),
            )
        )

    def load_instructions(self) -> str:
        """Load only the Architect's technical skill."""

        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        role_skill = self.role_skill_path.read_text(encoding="utf-8")
        return f"# ARCHITECT TECHNICAL SKILL\n\n{role_skill}\n"

    def run(
        self,
        request: str | Mapping[str, Any],
        *,
        output_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        """Create and persist architecture contracts for ``request``."""

        target = output_dir or (WORKSPACE_ROOT / "architecture")
        target.mkdir(parents=True, exist_ok=True)

        if isinstance(request, str):
            intake = build_architect_intake(request)
        else:
            intake = build_architect_intake(
                "Legacy structured hardware specification supplied by the caller."
            )
            intake["legacy_user_specification"] = dict(request)
            intake["provenance"]["user_supplied_fields"].append(
                "legacy_user_specification"
            )

        intake_dir = WORKSPACE_ROOT / "specs" if output_dir is None else target.parent / "specs"
        persist_intake(intake, run_id=run_id, output_dir=intake_dir)
        task = self._build_architecture_task(intake)
        result = self.run_structured(
            task=task,
            schema_path=ARCHITECT_OUTPUT_SCHEMA,
            log_name=f"architect-{run_id}.json",
        )

        if result["status"] == "SPEC_CONFLICT":
            conflict_path = target / "spec_conflict.json"
            self._write_json(conflict_path, result)
            return result

        if result["conflicts"]:
            raise ValueError(
                "Architect returned READY while also reporting specification conflicts."
            )

        self._validate_contract_references(result)

        self._write_yaml(
            target / "architecture_contract.yaml",
            result["architecture_contract"],
        )
        self._write_yaml(
            target / "interface_contract.yaml",
            result["interface_contract"],
        )
        self._write_json(
            target / "module_manifest.json",
            result["module_manifest"],
        )
        self._write_yaml(
            target / "acceptance_criteria.yaml",
            result["acceptance_criteria"],
        )
        self._write_json(target / "architect_result.json", result)
        return result

    @staticmethod
    def _validate_contract_references(result: Mapping[str, Any]) -> None:
        """Deterministically reject broken relational invariants in READY output.

        JSON Schema validates structure and primitive types. This second layer checks
        relationships that are generic across accelerator families: operation/object
        graph reciprocity, type/dimension/parameter references, interface visibility,
        storage references, and module dependencies/parameters.
        """

        arch = result["architecture_contract"]
        interface = result["interface_contract"]
        manifest = result["module_manifest"]
        errors: list[str] = []

        def unique_names(items: list[Mapping[str, Any]], kind: str) -> set[str]:
            names = [str(item["name"]) for item in items]
            if len(names) != len(set(names)):
                errors.append(f"duplicate {kind} names")
            return set(names)

        operation_names = unique_names(arch["operations"], "operation")
        type_names = unique_names(arch["data_types"], "data type")
        object_names = unique_names(arch["data_objects"], "data object")
        dimension_names = unique_names(arch["dimensions"], "dimension")
        parameter_names = unique_names(arch["parameters"], "parameter")
        storage_names = unique_names(arch["storage"], "storage")
        channel_names = unique_names(interface["channels"], "channel")
        del storage_names, channel_names  # uniqueness side effect is the required check
        errors.extend(validate_interface_signal_roles(interface))
        errors.extend(validate_interface_semantics(interface))
        errors.extend(validate_architecture_operation_features(arch))

        operations = {str(item["name"]): item for item in arch["operations"]}
        objects = {str(item["name"]): item for item in arch["data_objects"]}
        parameters = {str(item["name"]): item for item in arch["parameters"]}

        for dim in arch["dimensions"]:
            dim_name = str(dim["name"])
            minimum = int(dim["minimum"])
            maximum = int(dim["maximum"])
            if maximum < minimum:
                errors.append(
                    f"dimension {dim_name} maximum is smaller than minimum"
                )

            bound_parameter = str(dim["bound_parameter"]).strip()
            if bound_parameter:
                if bound_parameter not in parameter_names:
                    errors.append(
                        f"dimension {dim_name} references unknown parameter "
                        f"{bound_parameter}"
                    )
                else:
                    # When the bound parameter has an integer default, the default
                    # build itself must lie within the architecture's declared bounds.
                    default_value = str(parameters[bound_parameter]["default_value"]).strip()
                    try:
                        default_int = int(default_value, 0)
                    except ValueError:
                        default_int = None
                    if default_int is not None and not minimum <= default_int <= maximum:
                        errors.append(
                            f"dimension {dim_name} bound parameter {bound_parameter} "
                            f"default {default_int} lies outside [{minimum}, {maximum}]"
                        )

        for obj in arch["data_objects"]:
            name = str(obj["name"])
            if obj["data_type"] not in type_names:
                errors.append(
                    f"data object {name} references unknown data type {obj['data_type']}"
                )
            for dimension in obj["dimensions"]:
                if dimension not in dimension_names:
                    errors.append(
                        f"data object {name} references unknown dimension {dimension}"
                    )

            producer = str(obj["producer"])
            if producer != "external":
                if producer not in operation_names:
                    errors.append(
                        f"data object {name} references unknown producer {producer}"
                    )
                elif name not in operations[producer]["outputs"]:
                    errors.append(
                        f"data object {name} names producer {producer}, but operation "
                        f"{producer} does not list {name} as an output"
                    )

            for consumer in obj["consumers"]:
                consumer_name = str(consumer)
                if consumer_name == "external":
                    continue
                if consumer_name not in operation_names:
                    errors.append(
                        f"data object {name} references unknown consumer {consumer_name}"
                    )
                elif name not in operations[consumer_name]["inputs"]:
                    errors.append(
                        f"data object {name} names consumer {consumer_name}, but operation "
                        f"{consumer_name} does not list {name} as an input"
                    )

            crosses_boundary = producer == "external" or "external" in obj["consumers"]
            if crosses_boundary and not bool(obj["external"]):
                errors.append(
                    f"data object {name} crosses the external boundary but external=false"
                )
            if bool(obj["external"]) and not crosses_boundary:
                errors.append(
                    f"data object {name} is marked external=true but has no external "
                    "producer or consumer"
                )

        for operation in arch["operations"]:
            operation_name = str(operation["name"])
            for object_name in operation["inputs"]:
                if object_name not in object_names:
                    errors.append(
                        f"operation {operation_name} references unknown data object "
                        f"{object_name}"
                    )
                elif operation_name not in objects[object_name]["consumers"]:
                    errors.append(
                        f"operation {operation_name} lists {object_name} as input, but "
                        f"data object {object_name} does not list {operation_name} as consumer"
                    )
            for object_name in operation["outputs"]:
                if object_name not in object_names:
                    errors.append(
                        f"operation {operation_name} references unknown data object "
                        f"{object_name}"
                    )
                elif str(objects[object_name]["producer"]) != operation_name:
                    errors.append(
                        f"operation {operation_name} lists {object_name} as output, but "
                        f"data object {object_name} names producer "
                        f"{objects[object_name]['producer']}"
                    )

        for storage in arch["storage"]:
            for object_name in storage["stored_objects"]:
                if object_name not in object_names:
                    errors.append(
                        f"storage {storage['name']} references unknown data object "
                        f"{object_name}"
                    )

        externally_carried_objects: set[str] = set()
        for channel in interface["channels"]:
            for object_name in channel["data_objects"]:
                if object_name not in object_names:
                    errors.append(
                        f"channel {channel['name']} references unknown data object "
                        f"{object_name}"
                    )
                    continue
                externally_carried_objects.add(str(object_name))
                if not bool(objects[object_name]["external"]):
                    errors.append(
                        f"channel {channel['name']} exposes internal data object {object_name}"
                    )

        for obj in arch["data_objects"]:
            if bool(obj["external"]) and str(obj["name"]) not in externally_carried_objects:
                errors.append(
                    f"external data object {obj['name']} is not carried by any interface channel"
                )

        module_names = unique_names(manifest["modules"], "module")
        if manifest["top"] not in module_names:
            errors.append(f"top module {manifest['top']} is not declared")
        for module in manifest["modules"]:
            ports = module.get("ports", [])
            if ports:
                unique_names(ports, f"port in {module['name']}")
            if module["name"] == manifest["top"] and interface.get("signals") and ports:
                if {p['name'] for p in ports} != {p['name'] for p in interface['signals']}:
                    errors.append("Top module ports must match the external interface signals")
            for dependency in module["dependencies"]:
                if dependency not in module_names:
                    errors.append(
                        f"module {module['name']} references unknown dependency "
                        f"{dependency}"
                    )
            for parameter in module["parameters"]:
                if parameter not in parameter_names:
                    errors.append(
                        f"module {module['name']} references unknown parameter {parameter}"
                    )

        if errors:
            formatted = "; ".join(errors)
            raise ContractValidationError(
                "Architect returned a structurally valid but internally inconsistent "
                f"READY contract: {formatted}", result,
            )

    @staticmethod
    def _build_architecture_task(intake: Mapping[str, Any]) -> str:
        serialized = yaml.safe_dump(
            dict(intake),
            sort_keys=False,
            default_flow_style=False,
        )
        signal_roles = render_signal_role_catalog()
        interface_semantics = render_interface_semantic_catalog()
        operation_coverage = (
            render_operation_coverage_catalog()
            + "\n"
            + render_operation_assertion_catalog()
        )
        return f"""Design and freeze a synthesizable RTL microarchitecture from the intake envelope below.

INPUT AUTHORITY
---------------
1. ``user_request`` (and only for legacy runs, ``legacy_user_specification``)
   contains explicit user requirements.
2. ``project_constraints`` contains mandatory technical runtime policy.
3. ``architect_must_decide_when_unspecified`` lists architecture choices you must
   resolve when the user leaves them unspecified.

Do not treat a short request as an error. Choose simple, technically justified,
synthesizable defaults for unspecified architecture choices and record them in
``open_assumptions``. Return ``SPEC_CONFLICT`` only for genuinely contradictory
explicit requirements.
For a minimal workload request with no throughput, tiling, or exact-cycle target,
prefer the least complicated legal compute and interface schedule that satisfies
the operation. Do not make tiling, multi-job overlap, or exact-cycle latency a
mandatory requirement merely to make the design sound sophisticated. This is a
default-design preference, not a ban: select those features when explicitly
requested or when your chosen architecture genuinely needs them.

This is a GENERIC hardware architecture task. Do not assume GEMM, matrix
multiplication, M/N/K dimensions, activation/weight/bias terminology, a MAC array,
systolic execution, a particular interface, or any benchmark-specific structure
unless the user request itself requires it.

Your output is a CONTRACT, not RTL. Do not generate SystemVerilog. Synthesis/PPA
metrics are valid only when supplied by deterministic Synopsys reports; do not
infer or fabricate timing, area, power, frequency, or utilization values.

Required design work:
1. Define all requested operations with exact functional semantics. Every operation
   input/output must reference a declared logical ``data_object``. Select an exact
   ``coverage_family`` from OPERATION FEATURE TAXONOMY for every operation, set
   ``coverage_family_source`` to ``catalog``, and copy
   that family's complete baseline concept set into ``features``. When kind is
   generic but semantics identify a known family, select that known family. If no
   catalog family genuinely applies, create a concise new family name, set its source
   to ``novel``, and declare explicit, reusable feature names derived from the
   requested operation semantics. For a known family, inspect its optional-concept
   pool and copy every concept whose ``applies_when`` condition is present in this
   design into ``feature_extensions``. Do not select a mode the contract does not
   implement merely because it exists in the pool. A common self-contradiction:
   selecting ``runtime_shape`` (or any concept whose ``applies_when`` requires a
   dimension/mode to be programmable per job) while also declaring that same
   dimension/mode fixed and non-configurable elsewhere in this same contract.
   Before finalizing ``feature_extensions``, re-check each selected concept's
   ``applies_when`` against your own declared parameters/dimensions for this
   design; drop the concept if your own contract contradicts its condition. Also
   put important contract
   features absent from both the baseline and optional pools in
   ``feature_extensions``; the catalog is deliberately extensible rather than a
   closed vocabulary. For a novel family, use explicit reusable feature names.
2. Define scalar/element ``data_types`` separately from logical ``data_objects``.
   Every data object must name its data type, dimensions, producer, consumers, and
   whether it crosses the external interface. Producer/consumer declarations must
   be reciprocal with operation outputs/inputs.
   Interface registers, protocol state, lifecycle flags, and status need not be
   invented as operation data objects. Every operation name referenced by a data
   object must actually be declared; never invent a producer/consumer operation
   merely to attach MMIO transport state.
3. Define every runtime-varying dimension with concrete integer minimum/maximum
   bounds and any compile-time bound parameter. A bound parameter's default build
   must fall inside the declared dimension range. If no bound parameter applies,
   use the schema's empty representation; never emit placeholders such as ``none``,
   ``n/a``, or an undeclared parameter name.
4. Define all compile-time parameters with concrete defaults, legality constraints,
   and purposes. Parameter-dependent signal widths and capacities must be expressed
   symbolically rather than frozen to values valid only at the defaults.
5. Choose compute organization, dataflow, parallelism, and scheduling appropriate
   for the requested workload rather than copying benchmark examples.
6. Close all storage/reuse semantics. Storage capacity and read/write/banking/port
   requirements must sustain the stated compute schedule under the declared bounds.
   Cross-check input framing against storage lifetime: once-per-job data must be
   retained if later phases reuse it; otherwise the interface must explicitly define
   retransmission.
7. Account for interface bandwidth. If scalar streams load several operands for one
   parallel compute step, include the load cycles or provide sufficient prefetch/
   buffering/double-buffering to sustain the claimed throughput.
   Phase accounting is mandatory. You may choose exact latency even when the user
   did not prescribe it, but then the claim is contractual: freeze the reference
   acceptance event, completion event, cycle-zero/one convention, every included
   phase, whether each release-handshake cycle is already included, and the exact
   effect of every legal stall on every channel. Use a handshake-derived finite
   liveness bound only when latency is genuinely variable; never emit an exact-
   looking formula with an ambiguous counting origin or stall convention.
8. Define pipeline stages, valid behavior, and stall behavior.
9. Define control strategy, state progression, counters/indices, illegal-input
   behavior, and an explicit implementable recovery path. Never reference a clear or
   retry command that is absent from the interface.
10. Fully define logical channels and top-level signals. Each channel must list the
    declared external data objects it carries plus any metadata, framing, ordering,
    backpressure, widths, and reset behavior. Every external data object must be
    represented by at least one interface channel. For every signal, assign exactly
    one role from SIGNAL ROLE TAXONOMY below and set ``channel`` to the declared
    channel name required by that role, or null for standalone roles. Assign
    ``semantic_class`` from INTERFACE SEMANTICS when required by the role. Every
    channel must select one ``protocol_profile``. Never infer any of these fields
    from the signal name; they are explicit parts of the frozen contract. A signal
    attached to a channel must have the direction required by that channel role:
    in particular, do not attach output status/error metadata to an input command
    or configuration channel. Put such metadata on an output/status channel or use
    an appropriate standalone role.
11. Define module decomposition with explicit responsibilities, dependencies,
    parameters, and statefulness. All dependencies and parameters must resolve.
    Every state transition or output decision must be implementable from the
    module's declared inputs and retained state. Freeze actual transfer/phase-done
    feedback into controllers and final-transaction metadata into serializers when
    they own those decisions; do not leave necessary information outside their ports.
12. Define deterministic functional, verification, RTL, and Synopsys-handoff
    acceptance criteria from the technical project policy. Require illegal-value
    tests only for illegal encodings that are physically representable with the
    declared signal widths and parameterization; do not require an impossible
    over-bound encoding.
13. Before returning READY, cross-check operations, data objects, data types, runtime
    bounds, parameters, compute schedule, storage bandwidth/capacity, pipeline,
    interface, control, reset, module manifest, and acceptance criteria. The RTL
    Generator must not need to guess architectural facts.

FIRST-CONTRACT EXTERNAL-SEMANTICS PRECHECK
------------------------------------------
Close these decisions in the first contract wherever the chosen design exposes
them; do not rely on the later Verifier to discover one ambiguity at a time:
- A ready/valid transfer on a reset edge: define whether reset suppresses it, and
  make reset-time ready values and the global transfer rule agree.
- Reset asserted during a producer stall: explicitly say whether reset aborts the
  pending beat and permits valid/payload withdrawal, or whether stall stability
  survives reset. Keep the global hold rule and reset-state rule consistent.
- Illegal-command error pulse: define whether a new command may transfer during
  that pulse and the exact cycle in which command-ready returns.
- Pending next command while busy: define whether its source may present and hold
  valid/payload, whether this is a legal stall, and its release acceptance edge.
- Final output handshake, busy deassertion, completion pulse and next command:
  define their observable order, including command-ready during completion.
- Indexed arithmetic recurrence: specify the initialization, exactly which k
  values update the accumulator, and the K=1 case without double counting.
- If an exact latency is promised, work a small legal transaction through the
  claimed formula and every phase/stall/release-handshake cycle; otherwise use
  partial order plus bounded liveness. Never mandate an arithmetic overflow bin
  that legal widths and dimension bounds cannot reach.
State only the rules applicable to your selected architecture. This is a clarity
check, not a mandate for a particular interface, phase schedule, or accelerator.

REFERENCE FIELDS
-----------------
``interface_contract.clock`` and ``interface_contract.reset`` are exact signal
names declared in ``signals`` (for example clk and rst_n), not explanatory prose.
Put edge, polarity, priority, and reset behavior in signal semantics and the
architecture reset contract instead. This is a relational reference, not a naming
convention: any declared clock/reset signal name is permitted.

SIGNAL ROLE TAXONOMY
--------------------
{signal_roles}

INTERFACE SEMANTICS AND PROTOCOL PROFILES
-----------------------------------------
{interface_semantics}

OPERATION FEATURE TAXONOMY
--------------------------
Known family names and baseline features below are mandatory when applicable.
Novel operations may extend this vocabulary explicitly in the frozen contract.
Starter bins guide the later Verifier but are not Architect fields.

{operation_coverage}

ARCHITECT INTAKE ENVELOPE
-------------------------
{serialized}
"""

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_yaml(path: Path, value: Any) -> None:
        path.write_text(
            yaml.safe_dump(value, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )


def load_legacy_spec(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(raw)
    else:
        value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise TypeError("Hardware specification must decode to a mapping/object.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hardware Architect Agent")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--request",
        type=str,
        help="Minimal natural-language hardware accelerator request",
    )
    source.add_argument(
        "--request-file",
        type=Path,
        help="Text file containing only the user's natural-language request",
    )
    source.add_argument(
        "--spec",
        type=Path,
        help="Legacy YAML/JSON structured specification",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
        help="Architect artifact directory",
    )
    parser.add_argument("--run-id", default="manual")
    parser.add_argument("--model", default=None, help="Override NPU_AGENT_MODEL")
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        default=None,
        help="Override NPU_AGENT_API_MODE",
    )
    args = parser.parse_args()

    if args.request is not None:
        request: str | Mapping[str, Any] = args.request
    elif args.request_file is not None:
        request = args.request_file.read_text(encoding="utf-8").strip()
    else:
        request = load_legacy_spec(args.spec)

    agent = ArchitectAgent(model=args.model, api_mode=args.api_mode)
    result = agent.run(
        request,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(json.dumps({"status": result["status"]}, indent=2))


if __name__ == "__main__":
    main()
