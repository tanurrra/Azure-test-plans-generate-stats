"""Backfill historical weekly snapshots by replaying Jira issue status changelogs.

Usage:
    python backfill.py                        # Jan 6 2026 to last Monday
    python backfill.py --from 2026-01-06      # explicit start date
    python backfill.py --from 2026-01-06 --to 2026-02-24

The script rewrites the CSV from scratch so run it before (or instead of) main.py.
Today's snapshot is appended at the end automatically.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests

from aggregation import SuiteAggregation, _classify_status, _stable_id, _UNASSIGNED_COMPONENT, _map_to_super_group
from config import load_config, JiraConfig
from csv_writer import append_aggregations_to_csv


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ChangelogEntry:
    created: datetime
    from_status: Optional[str]
    to_status: Optional[str]


@dataclass
class IssueSnapshot:
    issue_id: str
    components: List[str]
    created_date: date
    current_status: Optional[str]
    changelog: List[ChangelogEntry] = field(default_factory=list)  # sorted ascending


# ---------------------------------------------------------------------------
# Jira helpers
# ---------------------------------------------------------------------------

def _auth_headers(config: JiraConfig) -> dict:
    encoded = base64.b64encode(f"{config.email}:{config.api_token}".encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _parse_jira_datetime(raw: str) -> datetime:
    """Parse Jira's ISO-8601 datetime string to an aware UTC datetime."""
    # Jira returns e.g. "2026-01-15T10:23:45.000+0200"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        # Fallback: strip milliseconds
        raw_clean = raw[:19]
        dt = datetime.fromisoformat(raw_clean).replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_issues_with_changelog(
    config: JiraConfig,
    jql: str,
    workers: int = 10,
    delay_seconds: float = 0.0,
    retries: int = 3,
) -> List[IssueSnapshot]:
    """Fetch all matching issues and their status changelogs.

    Issues are fetched via the paginated search endpoint, then each issue's
    full changelog is retrieved individually and filtered to status-field
    transitions only.
    """

    headers = _auth_headers(config)
    search_url = f"{config.jira_url}/rest/api/3/search/jql"
    fields = ["id", "key", "summary", "components", "status", "created"]
    page_size = 100
    raw_issues: List[dict] = []
    next_page_token: Optional[str] = None

    logging.info("Fetching issue list…")
    while True:
        payload: dict = {
            "jql": jql,
            "maxResults": page_size,
            "fields": fields,
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token

        resp = requests.post(search_url, headers=headers, data=json.dumps(payload), timeout=60)
        if not resp.ok:
            raise RuntimeError(f"Jira search failed {resp.status_code}: {resp.text}")

        body = resp.json()
        raw_issues.extend(body.get("issues", []))
        logging.info("  …fetched %s issues so far", len(raw_issues))

        next_page_token = body.get("nextPageToken")
        if not body.get("issues") or not next_page_token:
            break

    logging.info("Fetched %s issues total. Now fetching changelogs (parallel)…", len(raw_issues))

    # Fetch all changelogs concurrently
    def fetch_one(raw: dict) -> IssueSnapshot:
        issue_key = raw.get("key", raw.get("id"))
        changelog = _fetch_full_changelog(
            config,
            headers,
            issue_key,
            delay_seconds=delay_seconds,
            retries=retries,
        )
        return _parse_issue_snapshot(raw, config, changelog)

    results: List[IssueSnapshot] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(fetch_one, raw): raw for raw in raw_issues}
        done = 0
        for future in as_completed(futures):
            results.append(future.result())
            done += 1
            if done % 100 == 0 or done == len(raw_issues):
                logging.info("  changelogs: %s / %s", done, len(raw_issues))

    return results


def _fetch_full_changelog(
    config: JiraConfig,
    headers: dict,
    issue_key: str,
    delay_seconds: float = 0.0,
    retries: int = 3,
) -> List[ChangelogEntry]:
    """Fetch all changelog entries for an issue, filtered to status transitions."""
    base_url = f"{config.jira_url}/rest/api/3/issue/{issue_key}/changelog"
    entries: List[ChangelogEntry] = []
    start_at = 0

    while True:
        resp = None
        for attempt in range(retries + 1):
            resp = requests.get(
                base_url,
                headers=headers,
                params={"startAt": start_at, "maxResults": 100},
                timeout=30,
            )
            if resp.ok:
                break

            status_code = resp.status_code
            retry_after = resp.headers.get("Retry-After")
            if status_code == 429 or status_code >= 500:
                if attempt < retries:
                    wait_seconds = float(retry_after) if retry_after else float(2 ** attempt)
                    logging.warning(
                        "Rate limited fetching %s (status %s). Retrying in %.1fs...",
                        issue_key,
                        status_code,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
            logging.warning("Could not fetch changelog for %s: %s", issue_key, status_code)
            resp = None
            break

        if resp is None or not resp.ok:
            break

        body = resp.json()
        values = body.get("values", [])
        for history in values:
            created = _parse_jira_datetime(history["created"])
            for item in history.get("items", []):
                if item.get("field") == "status":
                    entries.append(ChangelogEntry(
                        created=created,
                        from_status=item.get("fromString"),
                        to_status=item.get("toString"),
                    ))

        start_at += len(values)
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        is_last = body.get("isLast", True)
        if is_last or not values:
            break

    entries.sort(key=lambda e: e.created)
    return entries


def _parse_issue_snapshot(raw: dict, config: JiraConfig, changelog: List[ChangelogEntry]) -> IssueSnapshot:
    issue_fields = raw.get("fields") or {}

    # Components
    components: List[str] = [
        c["name"] for c in (issue_fields.get("components") or []) if c.get("name")
    ]

    # Current status
    status_obj = issue_fields.get("status") or {}
    current_status: Optional[str] = status_obj.get("name") or None

    # Created date (UTC)
    created_raw = issue_fields.get("created", "")
    created_dt = _parse_jira_datetime(created_raw) if created_raw else datetime.now(timezone.utc)
    created_date = created_dt.date()

    return IssueSnapshot(
        issue_id=str(raw.get("id", "")),
        components=components,
        created_date=created_date,
        current_status=current_status,
        changelog=changelog,
    )


def _fetch_remaining_changelog(
    config: JiraConfig,
    headers: dict,
    issue_key: str,
    start_at: int,
    total: int,
) -> List[ChangelogEntry]:
    """Fetch additional changelog pages for a single issue."""
    extra: List[ChangelogEntry] = []
    base_url = f"{config.jira_url}/rest/api/3/issue/{issue_key}/changelog"
    current = start_at

    while current < total:
        resp = requests.get(
            base_url,
            headers=headers,
            params={"startAt": current, "maxResults": 100},
            timeout=30,
        )
        if not resp.ok:
            logging.warning("Could not fetch extra changelog for %s: %s", issue_key, resp.status_code)
            break

        body = resp.json()
        for history in body.get("values", []):
            created = _parse_jira_datetime(history["created"])
            for item in history.get("items", []):
                if item.get("field") == "status":
                    extra.append(
                        ChangelogEntry(
                            created=created,
                            from_status=item.get("fromString"),
                            to_status=item.get("toString"),
                        )
                    )
        current += len(body.get("values", []))
        if not body.get("values"):
            break

    return extra


# ---------------------------------------------------------------------------
# Status reconstruction
# ---------------------------------------------------------------------------

def status_at_date(snapshot: IssueSnapshot, target: date) -> Optional[str]:
    """Return the status the issue had at the end of *target* day.

    Returns None if the issue did not yet exist on that date.
    """
    if snapshot.created_date > target:
        return None  # issue didn't exist yet

    status = snapshot.current_status
    for entry in reversed(snapshot.changelog):
        if entry.created.date() > target:
            status = entry.from_status
        else:
            break
    return status


# ---------------------------------------------------------------------------
# Aggregation for a snapshot date
# ---------------------------------------------------------------------------

def aggregate_snapshot(
    config: JiraConfig,
    snapshots: List[IssueSnapshot],
    snapshot_date: date,
    plan_id: int = 0,
) -> List[SuiteAggregation]:
    """Aggregate super-group statistics for a single historical snapshot date."""

    excluded_lower = {s.strip().lower() for s in config.excluded_statuses}
    buckets: Dict[str, Dict[str, int]] = {}

    for snap in snapshots:
        raw_status = status_at_date(snap, snapshot_date)

        if raw_status is None:
            continue  # issue didn't exist yet

        if raw_status.strip().lower() in excluded_lower:
            continue  # excluded status

        classification = _classify_status(raw_status, config)
        components = snap.components if snap.components else [_UNASSIGNED_COMPONENT]
        
        # Map components to super-group
        super_group = _map_to_super_group(components)

        if super_group not in buckets:
            buckets[super_group] = {"automated": 0, "planned": 0, "not_automated": 0, "total": 0}
        buckets[super_group][classification] += 1
        buckets[super_group]["total"] += 1

    return [
        SuiteAggregation(
            plan_id=plan_id,
            root_suite_id=_stable_id(name),
            root_suite_name=name,
            total_cases=counts["total"],
            automated=counts["automated"],
            planned=counts["planned"],
            not_automated=counts["not_automated"],
        )
        for name, counts in sorted(buckets.items())
    ]


# ---------------------------------------------------------------------------
# Weekly date generation
# ---------------------------------------------------------------------------

def monday_on_or_before(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weekly_mondays(start: date, end: date) -> List[date]:
    """Return all Mondays from *start* up to and including *end*."""
    first = monday_on_or_before(start) if start.weekday() == 0 else start + timedelta(days=(7 - start.weekday()) % 7)
    if first < start:
        first += timedelta(weeks=1)
    dates = []
    current = first
    while current <= end:
        dates.append(current)
        current += timedelta(weeks=1)
    return dates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    start_date: date,
    end_date: date,
    workers: int,
    delay_seconds: float,
    retries: int,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = load_config()
    query = config.queries[0]
    plan_names = {0: query.label}

    snapshots = fetch_issues_with_changelog(
        config,
        query.jql,
        workers=workers,
        delay_seconds=delay_seconds,
        retries=retries,
    )

    dates = weekly_mondays(start_date, end_date)
    # Always include today even if it's not a Monday
    if end_date not in dates:
        dates.append(end_date)

    logging.info("Will generate %s snapshots: %s → %s", len(dates), dates[0], dates[-1])

    # Rewrite CSV from scratch
    if os.path.exists(query.csv_path):
        os.remove(query.csv_path)
        logging.info("Removed existing CSV '%s'.", query.csv_path)

    for snap_date in dates:
        aggs = aggregate_snapshot(config, snapshots, snap_date, plan_id=0)
        append_aggregations_to_csv(query.csv_path, aggs, run_date=snap_date, plan_names=plan_names)
        logging.info("  %s → %s super-group rows written.", snap_date, len(aggs))

    logging.info("Backfill complete. CSV written to '%s'.", query.csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill weekly Jira test stats from changelogs.")
    parser.add_argument("--from", dest="start", default="2026-01-06",
                        help="Start date (YYYY-MM-DD). Defaults to 2026-01-06.")
    parser.add_argument("--to", dest="end", default=str(date.today()),
                        help="End date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--workers", type=int, default=10,
                        help="Parallel changelog fetch workers (default: 10).")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="Delay in seconds between changelog page requests (default: 0).")
    parser.add_argument("--retries", type=int, default=3,
                        help="Retry count for 429/5xx responses (default: 3).")
    args = parser.parse_args()

    run(
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        workers=args.workers,
        delay_seconds=args.delay,
        retries=args.retries,
    )
