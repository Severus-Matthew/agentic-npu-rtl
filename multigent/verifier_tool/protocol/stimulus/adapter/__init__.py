"""The "adapter" half of the memory/adapter/driver split -- see
`operation_memory_adapter.py`'s module docstring for the full rationale.
"""

from .operation_memory_adapter import (
    OperationMemoryAdapter,
    OperationMemoryAdapterError,
    build_address_windows,
    expected_elements,
    find_window_mapping,
    pack_words,
    unpack_words,
    word_count,
)

__all__ = [
    "OperationMemoryAdapter",
    "OperationMemoryAdapterError",
    "build_address_windows",
    "expected_elements",
    "find_window_mapping",
    "pack_words",
    "unpack_words",
    "word_count",
]
