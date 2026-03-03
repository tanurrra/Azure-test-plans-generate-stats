from __future__ import annotations

import logging
from datetime import date
from typing import List

from aggregation import SuiteAggregation, aggregate_by_component
from config import JiraConfig, JiraQueryConfig, load_config
from csv_writer import append_aggregations_to_csv
from jira_client import JiraClient


def _process_query(
    config: JiraConfig,
    client: JiraClient,
    query: JiraQueryConfig,
    plan_id: int,
) -> List[SuiteAggregation]:
    """Fetch Jira test issues for one query configuration and aggregate them.

    Args:
        config: Jira configuration instance.
        client: Jira API client.
        query: Query configuration specifying the JQL and destination CSV.
        plan_id: Numeric plan identifier written into aggregation rows.

    Returns:
        List of SuiteAggregation instances grouped by Jira component.
    """

    logging.info("Searching Jira with JQL: %s", query.jql)
    test_cases = client.search_test_cases(query.jql)
    logging.info("Fetched %s test issues for query '%s'.", len(test_cases), query.label)

    aggregations = aggregate_by_component(config, test_cases, plan_id=plan_id)
    logging.info(
        "Query '%s': aggregated into %s component rows.",
        query.label,
        len(aggregations),
    )
    return aggregations


def run() -> None:
    """Fetch Jira test statistics, aggregate by component, and write CSV output."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = load_config()

    logging.info("Starting Jira test statistics aggregation (Jira: %s).", config.jira_url)
    client = JiraClient(config)

    for plan_id, query in enumerate(config.queries):
        try:
            aggregations = _process_query(config, client, query, plan_id=plan_id)

            if aggregations:
                plan_names = {plan_id: query.label}
                logging.info(
                    "Appending %s rows to CSV at '%s'.",
                    len(aggregations),
                    query.csv_path,
                )
                append_aggregations_to_csv(
                    query.csv_path,
                    aggregations,
                    run_date=date.today(),
                    plan_names=plan_names,
                )
            else:
                logging.warning(
                    "No aggregations produced for query '%s'; CSV will not be updated.",
                    query.label,
                )
        except Exception:
            logging.exception("Failed to process query '%s'.", query.label)

    logging.info("Aggregation and CSV update completed successfully.")


if __name__ == "__main__":
    run()
