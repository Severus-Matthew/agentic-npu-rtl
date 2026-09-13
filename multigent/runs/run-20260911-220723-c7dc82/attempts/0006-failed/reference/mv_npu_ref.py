MASK32 = (1 << 32) - 1


def s8(v: int) -> int:
    v &= 0xFF
    return v - 0x100 if v & 0x80 else v


def s32(v: int) -> int:
    v &= MASK32
    return v - (1 << 32) if v & (1 << 31) else v


def wrap32(v: int) -> int:
    return s32(v)


def relu32(v: int) -> int:
    return 0 if v < 0 else s32(v)


def dot_row_int8_int32(a_row, x_vec):
    acc = 0
    for a, x in zip(a_row, x_vec):
        acc = wrap32(acc + (s8(a) * s8(x)))
    return acc


def mv_job(cfg, x_vec, a_mat, bias_vec=None):
    m = cfg["M"]
    n = cfg["N"]
    bias_en = cfg["bias_en"]
    relu_en = cfg["relu_en"]

    assert len(x_vec) == n
    assert len(a_mat) == m
    for r in range(m):
        assert len(a_mat[r]) == n
    if bias_en:
        assert bias_vec is not None and len(bias_vec) == m

    y = []
    for r in range(m):
        acc = dot_row_int8_int32(a_mat[r], x_vec)
        if bias_en:
            acc = wrap32(acc + s32(bias_vec[r]))
        out = relu32(acc) if relu_en else s32(acc)
        y.append(s32(out))
    return y


def sanity_checks():
    # zero
    cfg = {"M": 1, "N": 1, "bias_en": 0, "relu_en": 0}
    assert mv_job(cfg, [0], [[0]]) == [0]
    # sign
    assert mv_job(cfg, [-1], [[1]]) == [-1]
    # wrap
    cfg2 = {"M": 1, "N": 1, "bias_en": 1, "relu_en": 0}
    assert mv_job(cfg2, [127], [[127]], [0x7FFFFFFF]) == [s32(127 * 127 + 0x7FFFFFFF)]
    # relu
    cfg3 = {"M": 1, "N": 1, "bias_en": 0, "relu_en": 1}
    assert mv_job(cfg3, [-1], [[1]]) == [0]
