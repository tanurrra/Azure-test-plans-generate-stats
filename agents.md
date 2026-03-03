# Automation Agents

## Overview

This document describes the automation agents and components used in the stats-automation project.

## Main Agent

### Test Stats Fetcher (`main.py`)

**Purpose**: Fetches test automation statistics from Jira by running JQL queries and aggregates results into a CSV report grouped by Jira component.

**Frequency**: Weekly (manual or scheduled)

**Configuration**: Environment variables via `.env` file

**Responsibilities**:
- Connect to Jira REST API using Basic authentication (e-mail + API token)
- Execute JQL queries to retrieve test issues matching configured criteria
- Group issues by Jira component
- Count automation status per component (Automated / Planned / Not Automated)
- Append results to CSV file with timestamp

## Components

### Jira Client (`jira_client.py`)
- Handles all API communication with Jira Cloud REST API v3
- Authenticates using e-mail and API Token (Basic auth)
- Implements paginated JQL search requests
- Parses component and automation status fields from issue responses

### Aggregation Engine (`aggregation.py`)
- Groups fetched Jira test issues by component name
- Issues belonging to multiple components are counted in each component
- Issues with no component are grouped under "Unassigned"
- Counts test cases by automation status (Automated / Planned / Not Automated)
- Produces per-component statistics compatible with the existing CSV schema

### CSV Writer (`csv_writer.py`)
- Manages output CSV files
- Creates headers on first run
- Appends new rows for each execution
- Maintains historical data over time

### Chart Generator (`generate_charts.py`)
- Reads CSV files and generates Excel dashboards
- Creates multiple chart types:
  - Stacked area charts for overall progress
  - Line charts with markers for percentage trends
  - Stacked column charts for module (component) comparisons
  - Horizontal bar charts for current status
- Provides weekly trend analysis with visible axis labels and values
- Tracks automation percentage growth per component and overall
- Calculates automation percentages
- Produces professional formatted reports with vibrant colour schemes
- Adds data labels showing percentages on charts

### Chart Image Generator (`generate_chart_images.py`)
- Reads the same CSV files used for dashboards
- Generates high-quality PNG images of:
  - Overall progress (stacked area)
  - Overall automation % (line)
  - Component trends (stacked column)
  - Component % trends (lines)
  - Current status (horizontal bar)
- Uses `matplotlib` for rendering
- Images are saved in `chart_images/` directory
- Suitable for uploading to Confluence or other reports

## Configuration

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `JIRA_URL` | Yes | Base Jira instance URL, e.g. `https://crayon-group.atlassian.net` |
| `JIRA_EMAIL` | Yes | Jira user e-mail for Basic auth |
| `JIRA_API_TOKEN` | Yes | Jira API token |
| `JIRA_JQL` | Yes | JQL query to select test issues |
| `JIRA_CSV_PATH` | Yes | Output CSV file path |
| `JIRA_QUERY_LABEL` | No | Human-readable label (default: `Regression`) |
| `JIRA_AUTOMATION_STATUS_FIELD` | No | Field name or ID for automation status (default: `status`) |
| `JIRA_AUTOMATED_VALUE` | No | Value that means Automated (default: `Ready - Automated`) |
| `JIRA_PLANNED_VALUE` | No | Value that means Planned (default: `Ready - Automation Candidate`) |
| `JIRA_EXCLUDED_STATUSES` | No | Comma-separated values to exclude (default: `Closed`) |

### Finding the automation status field ID

```bash
curl -u email:api_token \
  "https://crayon-group.atlassian.net/rest/api/3/field" | python -m json.tool | grep -A2 "utomation"
```

## Usage

### First-time setup: Backfill historical data

```bash
python backfill.py --from 2026-01-06
```

Fetches all test issues with their full changelog history, reconstructs weekly snapshots from the start date to today, and writes the complete CSV from scratch (~5-10 minutes for 1000+ issues).

### Ongoing weekly updates

```bash
python main.py
```

Appends only today's snapshot to the existing CSV (runs in seconds).

## Scheduling

### Windows Task Scheduler
```powershell
schtasks /create /tn "JiraTestStats" /tr "C:\Path\To\python.exe C:\Path\To\main.py" /sc weekly /d MON /st 09:00
```

### Azure DevOps Pipeline
```yaml
schedules:
- cron: "0 9 * * 1"
  displayName: Weekly Monday 9am
  branches:
    include:
    - main
```

## Output

- **File**: `automation_stats_regression.csv` (default)
- **Format**: One row per Jira component per run
- **Columns**: `date`, `plan_id`, `plan_name`, `root_suite_id`, `root_suite_name`, `total_cases`, `automated`, `planned`, `not_automated`
- `root_suite_name` = Jira component name (or "Unassigned")
- `plan_name` = value of `JIRA_QUERY_LABEL`

## Dashboards

Generate Excel dashboards with visualisations:

```bash
python generate_charts.py
```

Creates timestamped Excel files:
- `dashboard_regression_YYYYMMDD.xlsx`

Each dashboard includes 5 sheets:

1. **Overall Progress** — stacked area + line chart of overall automation % over time
2. **Module Trends** — stacked column chart of automated count per component over time
3. **Module % Trends** — line chart of automation % per component over time
4. **Current Status** — horizontal bar chart of the latest week by component
5. **Raw Data** — complete dataset with calculated percentages

## Error Handling

The agent logs errors and continues processing remaining queries if one fails. Check logs for diagnostic information.
