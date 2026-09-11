from typing import List, Tuple

INT8_MIN = -128
INT8_MAX = 127
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


def to_s8(x: int) -> int:
    x &= 0xFF
    return x - 0x100 if x & 0x80 else x


def to_s16(x: int) -> int:
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def to_s32(x: int) -> int:
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x


def add_s32_wrap(a: int, b: int) -> int:
    return to_s32((a & 0xFFFFFFFF) + (b & 0xFFFFFFFF))


def pack_cmd(M: int, N: int, K: int, bias_enable: int) -> int:
    cmd = 0
    cmd |= (M & 0xFFFF)
    cmd |= (N & 0xFFFF) << 16
    cmd |= (K & 0xFFFF) << 32
    cmd |= (bias_enable & 0x1) << 48
    return cmd


def gemm_bias_relu_ref(M: int, N: int, K: int, A: List[int], B: List[int], bias: List[int], bias_enable: int) -> List[int]:
    if len(A) != M * K:
        raise ValueError("A length mismatch")
    if len(B) != K * N:
        raise ValueError("B length mismatch")
    if bias_enable not in (0, 1):
        raise ValueError("bias_enable must be 0/1")
    if bias_enable == 1 and len(bias) != N:
        raise ValueError("bias length mismatch")

    out = []
    for m in range(M):
        for n in range(N):
            acc = 0
            for k in range(K):
                a = to_s8(A[m * K + k])
                b = to_s8(B[k * N + n])
                prod16 = to_s16(a * b)
                prod32 = to_s32(prod16)
                acc = add_s32_wrap(acc, prod32)
            t = acc
            if bias_enable:
                t = add_s32_wrap(t, to_s32(bias[n]))
            y = t if t > 0 else 0
            out.append(to_s32(y))
    return out


def flatten_a_row_major(A2d: List[List[int]]) -> List[int]:
    return [v for row in A2d for v in row]


def flatten_b_row_major(B2d: List[List[int]]) -> List[int]:
    return [v for row in B2d for v in row]
