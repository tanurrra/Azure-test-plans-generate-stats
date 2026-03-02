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
- Creates multiple chart types:
  - Stacked area charts for overall progress
  - Line charts with markers for percentage trends
  - Stacked column charts for module comparisons
  - Horizontal bar charts for current status
- Provides weekly trend analysis with visible axis labels and values
- Tracks automation percentage growth per module and overall
- Compares module performance
- Calculates automation percentages
- Produces professional formatted reports with vibrant color schemes
- Adds data labels showing percentages on charts

### Chart Image Generator (`generate_chart_images.py`)
- Reads the same CSV files used for dashboards
- Generates high-quality PNG images of:
  - Overall progress (stacked area)
  - Overall automation % (line)
  - Module trends (stacked column)
  - Module % trends (lines)
  - Current status (horizontal bar)
- Uses `matplotlib` for rendering
- Images are saved in `chart_images/` directory
- Suitable for uploading to Confluence or other reports

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

- **File**: `automation_stats_regression.csv` (for E2E - Automations test plan)
- **File**: `automation_stats_release.csv` (for E2E - V5 test plan)
- **Format**: One row per root suite per plan per run
- **Columns**: date, plan_id, plan_name, root_suite_id, root_suite_name, total_cases, automated, planned, not_automated

## Dashboards

Generate Excel dashboards with visualizations:

```bash
python generate_charts.py
```

Creates timestamped Excel files:
- `dashboard_regression_YYYYMMDD.xlsx`
- `dashboard_release_YYYYMMDD.xlsx`

Each dashboard includes 5 sheets:

1. **Overall Progress**
   - Stacked area chart showing test count growth (automated, planned, not automated)
   - Line chart tracking overall automation percentage over time
   
2. **Module Trends**
   - Stacked column chart showing automated test counts per module
   - Y-axis with visible numbers for precise reading
   
3. **Module % Trends**
   - Line chart showing automation percentage growth per module
   - Multiple colored lines with markers for each module
   - Y-axis labels showing percentage values
   
4. **Current Status**
   - Horizontal stacked bar chart comparing latest week by module
   - Module names on vertical axis
   - Percentage labels displayed next to each bar
   
5. **Raw Data**
   - Complete dataset with calculated percentages

## Error Handling

The agent logs errors and continues processing remaining plans if one fails. Check logs for diagnostic information.
