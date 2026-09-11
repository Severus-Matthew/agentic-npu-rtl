INT8_MIN = -128
INT8_MAX = 127
INT32_MIN = -2147483648
INT32_MAX = 2147483647
MASK8 = 0xFF
MASK32 = 0xFFFFFFFF

M = 8
N = 8
K = 32
A_ELEMS = M * K
B_ELEMS = K * N
BIAS_ELEMS = N
Y_ELEMS = M * N


def to_s8(x: int) -> int:
    x &= MASK8
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
                prod = a[m * K + k] * b[k * N + n]
                acc = add_wrap_s32(acc, prod)
            pre = add_wrap_s32(acc, bz[n])
            y.append(relu_s32(pre))
    return y


def sanity_check_reference():
    a0 = [0] * A_ELEMS
    b0 = [0] * B_ELEMS
    z = [0] * BIAS_ELEMS
    assert gemm8x8x32_bias_relu(a0, b0, z) == [0] * Y_ELEMS

    a1 = [1] * A_ELEMS
    b1 = [1] * B_ELEMS
    assert gemm8x8x32_bias_relu(a1, b1, z) == [32] * Y_ELEMS

    an = [-1] * A_ELEMS
    bp = [1] * B_ELEMS
    assert gemm8x8x32_bias_relu(an, bp, z) == [0] * Y_ELEMS

    wrapped = add_wrap_s32(0x7FFFFFFF, 1)
    assert wrapped == INT32_MIN
    assert relu_s32(wrapped) == 0
