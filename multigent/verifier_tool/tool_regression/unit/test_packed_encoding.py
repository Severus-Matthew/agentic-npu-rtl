"""Proves the generic `packed_encoding` engine reproduces, byte for byte, the
exact DRAM image `gemm_hls/int8_gemm.cpp` (packed_gemm_contract, M=32/K=64/N=128)
expects for its A and B inputs -- once purely from a metadata declaration, with
zero GEMM-specific code in the engine itself.

Reference encoders below are hand-transcribed directly from the C++ comments:
  A: "each 512-bit word carries the 32 rows for one K position in lanes 0..31;
      lanes 32..63 are padding" (int8_gemm.hpp)
  B: "Each 32-bit storage lane carries the low 27 bits of
      (B[k][2*p+1] << 18) + B[k][2*p])" (int8_gemm.cpp, load_b)
"""
from __future__ import annotations

import random

import pytest

from multigent.verifier_tool.pool.operation_metadata.io_metadata import (
    declared_serialization,
)
from multigent.verifier_tool.pool.operation_metadata.packed_encoding import (
    PackedEncodingError,
    pack_words,
    packed_encoding_word_bits,
    packed_encoding_word_count,
    validate_packed_encoding_declaration,
)

M, K, N = 32, 64, 128
EXTENTS = {"M": M, "K": K, "N": N}


def _a_serialization() -> dict:
    return {
        "kind": "packed_encoding",
        "description": "A: word=K, whole word is one container, field[m]=A[m][k] raw unsigned byte.",
        "traversal": {
            "word_axes": ["K"],
            "containers_per_word": 1,
            "container_axis": None,
            "field_axis": "M",
        },
        "packed_encoding": {
            "physical_container_width": 512,
            "used_width": 256,
            "used_bit_range": [0, 255],
            "padding_value": "zero",
            "container_bit_layout": "contiguous_ascending",
            "group_size": 32,
            "fields": [
                {"logical_offset": m, "source_width": 8, "interpretation": "unsigned", "shift": m * 8}
                for m in range(32)
            ],
        },
    }


def _b_serialization() -> dict:
    return {
        "kind": "packed_encoding",
        "description": "B: N=N_tile*32+N_lane*2+N_offset; word=K*4+N_tile; lane=N_lane; signed shift-add pair packing.",
        "derived_axes": [
            {
                "real_axis": "N",
                "order": ["N_tile", "N_lane", "N_offset"],
                "sub_axes": [
                    {"name": "N_tile", "extent": 4},
                    {"name": "N_lane", "extent": 16},
                    {"name": "N_offset", "extent": 2},
                ],
            }
        ],
        "traversal": {
            "word_axes": ["K", "N_tile"],
            "containers_per_word": 16,
            "container_axis": "N_lane",
            "field_axis": "N_offset",
        },
        "packed_encoding": {
            "physical_container_width": 32,
            "used_width": 27,
            "used_bit_range": [0, 26],
            "padding_value": "zero",
            "container_bit_layout": "contiguous_ascending",
            "group_size": 2,
            "fields": [
                {"logical_offset": 0, "source_width": 8, "interpretation": "signed", "shift": 0},
                {"logical_offset": 1, "source_width": 8, "interpretation": "signed", "shift": 18},
            ],
        },
    }


def _reference_pack_a(a_flat: list[int]) -> list[int]:
    """a_flat indexed [m][k] row-major (dimensions=[M,K])."""

    words = []
    for k in range(K):
        word = 0
        for m in range(M):
            byte = a_flat[m * K + k] & 0xFF
            word |= byte << (m * 8)
        words.append(word)
    return words


def _as_signed8(x: int) -> int:
    x &= 0xFF
    return x - 256 if x & 0x80 else x


def _reference_pack_b(b_flat: list[int]) -> list[int]:
    """b_flat indexed [k][n] row-major (dimensions=[K,N])."""

    words = [0] * (K * 4)
    for k in range(K):
        for tile in range(4):
            word = 0
            for lane in range(16):
                n0 = tile * 32 + lane * 2 + 0
                n1 = tile * 32 + lane * 2 + 1
                b0 = _as_signed8(b_flat[k * N + n0])
                b1 = _as_signed8(b_flat[k * N + n1])
                packed = (b1 << 18) + b0
                packed &= (1 << 27) - 1
                word |= packed << (lane * 32)
            words[k * 4 + tile] = word
    return words


def test_a_matches_reference_encoding_for_random_data():
    serialization = _a_serialization()
    validate_packed_encoding_declaration(
        serialization, ["M", "K"], dimension_extents=EXTENTS, element_width_bits=8
    )
    rng = random.Random(1)
    a_flat = [rng.randint(-128, 127) for _ in range(M * K)]
    expected = _reference_pack_a(a_flat)
    actual = pack_words(serialization, ["M", "K"], EXTENTS, a_flat)
    assert actual == expected
    assert packed_encoding_word_count(serialization, EXTENTS) == K
    assert packed_encoding_word_bits(serialization) == 512


def test_b_matches_reference_encoding_for_random_data():
    serialization = _b_serialization()
    validate_packed_encoding_declaration(
        serialization, ["K", "N"], dimension_extents=EXTENTS, element_width_bits=8
    )
    rng = random.Random(2)
    b_flat = [rng.randint(-128, 127) for _ in range(K * N)]
    expected = _reference_pack_b(b_flat)
    actual = pack_words(serialization, ["K", "N"], EXTENTS, b_flat)
    assert actual == expected
    assert packed_encoding_word_count(serialization, EXTENTS) == K * 4
    assert packed_encoding_word_bits(serialization) == 512


def test_b_extreme_values_exercise_sign_extension_carry():
    """The whole point of `signed` packing is the carry from B[2p]'s sign
    extension into B[2p+1]'s field when B[2p] is negative -- prove it with the
    most negative/positive extremes, not just random mid-range values."""

    serialization = _b_serialization()
    b_flat = [0] * (K * N)
    b_flat[0 * N + 0] = -128  # k=0, n=0 (tile0,lane0,offset0)
    b_flat[0 * N + 1] = 127   # k=0, n=1 (tile0,lane0,offset1)
    expected = _reference_pack_b(b_flat)
    actual = pack_words(serialization, ["K", "N"], EXTENTS, b_flat)
    assert actual == expected
    # Sanity: this pair's packed value is not simply (-128 & 0xFF) | (127<<18);
    # a naive bitwise-OR implementation would disagree here.
    lane0_word0 = expected[0] & ((1 << 32) - 1)
    packed = lane0_word0 & ((1 << 27) - 1)
    assert packed == (((127 << 18) + (-128)) & ((1 << 27) - 1))


@pytest.mark.parametrize("field", ["traversal", "packed_encoding"])
def test_missing_required_block_is_rejected(field):
    serialization = _a_serialization()
    serialization.pop(field)
    with pytest.raises(PackedEncodingError):
        validate_packed_encoding_declaration(
            serialization, ["M", "K"], dimension_extents=EXTENTS, element_width_bits=8
        )


def test_unsigned_field_overlap_is_rejected():
    serialization = _a_serialization()
    serialization["packed_encoding"]["fields"][1]["shift"] = 0  # now collides with field 0
    with pytest.raises(PackedEncodingError, match="overlap"):
        validate_packed_encoding_declaration(
            serialization, ["M", "K"], dimension_extents=EXTENTS, element_width_bits=8
        )


def test_signed_field_overlap_is_allowed():
    """The opposite of the unsigned case -- B's fields are *supposed* to overlap
    once sign-extended; this must never be rejected."""

    serialization = _b_serialization()
    validate_packed_encoding_declaration(
        serialization, ["K", "N"], dimension_extents=EXTENTS, element_width_bits=8
    )  # shift=0/18, source_width=8 each -> nominal ranges [0,8) and [18,26) don't even
    # nominally overlap, but sign extension does; this test exists to document
    # that overlap detection is intentionally skipped for signed fields at all.


def test_derived_axes_extent_mismatch_is_rejected():
    serialization = _b_serialization()
    serialization["derived_axes"][0]["sub_axes"][0]["extent"] = 5  # 5*16*2=160 != 128
    with pytest.raises(PackedEncodingError, match="multiply"):
        validate_packed_encoding_declaration(
            serialization, ["K", "N"], dimension_extents=EXTENTS, element_width_bits=8
        )


def test_uncovered_dimension_is_rejected():
    serialization = _a_serialization()  # only ever places M and K
    with pytest.raises(PackedEncodingError, match="not accounted for"):
        validate_packed_encoding_declaration(
            serialization, ["M", "K", "Extra"], dimension_extents={**EXTENTS, "Extra": 2},
            element_width_bits=8,
        )


def test_repeated_traversal_axis_is_rejected():
    serialization = _a_serialization()
    serialization["traversal"]["field_axis"] = "K"  # K now repeats (also in word_axes)
    with pytest.raises(PackedEncodingError, match="must not repeat"):
        validate_packed_encoding_declaration(
            serialization, ["M", "K"], dimension_extents=EXTENTS, element_width_bits=8
        )


def test_source_width_must_match_element_width():
    serialization = _a_serialization()
    serialization["packed_encoding"]["fields"][0]["source_width"] = 4
    with pytest.raises(PackedEncodingError, match="source_width"):
        validate_packed_encoding_declaration(
            serialization, ["M", "K"], dimension_extents=EXTENTS, element_width_bits=8
        )


def test_declared_serialization_requires_context_for_packed_encoding():
    obj = {"name": "A_matrix", "dimensions": ["M", "K"], "serialization": _a_serialization()}
    with pytest.raises(ValueError, match="dimension_extents"):
        declared_serialization(obj)
    result = declared_serialization(obj, dimension_extents=EXTENTS, element_width_bits=8)
    assert result["kind"] == "packed_encoding"
