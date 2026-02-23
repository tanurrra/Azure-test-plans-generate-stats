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

    regression_aggregations: List[SuiteAggregation] = []
    automations_aggregations: List[SuiteAggregation] = []
    plan_names: dict[int, str] = {}
    
    for plan_id in config.plan_ids:
        try:
            logging.info("Aggregating automation statistics for plan %s.", plan_id)
            plan_name = client.get_plan_name(plan_id)
            plan_names[plan_id] = plan_name
            logging.info("Plan %s name: '%s'.", plan_id, plan_name)
            plan_aggregations = aggregate_for_plan(config, client, plan_id)
            logging.info("Plan %s: produced %s root suite rows.", plan_id, len(plan_aggregations))
            
            # Route aggregations to appropriate list based on plan type
            if plan_id == config.regression_plan_id:
                regression_aggregations.extend(plan_aggregations)
            else:
                automations_aggregations.extend(plan_aggregations)
        except Exception:
            logging.exception("Failed to aggregate statistics for plan %s.", plan_id)

    # Write regression plan data to main CSV file
    if regression_aggregations:
        logging.info("Appending %s rows to regression CSV at '%s'.", len(regression_aggregations), config.csv_path)
        append_aggregations_to_csv(config.csv_path, regression_aggregations, run_date=date.today(), plan_names=plan_names)
    else:
        logging.warning("No regression aggregations produced; regression CSV file will not be updated.")

    # Write automations plan data to separate CSV file
    if automations_aggregations:
        logging.info("Appending %s rows to automations CSV at '%s'.", len(automations_aggregations), config.automations_csv_path)
        append_aggregations_to_csv(config.automations_csv_path, automations_aggregations, run_date=date.today(), plan_names=plan_names)
    else:
        logging.warning("No automations aggregations produced; automations CSV file will not be updated.")

    logging.info("Aggregation and CSV update completed successfully.")


if __name__ == "__main__":
    run()
