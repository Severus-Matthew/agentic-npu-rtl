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

from multigent.intake.request_builder import build_architect_intake, persist_intake

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT, WORKSPACE_ROOT


ARCHITECT_OUTPUT_SCHEMA = SCHEMA_ROOT / "architect_output.schema.json"


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
            raise AgentRuntimeError(
                "Architect returned a structurally valid but internally inconsistent "
                f"READY contract: {formatted}"
            )

    @staticmethod
    def _build_architecture_task(intake: Mapping[str, Any]) -> str:
        serialized = yaml.safe_dump(
            dict(intake),
            sort_keys=False,
            default_flow_style=False,
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

This is a GENERIC hardware architecture task. Do not assume GEMM, matrix
multiplication, M/N/K dimensions, activation/weight/bias terminology, a MAC array,
systolic execution, a particular interface, or any benchmark-specific structure
unless the user request itself requires it.

Your output is a CONTRACT, not RTL. Do not generate SystemVerilog. Synthesis/PPA
metrics are valid only when supplied by deterministic Synopsys reports; do not
infer or fabricate timing, area, power, frequency, or utilization values.

Required design work:
1. Define all requested operations with exact functional semantics. Every operation
   input/output must reference a declared logical ``data_object``.
2. Define scalar/element ``data_types`` separately from logical ``data_objects``.
   Every data object must name its data type, dimensions, producer, consumers, and
   whether it crosses the external interface. Producer/consumer declarations must
   be reciprocal with operation outputs/inputs.
3. Define every runtime-varying dimension with concrete integer minimum/maximum
   bounds and any compile-time bound parameter. A bound parameter's default build
   must fall inside the declared dimension range.
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
8. Define pipeline stages, valid behavior, and stall behavior.
9. Define control strategy, state progression, counters/indices, illegal-input
   behavior, and an explicit implementable recovery path. Never reference a clear or
   retry command that is absent from the interface.
10. Fully define logical channels and top-level signals. Each channel must list the
    declared external data objects it carries plus any metadata, framing, ordering,
    backpressure, widths, and reset behavior. Every external data object must be
    represented by at least one interface channel.
11. Define module decomposition with explicit responsibilities, dependencies,
    parameters, and statefulness. All dependencies and parameters must resolve.
12. Define deterministic functional, verification, RTL, and Synopsys-handoff
    acceptance criteria from the technical project policy.
13. Before returning READY, cross-check operations, data objects, data types, runtime
    bounds, parameters, compute schedule, storage bandwidth/capacity, pipeline,
    interface, control, reset, module manifest, and acceptance criteria. The RTL
    Generator must not need to guess architectural facts.

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
