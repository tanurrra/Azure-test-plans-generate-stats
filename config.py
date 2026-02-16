from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


@dataclass
class AzureConfig:
    """Azure DevOps connection and reporting configuration.

    Attributes:
        organization_url: Base Azure DevOps organization URL.
        project: Azure DevOps project name.
        personal_access_token: Personal Access Token with required permissions.
        regression_plan_id: Identifier of the regression test plan.
        release_plan_id: Identifier of the release test plan.
        automation_status_field: Reference name of the Automation Status field.
        csv_path: Absolute or relative path to the output CSV file.
    """

    organization_url: str
    project: str
    personal_access_token: str
    regression_plan_id: int
    release_plan_id: int
    automation_status_field: str
    csv_path: str

    @property
    def plan_ids(self) -> List[int]:
        """Return all configured test plan identifiers.

        Returns:
            List of unique test plan identifiers.
        """

        return list({self.regression_plan_id, self.release_plan_id})


def _require_env(name: str) -> str:
    """Retrieve a required environment variable.

    Args:
        name: Name of the environment variable.

    Returns:
        Value of the environment variable.

    Raises:
        RuntimeError: If the environment variable is not set or empty.
    """

    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Environment variable {name} is required and must not be empty.")
    return value


def load_config() -> AzureConfig:
    """Load Azure DevOps configuration from environment variables.

    Environment variables:
        ADO_ORG: Azure DevOps organization host, for example 'softwareone-pc'.
        ADO_PROJECT: Azure DevOps project name.
        ADO_PAT: Azure DevOps Personal Access Token.
        ADO_PLAN_ID_REGRESSION: Identifier of the regression test plan.
        ADO_PLAN_ID_RELEASE: Identifier of the release test plan.
        ADO_AUTOMATION_STATUS_FIELD: Reference name of the Automation Status field.
        ADO_AUTOMATION_CSV_PATH: Path to the CSV file for storing aggregated results.

    Returns:
        Loaded AzureConfig instance.
    """

    load_dotenv()

    organization_host = _require_env("ADO_ORG")
    project = _require_env("ADO_PROJECT")
    pat = _require_env("ADO_PAT")
    regression_plan_id_raw = _require_env("ADO_PLAN_ID_REGRESSION")
    release_plan_id_raw = _require_env("ADO_PLAN_ID_RELEASE")
    csv_path = _require_env("ADO_AUTOMATION_CSV_PATH")

    automation_status_field = os.getenv("ADO_AUTOMATION_STATUS_FIELD", "Custom.AutomationStatus").strip()
    if not automation_status_field:
        automation_status_field = "Custom.AutomationStatus"

    try:
        regression_plan_id = int(regression_plan_id_raw)
    except ValueError as exc:
        raise RuntimeError("ADO_PLAN_ID_REGRESSION must be an integer.") from exc

    try:
        release_plan_id = int(release_plan_id_raw)
    except ValueError as exc:
        raise RuntimeError("ADO_PLAN_ID_RELEASE must be an integer.") from exc

    organization_url = f"https://dev.azure.com/{organization_host}"

    return AzureConfig(
        organization_url=organization_url,
        project=project,
        personal_access_token=pat,
        regression_plan_id=regression_plan_id,
        release_plan_id=release_plan_id,
        automation_status_field=automation_status_field,
        csv_path=csv_path,
    )
