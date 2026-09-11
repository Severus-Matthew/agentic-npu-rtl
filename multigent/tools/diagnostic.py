"""Read-only signal monitoring around copied tests; never functional acceptance."""
import ast
import shutil
from pathlib import Path
from .cocotb_runner import run_cocotb_regression

MONITOR = '''import functools
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
'''


def collect_diagnostics(workspace: Path, plan: dict, output: Path) -> dict:
    tests = output/'tests'
    tests.mkdir(parents=True,exist_ok=False)
    for src in (workspace/'tests').glob('*.py'):
        tree=ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.AsyncFunctionDef) and any(
                isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr=='test'
                for d in node.decorator_list):
                node.decorator_list.append(ast.Name(id='diagnostic',ctx=ast.Load()))
        # Insert after future imports/docstring, so valid Python stays valid.
        index=0
        while index<len(tree.body) and (isinstance(tree.body[index],ast.Expr) or
                isinstance(tree.body[index],ast.ImportFrom) and tree.body[index].module=='__future__'):
            index+=1
        tree.body.insert(index,ast.ImportFrom(module='_npu_monitor',names=[ast.alias(name='diagnostic')],level=0))
        (tests/src.name).write_text(ast.unparse(ast.fix_missing_locations(tree))+'\n')
    (tests/'_npu_monitor.py').write_text(MONITOR)
    result=run_cocotb_regression(rtl_dir=workspace/'rtl',top_module=plan['top_module'],
                                tests_dir=tests,reference_dir=workspace/'reference',
                                test_modules=list(plan['regression_groups']['full']),seed=int(plan['seed']),
                                build_dir=output/'build',report_path=output/'simulation.json',timeout_seconds=120,public_signals=True)
    return {'artifact_path':str(output), 'purpose':'DIAGNOSTIC_ONLY_NOT_ACCEPTANCE','simulation_cap_ns':100000,
            'signal_sampling_interval_ns':1,'result':result}
