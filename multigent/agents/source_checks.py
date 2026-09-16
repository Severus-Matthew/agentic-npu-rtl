"""Generic source integrity checks. These do not prove functional correctness."""
import ast
import re
from pathlib import Path
from .base import AgentRuntimeError


def python_functions(source):
    tree = ast.parse(source)
    result = {}
    def visit(nodes, prefix=''):
        for node in nodes:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                name=prefix+node.name
                result[name] = {'async':isinstance(node,ast.AsyncFunctionDef),
                               'cocotb_test': any(isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr=='test' for d in node.decorator_list),
                               'posonly':[x.arg for x in node.args.posonlyargs],
                               'arguments':[x.arg for x in node.args.args],
                               'kwonly':[x.arg for x in node.args.kwonlyargs],
                               'vararg':node.args.vararg.arg if node.args.vararg else None,
                               'kwarg':node.args.kwarg.arg if node.args.kwarg else None}
                visit(node.body,name+'.')
            elif isinstance(node,ast.ClassDef):
                visit(node.body,prefix+node.name+'.')
    visit(tree.body)
    return result


def validate_python_integrity(filename, source):
    tree=ast.parse(source,filename=filename)
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            body=[s for s in node.body if not isinstance(s,ast.Pass) and not
                  (isinstance(s,ast.Expr) and isinstance(s.value,ast.Constant)
                   and (isinstance(s.value.value,str) or s.value.value is Ellipsis))]
            if not body:
                raise AgentRuntimeError(f'{filename}: function {node.name} has an empty/placeholder body')
        if isinstance(node,ast.Assert):
            try:
                value=ast.literal_eval(node.test)
            except (ValueError,TypeError,SyntaxError):
                value=None
            if value:
                raise AgentRuntimeError(f'{filename}:{node.lineno}: assertion is always true; compare an observation with an independently derived expectation')
            if isinstance(node.test,ast.BoolOp) and isinstance(node.test.op,ast.Or):
                if any(isinstance(x,ast.Constant) and bool(x.value) for x in node.test.values):
                    raise AgentRuntimeError(f'{filename}:{node.lineno}: assertion is disabled by a constant true OR operand')
            if isinstance(node.test,ast.Compare) and len(node.test.ops)==1 and isinstance(node.test.ops[0],ast.Eq):
                left,right=node.test.left,node.test.comparators[0]
                if isinstance(left,ast.Constant) and isinstance(right,ast.Constant) and left.value==right.value:
                    raise AgentRuntimeError(f'{filename}:{node.lineno}: assertion compares equal constants')


def preserve_python_api(previous, candidate):
    for field in ('test_files','reference_files'):
        old={Path(x['path']).name:x['content'] for x in previous.get(field,[])}
        new={Path(x['path']).name:x['content'] for x in candidate.get(field,[])}
        for filename,source in old.items():
            if filename not in new:
                raise AgentRuntimeError(f'Repair must preserve existing verification filename {filename}')
            try:
                before=python_functions(source)
            except SyntaxError:
                continue  # Invalid first drafts have no parsable API to freeze.
            after=python_functions(new[filename])
            for name,signature in before.items():
                if after.get(name)!=signature:
                    raise AgentRuntimeError(f'Repair must preserve function name and call signature: {filename}:{name}; add a new helper without renaming/removing existing functions')


def sv_function_names(source):
    source=re.sub(r'/\*.*?\*/|//[^\n]*','',source,flags=re.S)
    result=set()
    for match in re.finditer(r'\b(function|task)\b([^;(]*)(?:\(|;)',source):
        header=re.sub(r'\[[^]]*\]','',match.group(2))
        names=re.findall(r'[A-Za-z_][\w$]*',header)
        if names: result.add((match.group(1),names[-1]))
    return result


def sv_port_names(source, module):
    source=re.sub(r'/\*.*?\*/|//[^\n]*','',source,flags=re.S)
    match=re.search(r'\bmodule\s+(?:automatic\s+)?'+re.escape(module)+r'\b',source)
    if not match: return set()
    tail=source[match.end():].lstrip()
    def group(text):
        depth=0
        for i,c in enumerate(text):
            if c=='(': depth+=1
            elif c==')':
                depth-=1
                if depth==0:return text[1:i],text[i+1:].lstrip()
        raise AgentRuntimeError('Unbalanced SystemVerilog module header')
    if tail.startswith('#'):
        _,tail=group(tail[1:].lstrip())
    if not tail.startswith('('):return set()
    header,_=group(tail)
    names=set()
    for port in header.split(','):
        port=re.sub(r'\[[^]]*\]','',port.split('=')[0])
        identifiers=re.findall(r'[A-Za-z_][\w$]*',port)
        if identifiers:names.add(identifiers[-1])
    return names
