# Azure Test Plans Automation Stats

This tool connects to Azure DevOps to fetch test automation statistics for specified Test Plans. It aggregates data by "root" category (the top-level folders in the plan) and appends a weekly snapshot to a CSV file.

## Prerequisites

- Python 3.8+
- Network access to `https://dev.azure.com/softwareone-pc`
- A Personal Access Token (PAT) with **Test Plans (Read)** and **Work Items (Read)** scope.

## Setup

1. **Install dependencies**:
   ```bash
   pip install requests python-dotenv
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
   ADO_PLAN_ID_REGRESSION=228942
   ADO_PLAN_ID_RELEASE=230474
   
   # Output CSV Path (absolute or relative)
   ADO_AUTOMATION_CSV_PATH=C:\Users\tatyana.velikanova\SOne\stats-automation\automation_stats.csv
   
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
3. Appends a new set of rows to the CSV file with strict columns:
   - `date`, `plan_id`, `root_suite_id`, `root_suite_name`, `total_cases`, `automated`, `planned`, `not_automated`

### Scheduling

To run this weekly, configure a scheduled task (Windows Task Scheduler) or a CI/CD pipeline (Azure DevOps Pipeline) to execute `python main.py` once a week.

## CSV Output Format

| date       | plan_id | root_suite_id | root_suite_name     | total_cases | automated | planned | not_automated |
|------------|---------|---------------|---------------------|-------------|-----------|---------|---------------|
| 2026-02-16 | 228942  | 1045          | Vendor and profiles | 150         | 120       | 10      | 20            |
