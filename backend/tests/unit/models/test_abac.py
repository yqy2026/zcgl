"""ABAC model unit tests."""

from src.models.abac import ABACPolicy, ABACPolicyRule, ABACRolePolicy


def test_abac_policy_creation() -> None:
    policy = ABACPolicy(name="asset_read", effect="allow", priority=10)

    assert policy.name == "asset_read"
    assert policy.effect == "allow"
    assert policy.priority == 10


def test_abac_policy_rule_creation() -> None:
    rule = ABACPolicyRule(
        policy_id="policy-1",
        resource_type="asset",
        action="read",
        condition_expr={"==": [{"var": "subject.is_admin"}, True]},
    )

    assert rule.policy_id == "policy-1"
    assert rule.resource_type == "asset"
    assert rule.action == "read"


def test_abac_role_policy_creation() -> None:
    role_policy = ABACRolePolicy(role_id="role-1", policy_id="policy-1")

    assert role_policy.role_id == "role-1"
    assert role_policy.policy_id == "policy-1"


def test_abac_role_policy_unique_constraint_exists() -> None:
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in ABACRolePolicy.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("role_id", "policy_id") in unique_columns
