"""Aggregation of Jira test case statistics grouped by super-group.

Tests are mapped into one of three super-groups based on their Jira components:
- CloudiQ: Cloud-iQx, Adobe, Aws, Control Panel
- Operations: Operations Center, Phoenix, Product and Prices (if not in CloudiQ)
- Everything else: All other components
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from config import JiraConfig
from jira_client import JiraClient, JiraTestCase


_UNASSIGNED_COMPONENT = "Unassigned"

# Super-group component mappings
_CLOUDIQ_COMPONENTS = {"cloud-iqx", "adobe", "aws", "control panel"}
_OPERATIONS_COMPONENTS = {"operations center", "phoenix", "product and prices"}


def _map_to_super_group(components: List[str]) -> str:
    """Map a list of Jira components to one of three super-groups.
    
    Mapping rules (priority order):
    1. CloudiQ: Cloud-iQx, Adobe, Aws, Control Panel
    2. Operations: Operations Center, Phoenix, Product and Prices (if not in CloudiQ)
    3. Everything else: All other components
    
    Args:
        components: List of Jira component names.
        
    Returns:
        One of 'CloudiQ', 'Operations', or 'Everything else'.
    """
    # Normalize component names for case-insensitive matching
    normalized_components = {c.strip().lower() for c in components}
    
    # Check CloudiQ first (highest priority)
    if normalized_components & _CLOUDIQ_COMPONENTS:
        return "CloudiQ"
    
    # Check Operations second
    if normalized_components & _OPERATIONS_COMPONENTS:
        return "Operations"
    
    # Everything else
    return "Everything else"


@dataclass
class SuiteAggregation:
    """Aggregated automation statistics for a single super-group.

    The field names intentionally mirror the original Azure DevOps terminology so
    that the CSV writer and chart-generation modules require no changes.

    Attributes:
        plan_id: Numeric identifier for the query/plan bucket (0 by default).
        root_suite_id: Stable numeric identifier derived from the super-group name.
        root_suite_name: Super-group name (CloudiQ, Operations, or Everything else).
        total_cases: Total number of unique test issues in this super-group.
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
    """Aggregate automation statistics grouped by super-group.

    Tests are assigned to exactly one super-group based on their components:
    - CloudiQ: Cloud-iQx, Adobe, Aws, Control Panel
    - Operations: Operations Center, Phoenix, Product and Prices (if not in CloudiQ)
    - Everything else: All other components

    Args:
        config: Jira configuration instance.
        test_cases: List of JiraTestCase instances to aggregate.
        plan_id: Numeric plan identifier written to the CSV (default: 0).

    Returns:
        List of SuiteAggregation instances sorted alphabetically by super-group name.
    """

    # buckets: super_group_name -> {automated, planned, not_automated, total}
    buckets: Dict[str, Dict[str, int]] = {}

    excluded_lower = {s.strip().lower() for s in config.excluded_statuses}

    for tc in test_cases:
        # Skip issues whose status is in the excluded list
        if tc.automation_status and tc.automation_status.strip().lower() in excluded_lower:
            continue

        components = tc.components if tc.components else [_UNASSIGNED_COMPONENT]
        classification = _classify_status(tc.automation_status, config)
        
        # Determine which super-group this test belongs to
        super_group = _map_to_super_group(components)

        if super_group not in buckets:
            buckets[super_group] = {"automated": 0, "planned": 0, "not_automated": 0, "total": 0}
        buckets[super_group][classification] += 1
        buckets[super_group]["total"] += 1

    aggregations: List[SuiteAggregation] = []
    for super_group_name in sorted(buckets):
        counts = buckets[super_group_name]
        aggregations.append(
            SuiteAggregation(
                plan_id=plan_id,
                root_suite_id=_stable_id(super_group_name),
                root_suite_name=super_group_name,
                total_cases=counts["total"],
                automated=counts["automated"],
                planned=counts["planned"],
                not_automated=counts["not_automated"],
            )
        )

    return aggregations
