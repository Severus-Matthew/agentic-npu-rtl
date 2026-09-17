def add_unsigned(a, b):
    if not (0 <= a <= 255 and 0 <= b <= 255):
        raise ValueError("operands must be uint8")
    return a + b


def sanity_check():
    known = ((0, 0, 0), (255, 0, 255), (255, 1, 256), (255, 255, 510))
    for a, b, expected in known:
        actual = add_unsigned(a, b)
        if actual != expected:
            raise AssertionError(f"oracle sanity failed: {a}+{b}, expected={expected}, actual={actual}")
