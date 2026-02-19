"""Unit tests for AuthzEngine JSONLogic evaluation behavior."""

from src.models.abac import ABACAction, ABACEffect, ABACPolicy, ABACPolicyRule
from src.services.authz.engine import AuthzEngine


def _build_policy(
    *,
    name: str,
    effect: ABACEffect,
    priority: int,
    resource_type: str,
    action: ABACAction,
    condition_expr: dict,
    field_mask: dict | None = None,
) -> ABACPolicy:
    policy = ABACPolicy(name=name, effect=effect, priority=priority, enabled=True)
    rule = ABACPolicyRule(
        policy_id="policy-1",
        resource_type=resource_type,
        action=action,
        condition_expr=condition_expr,
        field_mask=field_mask,
    )
    policy.rules = [rule]
    return policy


def test_authz_engine_deny_by_default_when_no_policy_matches() -> None:
    engine = AuthzEngine()

    decision = engine.evaluate_with_reason(
        subject={"owner_party_ids": ["party-1"], "manager_party_ids": []},
        resource={"resource_type": "asset", "owner_party_id": "party-1"},
        action="read",
        policies=[],
    )

    assert decision.allowed is False
    assert decision.reason_code == "deny_by_default"


def test_authz_engine_allows_owner_path_rule() -> None:
    engine = AuthzEngine()
    policy = _build_policy(
        name="owner-read",
        effect=ABACEffect.ALLOW,
        priority=10,
        resource_type="asset",
        action=ABACAction.READ,
        condition_expr={
            "in": [
                {"var": "resource.owner_party_id"},
                {"var": "subject.owner_party_ids"},
            ]
        },
    )

    decision = engine.evaluate_with_reason(
        subject={"owner_party_ids": ["party-owner"], "manager_party_ids": []},
        resource={"resource_type": "asset", "owner_party_id": "party-owner"},
        action="read",
        policies=[policy],
    )

    assert decision.allowed is True
    assert decision.reason_code == "policy_allow"


def test_authz_engine_allows_manager_path_rule() -> None:
    engine = AuthzEngine()
    policy = _build_policy(
        name="manager-update",
        effect=ABACEffect.ALLOW,
        priority=10,
        resource_type="asset",
        action=ABACAction.UPDATE,
        condition_expr={
            "in": [
                {"var": "resource.manager_party_id"},
                {"var": "subject.manager_party_ids"},
            ]
        },
    )

    decision = engine.evaluate_with_reason(
        subject={"owner_party_ids": [], "manager_party_ids": ["party-manager"]},
        resource={"resource_type": "asset", "manager_party_id": "party-manager"},
        action="update",
        policies=[policy],
    )

    assert decision.allowed is True
    assert decision.reason_code == "policy_allow"


def test_authz_engine_returns_field_mask_for_allow_rule() -> None:
    engine = AuthzEngine()
    field_mask = {"include": ["id", "name"]}
    policy = _build_policy(
        name="asset-read-mask",
        effect=ABACEffect.ALLOW,
        priority=10,
        resource_type="asset",
        action=ABACAction.READ,
        condition_expr={"==": [{"var": "action"}, "read"]},
        field_mask=field_mask,
    )

    decision = engine.evaluate_with_reason(
        subject={"owner_party_ids": [], "manager_party_ids": []},
        resource={"resource_type": "asset"},
        action="read",
        policies=[policy],
    )

    assert decision.allowed is True
    assert decision.field_mask == field_mask
