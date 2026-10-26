"""Independent, black-box arithmetic invariants on accepted external tensors.

These checks never use an expected array, the golden evaluator, hierarchical
handles, or an internal trace. They supplement, rather than replace, exact
golden equivalence. Returned IDs identify checks actually exercised by this job.
"""

from __future__ import annotations

from math import prod


PROFILES = frozenset({
    "integer_qk_score", "fixed_point_attention_scale", "binary_attention_mask",
    "integer_block_matmul", "fixed_point_softmax", "integer_sparse_attention",
})


def assert_external_operation_invariants(operation_metadata, stimulus, observed):
    operation = operation_metadata
    spec = operation.get("arithmetic", {})
    profile = spec.get("classifier_profile")
    if profile not in PROFILES:
        return ()
    checked = []

    def check(name, condition):
        if not condition:
            raise AssertionError(f"external_operation.{name}: accepted output violates the external invariant")
        if name not in checked:
            checked.append(name)

    def bounds(dtype):
        width = int(dtype["width_bits"])
        return (-(1 << (width-1)), (1 << (width-1))-1) if dtype["signed"] else (0, (1 << width)-1)

    def tensor(role, output=False):
        bindings = operation["outputs" if output else "inputs"]
        matches = [b for b in bindings if b["object_role"] == role]
        if len(matches) != 1:
            raise AssertionError(f"external_operation.binding: missing or ambiguous role {role}")
        binding = matches[0]
        values = list((observed if output else stimulus)[binding["data_object"]])
        shape = [operation["dimensions"][d] for d in binding["dimensions"]]
        low, high = bounds(binding["data_type"])
        if len(values) != prod(shape) or any(type(v) is not int or not low <= v <= high for v in values):
            raise AssertionError(f"external_operation.tensor_domain: invalid external tensor {role}")
        return values, shape, binding["data_type"]

    def chunks(values, width):
        return [values[i:i+width] for i in range(0, len(values), width)]

    def repeated(keys, values, name):
        seen = {}
        for key, value in zip(keys, values):
            key = tuple(key)
            if key in seen:
                check(name, seen[key] == value)
            seen[key] = value

    def convert(value, dtype, policy):
        if policy == "wrap_twos_complement":
            width = int(dtype["width_bits"])
            value %= 1 << width
            if dtype["signed"] and value >= 1 << (width-1):
                value -= 1 << width
        return value

    if profile == "integer_qk_score":
        q, (rows, depth), _ = tensor("query_matrix")
        k, (columns, _), _ = tensor("key_matrix")
        out, _, dtype = tensor("attention_score_matrix", True)
        qr, kr, result = chunks(q, depth), chunks(k, depth), chunks(out, columns)
        initial = int(spec["score_accumulator_initialization"])
        zero = convert(initial, dtype, spec["result_data_type"]["conversion"])
        for r in range(rows):
            for c in range(columns):
                if not any(qr[r]) or not any(kr[c]):
                    check("qk.zero_operand", result[r][c] == zero)
        repeated(qr, result, "qk.equal_queries")
        repeated(kr, [[result[r][c] for r in range(rows)] for c in range(columns)], "qk.equal_keys")
    elif profile == "fixed_point_attention_scale":
        values, _, _ = tensor("attention_score_matrix")
        out, _, _ = tensor("scaled_attention_score_matrix", True)
        for value, result in zip(values, out):
            if value == 0:
                check("scale.zero_preserved", result == 0)
        repeated([[v] for v in values], out, "scale.equal_inputs")
        if spec["result_data_type"]["conversion"] == "exact":
            ordered = sorted(zip(values, out))
            check("scale.monotonic", all(a[1] <= b[1] for a, b in zip(ordered, ordered[1:])))
    elif profile == "binary_attention_mask":
        values, _, _ = tensor("scaled_attention_score_matrix")
        keep, _, _ = tensor("attention_mask")
        out, _, dtype = tensor("masked_attention_score_matrix", True)
        for value, bit, result in zip(values, keep, out):
            if bit == 0:
                check("mask.excluded_zero", result == 0)
            else:
                check("mask.kept_value", result == convert(value, dtype, spec["result_data_type"]["conversion"]))
    elif profile == "integer_block_matmul":
        _, (rows, _), _ = tensor("left_operand_matrix")
        _, right_shape, _ = tensor("right_operand_matrix")
        columns = right_shape[0 if spec["right_transposed"] else 1]
        indices, _, _ = tensor("block_coordinates")
        out, (_, bm, bn), _ = tensor("block_result", True)
        tiles = chunks(out, bm*bn)
        coordinates = chunks(indices, 2)
        for (rb, cb), tile in zip(coordinates, tiles):
            if (rb, cb) != (-1, -1) and not (0 <= rb < (rows+bm-1)//bm and 0 <= cb < (columns+bn-1)//bn):
                raise AssertionError("external_operation.block_coordinate_domain: illegal input coordinate")
            for lr in range(bm):
                for lc in range(bn):
                    if (rb, cb) == (-1, -1) or rb*bm+lr >= rows or cb*bn+lc >= columns:
                        check("block.padding_zero", tile[lr*bn+lc] == 0)
        repeated(coordinates, tiles, "block.duplicate_tile_equal")
    elif profile == "fixed_point_softmax":
        scores, (_, columns), _ = tensor("softmax_scores")
        out, _, _ = tensor("softmax_probabilities", True)
        keep = tensor("softmax_mask")[0] if spec["mask_mode"] == "binary_keep" else [1]*len(scores)
        row_keys, row_outputs = [], []
        for row, bits, result in zip(chunks(scores, columns), chunks(keep, columns), chunks(out, columns)):
            check("softmax.output_range", all(0 <= v <= spec["output_maximum"] for v in result))
            active = [(score, value) for score, bit, value in zip(row, bits, result) if bit]
            for bit, value in zip(bits, result):
                if not bit:
                    check("softmax.excluded_zero", value == 0)
            if not active:
                check("softmax.empty_row_zero", not any(result))
            repeated([[score] for score, _ in active], [value for _, value in active], "softmax.equal_scores")
            ordered = sorted(active)
            if len(ordered) > 1:
                check("softmax.score_order", all(a[1] <= b[1] for a, b in zip(ordered, ordered[1:])))
            if spec["division"]["kind"] == "exact_divide" and spec["rounding"] == "floor":
                check("softmax.floor_mass_bound", sum(result) <= spec["output_scale"])
            row_keys.append([*row, *bits]); row_outputs.append(result)
        repeated(row_keys, row_outputs, "softmax.equal_rows")
    else:
        _, (rows, _), _ = tensor("query_matrix")
        values, (keys, width), _ = tensor("value_matrix")
        keep, _, _ = tensor("attention_mask")
        out, _, _ = tensor("attention_result", True)
        result = chunks(out, width)
        for r in range(rows):
            if not any(keep[r*keys:(r+1)*keys]):
                check("sparse.empty_row_zero", not any(result[r]))
        columns = [[values[k*width+c] for k in range(keys)] for c in range(width)]
        output_columns = [[result[r][c] for r in range(rows)] for c in range(width)]
        for column, output in zip(columns, output_columns):
            if not any(column):
                check("sparse.zero_value_column", not any(output))
        repeated(columns, output_columns, "sparse.equal_value_columns")
    return tuple(checked)
