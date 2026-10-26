"""Axis-neutral indexed block contraction and independent result accounting.

Coordinates are logical output-block indices, never byte addresses. Reduction
chunks revisit one output; column/key blocks create distinct outputs. The fixed
wire shape includes explicit zero padding and inactive (-1,-1) work slots.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


FAMILY = "block_matmul"
TYPE_FIELDS = ("product_data_type", "accumulator_data_type", "result_data_type")
CONCEPTS = {
    "dimensions": ("fixed_shape",),
    "block_selection": ("empty", "singleton", "multiple", "nonadjacent", "reordered", "duplicate"),
    "block_mapping": ("origin", "nonzero_row", "nonzero_column", "distinct_tile_results"),
    "block_tails": ("full_tile", "row_tail", "column_tail", "reduction_tail"),
    "block_reduction": ("single_chunk", "multiple_chunks", "zero_result", "positive_result", "negative_result", "nonzero_reduction_tail"),
}


def object_roles(spec):
    return {"inputs": ("left_operand_matrix", "right_operand_matrix", "block_coordinates"),
            "outputs": ("block_result",)}


def validate_spec(spec):
    from .arithmetic_metadata import ArithmeticMetadataError, _type_bounds
    b = spec["bindings"]
    left, right, indices, output = [b[r] for r in (*object_roles(spec)["inputs"], "block_result")]
    if len(left["shape"]) != 2 or len(right["shape"]) != 2 or len(indices["shape"]) != 2:
        raise ArithmeticMetadataError("Block contraction requires rank-2 operands and coordinates[W,2]")
    m, k = left["shape"]
    n, rk = right["shape"] if spec["right_transposed"] else right["shape"][::-1]
    bm, bn, bk = [spec[name] for name in ("block_rows", "block_columns", "reduction_block_size")]
    w, pair = indices["shape"]
    if rk != k or pair != 2 or output["shape"] != [w, bm, bn]:
        raise ArithmeticMetadataError("Block shapes require A[M,K], B[K,N] or B[N,K], indices[W,2], output[W,BM,BN]")
    if output["axes"][0] != indices["axes"][0]:
        raise ArithmeticMetadataError("Block output and coordinate list must share their work-slot axis")
    if left["axes"][1] != right["axes"][1 if spec["right_transposed"] else 0]:
        raise ArithmeticMetadataError("Block operands must name the same reduction axis")
    if not indices["data_type"]["signed"]:
        raise ArithmeticMetadataError("Block indices must be signed to represent inactive (-1,-1)")
    ilo, ihi = _type_bounds(indices["data_type"])
    if ilo > -1 or ihi < max(ceil(m / bm), ceil(n / bn)) - 1:
        raise ArithmeticMetadataError("Block index type cannot represent every declared block coordinate")
    if spec["result_data_type"] != output["data_type"]:
        raise ArithmeticMetadataError("Block result_data_type must match output object")
    alo, ahi = _type_bounds(left["data_type"]); blo, bhi = _type_bounds(right["data_type"])
    plo, phi = _type_bounds(spec["product_data_type"])
    if any(not plo <= x*y <= phi for x in (alo, ahi) for y in (blo, bhi)):
        raise ArithmeticMetadataError("Block product type must represent every exact product")
    total_low=min(x*y for x in (alo,ahi) for y in (blo,bhi))*k
    total_high=max(x*y for x in (alo,ahi) for y in (blo,bhi))*k
    acc_low,acc_high=_type_bounds(spec["accumulator_data_type"])
    if spec["reduction_conversion"]=="exact" and not (acc_low<=min(0,total_low) and max(0,total_high)<=acc_high):
        raise ArithmeticMetadataError("Exact block accumulation type cannot represent every legal reduction prefix")
    result_low,result_high=_type_bounds(spec["result_data_type"])
    out_low,out_high=(acc_low,acc_high) if spec["reduction_conversion"]!="exact" else (total_low,total_high)
    if spec["result_conversion"]=="exact" and not (result_low<=out_low and out_high<=result_high):
        raise ArithmeticMetadataError("Exact block result type is narrower than the reduction domain")
    return {"rows": m, "columns": n, "depth": k, "slots": w}


@dataclass(frozen=True)
class BlockElement:
    slot: int
    local_row: int
    local_column: int
    row: int
    column: int
    valid: bool


def block_elements(spec, coordinates):
    shape = spec["shape"]; bm, bn = spec["block_rows"], spec["block_columns"]
    if len(coordinates) != 2 * shape["slots"]:
        raise ValueError("Block coordinate transfer count mismatch")
    if any(type(value) is not int for value in coordinates):
        raise ValueError("Block coordinates must be integers")
    seen = set()
    for slot in range(shape["slots"]):
        rb, cb = coordinates[2*slot:2*slot+2]
        inactive = (rb, cb) == (-1, -1)
        if not inactive:
            if not (0 <= rb < ceil(shape["rows"]/bm) and 0 <= cb < ceil(shape["columns"]/bn)):
                raise ValueError("Illegal block coordinate (only (-1,-1) is inactive)")
            if (rb, cb) in seen and spec["duplicate_policy"] == "forbid":
                raise ValueError("Duplicate selected block is forbidden by the contract")
            seen.add((rb, cb))
        for lr in range(bm):
            for lc in range(bn):
                row, col = rb*bm+lr, cb*bn+lc
                yield BlockElement(slot, lr, lc, row, col,
                                   not inactive and row < shape["rows"] and col < shape["columns"])


def events(operation, inputs):
    from .canonical import _reduction_trace, _wrap
    spec = operation["arithmetic"]; b = spec["bindings"]
    a, right, coordinates = [inputs[b[r]["name"]] for r in object_roles(spec)["inputs"]]
    shape = spec["shape"]; k, n = shape["depth"], shape["columns"]
    result = []
    for item in block_elements(spec, coordinates):
        terms = []
        if item.valid:
            terms = [a[item.row*k+d] * right[item.column*k+d if spec["right_transposed"] else d*n+item.column]
                     for d in range(k)]
        value, mathematical, converted = _reduction_trace(terms, spec["accumulator_data_type"], spec["reduction_conversion"])
        if spec["result_conversion"] == "wrap_twos_complement":
            value = _wrap(value, spec["result_data_type"])
        else:
            from .structured import check_integer_values
            check_integer_values([value], spec["result_data_type"], "block exact result")
        result.append({"coordinate": [item.slot, item.local_row, item.local_column],
                       "logical_coordinate": [item.row, item.column], "valid": item.valid,
                       "result_value": value, "mathematical_reduction_prefixes": mathematical,
                       "product_terms": terms,
                       "converted_reduction_prefixes": converted})
    return result


def evaluate(operation, inputs):
    spec = operation["arithmetic"]
    return {spec["bindings"]["block_result"]["name"]: [e["result_value"] for e in events(operation, inputs)]}


def classify(operation, inputs):
    spec = operation["arithmetic"]; shape = spec["shape"]; b = spec["bindings"]
    coordinates = inputs[b["block_coordinates"]["name"]]
    # Validate before classifying; a planned index is not evidence of a legal job.
    trace = events(operation, inputs)
    selected = [tuple(coordinates[i:i+2]) for i in range(0,len(coordinates),2) if coordinates[i] != -1]
    selection = ["empty" if not selected else "singleton" if len(selected)==1 else "multiple"]
    linear = [r*ceil(shape["columns"]/spec["block_columns"])+c for r,c in selected]
    if any(abs(a-b)>1 for a,b in zip(linear,linear[1:])): selection.append("nonadjacent")
    if any(a>b for a,b in zip(linear,linear[1:])): selection.append("reordered")
    if len(set(selected)) < len(selected): selection.append("duplicate")
    mapping = []
    if (0,0) in selected: mapping.append("origin")
    if any(r>0 for r,c in selected): mapping.append("nonzero_row")
    if any(c>0 for r,c in selected): mapping.append("nonzero_column")
    tiles = {}
    for event in trace:
        slot = event["coordinate"][0]
        if coordinates[2*slot] >= 0:
            tiles.setdefault(slot, []).append(event["result_value"])
    if len({tuple(values) for values in tiles.values()}) > 1:
        mapping.append("distinct_tile_results")
    tails = []
    for r,c in selected:
        rt=(r+1)*spec["block_rows"]>shape["rows"]; ct=(c+1)*spec["block_columns"]>shape["columns"]
        if not rt and not ct: tails.append("full_tile")
        if rt: tails.append("row_tail")
        if ct: tails.append("column_tail")
    if selected and shape["depth"] % spec["reduction_block_size"]: tails.append("reduction_tail")
    reductions = []
    if selected:
        reductions.append("single_chunk" if spec["reduction_block_size"]>=shape["depth"] else "multiple_chunks")
        for event in trace:
            if event["valid"]:
                reductions.append("zero_result" if event["result_value"]==0 else "positive_result" if event["result_value"]>0 else "negative_result")
        tail = shape["depth"] % spec["reduction_block_size"]
        def tail_changes_result(event):
            before = event["converted_reduction_prefixes"][-tail-1] if len(event["product_terms"]) > tail else 0
            if spec["result_conversion"] == "wrap_twos_complement":
                from .canonical import _wrap
                before = _wrap(before, spec["result_data_type"])
            return event["result_value"] != before
        if tail and any(tail_changes_result(event) for event in trace if event["valid"]):
            reductions.append("nonzero_reduction_tail")
    return {"dimensions":["fixed"], "block_selection":selection, "block_mapping":mapping,
            "block_tails":list(dict.fromkeys(tails)), "block_reduction":list(dict.fromkeys(reductions)),
            "numeric_stage_events":trace}


def assert_block_records(expected_records, observed_records):
    """Check real externally captured (slot,row,column,value) records, not internal nets."""
    def collect(records, label):
        result = {}
        for record in records:
            if len(record) != 4: raise AssertionError(f"{label}: malformed block record")
            key = tuple(record[:3])
            if key in result: raise AssertionError(f"{label}: duplicate block destination {key}")
            result[key] = record[3]
        return result
    expected=collect(expected_records,"expected"); observed=collect(observed_records,"observed")
    if not expected:
        raise AssertionError("Block record assertion requires nonempty expected transfers; inactive padded slots are still transfers")
    if expected.keys() != observed.keys():
        raise AssertionError(f"Block destinations differ: missing={expected.keys()-observed.keys()}, unexpected={observed.keys()-expected.keys()}")
    if expected != observed: raise AssertionError("Block result value/coordinate mismatch")


def unreachable_reason(operation, concept, name):
    spec=operation["arithmetic"]; s=spec["shape"]
    nr=ceil(s["rows"]/spec["block_rows"]); nc=ceil(s["columns"]/spec["block_columns"])
    impossible=(
        (concept=="block_selection" and name in ("multiple","reordered","nonadjacent","duplicate") and s["slots"]<2)
        or (concept=="block_selection" and name=="duplicate" and spec["duplicate_policy"]=="forbid")
        or (concept=="block_selection" and name=="reordered" and nr*nc<2)
        or (concept=="block_selection" and name=="nonadjacent" and nr*nc<3)
        or (concept=="block_selection" and name=="multiple" and nr*nc<2 and spec["duplicate_policy"]=="forbid")
        or (concept=="block_mapping" and name=="nonzero_row" and nr<2)
        or (concept=="block_mapping" and name=="nonzero_column" and nc<2)
        or (concept=="block_mapping" and name=="distinct_tile_results" and (s["slots"]<2 or nr*nc<2))
        or (concept=="block_tails" and name=="full_tile" and (s["rows"]<spec["block_rows"] or s["columns"]<spec["block_columns"]))
        or (concept=="block_tails" and name=="row_tail" and s["rows"]%spec["block_rows"]==0)
        or (concept=="block_tails" and name=="column_tail" and s["columns"]%spec["block_columns"]==0)
        or (concept=="block_tails" and name=="reduction_tail" and s["depth"]%spec["reduction_block_size"]==0)
        or (concept=="block_reduction" and name=="single_chunk" and s["depth"]>spec["reduction_block_size"])
        or (concept=="block_reduction" and name=="multiple_chunks" and s["depth"]<=spec["reduction_block_size"])
        or (concept=="block_reduction" and name=="nonzero_reduction_tail" and s["depth"]%spec["reduction_block_size"]==0)
        or (concept=="block_reduction" and name=="negative_result" and not spec["result_data_type"]["signed"])
    )
    return "Excluded by fixed block geometry, result domain, or duplicate policy" if impossible else None
