import math

INT8_MIN = -128
INT8_MAX = 127
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


def wrap_u32(x: int) -> int:
    return x & 0xFFFFFFFF


def u32_to_s32(x: int) -> int:
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & (1 << 31) else x


def s8(x: int) -> int:
    x &= 0xFF
    return x - 256 if x & 0x80 else x


def pack_cmd(M: int, N: int, bias_enable: int, relu_enable: int) -> int:
    return (M & 0xFFFF) | ((N & 0xFFFF) << 16) | ((bias_enable & 1) << 32) | ((relu_enable & 1) << 33)


def unpack_mat_beat_lanes(beat: int, lanes: int = 16):
    out = []
    for i in range(lanes):
        out.append(s8((beat >> (8 * i)) & 0xFF))
    return out


def pack_mat_beat_lanes(vals):
    v = 0
    for i, x in enumerate(vals):
        v |= ((x & 0xFF) << (8 * i))
    return v


def golden_outputs(M, N, vec, mat_rows, bias_enable, relu_enable, bias_vals=None):
    assert 1 <= M <= 256
    assert 1 <= N <= 256
    assert len(vec) == N
    assert len(mat_rows) == M
    if bias_enable:
        assert bias_vals is not None and len(bias_vals) == M
    else:
        assert bias_vals is None or len(bias_vals) == 0

    y = []
    for r in range(M):
        acc_u = 0
        for k in range(N):
            p16 = s8(mat_rows[r][k]) * s8(vec[k])
            acc_u = wrap_u32(acc_u + p16)
        if bias_enable:
            acc_u = wrap_u32(acc_u + int(bias_vals[r]))
        y_s = u32_to_s32(acc_u)
        if relu_enable and y_s < 0:
            y_s = 0
        y.append(y_s)
    return y
