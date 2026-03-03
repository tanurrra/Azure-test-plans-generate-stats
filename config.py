from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv


@dataclass
class JiraQueryConfig:
    """Configuration for a single Jira JQL query that produces one CSV output file.

    Attributes:
        jql: JQL query string used to select test issues.
        csv_path: Absolute or relative path to the output CSV file.
        label: Human-readable label used in log messages and as plan_name in CSV rows.
    """

    jql: str
    csv_path: str
    label: str


@dataclass
class JiraConfig:
    """Jira connection and reporting configuration.

    Attributes:
        jira_url: Base Jira instance URL, e.g. 'https://your-org.atlassian.net'.
        email: Jira user e-mail used for Basic authentication.
        api_token: Jira API token used for Basic authentication.
        automation_status_field: Jira field name or custom field ID that holds the
            automation status value, e.g. 'customfield_10050'.
            If empty, every test case is counted as not_automated.
        automated_value: Field value that counts as Automated (case-insensitive).
        planned_value: Field value that counts as Planned (case-insensitive).
        queries: One or more JQL query configurations.
    """

    jira_url: str
    email: str
    api_token: str
    automation_status_field: str
    automated_value: str
    planned_value: str
    excluded_statuses: List[str] = field(default_factory=list)
    queries: List[JiraQueryConfig] = field(default_factory=list)


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


def load_config() -> JiraConfig:
    """Load Jira configuration from environment variables.

    Environment variables:
        JIRA_URL: Base Jira instance URL, e.g. 'https://your-org.atlassian.net'.
        JIRA_EMAIL: Jira user e-mail for authentication.
        JIRA_API_TOKEN: Jira API token for authentication.
        JIRA_JQL: JQL query to fetch test issues (primary query).
        JIRA_CSV_PATH: Path to the CSV file for the primary query results.
        JIRA_QUERY_LABEL: Human-readable label for the primary query (default: 'Regression').
        JIRA_AUTOMATION_STATUS_FIELD: Custom field ID holding automation status
            (default: 'customfield_10050').  Leave empty to disable status tracking.
        JIRA_AUTOMATED_VALUE: Field value treated as Automated (default: 'Automated').
        JIRA_PLANNED_VALUE: Field value treated as Planned (default: 'Planned').
        JIRA_EXCLUDED_STATUSES: Comma-separated status values to exclude from counts entirely.

    Returns:
        Loaded JiraConfig instance.
    """

    load_dotenv()

    jira_url = _require_env("JIRA_URL").rstrip("/")
    email = _require_env("JIRA_EMAIL")
    api_token = _require_env("JIRA_API_TOKEN")
    jql = _require_env("JIRA_JQL")
    csv_path = _require_env("JIRA_CSV_PATH")

    query_label = os.getenv("JIRA_QUERY_LABEL", "Regression").strip() or "Regression"
    automation_status_field = os.getenv("JIRA_AUTOMATION_STATUS_FIELD", "customfield_10050").strip()
    automated_value = os.getenv("JIRA_AUTOMATED_VALUE", "Automated").strip() or "Automated"
    planned_value = os.getenv("JIRA_PLANNED_VALUE", "Planned").strip() or "Planned"

    excluded_raw = os.getenv("JIRA_EXCLUDED_STATUSES", "").strip()
    excluded_statuses = [s.strip() for s in excluded_raw.split(",") if s.strip()] if excluded_raw else []

    primary_query = JiraQueryConfig(jql=jql, csv_path=csv_path, label=query_label)

    return JiraConfig(
        jira_url=jira_url,
        email=email,
        api_token=api_token,
        automation_status_field=automation_status_field,
        automated_value=automated_value,
        planned_value=planned_value,
        excluded_statuses=excluded_statuses,
        queries=[primary_query],
    )
