def u32(value):
    return value & 0xFFFFFFFF


def s32(value):
    value &= 0xFFFFFFFF
    return value - (1 << 32) if value & 0x80000000 else value


def s8(value):
    value &= 0xFF
    return value - 256 if value & 0x80 else value


def wrap32(value):
    return s32(value)


def gemm_relu(m, n, k, activations, weights, bias):
    assert len(activations) == m * k
    assert len(weights) == k * n
    assert len(bias) == n
    result = []
    for row in range(m):
        for col in range(n):
            acc = 0
            for red in range(k):
                a = s8(activations[row * k + red])
                w = s8(weights[red * n + col])
                acc = wrap32(acc + a * w)
            biased = wrap32(acc + s32(bias[col]))
            result.append(0 if biased < 0 else biased)
    return result


def pack_int8(values):
    beats = []
    for base in range(0, len(values), 8):
        word = 0
        for lane in range(8):
            index = base + lane
            value = values[index] if index < len(values) else 0
            word |= (value & 0xFF) << (8 * lane)
        beats.append(word)
    return beats


def pack_int32(values):
    beats = []
    for base in range(0, len(values), 2):
        lower = values[base] if base < len(values) else 0
        upper = values[base + 1] if base + 1 < len(values) else 0
        beats.append(u32(lower) | (u32(upper) << 32))
    return beats


def pack_command(m, n, k, m_width=7, n_width=7, k_width=7):
    assert 0 <= m < (1 << m_width)
    assert 0 <= n < (1 << n_width)
    assert 0 <= k < (1 << k_width)
    return m | (n << m_width) | (k << (m_width + n_width))


def reference_sanity_checks():
    assert s8(0x80) == -128
    assert s8(0x7F) == 127
    assert wrap32(0x7FFFFFFF + 1) == -0x80000000
    assert wrap32(-0x80000000 - 1) == 0x7FFFFFFF
    assert gemm_relu(1, 1, 1, [0], [127], [5]) == [5]
    assert gemm_relu(1, 1, 1, [1], [1], [0x7FFFFFFF]) == [0]
    assert gemm_relu(1, 1, 2, [-128, 127], [127, -128], [0]) == [0]
    assert pack_int8([1]) == [1]
    assert pack_int32([3]) == [3]
