"""Jira REST API client for fetching test issue data."""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional

import requests

from config import JiraConfig


@dataclass
class JiraTestCase:
    """Representation of a Jira test issue.

    Attributes:
        issue_id: Internal Jira issue identifier.
        issue_key: Human-readable issue key, e.g. 'PROJ-123'.
        summary: Short description of the test issue.
        components: List of component names assigned to the issue.
        automation_status: Value of the automation status field, or None if absent.
    """

    issue_id: str
    issue_key: str
    summary: str
    components: List[str] = field(default_factory=list)
    automation_status: Optional[str] = None


class JiraClient:
    """Client for interacting with the Jira Cloud REST API v3."""

    _PAGE_SIZE = 100

    def __init__(self, config: JiraConfig) -> None:
        """Initialize the client with configuration.

        Args:
            config: Jira configuration instance.
        """

        self._config = config
        raw = f"{config.email}:{config.api_token}".encode("utf-8")
        encoded = base64.b64encode(raw).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, method: str, url: str, **kwargs: object) -> Mapping[str, object]:
        """Execute an HTTP request and return the parsed JSON body.

        Args:
            method: HTTP method name.
            url: Fully qualified request URL.
            **kwargs: Additional keyword arguments for the requests library.

        Returns:
            Parsed JSON response body, or an empty dict for empty responses.

        Raises:
            RuntimeError: If the request fails or returns a non-success status code.
        """

        kwargs.setdefault("timeout", 30)
        try:
            response = requests.request(method, url, headers=self._headers, **kwargs)
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Jira request failed: {exc}") from exc

        if not response.ok:
            raise RuntimeError(
                f"Jira request failed with status {response.status_code}: {response.text}"
            )
        if not response.content:
            return {}
        return json.loads(response.content.decode("utf-8"))

    def _build_fields(self) -> List[str]:
        """Build the list of Jira fields to include in search results.

        Returns:
            List of field names/IDs to request.
        """

        fields = ["id", "key", "summary", "components"]
        if self._config.automation_status_field:
            fields.append(self._config.automation_status_field)
        return fields

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_test_cases(self, jql: str) -> List[JiraTestCase]:
        """Retrieve all Jira issues matching a JQL query.

        Results are fetched page by page until all issues are retrieved.

        Args:
            jql: JQL query string.

        Returns:
            List of JiraTestCase instances.
        """

        url = f"{self._config.jira_url}/rest/api/3/search/jql"
        fields = self._build_fields()
        results: List[JiraTestCase] = []
        next_page_token: Optional[str] = None

        while True:
            payload: dict = {
                "jql": jql,
                "maxResults": self._PAGE_SIZE,
                "fields": fields,
            }
            if next_page_token is not None:
                payload["nextPageToken"] = next_page_token

            body = self._request("POST", url, data=json.dumps(payload))

            issues = body.get("issues", [])
            for raw in issues:
                results.append(self._parse_issue(raw))

            logging.debug("Jira search: fetched %s issues so far.", len(results))

            next_page_token = body.get("nextPageToken")  # type: ignore[assignment]
            if not issues or not next_page_token:
                break

        return results

    def _parse_issue(self, raw: Mapping[str, object]) -> JiraTestCase:
        """Parse a single Jira issue from raw API response data.

        Args:
            raw: Raw issue dictionary from the Jira REST API.

        Returns:
            JiraTestCase populated from the raw data.
        """

        issue_id = str(raw.get("id", ""))
        issue_key = str(raw.get("key", ""))
        issue_fields: Mapping[str, object] = raw.get("fields") or {}

        summary = str(issue_fields.get("summary", ""))

        # Components
        components: List[str] = []
        raw_components = issue_fields.get("components") or []
        for comp in raw_components:
            name = comp.get("name") if isinstance(comp, dict) else None
            if name:
                components.append(str(name))

        # Automation status
        automation_status: Optional[str] = None
        if self._config.automation_status_field:
            raw_status = issue_fields.get(self._config.automation_status_field)
            if isinstance(raw_status, dict):
                # Built-in status field:  {"name": "Ready - Automated", ...}
                # Custom select/option field: {"value": "Automated", ...}
                automation_status = raw_status.get("name") or raw_status.get("value")
            elif isinstance(raw_status, str) and raw_status.strip():
                automation_status = raw_status.strip()

        return JiraTestCase(
            issue_id=issue_id,
            issue_key=issue_key,
            summary=summary,
            components=components,
            automation_status=automation_status,
        )
