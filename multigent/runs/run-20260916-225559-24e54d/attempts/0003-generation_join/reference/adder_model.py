def add(a, b):
    if not (0 <= a <= 255 and 0 <= b <= 255):
        raise ValueError('Operands must be uint8')
    return a + b


def sanity():
    examples = [(0, 0, 0), (255, 0, 255), (0, 255, 255),
                (255, 1, 256), (127, 128, 255), (128, 128, 256),
                (255, 255, 510), (85, 170, 255)]
    for a, b, expected in examples:
        actual = add(a, b)
        if actual != expected:
            raise AssertionError(f'Golden sanity: a={a} b={b} expected={expected} actual={actual}')
