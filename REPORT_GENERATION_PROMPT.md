# Report Generation Prompt

Copy and paste this prompt when you need to refresh the test automation report:

```text
Using the current project workspace, refresh the Jira test automation report end to end.

1. Inspect automation_stats_regression.csv and determine its latest snapshot date.
2. If the data is missing a longer period of history, run the historical backfill for the missing date range using backfill.py. The backfill rewrites its output, so:
   - Back up automation_stats_regression.csv first.
   - Write the backfill to a temporary CSV when existing history must be preserved.
   - Merge the backfilled rows with the existing CSV, remove duplicate rows for the same date/plan/component, and keep the complete chronological history.
   - Use weekly Monday snapshots for the requested historical range and include the latest current snapshot when appropriate.
3. If only the latest snapshot is missing, use main.py to fetch and append the current Jira data instead of running a full backfill.
4. Generate the Excel dashboard with all charts using generate_charts.py.
5. Generate all PNG chart images using generate_chart_images.py.
6. If the existing Excel file is locked, save the refreshed workbook with a new timestamped filename rather than overwriting it.
7. Validate the result by confirming:
   - The CSV latest date and row counts.
   - The Excel workbook exists and contains Overall Progress, Module Trends, Module % Trends, Current Status, and Raw Data sheets.
   - All five regression PNG files exist and are non-empty.
8. Report the exact output filenames and any backup files created.

Use the project's configured .env credentials and query. Do not expose secrets. Do not delete historical data without first creating a backup.
```