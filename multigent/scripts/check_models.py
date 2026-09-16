"""Small real API compatibility checks. No hardware workflow is launched."""
import argparse
import json
import time
from pathlib import Path
from openai import OpenAI
from multigent.api_config import resolve_base_url
from multigent.models import MODELS


def check(client, model):
    started = time.monotonic()
    try:
        response = client.responses.create(
            model=model, store=False, reasoning={'effort': 'low'},
            input='A box has 7 blue marbles and 5 red marbles. Return their total and a short friendly sentence about marbles.',
            text={'verbosity': 'low', 'format': {
                'type': 'json_schema', 'name': 'model_smoke', 'strict': True,
                'schema': {'type': 'object', 'properties': {
                    'total': {'type': 'integer'}, 'sentence': {'type': 'string'}},
                    'required': ['total', 'sentence'], 'additionalProperties': False}}},
            max_output_tokens=2048)
        output = json.loads(response.output_text)
        if response.status != 'completed' or output.get('total') != 12 or not output.get('sentence'):
            raise ValueError('Response failed the structured-output check')
        return {'model': model, 'status': 'PASS', 'returned_model': response.model,
                'output': output, 'seconds': round(time.monotonic()-started, 2),
                'usage': response.usage.model_dump() if response.usage else None}
    except Exception as exc:
        # Record API messages, never client configuration or credentials.
        return {'model': model, 'status': 'FAIL', 'error': str(exc),
                'seconds': round(time.monotonic()-started, 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    client = OpenAI(base_url=resolve_base_url(), timeout=120, max_retries=0)
    results = []
    for model in MODELS:
        result = check(client, model)
        results.append(result)
        print(json.dumps(result), flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2)+'\n')
    raise SystemExit(0 if all(r['status']=='PASS' for r in results) else 2)


if __name__ == '__main__':
    main()
