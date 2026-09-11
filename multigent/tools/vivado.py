"""External, deterministic Vivado OOC implementation adapter; no synthetic PPA.

Bundles are portable: copy the bundle and this installed package to a Vivado host,
then execute ``python -m multigent.tools.vivado --bundle PATH``. Report provenance
binds source hashes, constraints, target and script to the evaluated candidate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from multigent.tools.process import run_process
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def tcl_word(value: str) -> str:
    if any(c in value for c in '{}\n\r\\'):
        raise ValueError("Unsafe Tcl argument")
    return '{' + value + '}'


def prepare_bundle(rtl_dir: Path, output: Path, top: str, config: dict,
                   verification: dict) -> dict:
    if verification.get('status') != 'PASS':
        raise ValueError('Vivado requires deterministic functional PASS')
    if output.exists():
        raise FileExistsError(f'Use a fresh Vivado candidate directory: {output}')
    output.mkdir(parents=True)
    sources = []
    for src in sorted(rtl_dir.rglob('*.sv')):
        rel = Path('rtl') / src.relative_to(rtl_dir)
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        sources.append(rel.as_posix())
    if not sources:
        raise ValueError('No RTL sources')
    config = dict(config)
    if config.get('xdc'):
        shutil.copy2(config['xdc'], output / 'constraints.xdc')
        config['xdc'] = 'constraints.xdc'
    config_error = None
    try:
        if not config.get('part') or not config.get('clock_port'):
            raise ValueError('Explicit FPGA part, clock_port and period_ns are required')
        period = float(config['period_ns'])
        if not math.isfinite(period) or period <= 0:
            raise ValueError('period_ns must be finite and positive')
        if not re.fullmatch(r'[A-Za-z_][\w$]*', top):
            raise ValueError('Invalid top module')
    except (ValueError, KeyError, TypeError) as exc:
        config_error = str(exc)
    lines = ['cd [file dirname [info script]]', 'set_param general.maxThreads 1']
    for source in sources:
        lines.append('read_verilog -sv ' + tcl_word(source))
    if config.get('xdc'):
        lines.append('read_xdc constraints.xdc')
    lines += [
        f'synth_design -top {tcl_word(top)} -part {tcl_word(str(config.get("part", "CONFIGURE_PART")))} -mode out_of_context',
        f'if {{[llength [get_clocks -quiet]] == 0}} {{create_clock -name primary -period {tcl_word(str(config.get("period_ns", "CONFIGURE_PERIOD")))} [get_ports {tcl_word(str(config.get("clock_port", "CONFIGURE_CLOCK")))}]}}',
        'report_utilization -file synthesis_utilization.rpt',
        'opt_design', 'place_design', 'phys_opt_design', 'route_design',
        'report_route_status -file route_status.rpt',
        'report_utilization -file utilization.rpt',
        'report_timing_summary -report_unconstrained -file timing_summary.rpt',
        'report_timing -max_paths 10 -path_type full_clock_expanded -file critical_paths.rpt',
        'report_power -file power.rpt', 'report_drc -file drc.rpt',
        'set critical_drc_count 0',
        'foreach violation [get_drc_violations] {set severity [get_property SEVERITY $violation]; if {[string equal -nocase $severity "Error"] || [string equal -nocase $severity "Critical Warning"]} {incr critical_drc_count}}',
        'write_checkpoint -force implemented.dcp',
        'set f [open timing.tsv w]',
        'puts $f "vivado_version\t[version -short]"',
        'puts $f "clock_count\t[llength [get_clocks]]"',
        'puts $f "routed_fully\t[report_route_status -boolean_check ROUTED_FULLY]"',
        'puts $f "routing_errors\t[report_route_status -boolean_check ERRORS_IN_ROUTES]"',
        'puts $f "critical_drc_count\t$critical_drc_count"',
        'set setup [get_timing_paths -delay_type max -max_paths 1]',
        'set hold [get_timing_paths -delay_type min -max_paths 1]',
        'if {[llength $setup] != 1 || [llength $hold] != 1} {error "Missing constrained timing paths"}',
        'puts $f "wns_ns\t[get_property SLACK $setup]"',
        'puts $f "whs_ns\t[get_property SLACK $hold]"',
        'puts $f "critical_path_delay_ns\t[get_property DATAPATH_DELAY $setup]"',
        'close $f',
        'set f [open completed.marker w]', 'puts $f "VIVADO_OOC_COMPLETE"', 'close $f',
    ]
    (output / 'run.tcl').write_text('\n'.join(lines) + '\n')
    files = sources + ['run.tcl'] + (['constraints.xdc'] if config.get('xdc') else [])
    manifest = {'schema_version': 1, 'provider': 'vivado', 'flow': 'out_of_context_implementation',
                'top_module': top, 'config': config, 'configuration_error': config_error,
                'files': {name: digest(output/name) for name in files},
                'verification': verification}
    write_json(output / 'manifest.json', manifest)
    return manifest


def parse_reports(bundle: Path) -> dict:
    """Fail closed on missing/unsupported report fields; never fill gaps with zero."""
    timing = dict(line.split('\t', 1) for line in (bundle/'timing.tsv').read_text().splitlines())
    result = {k: float(timing[k]) for k in ('wns_ns', 'whs_ns', 'critical_path_delay_ns')}
    if not all(math.isfinite(v) for v in result.values()):
        raise ValueError('Non-finite timing metric')
    util = (bundle/'utilization.rpt').read_text()
    labels = {'lut': ['CLB LUTs', 'Slice LUTs'], 'ff': ['CLB Registers', 'Slice Registers'],
              'dsp': ['DSPs', 'DSP48E1', 'DSP48E2'], 'bram_tiles': ['Block RAM Tile']}
    for key, alternatives in labels.items():
        matches = [re.search(r'^\s*\|\s*'+re.escape(label)+r'\*?\s*\|\s*([\d,.]+)\s*\|', util, re.M)
                   for label in alternatives]
        match = next((m for m in matches if m), None)
        if match is None:
            raise ValueError(f'Unsupported/missing utilization metric {key}')
        result[key] = float(match.group(1).replace(',', ''))
    power = (bundle/'power.rpt').read_text()
    match = re.search(r'\|\s*Total On-Chip Power \(W\)\s*\|\s*([\d.]+)\s*\|', power)
    if not match:
        raise ValueError('Missing estimated total on-chip power')
    result['estimated_power_w'] = float(match.group(1))
    result['power_basis'] = 'Vivado report_power estimate; default activity unless constrained by user XDC'
    result['area_basis'] = 'FPGA resource counts, not silicon area'
    result['vivado_version'] = timing['vivado_version']
    result['clock_count'] = int(timing['clock_count'])
    if timing.get('routed_fully') != '1' or timing.get('routing_errors') != '0':
        raise ValueError('Cannot establish complete error-free routing')
    result['critical_drc_count'] = int(timing['critical_drc_count'])
    if result['critical_drc_count'] < 0:
        raise ValueError('Invalid DRC count')
    # A clock sweep would be needed for a verified maximum operating frequency.
    result['fmax_mhz'] = None
    result['fmax_note'] = 'Not measured; no frequency sweep performed'
    return result


def run_bundle(bundle: Path, executable: str = 'vivado', timeout: int = 3600) -> dict:
    bundle = bundle.resolve()
    manifest_path = bundle / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    result = {'provider': 'vivado', 'status': None, 'metrics': None,
              'manifest_sha256': digest(manifest_path), 'bundle': str(bundle),
              'return_code': None, 'reports': {}, 'warnings': []}
    def finish(status, error=None):
        result.update(status=status, error=error)
        from jsonschema import Draft202012Validator
        schema = Path(__file__).resolve().parents[1]/'schemas'/'synthesis_result.schema.json'
        Draft202012Validator(json.loads(schema.read_text())).validate(result)
        write_json(bundle/'result.json', result)
        return result
    for name, expected in manifest['files'].items():
        path = (bundle/name).resolve()
        if not path.is_relative_to(bundle) or not path.is_file() or digest(path) != expected:
            return finish('PROVENANCE_MISMATCH', f'Changed bundle input: {name}')
    binary = shutil.which(executable)
    if not binary:
        return finish('TOOL_UNAVAILABLE', f'{executable} not found; prepared bundle can run on a compatible host')
    if manifest.get('configuration_error'):
        return finish('CONFIGURATION_REQUIRED', manifest['configuration_error'])
    # Never reuse report files from an earlier process invocation.
    if (bundle/'completed.marker').exists() or (bundle/'vivado.log').exists():
        return finish('STALE_OUTPUT', 'Prepare a fresh candidate bundle before rerunning')
    try:
        completed = run_process([binary, '-mode', 'batch', '-source', 'run.tcl', '-notrace',
                                    '-log', 'vivado.log', '-journal', 'vivado.jou'],
                                   cwd=bundle, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return finish('TIMEOUT', 'Vivado wall-clock budget exhausted')
    except OSError as exc:
        return finish('TOOL_ERROR', str(exc))
    (bundle/'stdout.log').write_text(completed.stdout)
    (bundle/'stderr.log').write_text(completed.stderr)
    result['return_code'] = completed.returncode
    logs = completed.stdout + '\n' + completed.stderr
    if (bundle/'vivado.log').exists():
        logs += (bundle/'vivado.log').read_text(errors='replace')
    result['warnings'] = [line for line in logs.splitlines() if 'WARNING:' in line]
    if completed.returncode != 0:
        return finish('IMPLEMENTATION_FAILED', 'See raw Vivado logs')
    try:
        if (bundle/'completed.marker').read_text().strip() != 'VIVADO_OOC_COMPLETE':
            raise ValueError('Missing flow completion marker')
        for name in ['utilization.rpt', 'power.rpt', 'timing_summary.rpt', 'critical_paths.rpt', 'route_status.rpt', 'drc.rpt', 'timing.tsv']:
            result['reports'][name] = digest(bundle/name)
        metrics = parse_reports(bundle)
        result['metrics'] = metrics
        if metrics['critical_drc_count']:
            return finish('DRC_FAILED', 'Critical implementation DRC findings')
        return finish('TIMING_FAILED' if metrics['wns_ns'] < 0 or metrics['whs_ns'] < 0 else 'PASS')
    except (OSError, ValueError, KeyError) as exc:
        result['metrics'] = None
        return finish('REPORT_INCOMPLETE', str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--executable', default='vivado')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    result = run_bundle(args.bundle, args.executable, args.timeout)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 2)



def import_result(bundle: Path, rtl_dir: Path, config: dict) -> dict:
    """Validate a returned external bundle against current candidate and target."""
    bundle=bundle.resolve()
    manifest=json.loads((bundle/'manifest.json').read_text())
    result=json.loads((bundle/'result.json').read_text())
    if result.get('status') not in {'PASS','TIMING_FAILED'} or result.get('return_code') != 0:
        raise ValueError('External bundle has no completed deterministic implementation')
    if result.get('manifest_sha256') != digest(bundle/'manifest.json'):
        raise ValueError('External manifest hash mismatch')
    for name,sha in manifest['files'].items():
        p=(bundle/name).resolve()
        if not p.is_relative_to(bundle) or digest(p)!=sha:
            raise ValueError('External bundle input mismatch')
    expected={str(Path('rtl')/p.relative_to(rtl_dir)):digest(p) for p in rtl_dir.rglob('*.sv')}
    supplied={name:sha for name,sha in manifest['files'].items() if name.startswith('rtl/')}
    if expected!=supplied:
        raise ValueError('External PPA belongs to different RTL')
    for key in ('part','clock_port','period_ns'):
        if config.get(key)!=manifest['config'].get(key):
            raise ValueError('External target/clock configuration mismatch')
    if bool(config.get('xdc')) != bool(manifest['config'].get('xdc')):
        raise ValueError('External constraints mismatch')
    if config.get('xdc') and digest(Path(config['xdc']))!=manifest['files']['constraints.xdc']:
        raise ValueError('External constraints hash mismatch')
    required={'utilization.rpt','power.rpt','timing_summary.rpt','critical_paths.rpt','route_status.rpt','drc.rpt','timing.tsv'}
    if set(result['reports'])!=required:
        raise ValueError('Incomplete external report manifest')
    for name,sha in result['reports'].items():
        if digest(bundle/name)!=sha:
            raise ValueError('External report changed')
    metrics=parse_reports(bundle)
    if result['metrics']!=metrics:
        raise ValueError('External parsed metrics do not match reports')
    if metrics['critical_drc_count']:
        raise ValueError('External DRC failure')
    if (bundle/'completed.marker').read_text().strip()!='VIVADO_OOC_COMPLETE':
        raise ValueError('External completion marker missing')
    status='TIMING_FAILED' if metrics['wns_ns']<0 or metrics['whs_ns']<0 else 'PASS'
    if result['status']!=status:
        raise ValueError('External timing status contradicts deterministic metrics')
    return {**result,'bundle':str(bundle)}

if __name__ == '__main__':
    main()
