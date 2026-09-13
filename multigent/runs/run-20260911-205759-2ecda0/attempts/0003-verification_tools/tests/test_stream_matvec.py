import random
import cocotb
from cocotb.triggers import Timer
from matvec_oracle import MASK, OUTPUTS, Schedule, matvec, serialize, latency, sanity

SEED = 637901
INPUTS = ('rst', 'cmd_valid', 'cmd_rows', 'cmd_cols', 'cmd_bias_enable', 'cmd_relu_enable', 'in_valid', 'in_data', 'out_ready', 'done_ready')


def check_source(previous, current, ready, valid, fields):
    if previous is not None and not current['rst'] and not previous['rst']:
        if previous[valid] and not previous[ready]:
            assert current[valid], ('Source withdrew valid', valid)
            assert all(current[f] == previous[f] for f in fields), ('Source changed stalled payload', fields)


def source_sanity():
    p = dict(rst=0, in_valid=1, in_ready=0, in_data=23)
    check_source(p, dict(p), 'in_ready', 'in_valid', ('in_data',))
    bad = dict(p, in_valid=0)
    caught = False
    try:
        check_source(p, bad, 'in_ready', 'in_valid', ('in_data',))
    except AssertionError:
        caught = True
    assert caught, 'Source validator failed to diagnose withdrawal'
    bad = dict(p, in_data=24)
    caught = False
    try:
        check_source(p, bad, 'in_ready', 'in_valid', ('in_data',))
    except AssertionError:
        caught = True
    assert caught, 'Source validator failed to diagnose payload mutation'


def fixture(r, c, b, a, rng, label, kind='pattern', bounds=(256, 256)):
    j = dict(r=r, c=c, b=b, a=a, label=label, wire=[], expected=[])
    if not (1 <= r <= bounds[0] and 1 <= c <= bounds[1]):
        return j
    if kind == 'zero':
        x = [0] * c
        w = [[0] * c for _ in range(r)]
        bias = [0] * r
    elif kind == 'random':
        x = [rng.randrange(-128, 128) for _ in range(c)]
        w = [[rng.randrange(-128, 128) for _ in range(c)] for _ in range(r)]
        bias = [rng.getrandbits(32) for _ in range(r)]
    elif kind == 'overflow':
        x = [1] + [0] * (c - 1)
        w = [[1 if row % 2 == 0 else -1] + [0] * (c - 1) for row in range(r)]
        bias = [0x7fffffff if row % 2 == 0 else 0x80000000 for row in range(r)]
    else:
        x = [(-128, 127, -1, 0, 1, 63, -64)[col % 7] for col in range(c)]
        w = [[((row * 71 + col * 29 + row * col * 3) % 256) - 128 for col in range(c)] for row in range(r)]
        bias = [(0, 0x7fffffff, 0x80000000, 0xffffffff, 12345, 0xffff6789)[row % 6] for row in range(r)]
    j['expected'] = matvec(w, x, bias, b, a)
    j['wire'] = serialize(w, x, bias, b, rng)
    assert len(j['wire']) == c + b * r + c * r
    return j


class Harness:
    def __init__(self, dut, rows, cols):
        self.dut = dut
        self.model = Schedule(rows, cols)
        self.inputs = dict.fromkeys(INPUTS, 0)
        self.previous = None
        self.cycle = 0
        self.context = 'initialization'
        self.dut.clk.value = 0

    def sample(self):
        return {name: int(getattr(self.dut, name).value) & (MASK if name == 'out_data' else 1) for name in OUTPUTS}

    def compare(self, observed, phase):
        expected = self.model.outputs(bool(self.inputs['rst']))
        for name in OUTPUTS:
            assert observed[name] == expected[name], (f'{self.context} seed={SEED} cycle={self.cycle} {phase} state={self.model.state} base={self.model.base} col={self.model.col} lane={self.model.lane} operands={self.model.accepted} results={self.model.emitted} signal={name} expected={expected[name]} observed={observed[name]}')

    async def tick(self, updates=None, offered=None):
        if updates:
            self.inputs.update(updates)
        self.dut.clk.value = 0
        for name, value in self.inputs.items():
            getattr(self.dut, name).value = value
        await Timer(5, unit='ns')
        before = self.sample()
        self.compare(before, 'pre-edge')
        current = dict(self.inputs, **before)
        check_source(self.previous, current, 'cmd_ready', 'cmd_valid', ('cmd_rows', 'cmd_cols', 'cmd_bias_enable', 'cmd_relu_enable'))
        check_source(self.previous, current, 'in_ready', 'in_valid', ('in_data',))
        self.dut.clk.value = 1
        self.model.advance(self.inputs, offered)
        await Timer(5, unit='ns')
        self.compare(self.sample(), 'post-edge')
        self.previous = current
        self.cycle += 1
        self.dut.clk.value = 0
        return current

    async def reset(self):
        self.context = 'reset from ' + self.model.state
        await self.tick(dict(rst=1, cmd_valid=1, in_valid=1, in_data=0xdeadbeef, out_ready=1, done_ready=1))
        await self.tick()
        await self.tick(dict(rst=0, cmd_valid=0, in_valid=0, out_ready=0, done_ready=0))
        assert self.model.state == 'IDLE'


async def batch(h, jobs, rng, stalls):
    wire = [word for j in jobs for word in j['wire']]
    ci = wi = completed = 0
    cp = ip = False
    cd = idelay = 0
    command_edges = []
    out_counts = [0] * len(jobs)
    last_counts = [0] * len(jobs)
    sink_key = None
    sink_age = 0
    done_key = None
    done_age = 0
    limit = 40 * (len(wire) + sum(j['r'] for j in jobs if j['expected']) + len(jobs) + 1) + 1000
    for local in range(limit):
        if not cp and ci < len(jobs):
            if cd == 0:
                cp = True
            else:
                cd -= 1
        if not ip and wi < len(wire):
            if idelay == 0:
                ip = True
            else:
                idelay -= 1
        drive = dict(rst=0, cmd_valid=int(cp), in_valid=int(ip))
        offered = jobs[ci] if cp else None
        if cp:
            drive.update(cmd_rows=offered['r'], cmd_cols=offered['c'], cmd_bias_enable=offered['b'], cmd_relu_enable=offered['a'])
        else:
            drive.update(cmd_rows=rng.randrange(65536), cmd_cols=rng.randrange(65536), cmd_bias_enable=rng.randrange(2), cmd_relu_enable=rng.randrange(2))
        if ip:
            drive['in_data'] = wire[wi]
        else:
            drive['in_data'] = rng.getrandbits(32)
        key = (completed, h.model.base, h.model.lane) if h.model.state == 'EMIT' else None
        if key != sink_key:
            sink_key, sink_age = key, 0
        dkey = completed if h.model.state == 'DONE' else None
        if dkey != done_key:
            done_key, done_age = dkey, 0
        drive['out_ready'] = int(not stalls or (sink_age >= 3 and rng.randrange(4) != 0))
        drive['done_ready'] = int(not stalls or (done_age >= 7 and rng.randrange(4) != 0))
        if key is not None:
            sink_age += 1
        if dkey is not None:
            done_age += 1
        label = jobs[min(completed, len(jobs) - 1)]['label']
        h.context = f'batch {label} command_index={ci} wire_index={wi} completed={completed} stalls={stalls}'
        edge = h.cycle
        snap = await h.tick(drive, offered)
        if snap['cmd_valid'] and snap['cmd_ready']:
            command_edges.append(edge)
            ci += 1
            cp = False
            cd = rng.randrange(4) if stalls else 0
        if snap['in_valid'] and snap['in_ready']:
            wi += 1
            ip = False
            idelay = rng.randrange(4) if stalls else 0
        if snap['out_valid'] and snap['out_ready']:
            assert completed < len(jobs), 'Result after final completion'
            j = jobs[completed]
            index = out_counts[completed]
            assert index < len(j['expected']), (label, 'Extra result', index)
            assert snap['out_data'] == j['expected'][index], (label, SEED, index, j['expected'][index], snap['out_data'])
            assert snap['out_last'] == int(index == j['r'] - 1), (label, 'Incorrect last', index)
            out_counts[completed] += 1
            last_counts[completed] += snap['out_last']
        if snap['done_valid'] and snap['done_ready']:
            j = jobs[completed]
            legal = bool(j['expected'])
            assert snap['done_error'] == int(not legal), (label, 'Completion status')
            assert out_counts[completed] == (j['r'] if legal else 0), (label, 'Completion result count')
            assert last_counts[completed] == int(legal), (label, 'Last count')
            assert not snap['cmd_ready'], (label, 'Command accepted on completion edge')
            if not stalls:
                expected_latency = latency(j['r'], j['c'], j['b']) if legal else 1
                assert edge - command_edges[completed] == expected_latency, (label, 'Latency', expected_latency, edge - command_edges[completed])
            completed += 1
            if completed == len(jobs):
                assert ci == len(jobs) and wi == len(wire), ('Incomplete source counts', ci, wi, len(wire))
                assert not cp and not ip
                for _ in range(4):
                    await h.tick(dict(cmd_valid=0, in_valid=0, out_ready=1, done_ready=1))
                return
    raise AssertionError(f'Bounded liveness failure seed={SEED} completed={completed}/{len(jobs)} state={h.model.state}')


async def abort_at(h, job, target):
    sent = False
    index = 0
    limit = 10 * (len(job['wire']) + job['r'] + 20)
    for _ in range(limit):
        h.context = f'reset-target={target} job={job["label"]}'
        drive = dict(rst=0, cmd_valid=int(not sent), cmd_rows=job['r'], cmd_cols=job['c'], cmd_bias_enable=job['b'], cmd_relu_enable=job['a'], in_valid=int(index < len(job['wire'])), out_ready=int(target != 'EMIT'), done_ready=0)
        if index < len(job['wire']):
            drive['in_data'] = job['wire'][index]
        snap = await h.tick(drive, job if not sent else None)
        if snap['cmd_valid'] and snap['cmd_ready']:
            sent = True
        if snap['in_valid'] and snap['in_ready']:
            index += 1
        m = h.model
        reached = m.state == target
        if target == 'LOAD_X':
            reached = reached and m.x == 1
        if target in ('LOAD_BIAS', 'LOAD_W'):
            reached = reached and m.lane == 1
        if reached:
            if target in ('EMIT', 'DONE'):
                for _ in range(4):
                    hold = dict(cmd_valid=int(not sent), in_valid=int(index < len(job['wire'])), out_ready=0, done_ready=0)
                    if index < len(job['wire']):
                        hold['in_data'] = job['wire'][index]
                    await h.tick(hold)
            await h.reset()
            return
    raise AssertionError(f'Reset target not reached: {target}')


@cocotb.test(timeout_time=1000000000, timeout_unit='ns')
async def contract_regression(dut):
    sanity()
    source_sanity()
    rows = int(cocotb.plusargs.get('VERIFY_MAX_ROWS', '256'))
    cols = int(cocotb.plusargs.get('VERIFY_MAX_COLS', '256'))
    assert 16 <= rows <= 65535 and 1 <= cols <= 65535
    bounds = (rows, cols)
    rng = random.Random(SEED)
    dut._log.info('Contract regression seed=%d MAX_ROWS=%d MAX_COLS=%d randomized_jobs=100', SEED, rows, cols)
    h = Harness(dut, rows, cols)
    await h.reset()
    def make(r, c, b=0, a=0, label='directed', kind='pattern'):
        return fixture(r, c, b, a, rng, label, kind, bounds)
    directed = []
    for b in (0, 1):
        for a in (0, 1):
            directed.append(make(1, 1, b, a, f'min-{b}-{a}'))
            directed.append(make(min(17, rows), min(7, cols), b, a, f'zero-{b}-{a}', 'zero'))
            directed.append(make(16, min(3, cols), b, a, f'wrap-{b}-{a}', 'overflow'))
    for r in (15, 16, 17, 31, 32, 33):
        if r <= rows:
            directed.append(make(r, min(19, cols), 1, r % 2, f'tail-{r}'))
    directed.append(make(rows, 1, 1, 0, 'maximum-rows'))
    directed.append(make(1, cols, 0, 0, 'maximum-columns'))
    if rows * cols <= 262144:
        directed.append(make(rows, cols, 1, 1, 'both-maxima'))
    await batch(h, directed, rng, False)
    stalled = [make(min(33, rows), min(5, cols), b, a, f'stalled-{b}-{a}') for b in (0, 1) for a in (0, 1)]
    await batch(h, stalled, rng, True)
    invalid = [(0, 1), (1, 0), (0, 0)]
    if rows < 65535:
        invalid.extend([(rows + 1, 1), (65535, 1)])
    if cols < 65535:
        invalid.extend([(1, cols + 1), (1, 65535)])
    for stalls in (False, True):
        jobs = []
        for i, (r, c) in enumerate(invalid):
            jobs.append(make(r, c, i % 2, (i // 2) % 2, f'invalid-{r}-{c}'))
            jobs.append(make(min(17, rows), min(3, cols), i % 2, 1, f'error-recovery-{i}'))
        await batch(h, jobs, rng, stalls)
    random_jobs = []
    for i in range(100):
        r = rng.randint(1, min(rows, 65))
        c = rng.randint(1, min(cols, 37))
        random_jobs.append(make(r, c, i % 2, (i // 2) % 2, f'random-{i}-seed-{SEED}', 'random'))
    await batch(h, random_jobs, rng, True)
    targets = ['LOAD_BIAS', 'LOAD_W', 'MAC', 'FINALIZE', 'EMIT', 'DONE']
    if cols > 1:
        targets.insert(0, 'LOAD_X')
    for target in targets:
        job = make(min(17, rows), min(3, cols), 1, 1, f'aborted-{target}')
        await abort_at(h, job, target)
        await batch(h, [make(min(33, rows), min(5, cols), 0, 0, f'after-reset-{target}')], rng, True)
    await h.reset()
    await batch(h, [make(1, 1, 1, 0, 'final-recovery', 'overflow')], rng, False)
