from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Set

from azure_devops import AzureDevOpsClient, TestCaseReference, TestSuite
from config import AzureConfig


@dataclass
class SuiteAggregation:
    """Aggregated statistics for a root test suite.

    Attributes:
        plan_id: Identifier of the test plan.
        root_suite_id: Identifier of the root test suite.
        root_suite_name: Name of the root test suite.
        total_cases: Total number of unique test cases under the root suite.
        automated: Number of test cases with Automation Status equal to Automated.
        planned: Number of test cases with Automation Status equal to Planned.
        not_automated: Number of test cases without automation or explicitly Not Automated.
    """

    plan_id: int
    root_suite_id: int
    root_suite_name: str
    total_cases: int
    automated: int
    planned: int
    not_automated: int


def _build_suite_children_index(suites: Iterable[TestSuite]) -> Dict[Optional[int], List[TestSuite]]:
    """Construct an index of suites by parent identifier.

    Args:
        suites: Iterable of TestSuite instances.

    Returns:
        Mapping from parent_id to list of child suites.
    """

    index: Dict[Optional[int], List[TestSuite]] = {}
    for suite in suites:
        index.setdefault(suite.parent_id, []).append(suite)
    return index


def _collect_descendant_suite_ids(
    root_suite: TestSuite,
    children_index: Mapping[Optional[int], List[TestSuite]],
) -> Set[int]:
    """Collect all descendant suite identifiers for a given root suite.

    Args:
        root_suite: Root TestSuite instance.
        children_index: Mapping from parent identifiers to child suites.

    Returns:
        Set of suite identifiers including the root suite itself.
    """

    result: Set[int] = {root_suite.id}
    stack: List[int] = [root_suite.id]
    while stack:
        current_id = stack.pop()
        for child in children_index.get(current_id, []):
            if child.id not in result:
                result.add(child.id)
                stack.append(child.id)
    return result


def _determine_root_suites(suites: Iterable[TestSuite]) -> List[TestSuite]:
    """Determine root suites as suites without a parent suite.

    Args:
        suites: Iterable of TestSuite instances.

    Returns:
        List of root-level TestSuite instances.
    """

    return [suite for suite in suites if suite.parent_id is None]


def aggregate_for_plan(config: AzureConfig, client: AzureDevOpsClient, plan_id: int) -> List[SuiteAggregation]:
    """Aggregate automation statistics for all root suites in a plan.

    Args:
        config: Azure DevOps configuration instance.
        client: Azure DevOps API client.
        plan_id: Identifier of the test plan.

    Returns:
        List of SuiteAggregation instances, one per root suite.
    """

    suites = client.list_suites_for_plan(plan_id)
    children_index = _build_suite_children_index(suites)
    absolute_roots = _determine_root_suites(suites)

    # Heuristic: If there is exactly one root suite (the Plan root),
    # but the user wants a breakdown by category (e.g. "Vendor", "Helpdesk"),
    # we likely want to aggregate by the *children* of that single root.
    if len(absolute_roots) == 1:
        single_root = absolute_roots[0]
        root_children = children_index.get(single_root.id, [])
        if root_children:
            reporting_roots = root_children
        else:
            reporting_roots = absolute_roots
    else:
        reporting_roots = absolute_roots

    aggregations: List[SuiteAggregation] = []

    for root_suite in reporting_roots:
        descendant_suite_ids = _collect_descendant_suite_ids(root_suite, children_index)
        test_case_refs: List[TestCaseReference] = []
        for suite_id in descendant_suite_ids:
            test_case_refs.extend(client.list_test_cases_for_suite(plan_id, suite_id))

        work_item_ids = {ref.work_item_id for ref in test_case_refs}
        automation_map = client.get_automation_status_by_work_item(
            work_item_ids=work_item_ids,
            field_reference_name=config.automation_status_field,
        )

        automated_count = 0
        planned_count = 0
        not_automated_count = 0

        for work_item_id in work_item_ids:
            raw_status = automation_map.get(work_item_id)
            if raw_status is None:
                not_automated_count += 1
                continue
            normalized = raw_status.strip().lower()
            if normalized == "automated":
                automated_count += 1
            elif normalized == "planned":
                planned_count += 1
            elif normalized == "not automated":
                not_automated_count += 1
            else:
                not_automated_count += 1

        aggregation = SuiteAggregation(
            plan_id=plan_id,
            root_suite_id=root_suite.id,
            root_suite_name=root_suite.name,
            total_cases=len(work_item_ids),
            automated=automated_count,
            planned=planned_count,
            not_automated=not_automated_count,
        )
        aggregations.append(aggregation)

    return aggregations
