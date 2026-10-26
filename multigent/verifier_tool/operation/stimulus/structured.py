"""Bounded constructors for block geometry and softmax row cases.

Every directed constructor is independently reclassified by the canonical
generator before use. Shape-dependent impossibilities are explicit, never hits.
"""

from __future__ import annotations

from itertools import product
from math import ceil, prod

from multigent.verifier_tool.pool.operation_metadata.structured import profile_module


def _base(operation):
    return {b["data_object"]: [0]*prod(operation["dimensions"][d] for d in b["dimensions"])
            for b in operation["inputs"]}


def _values(dtype):
    w=dtype["width_bits"]; lo,hi=(-(1<<(w-1)),(1<<(w-1))-1) if dtype["signed"] else (0,(1<<w)-1)
    return list(dict.fromkeys(x for x in (0,1,-1,lo,hi) if lo<=x<=hi))


def _block_coordinates(spec):
    s=spec["shape"]; br=ceil(s["rows"]/spec["block_rows"]); bc=ceil(s["columns"]/spec["block_columns"])
    pairs=list(dict.fromkeys([(0,0),(br-1,0),(0,bc-1),(br-1,bc-1)]))
    if br*bc>1: pairs.append((0,1) if bc>1 else (1,0))
    options=[[], *[[p] for p in pairs]]
    if s["slots"]>1:
        far=(br-1,bc-1)
        options.extend([[pairs[0],far], [far,pairs[0]], [pairs[0],pairs[-1]]])
        if spec["duplicate_policy"]=="allow": options.append([pairs[0],pairs[0]])
    for seq in options:
        if len(seq)>s["slots"]: continue
        if spec["duplicate_policy"]=="forbid" and len(set(seq))!=len(seq): continue
        yield [v for pair in seq+[(-1,-1)]*(s["slots"]-len(seq)) for v in pair]


def candidates(operation):
    spec=operation["arithmetic"]; module=profile_module(spec["classifier_profile"])
    if module.FAMILY!="block_matmul":
        yield from module.candidates(operation)
        return
    b=spec["bindings"]
    for coordinates in _block_coordinates(spec):
        for av,bv in product(_values(b["left_operand_matrix"]["data_type"]), _values(b["right_operand_matrix"]["data_type"])):
            case=_base(operation)
            case[b["block_coordinates"]["name"]]=coordinates
            for role,value in (("left_operand_matrix",av),("right_operand_matrix",bv)):
                case[b[role]["name"]]=[value]*len(case[b[role]["name"]])
            yield case
            one_hot={name:list(values) for name,values in case.items()}
            for role in ("left_operand_matrix","right_operand_matrix"):
                one_hot[b[role]["name"]]=[0]*len(case[b[role]["name"]])
            for row in range(spec["shape"]["rows"]): one_hot[b["left_operand_matrix"]["name"]][row*spec["shape"]["depth"]]=av
            for col in range(spec["shape"]["columns"]):
                index=col*spec["shape"]["depth"] if spec["right_transposed"] else col
                one_hot[b["right_operand_matrix"]["name"]][index]=bv
            yield one_hot
            last_only = {name:list(values) for name,values in one_hot.items()}
            for role in ("left_operand_matrix", "right_operand_matrix"):
                last_only[b[role]["name"]] = [0]*len(case[b[role]["name"]])
            depth, columns = spec["shape"]["depth"], spec["shape"]["columns"]
            for row in range(spec["shape"]["rows"]):
                last_only[b["left_operand_matrix"]["name"]][row*depth+depth-1] = av
            for col in range(columns):
                index = col*depth+depth-1 if spec["right_transposed"] else (depth-1)*columns+col
                last_only[b["right_operand_matrix"]["name"]][index] = bv
            yield last_only
            # Coordinate-encoded operands distinguish a correct value at the
            # wrong tile. Constant matrices alone cannot establish this case.
            indexed = {name:list(values) for name,values in case.items()}
            for role in ("left_operand_matrix", "right_operand_matrix"):
                dtype = b[role]["data_type"]
                low, high = min(_values(dtype)), max(_values(dtype))
                name = b[role]["name"]
                indexed[name] = [low+(i*7+3)%(high-low+1) for i in range(len(case[name]))]
            yield indexed


def targeted_stimulus(operation, concept, bin_name):
    from .stimulus_generator import CanonicalStimulusGenerationError
    module=profile_module(operation["arithmetic"]["classifier_profile"])
    for stimulus in candidates(operation):
        evidence=module.classify(operation,stimulus)
        target="fixed" if concept=="dimensions" else bin_name
        if target in evidence.get(concept,[]): return stimulus
    # The profile constructors span the relevant geometry/row classes, not a
    # stochastic search. Keep a bounded, explicit status for unsupported witnesses.
    reason=getattr(module,"unreachable_reason",lambda *args: None)(operation,concept,bin_name)
    raise CanonicalStimulusGenerationError("unreachable" if reason else "generation_inconclusive", reason or "Bounded constructor did not establish a witness; no unreachability claim is made",
        operation_name=operation["operation_name"],concept=concept,bin_name=bin_name)


def randomized_stimulus(operation,rng):
    spec=operation["arithmetic"]; module=profile_module(spec["classifier_profile"])
    if module.FAMILY!="block_matmul": return module.randomized_stimulus(operation,rng)
    case=_base(operation); b=spec["bindings"]; s=spec["shape"]
    for role in ("left_operand_matrix","right_operand_matrix"):
        dtype=b[role]["data_type"]; edge=_values(dtype); low,high=min(edge),max(edge)
        case[b[role]["name"]]=[rng.choice(edge) if rng.random()<0.4 else rng.randint(low,high) for _ in case[b[role]["name"]]]
    # A sparse work list can address a huge logical grid even when its actual
    # operands/results fit the canonical budget. Never materialize that grid.
    grid_columns = ceil(s["columns"]/spec["block_columns"])
    grid_size = ceil(s["rows"]/spec["block_rows"]) * grid_columns
    count=rng.randrange(s["slots"]+1)
    if spec["duplicate_policy"]=="forbid":
        selected_indices = rng.sample(range(grid_size), min(count, grid_size))
    else:
        selected_indices = [rng.randrange(grid_size) for _ in range(count)]
    selected = [divmod(index, grid_columns) for index in selected_indices]
    case[b["block_coordinates"]["name"]]=[v for pair in selected+[(-1,-1)]*(s["slots"]-len(selected)) for v in pair]
    return case


def discriminating_stimuli(operation):
    from random import Random
    from .stimulus_generator import evaluate_canonical_operation
    from multigent.verifier_tool.pool.operation_metadata.canonical import assemble_canonical_job, classify_operation_job
    result=[]
    spec=operation["arithmetic"]; module=profile_module(spec["classifier_profile"])
    for i in range(3):
        stimulus=randomized_stimulus(operation,Random(0xB10C+i))
        if module.FAMILY=="block_matmul":
            b=spec["bindings"]
            options=list(_block_coordinates(spec))
            stimulus[b["block_coordinates"]["name"]]=options[-1]
            for role in ("left_operand_matrix","right_operand_matrix"):
                name=b[role]["name"]; vals=_values(b[role]["data_type"]); low,high=min(vals),max(vals)
                stimulus[name]=[0 if i==2 else low+(index*7+3)%(high-low+1) for index in range(len(stimulus[name]))]
        expected=evaluate_canonical_operation(operation,stimulus)
        job=assemble_canonical_job(operation,stimulus,expected,expected)
        result.append({"operation_name":operation["operation_name"],"kind":"directed",
                       "label":f"structured_index_sign_repeat_{i}","target":None,"stimulus":stimulus,
                       "expected":expected,"evidence":classify_operation_job(job)})
    return result
