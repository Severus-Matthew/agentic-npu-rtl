from __future__ import annotations

import pytest
import yaml

from multigent.intake.request_builder import build_verification_context
from multigent.tests.test_verifier import generic_fir_context


@pytest.mark.parametrize('name,default', [
    ('MAX_M', '64'), ('TRANSFORM_LENGTH', '1024'), ('DEPTH', 'LANES * 2'),
])
def test_verification_context_records_default_elaboration_without_changing_contract(
    tmp_path, name, default,
) -> None:
    frozen = generic_fir_context()['frozen_architecture']
    frozen['architecture_contract']['parameters'] = [
        {'name': name, 'default_value': default},
    ]
    for artifact, value in frozen.items():
        filename = f'{artifact}.json' if artifact == 'module_manifest' else f'{artifact}.yaml'
        (tmp_path / filename).write_text(yaml.safe_dump(value), encoding='utf-8')

    context = build_verification_context(user_request='implement a filter', architecture_dir=tmp_path)

    assert context['frozen_architecture'] == frozen
    assert context['execution_configuration'] == {
        'elaboration': 'declared_defaults',
        'parameter_overrides': {},
        'declared_parameter_defaults': {name: default},
    }
    assert context['provenance']['includes_generated_rtl'] is False
