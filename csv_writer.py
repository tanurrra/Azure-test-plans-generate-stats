from __future__ import annotations

import csv
import os
from dataclasses import asdict
from datetime import date
from typing import Iterable, List, Mapping

from aggregation import SuiteAggregation


CSV_COLUMNS: List[str] = [
    "date",
    "plan_id",
    "plan_name",
    "root_suite_id",
    "root_suite_name",
    "total_cases",
    "automated",
    "planned",
    "not_automated",
]


def append_aggregations_to_csv(
    path: str,
    aggregations: Iterable[SuiteAggregation],
    run_date: date | None = None,
    plan_names: dict[int, str] | None = None,
) -> None:
    """Append aggregated results to a CSV file.

    Args:
        path: Path to the CSV file.
        aggregations: Iterable of SuiteAggregation instances to persist.
        run_date: Optional date to record; defaults to today's date.
        plan_names: Optional mapping of plan ID to plan name.
    """

    if run_date is None:
        run_date = date.today()
    if plan_names is None:
        plan_names = {}

    file_exists = os.path.exists(path)
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    with open(path, mode="a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for aggregation in aggregations:
            row = _aggregation_to_row(aggregation, run_date, plan_names)
            writer.writerow(row)


def _aggregation_to_row(aggregation: SuiteAggregation, run_date: date, plan_names: dict[int, str]) -> Mapping[str, object]:
    """Convert a SuiteAggregation instance into a CSV row mapping.

    Args:
        aggregation: Aggregated statistics for a root suite.
        run_date: Date associated with the aggregation run.
        plan_names: Mapping of plan ID to plan name.

    Returns:
        Mapping from column name to value suitable for CSV writing.
    """

    return {
        "date": run_date.isoformat(),
        "plan_id": aggregation.plan_id,
        "plan_name": plan_names.get(aggregation.plan_id, f"Plan {aggregation.plan_id}"),
        "root_suite_id": aggregation.root_suite_id,
        "root_suite_name": aggregation.root_suite_name,
        "total_cases": aggregation.total_cases,
        "automated": aggregation.automated,
        "planned": aggregation.planned,
        "not_automated": aggregation.not_automated,
    }

