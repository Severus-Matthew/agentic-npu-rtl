MASK32 = (1 << 32) - 1

M = 8
N = 8
K = 32


def wrap_u32(x: int) -> int:
    return x & MASK32


def to_s32(x: int) -> int:
    x = wrap_u32(x)
    return x - (1 << 32) if x & (1 << 31) else x


def to_s8(x: int) -> int:
    x &= 0xFF
    return x - 256 if x & 0x80 else x


def relu_s32(x: int) -> int:
    sx = to_s32(x)
    return 0 if sx < 0 else sx


def gemm_bias_relu_ref(A, B, bias):
    assert len(A) == M and all(len(r) == K for r in A)
    assert len(B) == K and all(len(r) == N for r in B)
    assert len(bias) == N

    Y = [[0 for _ in range(N)] for _ in range(M)]
    for m in range(M):
        for n in range(N):
            acc_u32 = 0
            for k in range(K):
                a = to_s8(A[m][k])
                b = to_s8(B[k][n])
                prod = a * b
                acc_u32 = wrap_u32(acc_u32 + prod)
            pre_relu_u32 = wrap_u32(acc_u32 + to_s32(bias[n]))
            Y[m][n] = relu_s32(pre_relu_u32)
    return Y


def flatten_row_major(mat):
    return [mat[m][n] for m in range(M) for n in range(N)]


def sanity_checks():
    A0 = [[0]*K for _ in range(M)]
    B0 = [[0]*N for _ in range(K)]
    bias0 = [0]*N
    y0 = gemm_bias_relu_ref(A0, B0, bias0)
    assert all(v == 0 for v in flatten_row_major(y0))

    A1 = [[0]*K for _ in range(M)]
    B1 = [[0]*N for _ in range(K)]
    A1[0][0] = 1
    B1[0][0] = 1
    y1 = gemm_bias_relu_ref(A1, B1, bias0)
    assert y1[0][0] == 1

    A2 = [[127]*K for _ in range(M)]
    B2 = [[127]*N for _ in range(K)]
    y2 = gemm_bias_relu_ref(A2, B2, bias0)
    assert y2[0][0] == 127*127*K

    A3 = [[0]*K for _ in range(M)]
    B3 = [[0]*N for _ in range(K)]
    bias3 = [-(1 << 31)] + [0]*(N-1)
    y3 = gemm_bias_relu_ref(A3, B3, bias3)
    assert y3[0][0] == 0
