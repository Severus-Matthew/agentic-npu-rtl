def to_s8(x: int) -> int:
    x &= 0xFF
    return x - 0x100 if x & 0x80 else x


def to_s16(x: int) -> int:
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def to_s32(x: int) -> int:
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x


def i32_add_wrap(a: int, b: int) -> int:
    return to_s32((a + b) & 0xFFFFFFFF)


def pack_cmd(M: int, N: int, K: int, bias_enable: int) -> int:
    cmd = 0
    cmd |= (M & 0xFFFF)
    cmd |= ((N & 0xFFFF) << 16)
    cmd |= ((K & 0xFFFF) << 32)
    cmd |= ((bias_enable & 0x1) << 48)
    return cmd


def gemm_bias_relu_ref(M, N, K, a_row_major, b_row_major, bias_enable, bias_vec):
    out = []
    for m in range(M):
        for n in range(N):
            acc = 0
            for k in range(K):
                a = to_s8(a_row_major[m * K + k])
                b = to_s8(b_row_major[k * N + n])
                prod16 = to_s16(a * b)
                acc = i32_add_wrap(acc, prod16)
            t = acc
            if bias_enable:
                t = i32_add_wrap(t, to_s32(bias_vec[n]))
            y = t if t > 0 else 0
            out.append(to_s32(y))
    return out
