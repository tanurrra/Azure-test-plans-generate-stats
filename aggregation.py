"""Aggregation of Jira test case statistics grouped by component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from config import JiraConfig
from jira_client import JiraClient, JiraTestCase


_UNASSIGNED_COMPONENT = "Unassigned"


@dataclass
class SuiteAggregation:
    """Aggregated automation statistics for a single Jira component.

    The field names intentionally mirror the original Azure DevOps terminology so
    that the CSV writer and chart-generation modules require no changes.

    Attributes:
        plan_id: Numeric identifier for the query/plan bucket (0 by default).
        root_suite_id: Stable numeric identifier derived from the component name.
        root_suite_name: Jira component name (or 'Unassigned' for issues with no component).
        total_cases: Total number of unique test issues in this component.
        automated: Issues whose automation status matches the configured Automated value.
        planned: Issues whose automation status matches the configured Planned value.
        not_automated: Remaining issues (no status set, or any other value).
    """

    plan_id: int
    root_suite_id: int
    root_suite_name: str
    total_cases: int
    automated: int
    planned: int
    not_automated: int


def _stable_id(name: str) -> int:
    """Return a stable, positive integer identifier derived from a string.

    The value is consistent across runs but is NOT guaranteed to be unique for
    all possible strings; collisions are acceptable here as the ID is only used
    for the CSV and is not a database key.

    Args:
        name: Source string.

    Returns:
        Non-negative integer derived from the string.
    """

    return sum(idx * ord(ch) for idx, ch in enumerate(name, start=1)) % 1_000_000


def _classify_status(raw_status: str | None, config: JiraConfig) -> str:
    """Map a raw automation status value to 'automated', 'planned', or 'not_automated'.

    Args:
        raw_status: Raw field value from Jira, or None.
        config: Jira configuration providing the expected value strings.

    Returns:
        One of 'automated', 'planned', or 'not_automated'.
    """

    if not raw_status:
        return "not_automated"
    normalized = raw_status.strip().lower()
    if normalized == config.automated_value.strip().lower():
        return "automated"
    if normalized == config.planned_value.strip().lower():
        return "planned"
    return "not_automated"


def aggregate_by_component(
    config: JiraConfig,
    test_cases: List[JiraTestCase],
    plan_id: int = 0,
) -> List[SuiteAggregation]:
    """Aggregate automation statistics grouped by Jira component.

    Issues that belong to multiple components are counted once in each component.
    Issues with no component are grouped under 'Unassigned'.

    Args:
        config: Jira configuration instance.
        test_cases: List of JiraTestCase instances to aggregate.
        plan_id: Numeric plan identifier written to the CSV (default: 0).

    Returns:
        List of SuiteAggregation instances sorted alphabetically by component name.
    """

    # buckets: component_name -> {automated, planned, not_automated, total}
    buckets: Dict[str, Dict[str, int]] = {}

    excluded_lower = {s.strip().lower() for s in config.excluded_statuses}

    for tc in test_cases:
        # Skip issues whose status is in the excluded list
        if tc.automation_status and tc.automation_status.strip().lower() in excluded_lower:
            continue

        components = tc.components if tc.components else [_UNASSIGNED_COMPONENT]
        classification = _classify_status(tc.automation_status, config)

        for component in components:
            if component not in buckets:
                buckets[component] = {"automated": 0, "planned": 0, "not_automated": 0, "total": 0}
            buckets[component][classification] += 1
            buckets[component]["total"] += 1

    aggregations: List[SuiteAggregation] = []
    for component_name in sorted(buckets):
        counts = buckets[component_name]
        aggregations.append(
            SuiteAggregation(
                plan_id=plan_id,
                root_suite_id=_stable_id(component_name),
                root_suite_name=component_name,
                total_cases=counts["total"],
                automated=counts["automated"],
                planned=counts["planned"],
                not_automated=counts["not_automated"],
            )
        )

    return aggregations
