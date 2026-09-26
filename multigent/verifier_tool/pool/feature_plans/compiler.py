"""Compile one resolved domain Feature Plan into three independent branches."""

from __future__ import annotations

from typing import Any, Mapping

from multigent.verifier_tool.pool.diagnostics import is_code_owned


_SELECTORS = {
    "assertion": "checker",
    "coverage": "sampler",
    "stimulus": "strategy",
}


def compile_feature_branch(
    feature_plan: Mapping[str, Any], branch: str
) -> dict[str, Any]:
    """Select a declarative branch without re-running domain matching."""

    if branch not in _SELECTORS:
        raise ValueError(f"Unknown feature-plan branch {branch!r}")
    selector = _SELECTORS[branch]
    entries: list[dict[str, Any]] = []
    for feature in feature_plan.get("features", []):
        if not isinstance(feature, Mapping):
            continue
        if not is_code_owned(feature):
            # Contract-required but blocked from automation: it stays in the plan
            # (with its obligations) and simply has no tool-owned checker,
            # sampler, or strategy to compile.
            continue
        config = feature.get(branch, {})
        if not isinstance(config, Mapping):
            raise ValueError(f"feature {feature.get('id')!r} has invalid {branch} branch")
        implementation = config.get(selector)
        if implementation in {None, ""}:
            continue
        entries.append(
            {
                "id": str(feature["id"]),
                "domain": str(feature_plan.get("domain", "")),
                "kind": str(feature.get("kind", "")),
                "scope": str(feature.get("scope", "")),
                "scope_name": str(feature.get("scope_name", "")),
                "bindings": dict(feature.get("bindings", {})),
                "implementation": str(implementation),
                "parameters": {
                    str(key): value
                    for key, value in config.items()
                    if key != selector
                },
            }
        )
    return {
        "schema_version": 1,
        "domain": str(feature_plan.get("domain", "")),
        "branch": branch,
        "entries": entries,
    }


def compile_assertion_feature_plan(
    feature_plan: Mapping[str, Any]
) -> dict[str, Any]:
    return compile_feature_branch(feature_plan, "assertion")


def compile_coverage_feature_plan(
    feature_plan: Mapping[str, Any]
) -> dict[str, Any]:
    return compile_feature_branch(feature_plan, "coverage")


def compile_stimulus_feature_plan(
    feature_plan: Mapping[str, Any]
) -> dict[str, Any]:
    return compile_feature_branch(feature_plan, "stimulus")


__all__ = [
    "compile_assertion_feature_plan",
    "compile_coverage_feature_plan",
    "compile_feature_branch",
    "compile_stimulus_feature_plan",
]
