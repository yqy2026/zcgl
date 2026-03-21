"""ABAC engine backed by JSONLogic expressions."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from jsonlogic import JSONLogicExpression
from jsonlogic.evaluation import evaluate as jsonlogic_evaluate
from jsonlogic.operators import operator_registry

from ...models.abac import ABACEffect, ABACPolicy, ABACPolicyRule

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthzDecision:
    """Authorization decision with minimal diagnostics."""

    allowed: bool
    reason_code: str
    matched_policy_id: str | None = None
    matched_rule_id: str | None = None
    field_mask: dict[str, Any] | None = None


class AuthzEngine:
    """Evaluate ABAC policies against subject/resource/action context."""

    def evaluate(
        self,
        *,
        subject: Mapping[str, Any],
        resource: Mapping[str, Any],
        action: str,
        policies: Sequence[ABACPolicy],
    ) -> bool:
        """Boolean compatibility wrapper."""
        return self.evaluate_with_reason(
            subject=subject,
            resource=resource,
            action=action,
            policies=policies,
        ).allowed

    def evaluate_with_reason(
        self,
        *,
        subject: Mapping[str, Any],
        resource: Mapping[str, Any],
        action: str,
        policies: Sequence[ABACPolicy],
    ) -> AuthzDecision:
        resource_type = str(resource.get("resource_type") or "")
        if resource_type.strip() == "":
            return AuthzDecision(
                allowed=False,
                reason_code="missing_resource_type",
            )

        if not policies:
            return AuthzDecision(
                allowed=False,
                reason_code="deny_by_default",
            )

        eval_data = {
            "subject": dict(subject),
            "resource": dict(resource),
            "action": action,
        }

        sorted_policies = sorted(
            policies,
            key=lambda policy: (
                int(getattr(policy, "priority", 100)),
                0 if self._is_deny(policy) else 1,
            ),
        )

        for policy in sorted_policies:
            if not bool(getattr(policy, "enabled", True)):
                continue

            rules = self._get_policy_rules(policy)
            for rule in rules:
                if str(rule.resource_type) != resource_type:
                    continue
                if str(rule.action) != action:
                    continue

                if not self._evaluate_condition(rule.condition_expr, eval_data):
                    continue

                matched_policy_id = self._safe_id(getattr(policy, "id", None))
                matched_rule_id = self._safe_id(getattr(rule, "id", None))
                if self._is_deny(policy):
                    return AuthzDecision(
                        allowed=False,
                        reason_code="policy_deny",
                        matched_policy_id=matched_policy_id,
                        matched_rule_id=matched_rule_id,
                    )

                return AuthzDecision(
                    allowed=True,
                    reason_code="policy_allow",
                    matched_policy_id=matched_policy_id,
                    matched_rule_id=matched_rule_id,
                    field_mask=self._normalize_field_mask(
                        getattr(rule, "field_mask", None)
                    ),
                )

        return AuthzDecision(
            allowed=False,
            reason_code="deny_by_default",
        )

    @staticmethod
    def _get_policy_rules(policy: ABACPolicy) -> list[ABACPolicyRule]:
        raw_rules = getattr(policy, "rules", [])
        return [rule for rule in raw_rules if isinstance(rule, ABACPolicyRule)]

    @staticmethod
    def _is_deny(policy: ABACPolicy) -> bool:
        return str(getattr(policy, "effect", "allow")) == ABACEffect.DENY.value

    @staticmethod
    def _normalize_field_mask(raw_mask: Any) -> dict[str, Any] | None:
        if isinstance(raw_mask, dict):
            return raw_mask
        return None

    @staticmethod
    def _safe_id(raw_id: Any) -> str | None:
        if raw_id is None:
            return None
        text = str(raw_id).strip()
        return text if text != "" else None

    def _evaluate_condition(
        self,
        condition_expr: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        if not isinstance(condition_expr, dict):
            return False

        try:
            expression = JSONLogicExpression.from_json(condition_expr)
            operator_tree = expression.as_operator_tree(operator_registry)
            return bool(jsonlogic_evaluate(operator_tree, data=data, data_schema=None))
        except Exception:
            logger.debug("JSONLogic runtime fallback engaged", exc_info=True)
            try:
                return bool(self._fallback_eval(condition_expr, data))
            except Exception:
                logger.warning("JSONLogic fallback evaluation failed", exc_info=True)
                return False

    def _fallback_eval(self, expr: Any, data: dict[str, Any]) -> Any:
        if isinstance(expr, list):
            return [self._fallback_eval(item, data) for item in expr]

        if not isinstance(expr, dict):
            return expr

        if len(expr) != 1:
            return False

        operator, raw_args = next(iter(expr.items()))
        args = raw_args if isinstance(raw_args, list) else [raw_args]

        if operator == "var":
            path = self._fallback_eval(args[0], data) if args else None
            default = self._fallback_eval(args[1], data) if len(args) > 1 else None
            return self._resolve_var(path, data, default)

        if operator == "==":
            if len(args) < 2:
                return False
            return self._fallback_eval(args[0], data) == self._fallback_eval(
                args[1], data
            )

        if operator == "!=":
            if len(args) < 2:
                return False
            return self._fallback_eval(args[0], data) != self._fallback_eval(
                args[1], data
            )

        if operator == ">":
            if len(args) < 2:
                return False
            return self._fallback_eval(args[0], data) > self._fallback_eval(
                args[1], data
            )

        if operator == ">=":
            if len(args) < 2:
                return False
            return self._fallback_eval(args[0], data) >= self._fallback_eval(
                args[1], data
            )

        if operator == "<":
            if len(args) < 2:
                return False
            return self._fallback_eval(args[0], data) < self._fallback_eval(
                args[1], data
            )

        if operator == "<=":
            if len(args) < 2:
                return False
            return self._fallback_eval(args[0], data) <= self._fallback_eval(
                args[1], data
            )

        if operator == "and":
            return all(bool(self._fallback_eval(arg, data)) for arg in args)

        if operator == "or":
            return any(bool(self._fallback_eval(arg, data)) for arg in args)

        if operator == "!":
            if not args:
                return True
            return not bool(self._fallback_eval(args[0], data))

        if operator == "!!":
            if not args:
                return False
            return bool(self._fallback_eval(args[0], data))

        if operator == "in":
            if len(args) < 2:
                return False
            needle = self._fallback_eval(args[0], data)
            haystack = self._fallback_eval(args[1], data)
            if isinstance(haystack, str):
                return str(needle) in haystack
            if isinstance(haystack, Sequence):
                return needle in haystack
            return False

        if operator == "if":
            index = 0
            while index + 1 < len(args):
                if bool(self._fallback_eval(args[index], data)):
                    return self._fallback_eval(args[index + 1], data)
                index += 2
            if len(args) % 2 == 1:
                return self._fallback_eval(args[-1], data)
            return False

        if operator == "+":
            return sum(self._to_number(self._fallback_eval(arg, data)) for arg in args)

        if operator == "-":
            if not args:
                return 0
            first = self._to_number(self._fallback_eval(args[0], data))
            if len(args) == 1:
                return -first
            return first - self._to_number(self._fallback_eval(args[1], data))

        if operator == "*":
            result = 1.0
            for arg in args:
                result *= self._to_number(self._fallback_eval(arg, data))
            return result

        if operator == "/":
            if len(args) < 2:
                return False
            denominator = self._to_number(self._fallback_eval(args[1], data))
            if denominator == 0:
                return False
            return self._to_number(self._fallback_eval(args[0], data)) / denominator

        if operator == "%":
            if len(args) < 2:
                return False
            denominator = self._to_number(self._fallback_eval(args[1], data))
            if denominator == 0:
                return False
            return self._to_number(self._fallback_eval(args[0], data)) % denominator

        return False

    @staticmethod
    def _resolve_var(path: Any, data: dict[str, Any], default: Any) -> Any:
        if not isinstance(path, str) or path.strip() == "":
            return default

        node: Any = data
        for segment in path.split("."):
            if isinstance(node, dict):
                if segment not in node:
                    return default
                node = node[segment]
                continue

            if isinstance(node, list):
                if not segment.isdigit():
                    return default
                index = int(segment)
                if index < 0 or index >= len(node):
                    return default
                node = node[index]
                continue

            return default

        return node

    @staticmethod
    def _to_number(value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0


__all__ = ["AuthzDecision", "AuthzEngine"]
