def uadd8_uadd8_to_u9(a: int, b: int) -> int:
    if not (0 <= a <= 0xFF):
        raise ValueError(f"a out of range: {a}")
    if not (0 <= b <= 0xFF):
        raise ValueError(f"b out of range: {b}")
    s = a + b
    if not (0 <= s <= 0x1FF):
        raise AssertionError(f"sum out of u9 range: {s}")
    return s
