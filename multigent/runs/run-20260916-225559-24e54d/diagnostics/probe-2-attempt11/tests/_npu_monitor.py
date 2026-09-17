import functools
from collections import deque
import cocotb
from cocotb.triggers import Timer, with_timeout
from cocotb.utils import get_sim_time

def diagnostic(func):
    @functools.wraps(func)
    async def wrapped(dut, *args, **kwargs):
        ring = deque(maxlen=128)
        async def monitor():
            previous = None
            while True:
                await Timer(1, unit="ns")
                values = {}
                for handle in dut:
                    try:
                        if len(handle) <= 64:
                            values[handle._name] = int(handle.value)
                    except (AttributeError, TypeError, ValueError):
                        continue
                if values != previous:
                    ring.append((float(get_sim_time(unit="ns")), values))
                    previous = values
        task = cocotb.start_soon(monitor())
        try:
            return await with_timeout(func(dut, *args, **kwargs), 100000, "ns")
        finally:
            task.cancel()
            print("DIAGNOSTIC_ONLY: last signal transitions; sampling every 1ns; 100us diagnostic cap", flush=True)
            for time_ns, values in ring:
                print("SIGNAL_TRACE", time_ns, values, flush=True)
    return wrapped

def diagnostic_operation_check(expected, observed):
    assert observed == expected, (
        "diagnostic operation mismatch; expected=" + repr(expected)
        + "; observed=" + repr(observed)
    )
    return None
