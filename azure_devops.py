from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional

import requests

from config import AzureConfig


@dataclass
class TestSuite:
    """Representation of a test suite in Azure DevOps.

    Attributes:
        id: Identifier of the test suite.
        name: Name of the test suite.
        parent_id: Identifier of the parent suite if present.
        plan_id: Identifier of the owning test plan.
    """

    id: int
    name: str
    parent_id: Optional[int]
    plan_id: int


@dataclass
class TestCaseReference:
    """Reference to a test case associated with a suite.

    Attributes:
        work_item_id: Work item identifier of the test case.
        suite_id: Identifier of the suite where the test case is linked.
    """

    work_item_id: int
    suite_id: int


class AzureDevOpsClient:
    """Client for interacting with Azure DevOps Test Plans and Work Items APIs."""

    def __init__(self, config: AzureConfig) -> None:
        """Initialize the client with configuration.

        Args:
            config: Azure DevOps configuration instance.
        """

        self._config = config
        encoded_token = base64.b64encode(f":{config.personal_access_token}".encode("utf-8")).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {encoded_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs: Mapping[str, object]) -> Mapping[str, object]:
        """Execute an HTTP request and return the parsed JSON body.

        Args:
            method: HTTP method name.
            url: Fully qualified request URL.
            **kwargs: Additional arguments for the requests library.

        Returns:
            Parsed JSON response body.

        Raises:
            RuntimeError: If the request fails or returns a non-success status code.
        """

        kwargs.setdefault("timeout", 30)
        try:
            response = requests.request(method, url, headers=self._headers, **kwargs)
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Azure DevOps request failed: {exc}") from exc

        if not response.ok:
            message = f"Azure DevOps request failed with status {response.status_code}: {response.text}"
            raise RuntimeError(message)
        if not response.content:
            return {}
        return json.loads(response.content.decode("utf-8"))

    def list_suites_for_plan(self, plan_id: int) -> List[TestSuite]:
        """Retrieve all test suites defined in a test plan.

        Args:
            plan_id: Identifier of the test plan.

        Returns:
            List of TestSuite instances.
        """

        api_version = "7.1-preview.1"
        url = (
            f"{self._config.organization_url}/{self._config.project}/_apis/"
            f"testplan/Plans/{plan_id}/suites?api-version={api_version}"
        )
        body = self._request("GET", url)
        suites: List[TestSuite] = []
        raw_suites = body.get("value", [])
        for raw in raw_suites:
            suite_id = int(raw["id"])
            name = str(raw["name"])
            parent_id: Optional[int]
            parent_reference = raw.get("parentSuite")
            if parent_reference and "id" in parent_reference:
                parent_id = int(parent_reference["id"])
            else:
                parent_id = None
            suites.append(TestSuite(id=suite_id, name=name, parent_id=parent_id, plan_id=plan_id))
        return suites

    def get_plan_name(self, plan_id: int) -> str:
        """Retrieve the name of a test plan.

        Args:
            plan_id: Identifier of the test plan.

        Returns:
            Name of the test plan.
        """

        api_version = "7.1-preview.1"
        url = f"{self._config.organization_url}/{self._config.project}/_apis/testplan/Plans/{plan_id}?api-version={api_version}"
        body = self._request("GET", url)
        return str(body.get("name", f"Plan {plan_id}"))

    def list_test_cases_for_suite(self, plan_id: int, suite_id: int) -> List[TestCaseReference]:
        """Retrieve test cases associated with a specific suite.

        Args:
            plan_id: Identifier of the test plan.
            suite_id: Identifier of the suite.

        Returns:
            List of TestCaseReference instances.
        """

        api_version = "7.1-preview.3"
        url = (
            f"{self._config.organization_url}/{self._config.project}/_apis/test/"
            f"Plans/{plan_id}/suites/{suite_id}/testcases?api-version={api_version}"
        )
        body = self._request("GET", url)
        items = body.get("value", [])
        result: List[TestCaseReference] = []
        for item in items:
            test_case = item.get("testCase") or {}
            test_case_id_raw = test_case.get("id")
            if test_case_id_raw is None:
                continue
            work_item_id = int(test_case_id_raw)
            result.append(TestCaseReference(work_item_id=work_item_id, suite_id=suite_id))
        return result

    def get_automation_status_by_work_item(
        self,
        work_item_ids: Iterable[int],
        field_reference_name: str,
    ) -> Dict[int, Optional[str]]:
        """Retrieve Automation Status values for given work items.

        Args:
            work_item_ids: Iterable of work item identifiers.
            field_reference_name: Reference name of the Automation Status field.

        Returns:
            Mapping from work item identifier to the field value or None.
        """

        ids_list = list(dict.fromkeys(int(x) for x in work_item_ids))
        if not ids_list:
            return {}

        api_version = "7.1-preview.1"
        url = f"{self._config.organization_url}/{self._config.project}/_apis/wit/workitemsbatch?api-version={api_version}"
        result: Dict[int, Optional[str]] = {}

        batch_size = 200
        for index in range(0, len(ids_list), batch_size):
            batch_ids = ids_list[index : index + batch_size]
            payload = {
                "ids": batch_ids,
                "fields": [field_reference_name],
            }
            body = self._request("POST", url, data=json.dumps(payload))
            values = body.get("value", [])
            for item in values:
                item_id_raw = item.get("id")
                if item_id_raw is None:
                    continue
                item_id = int(item_id_raw)
                fields = item.get("fields") or {}
                value_raw = fields.get(field_reference_name)
                value = str(value_raw).strip() if isinstance(value_raw, str) else None
                result[item_id] = value

        return result
