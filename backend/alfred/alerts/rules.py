"""Custom alert grouping rules DSL and engine.

Provides a YAML-based configuration system for per-service grouping
rules with dynamic evaluation.
"""

import operator
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import redis
import yaml

from alfred.core.protocols import AlertProtocol

@dataclass
class RuleCondition:
    """Single condition in a rule"""

    field: str
    operator: str
    value: Any

    def evaluate(self, alert: AlertProtocol) -> bool:
        """Evaluate condition against an alert"""
        # Get field value from alert
        if "." in self.field:
            # Nested field access
            parts = self.field.split(".")
            value = alert
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
        else:
            value = getattr(alert, self.field, None)

        # Apply operator
        ops = {
            "eq": operator.eq,
            "==": operator.eq,
            "ne": operator.ne,
            "!=": operator.ne,
            "gt": operator.gt,
            ">": operator.gt,
            "gte": operator.ge,
            ">=": operator.ge,
            "lt": operator.lt,
            "<": operator.lt,
            "lte": operator.le,
            "<=": operator.le,
            "in": lambda a, b: a in b,
            "not_in": lambda a, b: a not in b,
            "contains": lambda a, b: b in str(a),
            "matches": lambda a, b: bool(re.match(b, str(a))),
        }

        op = ops.get(self.operator)
        if not op:
            raise ValueError(f"Unknown operator: {self.operator}")

        try:
            return op(value, self.value)
        except Exception:
            return False

@dataclass
class GroupingRule:
    """Custom grouping rule"""

    name: str
    priority: int
    conditions: List[RuleCondition]
    logic: str  # 'and' or 'or'
    grouping_keys: List[str]
    similarity_threshold: float
    time_window: int  # seconds

    def matches(self, alert: AlertProtocol) -> bool:
        """Check if alert matches this rule"""
        if self.logic == "and":
            return all(cond.evaluate(alert) for cond in self.conditions)
        else:  # 'or'
            return any(cond.evaluate(alert) for cond in self.conditions)

    def get_group_key(self, alert: AlertProtocol) -> str:
        """Generate group key for alert based on this rule"""
        key_parts = []

        for key in self.grouping_keys:
            if "." in key:
                # Nested field access
                parts = key.split(".")
                value = alert
                for part in parts:
                    if hasattr(value, part):
                        value = getattr(value, part)
                    elif isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = "unknown"
                        break
                key_parts.append(str(value))
            else:
                value = getattr(alert, key, "unknown")
                key_parts.append(str(value))

        return ":".join(key_parts)

class RulesEngine:
    """Engine for evaluating custom grouping rules"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the rules engine.

        Args:
            redis_client: Redis client for caching rules

        """
        self.rules: Dict[str, List[GroupingRule]] = {}
        self.redis = redis_client
        self.default_similarity_threshold = 0.7
        self.default_time_window = 900  # 15 minutes

    def load_rules_from_yaml(self, yaml_content: str):
        """Load rules from YAML configuration.

        Example YAML:
        ```yaml
        services:
          api-gateway:
            rules:
              - name: "High CPU alerts"
                priority: 10
                conditions:
                  - field: name
                    operator: contains
                    value: "CPU"
                  - field: severity
                    operator: in
                    value: ["critical", "warning"]
                logic: and
                grouping_keys: ["service", "environment", "instance"]
                similarity_threshold: 0.8
                time_window: 600
        ```
        """
        config = yaml.safe_load(yaml_content)

        for service, service_config in config.get("services", {}).items():
            self.rules[service] = []

            for rule_config in service_config.get("rules", []):
                conditions = []
                for cond in rule_config.get("conditions", []):
                    conditions.append(
                        RuleCondition(
                            field=cond["field"],
                            operator=cond["operator"],
                            value=cond["value"],
                        )
                    )

                rule = GroupingRule(
                    name=rule_config["name"],
                    priority=rule_config.get("priority", 0),
                    conditions=conditions,
                    logic=rule_config.get("logic", "and"),
                    grouping_keys=rule_config.get("grouping_keys", []),
                    similarity_threshold=rule_config.get(
                        "similarity_threshold", self.default_similarity_threshold
                    ),
                    time_window=rule_config.get("time_window", self.default_time_window),
                )

                self.rules[service].append(rule)

            # Sort rules by priority (highest first)
            self.rules[service].sort(key=lambda r: r.priority, reverse=True)

    def load_rules_from_file(self, filepath: str):
        """Load rules from YAML file"""
        with open(filepath, "r") as f:
            self.load_rules_from_yaml(f.read())

    def find_matching_rule(self, alert: AlertProtocol) -> Optional[GroupingRule]:
        """Find the highest priority matching rule for an alert"""
        service = alert.labels.get("service", "default")
        service_rules = self.rules.get(service, []) + self.rules.get("default", [])

        for rule in service_rules:
            if rule.matches(alert):
                return rule

        return None

    def get_group_key(self, alert: AlertProtocol) -> str:
        """Get group key for alert based on matching rule"""
        rule = self.find_matching_rule(alert)

        if rule:
            return rule.get_group_key(alert)
        else:
            # Default grouping
            return f"{alert.labels.get('service', 'unknown')}:{alert.name}:{alert.severity}"

    def get_similarity_threshold(self, alert: AlertProtocol) -> float:
        """Get similarity threshold for alert based on matching rule"""
        rule = self.find_matching_rule(alert)
        return rule.similarity_threshold if rule else self.default_similarity_threshold

    def get_time_window(self, alert: AlertProtocol) -> int:
        """Get time window for alert based on matching rule"""
        rule = self.find_matching_rule(alert)
        return rule.time_window if rule else self.default_time_window

    def evaluate_alert(self, alert: AlertProtocol) -> Dict[str, Any]:
        """Evaluate all aspects of an alert against rules"""
        rule = self.find_matching_rule(alert)

        return {
            "matching_rule": rule.name if rule else None,
            "group_key": self.get_group_key(alert),
            "similarity_threshold": self.get_similarity_threshold(alert),
            "time_window": self.get_time_window(alert),
            "rule_priority": rule.priority if rule else 0,
        }

    def validate_rules(self) -> Dict[str, List[str]]:
        """Validate all loaded rules and return any errors"""
        errors = {}

        for service, service_rules in self.rules.items():
            service_errors = []

            for rule in service_rules:
                # Check for duplicate rule names
                rule_names = [r.name for r in service_rules]
                if rule_names.count(rule.name) > 1:
                    service_errors.append(f"Duplicate rule name: {rule.name}")

                # Check for invalid operators
                for condition in rule.conditions:
                    valid_ops = [
                        "eq",
                        "==",
                        "ne",
                        "!=",
                        "gt",
                        ">",
                        "gte",
                        ">=",
                        "lt",
                        "<",
                        "lte",
                        "<=",
                        "in",
                        "not_in",
                        "contains",
                        "matches",
                    ]
                    if condition.operator not in valid_ops:
                        service_errors.append(
                            f"Invalid operator in rule {rule.name}: {condition.operator}"
                        )

                # Check for empty grouping keys
                if not rule.grouping_keys:
                    service_errors.append(f"No grouping keys in rule {rule.name}")

            if service_errors:
                errors[service] = service_errors

        return errors

    def get_rules_summary(self) -> Dict[str, Dict]:
        """Get summary of all loaded rules"""
        summary = {}

        for service, service_rules in self.rules.items():
            summary[service] = {
                "rule_count": len(service_rules),
                "rules": [
                    {
                        "name": rule.name,
                        "priority": rule.priority,
                        "conditions": len(rule.conditions),
                        "logic": rule.logic,
                        "grouping_keys": rule.grouping_keys,
                    }
                    for rule in service_rules
                ],
            }

        return summary
