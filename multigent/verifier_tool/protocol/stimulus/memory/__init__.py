"""The "memory" half of the memory/adapter/driver split: raw, protocol- and
operation-agnostic byte-addressable storage, nothing else.

Deliberately tiny -- `cocotbext.axi.memory.Memory` (from the cocotbext-axi
dependency) already *is* exactly this: a plain, sparse, byte-addressable
backing store that knows nothing about AXI, canonical values, word packing,
or which operation a byte belongs to. Re-exported here, rather than imported
directly from `cocotbext.axi` at each call site, only so this package is the
one obvious place to look for "where does storage live" -- see
`../adapter/README.md` (or its module docstring) for the layer built on top
of this that actually knows about operations, and `../drivers/` for the
wire-protocol layer built on top of that.
"""

from cocotbext.axi.memory import Memory

__all__ = ["Memory"]
