"""Append-only, observational progress events; routing remains in LangGraph."""
import json
from datetime import datetime, timezone
from pathlib import Path


def emit(root, stage, phase, **details):
    path = Path(root) / 'state' / 'events.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {'stage': stage, 'phase': phase,
             'time': datetime.now(timezone.utc).isoformat(), **details}
    with path.open('a') as stream:
        stream.write(json.dumps(event) + '\n')
