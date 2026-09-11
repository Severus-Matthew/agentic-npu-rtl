"""Real-simulator infrastructure test using a known identity block, not benchmark RTL."""
import shutil
import pytest
from multigent.tools.cocotb_runner import run_cocotb_regression


@pytest.mark.skipif(shutil.which('verilator') is None,reason='Verilator not on PATH')
def test_runner_signed_data_backpressure_reset_and_bad_expectation(tmp_path):
    rtl=tmp_path/'rtl';rtl.mkdir()
    tests=tmp_path/'tests';tests.mkdir()
    ref=tmp_path/'reference';ref.mkdir()
    (rtl/'identity.sv').write_text('''module identity(input logic clk, rst, iv, ordy,
        input logic signed [7:0] data, output logic ir, ov,
        output logic signed [7:0] result);
        assign ir = !ov || ordy;
        always_ff @(posedge clk) begin
          if (rst) begin ov <= 0; result <= 0; end
          else if (ir) begin ov <= iv; if (iv) result <= data; end
        end
        endmodule
    ''')
    (ref/'model.py').write_text('def identity(value): return value\n')
    code='''import cocotb
from reference.model import identity as packaged_identity
from model import identity as flat_identity
from cocotb.triggers import Timer
@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def check(dut):
    assert packaged_identity(-128)==flat_identity(-128)==-128
    dut.clk.value=0
    dut.rst.value=1
    dut.iv.value=0
    dut.ordy.value=0
    dut.data.value=0
    async def cycle():
        dut.clk.value=0
        await Timer(5, unit="ns")
        snapshot=(int(dut.ir.value),int(dut.ov.value),dut.result.value.to_signed())
        dut.clk.value=1
        await Timer(5, unit="ns")
        dut.clk.value=0
        return snapshot
    await cycle()
    assert int(dut.ov.value)==0
    dut.rst.value=0
    for value in (-128,-1,0,1,127):
        dut.iv.value=1
        dut.data.value=value & 255
        await cycle()
        dut.iv.value=0
        for _ in range(3):
            _,valid,observed=await cycle()
            assert valid and observed==value
        dut.ordy.value=1
        _,valid,observed=await cycle()
        assert valid and observed==value
        dut.ordy.value=0
    dut.rst.value=1
    await cycle()
    assert int(dut.ov.value)==0
'''
    path=tests/'test_identity.py';path.write_text(code)
    def run(tag):
        return run_cocotb_regression(rtl_dir=rtl,top_module='identity',tests_dir=tests,reference_dir=ref,
            test_modules=['test_identity'],seed=7,build_dir=tmp_path/tag,report_path=tmp_path/(tag+'.json'),timeout_seconds=120)
    result=run('good')
    assert result['status']=='PASS',result
    path.write_text(code.replace('observed==value','observed==value+1'))
    assert run('bad')['status']=='SIMULATION_FAILURE'
