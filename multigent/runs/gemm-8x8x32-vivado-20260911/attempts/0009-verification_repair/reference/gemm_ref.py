INT8_MIN = -128
INT8_MAX = 127
INT32_MIN = -2147483648
INT32_MAX = 2147483647
MASK32 = 0xFFFFFFFF

M = 8
N = 8
K = 32
A_ELEMS = M * K
B_ELEMS = K * N
BIAS_ELEMS = N
Y_ELEMS = M * N


def to_s8(x: int) -> int:
    x &= 0xFF
    return x - 0x100 if x & 0x80 else x


def to_s32(x: int) -> int:
    x &= MASK32
    return x - 0x100000000 if x & 0x80000000 else x


def add_wrap_s32(a: int, b: int) -> int:
    return to_s32((a & MASK32) + (b & MASK32))


def relu_s32(x: int) -> int:
    return 0 if x < 0 else x


def gemm8x8x32_bias_relu(a_flat, b_flat, bias):
    assert len(a_flat) == A_ELEMS
    assert len(b_flat) == B_ELEMS
    assert len(bias) == BIAS_ELEMS

    a = [to_s8(v) for v in a_flat]
    b = [to_s8(v) for v in b_flat]
    bz = [to_s32(v) for v in bias]

    y = []
    for m in range(M):
        for n in range(N):
            acc = 0
            for k in range(K):
                av = a[m * K + k]
                bv = b[k * N + n]
                prod = av * bv
                acc = add_wrap_s32(acc, prod)
            pre = add_wrap_s32(acc, bz[n])
            y.append(relu_s32(pre))
    return y


def sanity_check_reference():
    a0 = [0] * A_ELEMS
    b0 = [0] * B_ELEMS
    zbias = [0] * BIAS_ELEMS
    y0 = gemm8x8x32_bias_relu(a0, b0, zbias)
    assert y0 == [0] * Y_ELEMS

    a_ones = [1] * A_ELEMS
    b_ones = [1] * B_ELEMS
    y1 = gemm8x8x32_bias_relu(a_ones, b_ones, zbias)
    assert all(v == 32 for v in y1)

    a_neg = [-1] * A_ELEMS
    b_pos = [1] * B_ELEMS
    y2 = gemm8x8x32_bias_relu(a_neg, b_pos, zbias)
    assert y2 == [0] * Y_ELEMS

    # explicit wrap + ReLU ordering check
    # 0x7fffffff + 1 -> -2147483648 -> ReLU -> 0
    pre = add_wrap_s32(0x7FFFFFFF, 1)
    assert pre == INT32_MIN
    assert relu_s32(pre) == 0
