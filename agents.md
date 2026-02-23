# Automation Agents

## Overview

This document describes the automation agents and components used in the stats-automation project.

## Main Agent

### Test Stats Fetcher (`main.py`)

**Purpose**: Fetches test automation statistics from Azure DevOps Test Plans and aggregates them into a CSV report.

**Frequency**: Weekly (manual or scheduled)

**Configuration**: Environment variables via `.env` file

**Responsibilities**:
- Connect to Azure DevOps API using PAT authentication
- Retrieve test plan structure (suites and test cases)
- Fetch automation status for each test case
- Aggregate statistics per root test suite
- Append results to CSV file with timestamp

## Components

### Azure DevOps Client (`azure_devops.py`)
- Handles all API communication with Azure DevOps
- Authenticates using Personal Access Token
- Implements REST API calls for:
  - Test Plans
  - Test Suites
  - Test Cases
  - Work Items

### Aggregation Engine (`aggregation.py`)
- Builds test suite hierarchy
- Identifies root test suites
- Traverses nested suite structures
- Counts test cases by automation status
- Produces per-suite statistics

### CSV Writer (`csv_writer.py`)
- Manages output CSV files
- Creates headers on first run
- Appends new rows for each execution
- Maintains historical data
- Supports separate files for different test plans

### Chart Generator (`generate_charts.py`)
- Reads CSV files and generates Excel dashboards
- Creates multiple chart types (stacked area, line, horizontal bar)
- Provides weekly trend analysis
- Compares module performance
- Calculates automation percentages
- Produces professional formatted reports

## Scheduling

To run this agent automatically:

### Windows Task Scheduler
```powershell
# Create a weekly task
schtasks /create /tn "AzureTestStats" /tr "C:\Path\To\python.exe C:\Path\To\main.py" /sc weekly /d MON /st 09:00
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

- **File**: `automation_stats.csv` (for E2E - V5 regression test plan)
- **File**: `automation_stats_automations.csv` (for E2E - Automations test plan)
- **Format**: One row per root suite per plan per run
- **Columns**: date, plan_id, plan_name, root_suite_id, root_suite_name, total_cases, automated, planned, not_automated

## Dashboards

Generate Excel dashboards with visualizations:

```bash
python generate_charts.py
```

Creates timestamped Excel files:
- `dashboard_regression_YYYYMMDD.xlsx`
- `dashboard_automations_YYYYMMDD.xlsx`

Each dashboard includes:
- Overall automation progress (stacked area chart)
- Module trends over time (line chart)
- Current status comparison (horizontal bar chart)
- Raw data with calculated percentages

## Error Handling

The agent logs errors and continues processing remaining plans if one fails. Check logs for diagnostic information.
