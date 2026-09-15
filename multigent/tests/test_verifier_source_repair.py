from __future__ import annotations

import copy

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VERIFIER_SOURCE_REPAIR_SCHEMA, VerifierAgent
from multigent.tests.test_verifier import generic_fir_context, verification_ready_result


def review_context():
    context = generic_fir_context()
    draft = verification_ready_result()
    draft['test_files'][0]['content'] = 'import cocotb\n'
    context['semantic_validation_review'] = {
        'validator_error': 'Generated test file contains no executable async functions',
        'previous_verifier_output': draft,
    }
    return context, draft


def complete_sources():
    result = verification_ready_result()
    return {
        'status': 'VERIFICATION_READY', 'architecture_conflict': None,
        'known_verification_gaps': [],
        'files': [
            {'path': f"{owner}/{item['path']}", 'content': item['content']}
            for field, owner in [('reference_files', 'reference'), ('test_files', 'tests')]
            for item in result[field]
        ],
    }


def test_source_completion_is_one_counted_call_and_keeps_metadata(tmp_path):
    class StubVerifier(VerifierAgent):
        def __init__(self):
            super().__init__()
            self.calls = []

        def run_structured(self, **kwargs):
            self.calls.append(kwargs)
            return complete_sources()

    context, draft = review_context()
    previous = copy.deepcopy(draft)
    agent = StubVerifier()
    result = agent.run(context, workspace_dir=tmp_path)
    assert len(agent.calls) == 1
    assert agent.calls[0]['schema_path'] == VERIFIER_SOURCE_REPAIR_SCHEMA
    assert 'Metadata is reused by the runtime' in agent.calls[0]['task']
    assert 'semantic_validation_review' not in agent.calls[0]['task']
    assert result['operation_coverage'] == draft['operation_coverage']
    assert result['verification_plan'] == draft['verification_plan']
    assert draft == previous
    assert (tmp_path / 'tests/test_fir_contract.py').is_file()


@pytest.mark.parametrize('reason', ['other_error', 'invalid_metadata', 'no_draft'])
def test_source_completion_only_handles_incomplete_source_with_valid_metadata(reason):
    context, draft = review_context()
    if reason == 'other_error':
        context['semantic_validation_review']['validator_error'] = 'missing operation feature'
    elif reason == 'invalid_metadata':
        draft['operation_coverage'] = []
    else:
        del context['semantic_validation_review']['previous_verifier_output']
    assert VerifierAgent._source_repair_draft(context) is None


@pytest.mark.parametrize('defect', ['missing', 'unknown', 'duplicate'])
def test_source_completion_rejects_inexact_file_set(defect):
    _, draft = review_context()
    sources = complete_sources()
    if defect == 'missing':
        sources['files'].pop()
    elif defect == 'unknown':
        sources['files'][0]['path'] = 'rtl/injected.py'
    else:
        sources['files'].append(sources['files'][0])
    with pytest.raises(AgentRuntimeError, match='Source completion'):
        VerifierAgent._merge_source_repair(draft, sources)


def test_source_completion_does_not_bypass_full_validation(tmp_path):
    _, draft = review_context()
    sources = complete_sources()
    sources['files'][1]['content'] = 'import cocotb\n'
    result = VerifierAgent._merge_source_repair(draft, sources)
    with pytest.raises(AgentRuntimeError, match='no executable async'):
        VerifierAgent().persist_validated_result(
            result=result, context=generic_fir_context(), root=tmp_path,
        )
    assert not (tmp_path / 'tests/test_fir_contract.py').exists()
