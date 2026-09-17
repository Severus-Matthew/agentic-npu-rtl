"""Code-owned operation coverage sampling from declared DUT observations.

OPERATION_SAMPLING_BINDINGS in a generated TB is static connection metadata.
The existing clock monitor reads values. Custom observers transform runtime-read
snapshots, never receive the DUT/tracker, and feed the same coverage backend.
"""

from __future__ import annotations

import ast
import copy
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping
from types import MappingProxyType

import yaml


TEMPLATES_PATH = Path(__file__).with_name("sampling_templates.yaml")
_SAMPLERS = {"custom", "dimension", "integer_operand", "boolean_mode", "discrete_mode",
             "tile_shape", "channel_stall", "integer_add_overflow"}


class OperationSamplingError(ValueError):
    """Invalid static operation coverage connection metadata."""


def _static_binding_value(
    node: ast.AST, definitions: Mapping[str, ast.AST], resolving: set[str] | None = None,
) -> Any:
    """Resolve inert literals and top-level literal aliases without executing TB code."""
    resolving = set() if resolving is None else set(resolving)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_static_binding_value(item, definitions, resolving) for item in node.elts]
        return values if isinstance(node, ast.List) else tuple(values)
    if isinstance(node, ast.Dict):
        return {
            _static_binding_value(key, definitions, resolving):
            _static_binding_value(value, definitions, resolving)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.Name) and node.id in definitions and node.id not in resolving:
        return _static_binding_value(
            definitions[node.id], definitions, resolving | {node.id}
        )
    raise ValueError("operation binding metadata is not statically resolvable")


def _binding_syntax(content: str) -> tuple[list[str], list[ast.AST], dict[str, ast.AST]]:
    tree = ast.parse(content)
    definitions: dict[str, ast.AST] = {}
    declarations: list[ast.AST] = []
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        for target in targets:
            if isinstance(target, ast.Name):
                definitions[target.id] = node.value
                if target.id == "OPERATION_SAMPLING_BINDINGS":
                    declarations.append(node)
    return content.splitlines(), declarations, definitions


@lru_cache(maxsize=1)
def load_operation_sampling_templates() -> dict[str, Any]:
    raw = yaml.safe_load(TEMPLATES_PATH.read_text(encoding="utf-8"))
    templates = raw.get("templates", {})
    if set(templates) != _SAMPLERS:
        raise OperationSamplingError("Operation sampling YAML and runtime registry differ")
    return raw


def render_operation_sampling_catalog() -> str:
    return "\n".join(
        f"- {name}: fields={spec['required_fields']}; metadata={spec['metadata']}; "
        f"bin_rule={spec['bin_rule']}; {spec['description']}"
        for name, spec in load_operation_sampling_templates()["templates"].items()
    )


def extract_operation_sampling_bindings(contents: list[str]) -> list[dict[str, Any]]:
    """Read only literal module constants, never execute generated Python."""
    result: list[dict[str, Any]] = []
    for content in contents:
        try:
            _, declarations, definitions = _binding_syntax(content)
        except SyntaxError as exc:
            raise OperationSamplingError("Cannot read operation sampling bindings from invalid Python") from exc
        if len(declarations) > 1:
            raise OperationSamplingError("OPERATION_SAMPLING_BINDINGS must be declared once per module")
        for node in declarations:
            try:
                bindings = _static_binding_value(node.value, definitions)
            except (ValueError, TypeError, SyntaxError) as exc:
                raise OperationSamplingError(
                    "OPERATION_SAMPLING_BINDINGS must be a statically resolvable literal list"
                ) from exc
            if not isinstance(bindings, list) or any(not isinstance(item, dict) for item in bindings):
                raise OperationSamplingError("OPERATION_SAMPLING_BINDINGS must be a list of mappings")
            result.extend(bindings)
    return result


def normalize_operation_sampling_bindings(content: str) -> str:
    """Rewrite safely resolvable aliases into one visibly literal binding list."""
    try:
        lines, declarations, definitions = _binding_syntax(content)
    except SyntaxError as exc:
        raise OperationSamplingError("Cannot normalize bindings in invalid Python") from exc
    if not declarations:
        return content
    if len(declarations) != 1:
        raise OperationSamplingError("OPERATION_SAMPLING_BINDINGS must be declared once per module")
    node = declarations[0]
    try:
        bindings = _static_binding_value(node.value, definitions)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise OperationSamplingError(
            "OPERATION_SAMPLING_BINDINGS must be statically resolvable"
        ) from exc
    if not isinstance(bindings, list) or any(not isinstance(item, dict) for item in bindings):
        raise OperationSamplingError("OPERATION_SAMPLING_BINDINGS must be a list of mappings")
    lines[node.lineno - 1:node.end_lineno] = [
        f"OPERATION_SAMPLING_BINDINGS = {bindings!r}"
    ]
    normalized = "\n".join(lines)
    return normalized + ("\n" if content.endswith("\n") else "")


def operation_observer_views(contents: list[str]) -> list[dict[str, Any]]:
    """Expose actual custom observer bodies/helpers, not stimulus schedules."""
    result = []
    for content in contents:
        definitions = {node.name: node for node in ast.parse(content).body
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        names = {item.get("observer") for item in extract_operation_sampling_bindings([content])
                 if item.get("template") == "custom" and isinstance(item.get("observer"), str)}
        for name in sorted(names):
            node = definitions.get(name)
            if (not isinstance(node, ast.FunctionDef) or node.decorator_list
                    or len(node.args.posonlyargs) + len(node.args.args) != 2
                    or node.args.vararg or node.args.kwarg or node.args.kwonlyargs
                    or node.args.defaults or node.args.kw_defaults):
                raise OperationSamplingError(f"Custom observer {name!r} must be a local synchronous function(values, state) with two arguments and no decorators")
            pending, selected = [name], {}
            while pending:
                current = pending.pop()
                if current in selected:
                    continue
                function = definitions[current]
                selected[current] = function
                pending.extend(call.func.id for call in ast.walk(function)
                               if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                               and call.func.id in definitions and call.func.id not in selected)
            result.append({"observer": name, "source": ast.unparse(node),
                           "helpers": [ast.unparse(value) for key, value in sorted(selected.items()) if key != name]})
    return result


def _int(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise OperationSamplingError(f"{name} must be an integer >= {minimum}")
    return value


def _bin(name: str, op: str, *args: Any) -> dict[str, Any]:
    return {"name": name, "intent": f"Observe {name} from runtime-sampled values.",
            "predicate": {"op": op, "args": list(args)}}


def _bound_bins(low: int, high: int) -> list[dict[str, Any]]:
    if low == high:
        return [_bin("fixed", "eq", low)]
    result = [_bin("minimum", "eq", low), _bin("maximum", "eq", high)]
    if low + 1 <= high - 1:
        result.insert(1, _bin("interior", "between", low + 1, high - 1))
    return result


def _dtype(name: str, architecture: Mapping[str, Any]) -> dict[str, Any]:
    matches = [item for item in architecture.get("data_types", []) if item.get("name") == name]
    if len(matches) != 1:
        raise OperationSamplingError(f"Unknown or ambiguous contract data type {name!r}")
    item = matches[0]
    width = _int(item.get("width_bits"), f"{name}.width_bits", 1)
    if type(item.get("signed")) is not bool:
        raise OperationSamplingError(f"{name}.signed must be declared")
    signed = item["signed"]
    return {"width": width, "signed": signed,
            "minimum": -(1 << (width - 1)) if signed else 0,
            "maximum": (1 << (width - int(signed))) - 1}


def _channel(name: str, interface: Mapping[str, Any]) -> dict[str, str]:
    if name not in {item["name"] for item in interface.get("channels", [])}:
        raise OperationSamplingError(f"Unknown sampling channel {name!r}")
    result = {}
    for role in ("valid", "ready"):
        names = [item["name"] for item in interface.get("signals", [])
                 if item.get("channel") == name and item.get("role") == role]
        if len(names) != 1:
            raise OperationSamplingError(f"Channel {name!r} needs one declared {role} signal")
        result[role] = names[0]
    return result


def _field(raw: Mapping[str, Any], interface: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) - {"signal", "channel", "role", "lsb", "width"}:
        raise OperationSamplingError("A field needs a declared signal or channel/role and optional lsb/width")
    signals = interface.get("signals", [])
    if "signal" in raw:
        if "channel" in raw or "role" in raw:
            raise OperationSamplingError("A field cannot combine signal and channel/role")
        matches = [item for item in signals if item.get("name") == raw["signal"]]
    else:
        if not raw.get("channel") or not raw.get("role"):
            raise OperationSamplingError("A field needs signal or channel plus role")
        matches = [item for item in signals
                   if item.get("channel") == raw["channel"] and item.get("role") == raw["role"]]
    if len(matches) != 1:
        raise OperationSamplingError(f"Unknown or ambiguous sampling field {dict(raw)!r}")
    signal = matches[0]
    lsb = _int(raw.get("lsb", 0), "field.lsb")
    width = raw.get("width")
    if width is not None:
        width = _int(width, "field.width", 1)
    declared = str(signal.get("width", ""))
    literal_width = int(declared) if declared.isdigit() else None
    if literal_width is not None and (lsb >= literal_width or (width is not None and lsb + width > literal_width)):
        raise OperationSamplingError(f"Field exceeds declared signal width: {dict(raw)!r}")
    return {"signal": signal["name"], "lsb": lsb, "width": width,
            "declared_width": literal_width}


def _dimension(name: str, architecture: Mapping[str, Any]) -> dict[str, int]:
    matches = [item for item in architecture.get("dimensions", []) if item.get("name") == name]
    if len(matches) != 1:
        raise OperationSamplingError(f"Unknown or ambiguous dimension {name!r}")
    low = _int(matches[0].get("minimum"), f"{name}.minimum")
    high = _int(matches[0].get("maximum"), f"{name}.maximum", low)
    return {"minimum": low, "maximum": high}


def _known_width(field: Mapping[str, Any]) -> int | None:
    if field["width"] is not None:
        return field["width"]
    return None if field["declared_width"] is None else field["declared_width"] - field["lsb"]


def _certain_whole_payload(
    channel_name: str, template: str, raw: Mapping[str, Any],
    architecture: Mapping[str, Any], interface: Mapping[str, Any],
) -> dict[str, str]:
    """Bind only an entire, uniquely typed payload; never infer a packed slice.

    This does not choose a channel or infer an operation's semantic feature. The
    Verifier still names the transfer channel and template. A missing field is
    code-owned only when role, width and signedness identify one whole value.
    """
    candidates = [signal for signal in interface.get("signals", [])
                  if signal.get("channel") == channel_name and signal.get("role") == "payload"]
    if len(candidates) != 1:
        raise OperationSamplingError(
            f"Cannot auto-bind {template} on {channel_name!r}: expected exactly one payload role; "
            "declare an explicit sampling field"
        )
    signal = candidates[0]
    width = str(signal.get("width", ""))
    if not width.isdigit() or type(signal.get("signed")) is not bool:
        raise OperationSamplingError(
            f"Cannot auto-bind {template} on {channel_name!r}: literal width and signedness "
            "are required; declare an explicit sampling field"
        )
    if template == "integer_operand":
        dtype = _dtype(raw["data_type"], architecture)
        expected_width, expected_signed = dtype["width"], dtype["signed"]
    else:
        expected_width, expected_signed = 1, False
    if int(width) != expected_width or signal["signed"] != expected_signed:
        raise OperationSamplingError(
            f"Cannot auto-bind {template} on {channel_name!r}: whole payload "
            f"width/signedness ({width}, {signal['signed']}) differs from "
            f"({expected_width}, {expected_signed}); declare an explicit sampling field"
        )
    return {"channel": channel_name, "role": "payload"}


def _check_unsigned_encoding(field: Mapping[str, Any], maximum: int) -> None:
    width = _known_width(field)
    if width is not None and maximum >= 1 << width:
        raise OperationSamplingError("Contract encodings exceed sampling field width; dimension template uses direct unsigned encoding")


def _compile(raw: Mapping[str, Any], architecture: Mapping[str, Any], interface: Mapping[str, Any]) -> tuple[dict, list]:
    allowed = {"operation", "point", "template", "event", "channel", "fields", "dimension",
               "data_type", "legal_values", "tile_parameters", "operand_types", "result_type", "guards", "observer", "field_types"}
    if set(raw) - allowed:
        raise OperationSamplingError(f"Unknown sampling binding keys: {sorted(set(raw) - allowed)}")
    name = raw.get("template")
    catalog = load_operation_sampling_templates()["templates"]
    if name not in catalog:
        raise OperationSamplingError(
            f"Unknown runtime sampling template {name!r}; the only valid template "
            f"names are {sorted(catalog)}. Use 'custom' (with an 'observer' function "
            "name) for new semantics, never an invented template name."
        )
    for key in catalog[name]["metadata"]:
        if key not in raw:
            raise OperationSamplingError(f"Template {name} needs {key}")
    event = raw.get("event", "transfer")
    if event not in {"clock", "transfer"} or (name == "channel_stall" and event != "transfer"):
        raise OperationSamplingError("Sampling event must be clock or transfer; channel_stall requires transfer")
    channel = _channel(raw.get("channel"), interface) if event == "transfer" else {}
    if event == "clock" and "channel" in raw:
        raise OperationSamplingError("Clock sampling must not declare a transfer channel")
    fields_raw = raw.get("fields", {})
    if not isinstance(fields_raw, Mapping):
        raise OperationSamplingError("Sampling fields must be a mapping")
    code_bound_field = False
    if not fields_raw and name in {"integer_operand", "boolean_mode"} and event == "transfer":
        fields_raw = {"value": _certain_whole_payload(
            raw["channel"], name, raw, architecture, interface,
        )}
        code_bound_field = True
    required = catalog[name]["required_fields"]
    dynamic_fields = required in {"dimensions", "observations"} if isinstance(required, str) else False
    if dynamic_fields and not fields_raw:
        raise OperationSamplingError(
            f"Template {name}'s 'fields' mapping is empty. Add at least one entry "
            "with any field name(s) you choose, each mapping to a declared signal "
            "your observer function reads (e.g. {'busy': {'signal': 'busy'}}); "
            "'required_fields' being the word 'observations' here is an internal "
            "marker meaning free-form fields, not a literal field name to add."
        )
    if not dynamic_fields and set(fields_raw) != set(required):
        raise OperationSamplingError(f"Template {name} needs fields {required}")
    fields = {key: _field(value, interface) for key, value in fields_raw.items()}
    guards = []
    guards_raw = raw.get("guards", [])
    if not isinstance(guards_raw, list):
        raise OperationSamplingError("Sampling guards must be a literal list")
    for guard in guards_raw:
        if not isinstance(guard, Mapping) or set(guard) != {"field", "equals"}:
            raise OperationSamplingError("A sampling guard needs field and equals")
        guards.append({"field": _field(guard["field"], interface), "equals": _int(guard["equals"], "guard.equals")})
        _check_unsigned_encoding(guards[-1]["field"], guards[-1]["equals"])
    if name == "channel_stall" and guards:
        raise OperationSamplingError(
            "channel_stall reuses the unguarded protocol stall observation; "
            "use a custom observer for mode-qualified stall semantics"
        )
    config = {"template": name, "event": event, "channel": channel, "fields": fields,
              "guards": guards, "field_binding_origin": "code_unique_role_and_type" if code_bound_field else "verifier_declared"}
    if name == "custom":
        observer = raw["observer"]
        if not isinstance(observer, str) or not observer.isidentifier():
            raise OperationSamplingError("custom observer must name a local function")
        config["observer"] = observer
        types = raw.get("field_types", {})
        if not isinstance(types, Mapping) or set(types) - set(fields):
            raise OperationSamplingError("field_types must map declared observation fields to contract data types")
        config["field_types"] = {key: _dtype(value, architecture) for key, value in types.items()}
        for key, dtype in config["field_types"].items():
            if _known_width(fields[key]) not in {None, dtype["width"]}:
                raise OperationSamplingError("Integer sampling field width must match its declared data type")
        bins = None  # Preserve generated feature-specific predicates.
    elif name == "dimension":
        bounds = _dimension(raw["dimension"], architecture)
        _check_unsigned_encoding(fields["value"], bounds["maximum"])
        config["bounds"] = bounds
        bins = _bound_bins(bounds["minimum"], bounds["maximum"])
    elif name == "integer_operand":
        dtype = _dtype(raw["data_type"], architecture)
        config["dtype"] = dtype
        if _known_width(fields["value"]) not in {None, dtype["width"]}:
            raise OperationSamplingError("Integer sampling field width must match its declared data type")
        bins = [_bin("zero", "eq", 0)]
        if dtype["maximum"] >= 1:
            bins.append(_bin("positive", "between", 1, dtype["maximum"]))
        if dtype["minimum"] < 0:
            bins.append(_bin("negative", "between", dtype["minimum"], -1))
        bins.extend([_bin("minimum", "eq", dtype["minimum"]), _bin("maximum", "eq", dtype["maximum"])])
    elif name in {"boolean_mode", "discrete_mode"}:
        values = raw["legal_values"]
        if not isinstance(values, list) or not values or any(type(value) is not int or value < 0 for value in values) or len(values) != len(set(values)):
            raise OperationSamplingError("legal_values needs distinct nonnegative contract encodings")
        if name == "boolean_mode" and not set(values) <= {0, 1}:
            raise OperationSamplingError("boolean_mode encodings must be 0 or 1")
        config["legal_values"] = list(values)
        _check_unsigned_encoding(fields["value"], max(values))
        bins = [_bin(("enabled" if value else "disabled") if name == "boolean_mode" else f"mode_{value}", "eq", value) for value in values]
    elif name == "tile_shape":
        parameters = {item["name"]: item for item in architecture.get("parameters", [])}
        if not isinstance(raw["tile_parameters"], Mapping) or set(raw["tile_parameters"]) != set(fields):
            raise OperationSamplingError("tile_parameters must map every dimension field to a contract parameter")
        axes = {}
        for axis, parameter_name in raw["tile_parameters"].items():
            if parameter_name not in parameters:
                raise OperationSamplingError(f"Unknown tile parameter {parameter_name!r}")
            value = str(parameters[parameter_name].get("default_value", ""))
            if not value.isdigit() or int(value) < 1:
                raise OperationSamplingError("tile_shape currently supports positive literal parameter defaults")
            axes[axis] = {**_dimension(axis, architecture), "tile": int(value)}
            _check_unsigned_encoding(fields[axis], axes[axis]["maximum"])
        config["axes"] = axes
        full = all((item["minimum"] + item["tile"] - 1) // item["tile"] * item["tile"] <= item["maximum"] for item in axes.values())
        partial = any(item["minimum"] != item["maximum"] and item["tile"] > 1 or item["minimum"] % item["tile"] for item in axes.values())
        bins = ([_bin("full_tile", "eq", False)] if full else []) + ([_bin("partial_tile", "eq", True)] if partial else [])
    elif name == "channel_stall":
        bins = copy.deepcopy(catalog[name]["bins"])
    else:
        if not isinstance(raw["operand_types"], Mapping) or set(raw["operand_types"]) != {"a", "b"}:
            raise OperationSamplingError("integer_add_overflow needs operand_types for a and b")
        config["operand_types"] = {key: _dtype(value, architecture) for key, value in raw["operand_types"].items()}
        for key, dtype in config["operand_types"].items():
            if _known_width(fields[key]) not in {None, dtype["width"]}:
                raise OperationSamplingError("Integer sampling field width must match its declared data type")
        config["result_type"] = _dtype(raw["result_type"], architecture)
        low = sum(item["minimum"] for item in config["operand_types"].values())
        high = sum(item["maximum"] for item in config["operand_types"].values())
        target = config["result_type"]
        bins = []
        if max(low, target["minimum"]) <= min(high, target["maximum"]):
            bins.append(_bin("no_overflow", "eq", False))
        if low < target["minimum"] or high > target["maximum"]:
            bins.append(_bin("overflow", "eq", True))
    return config, bins


def attach_operation_sampling(plan: Mapping[str, Any], bindings: list[Mapping[str, Any]],
                              architecture: Mapping[str, Any], interface: Mapping[str, Any]) -> dict:
    from multigent.verifier_tool.coverage.operation.plan import canonical_operation_obligation_id

    result = copy.deepcopy(dict(plan))
    points = {item["id"]: item for item in result["obligations"]}
    seen = {}
    for raw in bindings:
        if not isinstance(raw.get("operation"), str) or not isinstance(raw.get("point"), str):
            raise OperationSamplingError("A binding needs operation and point IDs")
        identity = canonical_operation_obligation_id(raw["operation"], raw["point"])
        if identity in seen:
            if seen[identity] != raw:
                raise OperationSamplingError(f"Conflicting sampling bindings for {identity}")
            continue  # Several TB modules may repeat the same connection metadata.
        seen[identity] = dict(raw)
        if identity not in points or points[identity]["bindings"]["operation_name"] != raw["operation"]:
            raise OperationSamplingError(f"Sampling binding references undeclared coverpoint {identity}")
        try:
            config, bins = _compile(raw, architecture, interface)
        except OperationSamplingError:
            raise
        except (TypeError, KeyError, ValueError) as exc:
            # Malformed static metadata is a counted Verifier correction, not a
            # Python orchestration exception escaping the existing repair loop.
            raise OperationSamplingError(f"Malformed sampling binding for {identity}: {exc}") from exc
        point = points[identity]
        if bins is not None:
            point["bins"] = bins
        point["bindings"]["sampling"] = config
    return result


def effective_operation_coverage(specs: list[Mapping[str, Any]], plan: Mapping[str, Any]) -> list[dict]:
    """Expose authoritative runtime bins to validation/review, not ignored draft bins."""
    from multigent.verifier_tool.coverage.operation.plan import canonical_operation_obligation_id

    points = {item["id"]: item for item in plan["obligations"]}
    result = copy.deepcopy(specs)
    for operation in result:
        for point in operation["coverpoints"]:
            identity = canonical_operation_obligation_id(operation["operation_name"], point["id"])
            if points[identity]["bindings"].get("sampling"):
                point["bins"] = copy.deepcopy(points[identity]["bins"])
    return result


class OperationSamplingMonitor:
    """Read actual DUT fields and feed the real cocotb-coverage backend."""

    def __init__(self, plan: Mapping[str, Any], read_signal: Callable, read_width: Callable):
        missing = [item["id"] for item in plan.get("obligations", [])
                   if item.get("template") == "operation_coverpoint" and not item.get("bindings", {}).get("sampling")]
        if missing:
            raise OperationSamplingError(f"Missing operation sampling bindings: {sorted(missing)}; add reusable templates or custom observers")
        self.points = {item["id"]: item for item in plan.get("obligations", [])
                       if item.get("bindings", {}).get("sampling")}
        self.read_signal, self.read_width = read_signal, read_width
        self.counts: dict[str, int] = {}
        self.last_values: dict[str, Any] = {}
        self.observers: dict[str, Callable] = {}
        self.states: dict[str, dict[str, Any]] = {}

    def reset(self) -> None:
        self.states.clear()

    def bind_observers(self, module_globals: Mapping[str, Any]) -> None:
        """Automatically activate only custom points owned by this test module."""
        from multigent.verifier_tool.coverage.operation.plan import canonical_operation_obligation_id

        self.observers.clear()
        declarations = module_globals.get("OPERATION_SAMPLING_BINDINGS", [])
        owned = {canonical_operation_obligation_id(item["operation"], item["point"])
                 for item in declarations if item.get("template") == "custom"}
        for identity in owned:
            point = self.points.get(identity)
            if point is None or point["bindings"]["sampling"]["template"] != "custom":
                raise OperationSamplingError(f"Custom observer references unconfigured point {identity}")
            name = point["bindings"]["sampling"]["observer"]
            observer = module_globals.get(name)
            if not callable(observer):
                raise OperationSamplingError(f"Custom observer {name!r} is missing from test module")
            self.observers[identity] = observer

    def _read(self, dut: Any, field: Mapping[str, Any], dtype: Mapping[str, Any] | None = None) -> int:
        actual_width = self.read_width(dut, field["signal"], field.get("declared_width") or 0)
        width = field["width"] if field["width"] is not None else actual_width - field["lsb"]
        if width < 1 or field["lsb"] + width > actual_width:
            raise OperationSamplingError(f"Sampling field exceeds elaborated width: {field}")
        if dtype is not None and width != dtype["width"]:
            raise OperationSamplingError("Integer sampling field width must match its declared data type")
        value = (self.read_signal(dut, field["signal"]) >> field["lsb"]) & ((1 << width) - 1)
        if dtype and dtype["signed"] and value & (1 << (width - 1)):
            value -= 1 << width
        return value

    def sample(
        self,
        dut: Any,
        sample_value: Callable[[str, Any], Any],
        *,
        reset_active: bool = False,
        completed_stalls: Mapping[tuple[str, str], int],
    ) -> None:
        if reset_active:
            self.reset()
            return
        for identity, point in self.points.items():
            config = point["bindings"]["sampling"]
            if any(self._read(dut, item["field"]) != item["equals"] for item in config["guards"]):
                continue
            name = config["template"]
            if name == "custom" and identity not in self.observers:
                continue  # Another module's definition is sampled in its own tests.
            if config["event"] == "transfer":
                valid = bool(self.read_signal(dut, config["channel"]["valid"]))
                ready = bool(self.read_signal(dut, config["channel"]["ready"]))
                if name == "channel_stall":
                    if valid and not ready:
                        continue
                    if not (valid and ready):
                        continue
                elif not (valid and ready):
                    continue
            fields = config["fields"]
            if name == "custom":
                values = MappingProxyType({key: self._read(dut, field, config["field_types"].get(key))
                                           for key, field in fields.items()})
                try:
                    value = self.observers[identity](values, self.states.setdefault(identity, {}))
                except Exception as exc:
                    raise OperationSamplingError(f"Custom observer {config['observer']!r} failed: {type(exc).__name__}: {exc}") from exc
                if value is None:
                    continue
                if type(value) not in {str, int, float, bool} or isinstance(value, float) and not math.isfinite(value):
                    raise OperationSamplingError("Custom observer must return a finite scalar or None, never a claimed hit collection")
            elif name == "channel_stall":
                pair = (
                    str(config["channel"]["valid"]),
                    str(config["channel"]["ready"]),
                )
                value = int(completed_stalls.get(pair, 0))
            elif name == "integer_operand":
                value = self._read(dut, fields["value"], config["dtype"])
            elif name == "tile_shape":
                dimensions = {axis: self._read(dut, fields[axis]) for axis in config["axes"]}
                if any(not item["minimum"] <= dimensions[axis] <= item["maximum"]
                       for axis, item in config["axes"].items()):
                    continue  # An accepted illegal shape is not a legal tile witness.
                value = any(dimensions[axis] % item["tile"] for axis, item in config["axes"].items())
            elif name == "integer_add_overflow":
                total = sum(self._read(dut, fields[key], dtype) for key, dtype in config["operand_types"].items())
                value = not config["result_type"]["minimum"] <= total <= config["result_type"]["maximum"]
            else:
                value = self._read(dut, fields["value"])
            sample_value(identity, value)
            self.counts[identity] = self.counts.get(identity, 0) + 1
            self.last_values[identity] = value

    def report(self) -> list[dict[str, Any]]:
        return [{"id": identity, "origin": "runtime_dut_observation",
                 "implementation": "llm_custom_observer" if point["bindings"]["sampling"]["template"] == "custom" else "reusable_template",
                 "template": point["bindings"]["sampling"]["template"],
                 "field_binding_origin": point["bindings"]["sampling"].get(
                     "field_binding_origin", "verifier_declared"),
                 "samples": self.counts.get(identity, 0), "last_value": self.last_values.get(identity)}
                for identity, point in sorted(self.points.items())]
