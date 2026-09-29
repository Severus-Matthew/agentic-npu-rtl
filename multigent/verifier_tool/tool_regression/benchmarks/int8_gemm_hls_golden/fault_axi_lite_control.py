"""Non-destructive AXI4-Lite probes for a register-mapped control subordinate.

The caller supplies a contract-declared pointer register and its current value.
Probe writes either preserve that value or use WSTRB=0. Nothing here knows an
accelerator name, register spelling, or mathematical operation.
"""

from __future__ import annotations

from typing import Any, Mapping


async def drive_axi_lite_control_probes(
    master: Any,
    *,
    pointer_address: int,
    pointer_value: int,
    data_width_bytes: int,
    plan: Mapping[str, bool],
    qualification_fault: Mapping[str, Any] | None = None,
) -> None:
    """Execute the required safe control-bus probes using an existing master."""

    if data_width_bytes < 2 or pointer_address % data_width_bytes:
        raise ValueError("pointer probe needs an aligned multi-byte register")
    original = int(pointer_value).to_bytes(data_width_bytes, "little")
    if (
        qualification_fault is not None
        and qualification_fault.get("fault") == "attempt_unpaired_write_channel"
    ):
        aw = master.write_if.aw_channel._transaction_obj()
        aw.awaddr = pointer_address
        aw.awprot = 0
        await master.write_if.aw_channel.send(aw)
        raise AssertionError(
            "feature=protocol.control.write_address_and_data_are_independent; "
            "qualification source accepted AW but deliberately withheld its paired W transfer"
        )
    if plan.get("unaligned_write") or plan.get("sparse_strobe"):
        # A one-byte write at byte lane 1 leaves the pointer unchanged while
        # exercising both unaligned AWADDR and sparse WSTRB.
        await master.write(pointer_address + 1, original[1:2])
    if plan.get("unaligned_read"):
        await master.read(pointer_address + 1, 1)
    if plan.get("zero_strobe"):
        aw = master.write_if.aw_channel._transaction_obj()
        aw.awaddr = pointer_address
        aw.awprot = 0
        w = master.write_if.w_channel._transaction_obj()
        w.wdata = 0
        w.wstrb = 0
        await master.write_if.aw_channel.send(aw)
        await master.write_if.w_channel.send(w)
        await master.write_if.b_channel.recv()
    if plan.get("concurrent_read_write") or plan.get("multiple_outstanding"):
        # Queue both addresses before the next clock edge. Holding response
        # READY low ensures both requests can coexist without altering data.
        b_sink = master.write_if.b_channel
        r_sink = master.read_if.r_channel
        b_sink.pause = True
        r_sink.pause = True
        aw = master.write_if.aw_channel._transaction_obj()
        aw.awaddr = pointer_address
        aw.awprot = 0
        w = master.write_if.w_channel._transaction_obj()
        w.wdata = int(pointer_value)
        w.wstrb = 0
        ar = master.read_if.ar_channel._transaction_obj()
        ar.araddr = pointer_address
        ar.arprot = 0
        await master.write_if.aw_channel.send(aw)
        await master.write_if.w_channel.send(w)
        await master.read_if.ar_channel.send(ar)

        from cocotb.triggers import RisingEdge

        for _ in range(8):
            await RisingEdge(master.write_if.aw_channel.clock)
        b_sink.pause = False
        r_sink.pause = False
        await b_sink.recv()
        await r_sink.recv()

    lengths = plan.get("response_stall_lengths", {})
    for kind, sink, valid_signal in (
        ("write_response", master.write_if.b_channel, master.write_if.b_channel.bus.bvalid),
        ("read_data", master.read_if.r_channel, master.read_if.r_channel.bus.rvalid),
    ):
        for cycles in lengths.get(kind, ()):
            sink.pause = True
            sink.ready.value = 0
            if kind == "write_response":
                aw = master.write_if.aw_channel._transaction_obj()
                aw.awaddr = pointer_address
                aw.awprot = 0
                w = master.write_if.w_channel._transaction_obj()
                w.wdata = int(pointer_value)
                w.wstrb = 0
                await master.write_if.aw_channel.send(aw)
                await master.write_if.w_channel.send(w)
            else:
                ar = master.read_if.ar_channel._transaction_obj()
                ar.araddr = pointer_address
                ar.arprot = 0
                await master.read_if.ar_channel.send(ar)

            from cocotb.triggers import FallingEdge, RisingEdge, Timer

            clock = sink.clock
            while True:
                await RisingEdge(clock)
                await Timer(1, unit="ps")
                if int(valid_signal.value):
                    break
            for _ in range(int(cycles)):
                await RisingEdge(clock)
            await FallingEdge(clock)
            sink.ready.value = 1
            sink.pause = False
            await sink.recv()
