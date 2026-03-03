# Jira Test Automation Stats

This tool connects to Jira to fetch test automation statistics using JQL queries, aggregates data by **super-group** (CloudiQ, Operations, Everything else), and generates comprehensive Excel dashboards with visual trend analysis. Historical data is maintained in CSV files for week-over-week tracking.

## Super-Group Mapping

Tests are automatically grouped based on their Jira components:

- **CloudiQ**: Cloud-iQx, Adobe, Aws, Control Panel
- **Operations**: Operations Center, Phoenix, Product and Prices (if not in CloudiQ)
- **Everything else**: All other components not in CloudiQ or Operations

## Prerequisites

- Python 3.8+
- Network access to your Jira instance (e.g., `https://crayon-group.atlassian.net`)
- A Jira API token (generate at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens))
- **Dependencies**: `pandas`, `openpyxl`, `matplotlib`, `requests`, `python-dotenv` (see `requirements.txt`)

## Setup

1. **Install dependencies**:
   
   **Recommended**: Use a virtual environment:
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate on Windows
   .venv\Scripts\activate
   
   # Activate on Linux/Mac
   source .venv/bin/activate
   
   # Install dependencies in virtual environment
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   
   Copy `.env.example` to `.env` and fill in your values:

   ```dotenv
   # Base URL of your Jira Cloud instance (no trailing slash)
   JIRA_URL=https://yourinstance.atlassian.net
   
   # Jira user e-mail address used for Basic authentication
   JIRA_EMAIL=your.name@company.com
   
   # Jira API token (generate at https://id.atlassian.com/manage-profile/security/api-tokens)
   JIRA_API_TOKEN=your_api_token_here
   
   # JQL query to select test issues
   JIRA_JQL=Type = Test and labels in (Regression)
   
   # Human-readable label for the query (used in logs and as plan_name in CSV)
   JIRA_QUERY_LABEL=Regression
   
   # Path to the output CSV file
   JIRA_CSV_PATH=automation_stats_regression.csv
   
   # Custom field name or ID that stores the automation status value
   # Use "status" for the built-in status field, or "customfield_XXXXX" for custom fields
   JIRA_AUTOMATION_STATUS_FIELD=status
   
   # Field value that counts as "Automated" (case-insensitive match)
   JIRA_AUTOMATED_VALUE=Ready - Automated
   
   # Field value that counts as "Planned" (case-insensitive match)
   JIRA_PLANNED_VALUE=Ready - Automation Candidate
   
   # Comma-separated status values to exclude entirely from counts
   JIRA_EXCLUDED_STATUSES=Closed
   ```

   ### Finding the correct field ID
   
   If you need to find a custom field ID, query the Jira API:
   ```bash
   curl -u your.email@company.com:your_api_token \
     "https://instance.atlassian.net/rest/api/3/field" | python -m json.tool | grep -i automation
   ```

## Usage

There are two ways to populate the CSV with data:

### Option 1: Backfill Historical Data (Recommended for first run)

To generate weekly snapshots from a start date to today using Jira changelog history:

```bash
python backfill.py --from 2026-01-06
```

**What it does:**
1. Fetches all matching test issues and their full status changelogs from Jira
2. Reconstructs the status each issue had at the end of each Monday between the start date and today
3. Generates weekly aggregated snapshots grouped by Jira component
4. Writes all snapshots to the CSV (rewrites the file from scratch)

**Options:**
- `--from YYYY-MM-DD` - Start date (default: 2026-01-06)
- `--to YYYY-MM-DD` - End date (default: today)

**Note:** Backfill takes ~5-10 minutes for 1000+ issues due to per-issue changelog API calls.

### Option 2: Incremental Update (For ongoing weekly runs)

To append only today's snapshot to the existing CSV:

```bash
python main.py
```

**What it does:**
1. Connects to the Jira API
2. Executes the configured JQL query to retrieve test issues
3. Groups issues by Jira component (issues with multiple components are counted in each)
4. Issues with no component are grouped under "Unassigned"
5. Counts test cases by automation status:
   - **Automated**: Matches `JIRA_AUTOMATED_VALUE`
   - **Planned**: Matches `JIRA_PLANNED_VALUE`
   - **Not Automated**: Everything else (excluding statuses in `JIRA_EXCLUDED_STATUSES`)
6. Appends results to the CSV file with today's date

**CSV columns:**
- `date`, `plan_id`, `plan_name`, `root_suite_id`, `root_suite_name`, `total_cases`, `automated`, `planned`, `not_automated`
- `root_suite_name` = Jira component name (or "Unassigned")
- `plan_name` = value of `JIRA_QUERY_LABEL`

## Generating Excel Dashboards

After collecting data, generate interactive Excel dashboards with charts:

```bash
python generate_charts.py
```

### What it generates

Creates an Excel file with 5 sheets:

1. **Overall Progress** — Stacked area chart showing automation growth over time + line chart tracking overall automation percentage
2. **Module Trends** — Stacked column chart tracking automated test counts per component over time
3. **Module % Trends** — Line chart showing automation percentage growth per component over time
4. **Current Status** — Horizontal bar chart comparing latest week's status by component with percentage labels
5. **Raw Data** — Complete dataset with calculated percentages

File is named with timestamp: `dashboard_regression_YYYYMMDD.xlsx`

## Generating PNG Chart Images

If you need standalone images (e.g., for Confluence or external reports):

```bash
python generate_chart_images.py
```

### What it generates

Creates a `chart_images/` directory containing PNG files:
- `regression_overall_progress.png`
- `regression_overall_pct.png`
- `regression_module_trends.png`
- `regression_module_pct_trends.png`
- `regression_current_status.png`

### Dashboard Features

- **Automatic calculations**: Automation percentage per component and overall
- **Professional formatting**: Styled headers, auto-sized columns, and vibrant color schemes
- **Multiple visualizations**: Area charts, line charts with markers, and stacked bar charts
- **Percentage tracking**: Dedicated charts showing % growth trends by component and overall
- **Weekly trend analysis**: Track progress over time with clear axis labels and values
- **Component comparison**: Identify high and low performing areas with visual indicators
- **Data labels**: Percentage values displayed on charts for easy reading

## Scheduling

To run this weekly, configure a scheduled task or CI/CD pipeline to execute `python main.py` once a week.

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

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.8'
- script: |
    pip install -r requirements.txt
    python main.py
  displayName: 'Fetch Jira stats'
```

## CSV Output Format

The CSV file contains one row per Jira component per snapshot date:

## CSV Output Format

The CSV file contains one row per Jira component per snapshot date:

| date       | plan_id | plan_name  | root_suite_id | root_suite_name | total_cases | automated | planned | not_automated |
|------------|---------|------------|---------------|-----------------|-------------|-----------|---------|---------------|
| 2026-01-12 | 0       | Regression | 10828         | Cloud-iQx       | 419         | 235       | 47      | 137           |
| 2026-01-12 | 0       | Regression | 10830         | Microsoft       | 161         | 85        | 8       | 68            |

- **date**: Snapshot date (YYYY-MM-DD)
- **plan_id**: Numeric identifier (0 by default for the primary query)
- **plan_name**: Value of `JIRA_QUERY_LABEL`
- **root_suite_id**: Stable numeric hash of the component name
- **root_suite_name**: Jira component name (or "Unassigned" for issues with no component)
- **total_cases**: Total test issues in this component for this snapshot (issues count once per component)
- **automated**: Count matching `JIRA_AUTOMATED_VALUE`
- **planned**: Count matching `JIRA_PLANNED_VALUE`
- **not_automated**: Remaining count (excluding `JIRA_EXCLUDED_STATUSES`)

## Architecture

- **config.py** — Loads environment variables into `JiraConfig` data structure
- **jira_client.py** — Handles Jira REST API v3 communication (search + changelog)
- **aggregation.py** — Groups issues by component and counts by automation status
- **csv_writer.py** — Appends aggregation results to CSV with timestamps
- **main.py** — Main entry point for incremental updates (today's snapshot only)
- **backfill.py** — Historical data backfill using changelog replay
- **generate_charts.py** — Reads CSV and creates Excel dashboards
- **generate_chart_images.py** — Reads CSV and exports PNG charts

## Troubleshooting

**Issue: "Invalid request payload" error**
- The `/rest/api/3/search/jql` endpoint is strict. Ensure `JIRA_JQL` is valid JQL syntax.

**Issue: Wrong automation counts**
- Verify `JIRA_STATUS_FIELD` is correct (use `status` for built-in status, or `customfield_XXXXX` for custom fields)
- Check that `JIRA_AUTOMATED_VALUE` and `JIRA_PLANNED_VALUE` match exactly (case-insensitive)
- Verify `JIRA_EXCLUDED_STATUSES` contains statuses you want to skip

**Issue: Components missing from output**
- Issues with no component are grouped under "Unassigned"
- Check that the Jira `components` field is populated on your test issues

**Issue: Backfill is slow**
- Normal — fetching 1000+ changelogs takes ~5-10 minutes
- The script uses 10 concurrent threads; increasing beyond that may hit Jira rate limits
