from __future__ import annotations

import logging
from datetime import date
from typing import List

from aggregation import SuiteAggregation, aggregate_for_plan
from azure_devops import AzureDevOpsClient
from config import AzureConfig, load_config
from csv_writer import append_aggregations_to_csv


def run() -> None:
    """Execute aggregation for configured Azure DevOps test plans and write CSV output."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = load_config()

    logging.info("Starting aggregation for Azure DevOps project '%s'.", config.project)
    client = AzureDevOpsClient(config)

    all_aggregations: List[SuiteAggregation] = []
    plan_names: dict[int, str] = {}
    
    for plan_id in config.plan_ids:
        try:
            logging.info("Aggregating automation statistics for plan %s.", plan_id)
            plan_name = client.get_plan_name(plan_id)
            plan_names[plan_id] = plan_name
            logging.info("Plan %s name: '%s'.", plan_id, plan_name)
            plan_aggregations = aggregate_for_plan(config, client, plan_id)
            logging.info("Plan %s: produced %s root suite rows.", plan_id, len(plan_aggregations))
            all_aggregations.extend(plan_aggregations)
        except Exception:
            logging.exception("Failed to aggregate statistics for plan %s.", plan_id)

    if not all_aggregations:
        logging.warning("No aggregations produced; CSV file will not be updated.")
        return

    logging.info("Appending %s rows to CSV at '%s'.", len(all_aggregations), config.csv_path)
    append_aggregations_to_csv(config.csv_path, all_aggregations, run_date=date.today(), plan_names=plan_names)
    logging.info("Aggregation and CSV update completed successfully.")


if __name__ == "__main__":
    run()
