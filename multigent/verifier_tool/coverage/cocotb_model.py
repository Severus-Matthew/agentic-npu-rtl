"""Build cocotb-coverage objects directly from a frozen coverage contract.

This module is the coverage-backend boundary.  Taxonomy/Verifier output says
*what* must be covered in a plain-data plan; this builder turns every plan
obligation into a real :mod:`cocotb_coverage` ``CoverPoint`` and, for
ready/valid channels, a ``CoverCross``.  Runtime monitors only supply observed
values to the generated model.
"""

from __future__ import annotations

from typing import Any, Mapping

from cocotb_coverage.coverage import CoverCross, CoverPoint, coverage_db


class CocotbCoverageModelError(ValueError):
    """The contract cannot be represented as a cocotb-coverage model."""


def predicate_matches(value: Any, predicate: Mapping[str, Any]) -> bool:
    """Evaluate one validator-approved operation-bin predicate."""

    op = str(predicate.get("op", ""))
    args = list(predicate.get("args", []))
    if op == "eq":
        return value == args[0]
    if op == "neq":
        return value != args[0]
    if op == "lt":
        return value < args[0]
    if op == "lte":
        return value <= args[0]
    if op == "gt":
        return value > args[0]
    if op == "gte":
        return value >= args[0]
    if op == "between":
        return args[0] <= value <= args[1]
    if op == "one_of":
        return value in args
    if op == "mod_eq":
        return value % args[0] == args[1]
    if op == "mod_ne":
        return value % args[0] != args[1]
    if op == "truthy":
        return bool(value)
    if op == "falsy":
        return not bool(value)
    raise CocotbCoverageModelError(
        f"Unsupported operation coverage predicate {op!r}"
    )


class ContractCocotbCoverageModel:
    """Materialize contract obligations as cocotb-coverage objects."""

    _HANDSHAKE_VALUES = {
        "idle": (0, 0),
        "receiver_ready": (0, 1),
        "backpressured": (1, 0),
        "transfer": (1, 1),
    }

    def __init__(self, plan: Mapping[str, Any], namespace: str) -> None:
        self.namespace = namespace
        self.obligations = {
            str(item["id"]): dict(item) for item in plan.get("obligations", [])
        }
        self.coverage_items: dict[str, Any] = {}
        self._samplers: dict[str, Any] = {}
        self._handshake_cross_bins: dict[str, dict[str, tuple[str, str]]] = {}
        self._manifest: list[dict[str, Any]] = []

        for obligation_id, obligation in self.obligations.items():
            template = str(obligation.get("template", ""))
            if template == "handshake_states":
                self._build_handshake(obligation_id, obligation)
            elif template == "stall_stability":
                self._build_stall(obligation_id, obligation)
            elif template == "operation_coverpoint":
                self._build_operation(obligation_id, obligation)
            else:
                self._build_event_coverpoint(obligation_id, obligation)

    @staticmethod
    def _labels(obligation: Mapping[str, Any]) -> list[str]:
        labels = [str(item.get("name", "")) for item in obligation.get("bins", [])]
        if not labels or any(not label for label in labels):
            raise CocotbCoverageModelError("Every coverage obligation needs named bins")
        if len(labels) != len(set(labels)):
            raise CocotbCoverageModelError(
                f"Coverage obligation has duplicate bins: {labels}"
            )
        return labels

    def _build_event_coverpoint(
        self, obligation_id: str, obligation: Mapping[str, Any]
    ) -> None:
        labels = self._labels(obligation)
        point_name = f"{self.namespace}.{obligation_id}.coverpoint"

        def sample_event(value: str) -> str:
            return value

        sampler = CoverPoint(
            point_name,
            bins=labels,
            at_least=1,
            inj=True,
        )(sample_event)
        self.coverage_items[obligation_id] = coverage_db[point_name]
        self._samplers[obligation_id] = sampler
        self._manifest.append(
            {
                "obligation_id": obligation_id,
                "template": str(obligation.get("template", "")),
                "coverpoint": point_name,
            }
        )

    def _build_operation(
        self, obligation_id: str, obligation: Mapping[str, Any]
    ) -> None:
        labels = self._labels(obligation)
        predicates = [dict(item.get("predicate", {})) for item in obligation["bins"]]
        bin_indexes = list(range(len(labels)))
        point_name = f"{self.namespace}.{obligation_id}.coverpoint"

        def relation(value: Any, bin_index: int) -> bool:
            return predicate_matches(value, predicates[bin_index])

        def sample_value(value: Any) -> Any:
            return value

        sampler = CoverPoint(
            point_name,
            bins=bin_indexes,
            bins_labels=labels,
            rel=relation,
            at_least=1,
            # Operation bins may intentionally overlap (for example a boundary
            # value can also belong to an operand class).
            inj=False,
        )(sample_value)
        self.coverage_items[obligation_id] = coverage_db[point_name]
        self._samplers[obligation_id] = sampler
        self._manifest.append(
            {
                "obligation_id": obligation_id,
                "template": "operation_coverpoint",
                "coverpoint": point_name,
                "sample_field": str(obligation.get("bindings", {}).get("field", "")),
                "sampling_origin": "runtime_dut_observation" if obligation.get("bindings", {}).get("sampling") else "unbound_definition",
                "predicate_bins": labels,
            }
        )

    def _build_stall(
        self, obligation_id: str, obligation: Mapping[str, Any]
    ) -> None:
        labels = self._labels(obligation)
        ranges = {
            "one_cycle_stall": (1, 1),
            "short_stall": (2, 4),
            "long_stall": (5, None),
        }
        try:
            bounds = [ranges[label] for label in labels]
        except KeyError as exc:
            raise CocotbCoverageModelError(
                f"Unknown stall-length bin {exc.args[0]!r}"
            ) from exc
        point_name = f"{self.namespace}.{obligation_id}.coverpoint"

        def relation(length: int, bin_index: int) -> bool:
            low, high = bounds[bin_index]
            return int(length) >= low and (high is None or int(length) <= high)

        def sample_length(length: int) -> int:
            return int(length)

        sampler = CoverPoint(
            point_name,
            bins=list(range(len(labels))),
            bins_labels=labels,
            rel=relation,
            at_least=1,
            inj=True,
        )(sample_length)
        self.coverage_items[obligation_id] = coverage_db[point_name]
        self._samplers[obligation_id] = sampler
        self._manifest.append(
            {
                "obligation_id": obligation_id,
                "template": "stall_stability",
                "coverpoint": point_name,
                "sample_value": "completed_stall_length",
            }
        )

    def _build_handshake(
        self, obligation_id: str, obligation: Mapping[str, Any]
    ) -> None:
        labels = self._labels(obligation)
        try:
            state_bins = [self._HANDSHAKE_VALUES[label] for label in labels]
        except KeyError as exc:
            raise CocotbCoverageModelError(
                f"Unknown handshake-state bin {exc.args[0]!r}"
            ) from exc

        group_name = f"{self.namespace}.{obligation_id}"
        valid_name = f"{group_name}.valid"
        ready_name = f"{group_name}.ready"
        cross_name = f"{group_name}.valid_x_ready"

        # Construct component points before the cross so cocotb-coverage can
        # derive the Cartesian product.  Wrapping order makes both component
        # points sample before CoverCross reads their current hits.
        valid_point = CoverPoint(
            valid_name,
            xf=lambda valid, ready: int(bool(valid)),
            bins=[0, 1],
            bins_labels=["low", "high"],
            at_least=1,
        )
        ready_point = CoverPoint(
            ready_name,
            xf=lambda valid, ready: int(bool(ready)),
            bins=[0, 1],
            bins_labels=["low", "high"],
            at_least=1,
        )
        cross_point = CoverCross(
            cross_name,
            items=[valid_name, ready_name],
            at_least=1,
        )

        def sample_handshake(valid: int, ready: int) -> None:
            return None

        sampler = valid_point(ready_point(cross_point(sample_handshake)))
        self.coverage_items[obligation_id] = coverage_db[cross_name]
        self._samplers[obligation_id] = sampler
        level = {0: "low", 1: "high"}
        self._handshake_cross_bins[obligation_id] = {
            label: (level[state[0]], level[state[1]])
            for label, state in zip(labels, state_bins)
        }
        self._manifest.append(
            {
                "obligation_id": obligation_id,
                "template": "handshake_states",
                "coverpoints": [valid_name, ready_name],
                "covercross": cross_name,
                "bindings": dict(obligation.get("bindings", {})),
            }
        )

    def sample_bin(self, obligation_id: str, bin_name: str) -> None:
        """Sample a named temporal/event bin calculated by the monitor."""

        if obligation_id not in self._samplers:
            raise CocotbCoverageModelError(
                f"Unknown coverage obligation {obligation_id!r}"
            )
        labels = self._labels(self.obligations[obligation_id])
        if bin_name not in labels:
            raise CocotbCoverageModelError(
                f"Unknown bin {obligation_id}.{bin_name}"
            )
        self._samplers[obligation_id](bin_name)

    def sample_handshake(self, obligation_id: str, valid: int, ready: int) -> None:
        """Sample a generated valid × ready coverpoint/cross group."""

        if self.obligations.get(obligation_id, {}).get("template") != "handshake_states":
            raise CocotbCoverageModelError(
                f"{obligation_id!r} is not a handshake coverage obligation"
            )
        self._samplers[obligation_id](int(bool(valid)), int(bool(ready)))

    def sample_stall_length(self, obligation_id: str, length: int) -> None:
        """Let cocotb-coverage classify one completed observed stall length."""

        if self.obligations.get(obligation_id, {}).get("template") != "stall_stability":
            raise CocotbCoverageModelError(
                f"{obligation_id!r} is not a stall-stability coverage obligation"
            )
        self._samplers[obligation_id](int(length))

    def sample_operation(self, obligation_id: str, value: Any) -> list[str]:
        """Sample a contract field and return every matching named bin."""

        obligation = self.obligations.get(obligation_id, {})
        if obligation.get("template") != "operation_coverpoint":
            raise CocotbCoverageModelError(
                f"{obligation_id!r} is not an operation coverpoint"
            )
        self._samplers[obligation_id](value)
        return [
            str(bin_spec["name"])
            for bin_spec in obligation.get("bins", [])
            if predicate_matches(value, bin_spec.get("predicate", {}))
        ]

    def detailed_coverage(self, obligation_id: str) -> dict[str, int]:
        """Return named bin hit counts for one required obligation."""

        if obligation_id in self._handshake_cross_bins:
            detailed = self.coverage_items[obligation_id].detailed_coverage
            return {
                label: int(detailed.get(cross_bin, 0))
                for label, cross_bin in self._handshake_cross_bins[
                    obligation_id
                ].items()
            }
        return {
            str(name): int(count)
            for name, count in self.coverage_items[
                obligation_id
            ].detailed_coverage.items()
        }

    def manifest(self) -> list[dict[str, Any]]:
        """Describe the generated cocotb-coverage model in the JSON report."""

        return [dict(item) for item in self._manifest]
