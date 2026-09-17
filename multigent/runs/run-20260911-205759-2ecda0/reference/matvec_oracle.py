MASK = 0xffffffff
OUTPUTS = ('cmd_ready', 'in_ready', 'out_valid', 'out_data', 'out_last', 'done_valid', 'done_error')


def signed(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def wrap32(value):
    return signed(value, 32)


def matvec(matrix, vector, bias, bias_enable, relu_enable):
    result = []
    for r, row in enumerate(matrix):
        acc = 0
        for a, x in zip(row, vector):
            acc = wrap32(acc + signed(a, 8) * signed(x, 8))
        if bias_enable:
            acc = wrap32(acc + signed(bias[r], 32))
        if relu_enable:
            acc = max(0, acc)
        result.append(acc & MASK)
    return result


def serialize(matrix, vector, bias, enabled, rng):
    def byte(value):
        return (rng.getrandbits(24) << 8) | (value & 255)
    data = [byte(x) for x in vector]
    rows = len(matrix)
    for base in range(0, rows, 16):
        height = min(16, rows - base)
        if enabled:
            data.extend(bias[base + i] & MASK for i in range(height))
        for c in range(len(vector)):
            data.extend(byte(matrix[base + i][c]) for i in range(height))
    return data


def latency(rows, cols, bias):
    tiles = (rows + 15) // 16
    return cols + 2 * tiles + bias * rows + cols * (rows + tiles) + rows + 1


def sanity():
    assert signed(0x80, 8) == -128
    assert signed(0xff, 8) == -1
    assert wrap32(0x80000000) == -2147483648
    assert matvec([[0, 0]], [127, -128], [0], 0, 0) == [0]
    assert matvec([[1, 0], [0, 1]], [-128, 127], [0, 0], 0, 0) == [0xffffff80, 127]
    assert matvec([[-128], [-128], [127]], [-128], [0, 0, 0], 0, 0) == [16384, 16384, 0xffffc080]
    assert matvec([[1]], [1], [2147483647], 1, 0) == [0x80000000]
    assert matvec([[1]], [1], [2147483647], 1, 1) == [0]
    assert matvec([[-1]], [1], [-2147483648], 1, 1) == [2147483647]
    assert matvec([[0], [0]], [0], [-2147483648, 2147483647], 1, 0) == [0x80000000, 0x7fffffff]
    assert matvec([[-1]], [1], [2], 1, 1) == [1]
    assert latency(1, 1, 0) == 7
    assert latency(17, 1, 1) == 59


class Schedule:
    def __init__(self, max_rows, max_cols):
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.clear()

    def clear(self):
        self.state = 'IDLE'
        self.job = None
        self.base = self.lane = self.col = self.x = 0
        self.accepted = self.emitted = 0
        self.error = 0

    @property
    def height(self):
        return min(16, self.job['r'] - self.base)

    def outputs(self, reset=False):
        o = dict.fromkeys(OUTPUTS, 0)
        if reset:
            return o
        s = self.state
        o['cmd_ready'] = int(s == 'IDLE')
        o['in_ready'] = int(s in ('LOAD_X', 'LOAD_BIAS', 'LOAD_W'))
        o['out_valid'] = int(s == 'EMIT')
        o['done_valid'] = int(s == 'DONE')
        if s == 'EMIT':
            row = self.base + self.lane
            o['out_data'] = self.job['expected'][row]
            o['out_last'] = int(row == self.job['r'] - 1)
        if s == 'DONE':
            o['done_error'] = self.error
        return o

    def advance(self, inputs, offered_job=None):
        if inputs['rst']:
            self.clear()
            return
        s = self.state
        if s == 'IDLE':
            if inputs['cmd_valid']:
                assert offered_job is not None, 'Missing command fixture'
                j = offered_job
                assert (inputs['cmd_rows'], inputs['cmd_cols'], inputs['cmd_bias_enable'], inputs['cmd_relu_enable']) == (j['r'], j['c'], j['b'], j['a'])
                self.job = j
                self.error = int(not (1 <= j['r'] <= self.max_rows and 1 <= j['c'] <= self.max_cols))
                self.base = self.lane = self.col = self.x = 0
                self.accepted = self.emitted = 0
                self.state = 'DONE' if self.error else 'LOAD_X'
        elif s in ('LOAD_X', 'LOAD_BIAS', 'LOAD_W'):
            if not inputs['in_valid']:
                return
            assert self.accepted < len(self.job['wire']), 'Extra operand acceptance'
            expected = self.job['wire'][self.accepted]
            assert inputs['in_data'] == expected, ('Operand ordering', self.accepted, expected, inputs['in_data'])
            self.accepted += 1
            if s == 'LOAD_X':
                self.x += 1
                if self.x == self.job['c']:
                    self.state = 'TILE_INIT'
            else:
                self.lane += 1
                if self.lane == self.height:
                    self.lane = 0
                    self.state = 'LOAD_W' if s == 'LOAD_BIAS' else 'MAC'
        elif s == 'TILE_INIT':
            self.col = self.lane = 0
            self.state = 'LOAD_BIAS' if self.job['b'] else 'LOAD_W'
        elif s == 'MAC':
            self.col += 1
            self.state = 'FINALIZE' if self.col == self.job['c'] else 'LOAD_W'
        elif s == 'FINALIZE':
            self.lane = 0
            self.state = 'EMIT'
        elif s == 'EMIT':
            if inputs['out_ready']:
                self.emitted += 1
                self.lane += 1
                if self.lane == self.height:
                    if self.base + self.height == self.job['r']:
                        assert self.accepted == len(self.job['wire'])
                        assert self.emitted == self.job['r']
                        self.state = 'DONE'
                    else:
                        self.base += 16
                        self.state = 'TILE_INIT'
        elif s == 'DONE':
            if inputs['done_ready']:
                if self.error:
                    assert self.accepted == self.emitted == 0
                self.state = 'IDLE'
