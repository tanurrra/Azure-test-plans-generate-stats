# Azure Test Plans Automation Stats

This tool connects to Azure DevOps to fetch test automation statistics for specified Test Plans, aggregates data by "root" category (the top-level folders in the plan), and generates comprehensive Excel dashboards with visual trend analysis. Historical data is maintained in CSV files for week-over-week tracking.

## Prerequisites

- Python 3.8+
- Network access to `https://dev.azure.com/softwareone-pc`
- A Personal Access Token (PAT) with **Test Plans (Read)** and **Work Items (Read)** scope.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Or use a virtual environment if preferred)*

2. **Configure Environment Variables**:
   Create a `.env` file (or set these in your shell/pipeline) with the following variables:

   ```dotenv
   # Azure DevOps Organization (e.g. softwareone-pc)
   ADO_ORG=softwareone-pc
   
   # Project Name
   ADO_PROJECT=MPT
   
   # Personal Access Token
   ADO_PAT=your_pat_here
   
   # Test Plan IDs to process
   ADO_PLAN_ID_REGRESSION=230474
   ADO_PLAN_ID_RELEASE=228942
   
   # Output CSV Paths (absolute or relative)
   # Regression plan data will be written to this file
   ADO_AUTOMATION_CSV_PATH=automation_stats.csv
   
   # Release plan data will be written to this separate file
   ADO_RELEASE_CSV_PATH=automation_stats_release.csv
   
   # (Optional) Custom Automation Status Field Name
   # Default is "Custom.AutomationStatus"
   # ADO_AUTOMATION_STATUS_FIELD=Custom.AutomationStatus
   ```

## Usage

Run the script directly with Python:

```bash
python main.py
```

### What it does

1. Connects to the Azure DevOps API.
2. For each configured Test Plan:
   - Retrieves the full suite hierarchy.
   - Identifies "Root Suites" (top-level categories).
     > **Note**: If the Plan has a single root folder, the script currently aggregates by that single root. If you need breakdown by the *children* of the Plan Root, the logic in `aggregation.py` may need adjustment to select Level-1 children.
   - Recursively collects all test cases under each category.
   - Fetches the `Automation Status` for every test case.
   - Counts "Automated", "Planned", and "Not Automated".
3. Appends results to separate CSV files:
   - **Regression plan** (E2E - V5) data → `automation_stats.csv`
   - **Release plan** (E2E - Release) data → `automation_stats_release.csv`
   
   Each file contains columns:
   - `date`, `plan_id`, `plan_name`, `root_suite_id`, `root_suite_name`, `total_cases`, `automated`, `planned`, `not_automated`

## Generating Excel Dashboards

After collecting data, you can generate interactive Excel dashboards with charts:

```bash
python generate_charts.py
```

### What it generates

Creates two Excel files (one per test plan) with multiple sheets:
- **Overall Progress** - Stacked area chart showing automation growth over time + line chart tracking overall automation percentage
- **Module Trends** - Stacked column chart tracking automated test counts per module
- **Module % Trends** - Line chart showing automation percentage growth per module over time
- **Current Status** - Horizontal bar chart comparing latest week's status by module with percentage labels
- **Raw Data** - Complete dataset with calculated percentages

Files are named with timestamp: `dashboard_regression_YYYYMMDD.xlsx` and `dashboard_release_YYYYMMDD.xlsx`

### Dashboard Features

- **Automatic calculations**: Automation percentage per module and overall
- **Professional formatting**: Styled headers, auto-sized columns, and vibrant color schemes
- **Multiple visualizations**: Area charts, line charts with markers, and stacked bar charts
- **Percentage tracking**: Dedicated charts showing % growth trends by module and overall
- **Weekly trend analysis**: Track progress over time with clear axis labels and values
- **Module comparison**: Identify high and low performing areas with visual indicators
- **Data labels**: Percentage values displayed on charts for easy reading

### Scheduling

To run this weekly, configure a scheduled task (Windows Task Scheduler) or a CI/CD pipeline (Azure DevOps Pipeline) to execute `python main.py` once a week.

## CSV Output Format

Each test plan writes to its own CSV file:
- **automation_stats.csv** - Contains data for regression test plan (E2E - V5)
- **automation_stats_release.csv** - Contains data for release test plan (E2E - Release)

| date       | plan_id | plan_name | root_suite_id | root_suite_name     | total_cases | automated | planned | not_automated |
|------------|---------|-----------|---------------|---------------------|-------------|-----------|---------|---------------|
| 2026-02-16 | 230474  | E2E - V5  | 230476        | Commerce            | 239         | 9         | 1       | 229           |
