"""Explicit compilation boundary for indexed blocks and normalized rows.

These profiles change logical I/O, not the meaning of the existing dense QK,
mask, or GEMM profiles. No signal-name or RTL-based inference is performed.
"""

from __future__ import annotations

from copy import deepcopy
from math import prod
from typing import Any, Mapping


STRUCTURED_PROFILES = frozenset({"integer_block_matmul", "fixed_point_softmax"})


def profile_module(profile: str):
    if profile == "integer_block_matmul":
        from . import blocks
        return blocks
    if profile == "fixed_point_softmax":
        from . import softmax
        return softmax
    raise ValueError(f"Unknown structured arithmetic profile {profile!r}")


def compile_structured_arithmetic(operation, architecture, declaration):
    from .arithmetic_metadata import ArithmeticMetadataError, _dtype, _named

    module = profile_module(str(declaration["classifier_profile"]))
    if operation.get("coverage_family") != module.FAMILY:
        raise ArithmeticMetadataError(f"{declaration['classifier_profile']} requires family {module.FAMILY}")
    objects = {
        direction: [_named(architecture.get("data_objects", []), str(name), "data object")
                    for name in operation.get(direction, [])]
        for direction in ("inputs", "outputs")
    }
    bindings = {}
    dimensions = {}
    for direction, roles in module.object_roles(declaration).items():
        if len(objects[direction]) != len(roles):
            raise ArithmeticMetadataError(f"{module.FAMILY} has unmodeled or missing {direction}")
        for role in roles:
            matches = [obj for obj in objects[direction] if obj.get("role") == role]
            if len(matches) != 1:
                raise ArithmeticMetadataError(f"{module.FAMILY} needs exactly one object role {role!r}")
            obj = matches[0]
            shape = []
            for axis in obj.get("dimensions", []):
                dim = _named(architecture.get("dimensions", []), axis, "dimension")
                if dim.get("runtime_configurable"):
                    raise ArithmeticMetadataError("Runtime-configurable shapes require an explicit extension")
                low, high = dim.get("minimum"), dim.get("maximum")
                extent = low if low == high else None
                if extent is None:
                    param = _named(architecture.get("parameters", []), str(dim.get("bound_parameter", "")), "parameter")
                    try:
                        extent = int(str(param.get("default_value", "")), 0)
                    except ValueError as exc:
                        raise ArithmeticMetadataError(f"Dimension {axis!r} needs an integer default") from exc
                if any(type(x) is not int for x in (low, high, extent)) or not 0 < low <= extent <= high:
                    raise ArithmeticMetadataError(f"Dimension {axis!r} has invalid fixed bounds")
                dimensions[str(axis)] = extent
                shape.append(extent)
            bindings[role] = {"name": obj["name"], "shape": shape, "axes": list(obj.get("dimensions", [])),
                              "data_type": _dtype(architecture, str(obj["data_type"]))}
    if sum(prod(obj["shape"]) for obj in bindings.values()) > 1_000_000:
        raise ArithmeticMetadataError("Structured operation exceeds the bounded canonical element budget")
    types = {field: _dtype(architecture, str(declaration[field])) for field in module.TYPE_FIELDS}
    spec = deepcopy(dict(declaration))
    spec.update(types)
    spec["bindings"] = bindings
    spec["shape"] = module.validate_spec(spec)
    spec.update(metadata_origin="explicit_contract", support_status=f"supported_{declaration['classifier_profile']}")
    return spec


def validate_structured_resolved(metadata):
    """Recompile external canonical metadata; resolved dictionaries cannot bypass validation."""
    from .arithmetic_metadata import ArithmeticMetadataError, _schema

    arithmetic = metadata["arithmetic"]
    profile = str(arithmetic["classifier_profile"])
    module = profile_module(profile)
    branch = next(b for b in _schema()["anyOf"] if profile in b["properties"]["classifier_profile"]["enum"])
    absent = set(branch["required"]) - set(arithmetic)
    if absent:
        raise ArithmeticMetadataError(f"{profile} metadata is missing {sorted(absent)}")
    declaration = {name: deepcopy(arithmetic[name]) for name in branch["properties"] if name in arithmetic}
    types = {}

    def dtype(item):
        if not isinstance(item, Mapping) or not {"name", "width_bits", "signed"} <= set(item):
            raise ArithmeticMetadataError("Resolved structured data types need name, width_bits, signed")
        value = {key: item[key] for key in ("name", "width_bits", "signed")}
        name = str(value["name"])
        if name in types and types[name] != value:
            raise ArithmeticMetadataError(f"Conflicting data type {name!r}")
        types[name] = value
        return name

    for field in module.TYPE_FIELDS:
        declaration[field] = dtype(declaration[field])
    objects = []
    for direction in ("inputs", "outputs"):
        for binding in metadata.get(direction, []):
            objects.append({"name": binding["data_object"], "role": binding["object_role"],
                            "dimensions": list(binding["dimensions"]), "data_type": dtype(binding["data_type"])})
    architecture = {"data_types": list(types.values()), "data_objects": objects,
                    "dimensions": [{"name": name, "minimum": value, "maximum": value,
                                    "runtime_configurable": False} for name, value in metadata["dimensions"].items()]}
    operation = {"coverage_family": metadata["family"],
                 **{direction: [b["data_object"] for b in metadata.get(direction, [])] for direction in ("inputs", "outputs")}}
    # Validate the declaration too: canonical metadata is an untrusted external input.
    from jsonschema import Draft202012Validator
    errors = list(Draft202012Validator(branch).iter_errors(declaration))
    if errors:
        raise ArithmeticMetadataError(errors[0].message)
    rebuilt = compile_structured_arithmetic(operation, architecture, declaration)
    if rebuilt != arithmetic:
        raise ArithmeticMetadataError("Resolved structured arithmetic disagrees with its explicit declaration/bindings")


def check_integer_values(values, dtype, label):
    width = int(dtype["width_bits"])
    lo, hi = (-(1 << (width - 1)), (1 << (width - 1)) - 1) if dtype["signed"] else (0, (1 << width) - 1)
    if any(type(value) is not int or not lo <= value <= hi for value in values):
        raise ValueError(f"{label}: element outside declared integer domain [{lo}, {hi}]")


def canonical_inputs(operation, stimulus):
    from .canonical import assemble_canonical_job
    job = assemble_canonical_job(operation, stimulus, {}, {})
    if job is None:
        raise ValueError("Structured operation has no accepted inputs")
    for binding in operation["inputs"]:
        check_integer_values(job.inputs[binding["data_object"]], binding["data_type"], binding["data_object"])
    return job.inputs
