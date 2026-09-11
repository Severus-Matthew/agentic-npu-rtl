"""PPA planner: sees contracts and deterministic evidence, never verification code."""
import json
import os
from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT


class PPAOptimizerAgent(APIAgent):
    def __init__(self):
        super().__init__(AgentConfig(name='ppa_optimizer', role_skill='ppa_optimizer',
                                    model=os.getenv('NPU_AGENT_MODEL', 'gpt-5.3-codex'),
                                    api_mode=os.getenv('NPU_AGENT_API_MODE', 'responses')))

    def run(self, context, *, run_id):
        if context['synthesis_result']['status'] not in {'PASS', 'TIMING_FAILED'}:
            raise AgentRuntimeError('Optimizer requires deterministic Vivado metrics')
        result = self.run_structured(task=json.dumps(context),
                                    schema_path=SCHEMA_ROOT/'optimization_plan.schema.json',
                                    log_name=f'ppa-optimizer-{run_id}.json')
        self.validate(result, context)
        return result

    @staticmethod
    def validate(result, context):
        if result['action'] == 'STOP':
            if result['affected_modules']:
                raise AgentRuntimeError('STOP may not authorize module edits')
            return
        manifest = context['frozen_architecture']['module_manifest']
        modules = {m['name'] for m in manifest['modules']}
        affected = set(result['affected_modules'])
        if not affected or not affected <= modules:
            raise AgentRuntimeError('Optimization must name existing manifest modules')
        if set(result['protected_modules']) != modules - affected:
            raise AgentRuntimeError('Optimization must protect every unaffected module')
        if result['regression_required'] != 'FULL' or not result['preserve_contract']:
            raise AgentRuntimeError('Optimization cannot bypass frozen contract or full regression')
        if result['evidence_manifest_sha256'] != context['synthesis_result']['manifest_sha256']:
            raise AgentRuntimeError('Optimization plan references a different candidate')
        if not result['recommended_change'].strip():
            raise AgentRuntimeError('Optimization requires a concrete conceptual change')
