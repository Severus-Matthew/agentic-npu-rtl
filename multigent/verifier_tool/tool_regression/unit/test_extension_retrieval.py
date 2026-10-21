from __future__ import annotations

import yaml

from multigent.verifier_tool.extensions import (
    render_requested_extension_worklist,
    retrieve_extension_analogues,
)


def _request(identity: str, domain: str, summary: str, *, scope: str) -> dict:
    return {
        "id": identity,
        "domain": domain,
        "feature_name": identity.rsplit(".", 1)[-1],
        "target": {"scope": scope, "name": "target"},
        "semantics": {
            "summary": summary,
            "trigger": "A real DUT event occurs.",
            "required_behavior": [summary],
            "end_condition": "The matching terminal event is observed.",
            "forbidden_behavior": ["Credit expected values as observed evidence."],
        },
        "reason": "Absent from the current pool.",
        "required_observations": [
            {"name": "cycle_trace", "kind": "event", "description": "DUT trace"}
        ],
        "related_builtin_features": [],
    }


def test_retrieval_is_domain_filtered_and_structurally_ranked() -> None:
    architecture = {
        "verification_extensions": [
            _request(
                "protocol.obi_delayed_response",
                "protocol",
                "A split request grant is followed by a delayed one-cycle response pulse after wait states.",
                scope="interface",
            ),
            _request(
                "lifecycle.sticky_completion",
                "lifecycle",
                "Completion remains active until reset and then recovers.",
                scope="operation",
            ),
            _request(
                "operation.novel_activation",
                "operation",
                "Apply a mathematical activation after matrix accumulation.",
                scope="operation",
            ),
        ]
    }
    retrieved = retrieve_extension_analogues(architecture, top_k=4)
    assert all(
        item["domain"] == identity.split(".", 1)[0]
        for identity, items in retrieved.items()
        for item in items
    )
    protocol_ids = {item["id"] for item in retrieved["protocol.obi_delayed_response"]}
    assert protocol_ids & {
        "protocol.handshake_states",
        "protocol.handshake_arrival_order",
        "protocol.stall_stability",
    }
    lifecycle_ids = {
        item["id"] for item in retrieved["lifecycle.sticky_completion"]
    }
    assert any("completion" in identity or "reset" in identity for identity in lifecycle_ids)
    operation_ids = {item["id"] for item in retrieved["operation.novel_activation"]}
    assert "operation.matrix_multiply.activation" in operation_ids


def test_worklist_embeds_analogues_as_non_authoritative_references() -> None:
    request = _request(
        "protocol.new_wait_phase",
        "protocol",
        "Hold request content stable over multiple wait cycles.",
        scope="interface",
    )
    architecture = {"verification_extensions": [request], "operations": []}
    rendered = yaml.safe_load(render_requested_extension_worklist(architecture, {}))
    assert rendered[0]["retrieved_analogues"]
    assert all(
        item["usage"] == "analogy_only_preserve_frozen_request_semantics"
        for item in rendered[0]["retrieved_analogues"]
    )
    assert "never fabricate" in rendered[0]["retrieval_rule"]
