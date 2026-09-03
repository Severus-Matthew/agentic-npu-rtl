def s8(x):
    x &= 0xFF
    return x - 256 if x & 0x80 else x


def s16(x):
    x &= 0xFFFF
    return x - 65536 if x & 0x8000 else x


def s32(x):
    x &= 0xFFFFFFFF
    return x - 4294967296 if x & 0x80000000 else x


def add32(a, b):
    return s32((a & 0xFFFFFFFF) + (b & 0xFFFFFFFF))


def pack_cmd(M, N, K, bias_enable):
    v = 0
    v |= (M & 0xFFFF)
    v |= ((N & 0xFFFF) << 16)
    v |= ((K & 0xFFFF) << 32)
    v |= ((1 if bias_enable else 0) << 48)
    return v


def gemm_bias_relu_ref(M, N, K, A_row_major, B_row_major, bias_enable, bias_vec):
    out = []
    for m in range(M):
        for n in range(N):
            acc = 0
            for k in range(K):
                a = s8(A_row_major[m * K + k])
                b = s8(B_row_major[k * N + n])
                prod16 = s16(a * b)
                acc = add32(acc, prod16)
            if bias_enable:
                acc = add32(acc, s32(bias_vec[n]))
            out.append(acc if acc > 0 else 0)
    return out
