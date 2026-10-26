"""Contract-defined fixed-point row softmax, separate from binary score masking.

LUT values, scale, clipping, denominator conversion, division, and output rounding
are explicit. The mathematical model is a distinct characterization oracle.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from itertools import product

FAMILY = "softmax"
TYPE_FIELDS = ("result_data_type",)
CONCEPTS = {
    "dimensions": ("fixed_shape",),
    "row_patterns": ("uniform", "tied_maximum", "unique_maximum", "all_negative", "mixed_sign", "distinct_rows"),
    "mask_patterns": ("unmasked", "singleton", "partial", "fully_masked", "masked_maximum", "masked_zero"),
    "exp_domain": ("zero_delta", "interior_delta", "last_lut_entry", "clipped_delta"),
    "normalization": ("zero_probability", "positive_probability", "rounded_division", "exact_division", "tiny_positive_weight_zero"),
}


def object_roles(spec):
    return {"inputs": ("softmax_scores", "softmax_mask") if spec["mask_mode"] == "binary_keep" else ("softmax_scores",),
            "outputs": ("softmax_probabilities",)}


def validate_spec(spec):
    from .arithmetic_metadata import ArithmeticMetadataError
    b = spec["bindings"]
    score = b["softmax_scores"]
    output = b["softmax_probabilities"]
    if len(score["shape"]) != 2 or score["shape"] != output["shape"] or score["axes"] != output["axes"]:
        raise ArithmeticMetadataError("Softmax needs aligned scores[rows,columns] and probabilities[rows,columns]")
    if not score["data_type"]["signed"] or output["data_type"]["signed"]:
        raise ArithmeticMetadataError("Softmax scores must be signed and probabilities unsigned")
    if spec["result_data_type"] != output["data_type"]:
        raise ArithmeticMetadataError("Softmax result type must match the output object")
    if spec["mask_mode"] == "binary_keep":
        mask = b["softmax_mask"]
        if mask["shape"] != score["shape"] or mask["axes"] != score["axes"] or mask["data_type"]["signed"] or mask["data_type"]["width_bits"] != 1:
            raise ArithmeticMetadataError("Softmax mask must be aligned unsigned one-bit keep/exclude metadata")
    table = spec["exp_lut"]
    if table[0] != 1 << spec["exp_fraction_bits"] or any(a < b for a,b in zip(table,table[1:])):
        raise ArithmeticMetadataError("Softmax exp LUT must start at exact one and be nonincreasing")
    if not 0 < spec["output_scale"] <= 1 << (output["data_type"]["width_bits"] - 0):
        raise ArithmeticMetadataError("Invalid softmax output scale")
    if not 0 < spec["output_maximum"] <= min(spec["output_scale"], (1 << output["data_type"]["width_bits"]) - 1):
        raise ArithmeticMetadataError("Invalid softmax output saturation")
    if spec["division"]["kind"] == "reciprocal_newton":
        div = spec["division"]
        if div["denominator_fraction_bits"] > spec["exp_fraction_bits"]:
            raise ArithmeticMetadataError("Reciprocal denominator conversion only discards fractional bits")
        if div["denominator_width"] < div["denominator_fraction_bits"] + 1:
            raise ArithmeticMetadataError("Reciprocal denominator cannot represent exp(0)")
        maximum = score["shape"][1] << div["denominator_fraction_bits"]
        if maximum >= 1 << div["denominator_width"]:
            raise ArithmeticMetadataError("Reciprocal denominator would overflow for a uniform row")
        if div["reciprocal_width"] <= div["reciprocal_fraction_bits"]:
            raise ArithmeticMetadataError("Reciprocal must represent one exactly")
        if spec["rounding"] != "floor":
            raise ArithmeticMetadataError("Reciprocal multiply currently supports explicit floor rounding only")
    return {"rows": score["shape"][0], "columns": score["shape"][1]}


def _rounded_division(numerator, denominator, mode):
    q, r = divmod(numerator, denominator)
    if mode == "nearest_even" and (2*r > denominator or (2*r == denominator and q & 1)):
        q += 1
    return q, r


def _normalize(weights, total, spec):
    if not total:
        return [0]*len(weights), [0]*len(weights)
    div = spec["division"]
    if div["kind"] == "exact_divide":
        values = [_rounded_division(weight*spec["output_scale"], total, spec["rounding"]) for weight in weights]
    else:
        df, rf = div["denominator_fraction_bits"], div["reciprocal_fraction_bits"]
        denominator = total >> (spec["exp_fraction_bits"] - df)
        msb = denominator.bit_length()-1
        frac = (denominator >> (msb-3)) & 7
        # Round midpoint reciprocal seeds exactly using integers; no DUT table.
        seed, rem = divmod((1 << rf)*16, 17+2*frac)
        seed += 2*rem >= 17+2*frac
        reciprocal = seed >> (msb-df)
        mask = (1 << div["reciprocal_width"])-1
        for _ in range(div["iterations"]):
            correction = (2 << rf) - ((denominator*reciprocal) >> df)
            if correction < 0:
                raise ValueError("Reciprocal iteration escaped the declared positive domain")
            reciprocal = ((reciprocal*correction) >> rf) & mask
        den = 1 << (spec["exp_fraction_bits"]+rf)
        values = [divmod(weight*reciprocal*spec["output_scale"], den) for weight in weights]
    return [min(spec["output_maximum"], value) for value,rem in values], [rem for value,rem in values]


def events(operation, inputs):
    spec = operation["arithmetic"]
    b = spec["bindings"]
    rows, cols = spec["shape"]["rows"], spec["shape"]["columns"]
    scores = inputs[b["softmax_scores"]["name"]]
    mask = inputs[b["softmax_mask"]["name"]] if spec["mask_mode"] == "binary_keep" else [1]*len(scores)
    result = []
    for row in range(rows):
        values = list(scores[row*cols:(row+1)*cols])
        keep = list(mask[row*cols:(row+1)*cols])
        maximum = max((v for v,k in zip(values,keep) if k), default=None)
        raw_indices = [((maximum-v)*spec["delta_scale_multiplier"]) >> spec["delta_scale_shift"] if k else None for v,k in zip(values,keep)]
        weights = []
        for index in raw_indices:
            if index is None:
                weight = 0
            elif index >= len(spec["exp_lut"]):
                weight = spec["exp_lut"][-1] if spec["clipping"] == "clamp" else 0
            else:
                weight = spec["exp_lut"][index]
            weights.append(weight)
        probabilities, remainders = _normalize(weights, sum(weights), spec)
        result.append({"row": row, "scores": values, "mask": keep, "maximum": maximum,
                       "indices": raw_indices, "weights": weights, "denominator": sum(weights),
                       "probabilities": probabilities, "remainders": remainders})
    return result


def evaluate(operation, inputs):
    spec = operation["arithmetic"]
    return {spec["bindings"]["softmax_probabilities"]["name"]: [v for e in events(operation,inputs) for v in e["probabilities"]]}


def mathematical_probabilities(operation, inputs):
    """High-precision natural-exp reference; never substitutes for fixed-point semantics."""
    spec = operation["arithmetic"]
    result = []
    with localcontext() as context:
        context.prec = 60
        for event in events(operation,inputs):
            if event["maximum"] is None:
                result.extend([Decimal(0)]*len(event["scores"]))
                continue
            unit = Decimal(spec["delta_scale_multiplier"])/(1 << (spec["delta_scale_shift"]+spec["score_fraction_bits"]))
            weights = [(-(event["maximum"]-s)*unit).exp() if k else Decimal(0) for s,k in zip(event["scores"],event["mask"])]
            total = sum(weights)
            result.extend(weight/total for weight in weights)
    return result


def classify(operation,inputs):
    spec=operation["arithmetic"]; patterns=[]; masks=[]; domain=[]; normalization=[]
    trace = events(operation,inputs)
    for event in trace:
        active=[v for v,k in zip(event["scores"],event["mask"]) if k]
        count=len(active); size=len(event["scores"])
        masks.append("fully_masked" if not count else "singleton" if count==1 else "unmasked" if count==size else "partial")
        if active and any(not k and v > max(active) for v,k in zip(event["scores"],event["mask"])):
            masks.append("masked_maximum")
        if any(not k and v == 0 for v,k in zip(event["scores"],event["mask"])):
            masks.append("masked_zero")
        if active:
            if len(set(active))==1: patterns.append("uniform")
            patterns.append("tied_maximum" if active.count(max(active))>1 else "unique_maximum")
            if max(active)<0: patterns.append("all_negative")
            if min(active)<0<max(active): patterns.append("mixed_sign")
        for index in event["indices"]:
            if index is None: continue
            domain.append("zero_delta" if index==0 else "interior_delta" if index<len(spec["exp_lut"])-1 else "last_lut_entry" if index==len(spec["exp_lut"])-1 else "clipped_delta")
        for value,rem in zip(event["probabilities"],event["remainders"]):
            normalization.append("zero_probability" if value==0 else "positive_probability")
            if event["denominator"]: normalization.append("rounded_division" if rem else "exact_division")
        if any(k and weight > 0 and value == 0 for k,weight,value in zip(event["mask"],event["weights"],event["probabilities"])):
            normalization.append("tiny_positive_weight_zero")
    if len({tuple(e["probabilities"]) for e in trace}) > 1:
        patterns.append("distinct_rows")
    return {"dimensions":["fixed"],"row_patterns":list(dict.fromkeys(patterns)),"mask_patterns":list(dict.fromkeys(masks)),
            "exp_domain":list(dict.fromkeys(domain)),"normalization":list(dict.fromkeys(normalization)),
            "numeric_stage_events":trace}


def _base(operation):
    spec=operation["arithmetic"]; size=spec["shape"]["rows"]*spec["shape"]["columns"]
    result={spec["bindings"]["softmax_scores"]["name"]:[0]*size}
    if spec["mask_mode"]=="binary_keep": result[spec["bindings"]["softmax_mask"]["name"]]=[1]*size
    return result


def candidates(operation):
    spec=operation["arithmetic"]; width=spec["bindings"]["softmax_scores"]["data_type"]["width_bits"]
    lo,hi=-(1<<(width-1)),(1<<(width-1))-1; cols=spec["shape"]["columns"]
    mul,shift=spec["delta_scale_multiplier"],spec["delta_scale_shift"]
    differences=[0,1,1<<spec["score_fraction_bits"],hi-lo]
    last_positive = max(i for i,v in enumerate(spec["exp_lut"]) if v > 0)
    for target in (len(spec["exp_lut"])-1,len(spec["exp_lut"]),last_positive):
        delta=(target*(1<<shift)+mul-1)//mul
        differences.extend([max(0,delta-1),delta,delta+1])
    patterns=[[0]*cols,[lo]*cols,[hi]*cols]
    for delta in differences:
        if delta>hi-lo: continue
        top=hi if delta>hi else 0
        patterns.extend([[top]+[top-delta]*(cols-1),[top-delta]*(cols-1)+[top]])
        if cols>=3: patterns.append([top,top]+[top-delta]*(cols-2))
    patterns.append([lo if i%2 else hi for i in range(cols)])
    masks=[[1]*cols]
    if spec["mask_mode"]=="binary_keep": masks.extend([[0]*cols,[1]+[0]*(cols-1),[0]+[1]*(cols-1)])
    if spec["mask_mode"] == "binary_keep" and cols > 1:
        poisoned = _base(operation)
        row = [hi,lo] if cols == 2 else [hi,0]+[lo]*(cols-2)
        poisoned[spec["bindings"]["softmax_scores"]["name"]] = row*spec["shape"]["rows"]
        poisoned[spec["bindings"]["softmax_mask"]["name"]] = ([0]+[1]*(cols-1))*spec["shape"]["rows"]
        yield poisoned
    for pattern,mask in product(patterns,masks):
        result=_base(operation); result[spec["bindings"]["softmax_scores"]["name"]]=pattern*spec["shape"]["rows"]
        if spec["mask_mode"]=="binary_keep": result[spec["bindings"]["softmax_mask"]["name"]]=mask*spec["shape"]["rows"]
        yield result
        # A second row with a different distribution exposes shared row state.
        # Do not add an internal row-state port or assume a tile scheduler.
        if spec["shape"]["rows"] > 1:
            varied = {name:list(values) for name,values in result.items()}
            varied[spec["bindings"]["softmax_scores"]["name"]][cols:2*cols] = [0]*cols
            if spec["mask_mode"] == "binary_keep":
                varied[spec["bindings"]["softmax_mask"]["name"]][cols:2*cols] = [0]*cols
            yield varied


def randomized_stimulus(operation,rng):
    spec=operation["arithmetic"]; result=_base(operation); dtype=spec["bindings"]["softmax_scores"]["data_type"]
    width=dtype["width_bits"]; lo,hi=-(1<<(width-1)),(1<<(width-1))-1
    result[spec["bindings"]["softmax_scores"]["name"]]=[rng.randint(lo,hi) for _ in result[spec["bindings"]["softmax_scores"]["name"]]]
    if spec["mask_mode"]=="binary_keep":
        name=spec["bindings"]["softmax_mask"]["name"]
        result[name]=[rng.randrange(2) for _ in result[name]]
    return result


def unreachable_reason(operation,concept,name):
    spec=operation["arithmetic"]; cols=spec["shape"]["columns"]
    if concept == "row_patterns" and name == "distinct_rows" and spec["shape"]["rows"] < 2:
        return "Only one external row is declared"
    if concept == "row_patterns" and name == "distinct_rows" and spec["mask_mode"] == "none" and (cols == 1 or len(set(spec["exp_lut"])) == 1):
        return "All unmasked rows have the same fixed probability vector"
    if concept == "mask_patterns" and name in ("masked_maximum", "masked_zero"):
        if spec["mask_mode"] == "none": return "No mask input is declared"
        if name == "masked_maximum" and cols < 2: return "Need both an excluded and an active element"
    if concept == "normalization" and name == "tiny_positive_weight_zero":
        minimum = min(v for v in spec["exp_lut"] if v > 0)
        maximum = cols*spec["exp_lut"][0]
        div = spec["division"]
        if div["kind"] == "exact_divide" and minimum*spec["output_scale"]//maximum > 0:
            return "Every positive LUT weight has a strictly positive quantized probability"
        if div["kind"] == "reciprocal_newton":
            shift = spec["exp_fraction_bits"]-div["denominator_fraction_bits"]
            low, high = 1 << div["denominator_fraction_bits"], maximum >> shift
            if high-low <= 100000 and min(_normalize([minimum],d<<shift,spec)[0][0] for d in range(low,high+1)) > 0:
                return "Every positive weight remains positive over the complete reciprocal denominator domain"
    if concept == "normalization" and cols == 1:
        probabilities, remainders = _normalize([spec["exp_lut"][0]], spec["exp_lut"][0], spec)
        impossible = (
            (name == "rounded_division" and remainders[0] == 0)
            or (name == "exact_division" and remainders[0] != 0)
            or (name == "zero_probability" and spec["mask_mode"] == "none" and probabilities[0] > 0)
            or (name == "positive_probability" and probabilities[0] == 0)
        )
        if impossible:
            return "One-column active rows have one fixed weight and normalization; masked rows have no division"
    if concept=="normalization" and name=="zero_probability" and spec["mask_mode"]=="none" and spec["clipping"]=="clamp" and spec["exp_lut"][-1]>0:
        minimum=spec["exp_lut"][-1]; maximum=cols*spec["exp_lut"][0]
        div=spec["division"]
        if div["kind"]=="exact_divide":
            if minimum*spec["output_scale"]//maximum>0:
                return "Every unmasked clamped LUT weight has a strictly positive quantized probability"
        else:
            shift=spec["exp_fraction_bits"]-div["denominator_fraction_bits"]
            low=1<<div["denominator_fraction_bits"]; high=maximum>>shift
            if high-low<=100000 and min(_normalize([minimum],denominator<<shift,spec)[0][0] for denominator in range(low,high+1))>0:
                return "Exhaustive denominator-domain bound proves every clamped unmasked probability is positive"
    if concept=="mask_patterns":
        if spec["mask_mode"]=="none" and name in ("partial","fully_masked"): return "No mask input is declared"
        if name=="singleton" and spec["mask_mode"]=="none" and cols!=1: return "An unmasked fixed row has more than one element"
        if name=="partial" and cols<3: return "Partial means more than one but fewer than all active elements"
        if name=="unmasked" and cols==1: return "A one-element row is classified as singleton"
    if concept=="row_patterns" and cols==1 and name in ("tied_maximum","mixed_sign"): return "A one-element row cannot have a tie or mixed signs"
    if concept=="exp_domain" and cols==1 and name!="zero_delta": return "One-element stable softmax has only zero delta"
    if concept == "exp_domain" and name == "interior_delta":
        width = spec["bindings"]["softmax_scores"]["data_type"]["width_bits"]
        multiplier, shift = spec["delta_scale_multiplier"], spec["delta_scale_shift"]
        first_delta = ((1 << shift) + multiplier - 1) // multiplier
        first_index = (first_delta * multiplier) >> shift
        if first_delta > (1 << width) - 1 or first_index >= len(spec["exp_lut"]) - 1:
            return "The scaled score-index lattice contains no interior LUT index"
    if concept=="exp_domain" and name in ("last_lut_entry","clipped_delta"):
        width=spec["bindings"]["softmax_scores"]["data_type"]["width_bits"]
        max_index=(((1<<width)-1)*spec["delta_scale_multiplier"])>>spec["delta_scale_shift"]
        needed=len(spec["exp_lut"])-(name=="last_lut_entry")
        if max_index<needed: return "Score domain cannot reach this LUT boundary"
        if name=="last_lut_entry":
            delta=(needed*(1<<spec["delta_scale_shift"])+spec["delta_scale_multiplier"]-1)//spec["delta_scale_multiplier"]
            if (delta*spec["delta_scale_multiplier"]>>spec["delta_scale_shift"])!=needed: return "Scaled index lattice skips the last LUT entry"
    return None
