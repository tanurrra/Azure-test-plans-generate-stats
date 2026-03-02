"""Generate Excel dashboard with automation statistics charts."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import AreaChart, BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.chart.marker import Marker
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.colors import ColorChoice
from openpyxl.drawing.fill import SolidColorFillProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows


def load_and_prepare_data(csv_path: str) -> pd.DataFrame:
    """Load CSV data and add calculated fields.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with automation statistics and calculated percentage.
    """
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df["date_formatted"] = df["date"].dt.strftime("%d/%m/%Y")
    df["automation_pct"] = (df["automated"] / df["total_cases"] * 100).round(1)
    return df


def create_overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create summary of overall statistics by date.

    Args:
        df: Input DataFrame with test statistics.

    Returns:
        DataFrame grouped by date with summed statistics.
    """
    df_sorted = df.sort_values("date")
    summary = (
        df_sorted.groupby("date_formatted", sort=False)
        .agg({"automated": "sum", "planned": "sum", "not_automated": "sum", "total_cases": "sum"})
        .reset_index()
    )
    summary["automation_pct"] = (summary["automated"] / summary["total_cases"] * 100).round(1)
    summary.rename(columns={"date_formatted": "date"}, inplace=True)
    return summary


def create_module_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Create pivot of automated tests by module and date.

    Args:
        df: Input DataFrame with test statistics.

    Returns:
        Pivoted DataFrame with dates as rows and modules as columns.
    """
    df_sorted = df.sort_values("date")
    chronological_dates = df_sorted["date_formatted"].unique()
    pivot = df_sorted.pivot_table(index="date_formatted", columns="root_suite_name", values="automated", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(chronological_dates)
    pivot = pivot.reset_index()
    pivot.rename(columns={"date_formatted": "date"}, inplace=True)
    return pivot


def create_current_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Create snapshot of latest week's data sorted by total cases.

    Args:
        df: Input DataFrame with test statistics.

    Returns:
        DataFrame filtered to latest date and sorted by total cases.
    """
    latest_date = df["date"].max()
    snapshot = df[df["date"] == latest_date].copy()
    snapshot = snapshot.sort_values("total_cases", ascending=True)
    return snapshot[["root_suite_name", "total_cases", "automated", "planned", "not_automated", "automation_pct"]]


def create_module_pct_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Create pivot of automation percentage by module and date.

    Args:
        df: Input DataFrame with test statistics.

    Returns:
        Pivoted DataFrame with dates as rows and modules as columns showing percentages.
    """
    df_sorted = df.sort_values("date")
    chronological_dates = df_sorted["date_formatted"].unique()
    pivot = df_sorted.pivot_table(index="date_formatted", columns="root_suite_name", values="automation_pct", aggfunc="mean", fill_value=0)
    pivot = pivot.reindex(chronological_dates)
    pivot = pivot.reset_index()
    pivot.rename(columns={"date_formatted": "date"}, inplace=True)
    return pivot


def _apply_chart_margins(chart: Any) -> None:
    """Apply plot area layout and reserve extra space on the right for legends."""
    chart.plot_area.layout = Layout(
        manualLayout=ManualLayout(
            x=0.08,
            y=0.05,
            w=0.646,
            h=0.85,
        )
    )


def add_stacked_area_chart(ws: Any, data_range: str, title: str, position: str) -> None:
    """Add a stacked area chart to the worksheet.

    Args:
        ws: Worksheet object.
        data_range: Range of cells containing data.
        title: Chart title.
        position: Cell position for chart placement.
    """
    chart = AreaChart()
    chart.title = title
    chart.style = 10
    chart.x_axis.title = "Date"
    chart.y_axis.title = "Number of Tests"
    chart.grouping = "stacked"
    chart.height = 10
    chart.width = 26

    data = Reference(ws, min_col=2, min_row=1, max_col=4, max_row=ws.max_row)
    dates = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(dates)
    
    # Ensure x-axis labels are visible
    chart.x_axis.tickLblPos = "low"
    chart.x_axis.delete = False

    # Add vibrant colors: Green for Automated, Blue for Planned, Gray for Not Automated
    colors = ["70AD47", "4472C4", "808080"]
    for idx, series in enumerate(chart.series):
        if idx < len(colors):
            # Create fill properties
            color_fill = ColorChoice(srgbClr=colors[idx])
            fill_props = SolidColorFillProperties()
            fill_props.solidFill = color_fill
            
            # Create line properties
            line_props = LineProperties()
            line_props.solidFill = color_fill
            
            # Apply to series
            series.graphicalProperties = GraphicalProperties()
            series.graphicalProperties.solidFill = color_fill
            series.graphicalProperties.line = line_props

    _apply_chart_margins(chart)
    ws.add_chart(chart, position)


def add_line_chart(ws: Any, max_col: int, title: str, position: str) -> None:
    """Add a stacked column chart to the worksheet.

    Args:
        ws: Worksheet object.
        max_col: Maximum column index for data.
        title: Chart title.
        position: Cell position for chart placement.
    """
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.title = title
    chart.style = 12
    chart.x_axis.title = "Date"
    chart.y_axis.title = "Automated Tests"
    chart.height = 10
    chart.width = 26

    data = Reference(ws, min_col=2, min_row=1, max_col=max_col, max_row=ws.max_row)
    dates = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(dates)
    
    # Ensure x-axis labels are visible
    chart.x_axis.tickLblPos = "low"
    chart.x_axis.delete = False
    
    # Ensure y-axis labels (numbers) are visible on the left
    chart.y_axis.tickLblPos = "nextTo"
    chart.y_axis.delete = False

    # Vibrant color palette for different modules
    colors = [
        "5B9BD5", "ED7D31", "A5A5A5", "FFC000", "4472C4",
        "70AD47", "255E91", "9E480E", "636363", "997300",
        "264478", "43682B", "FF5050", "9933FF", "00B0F0",
        "92D050"
    ]

    for idx, series in enumerate(chart.series):
        color = colors[idx % len(colors)]
        color_fill = ColorChoice(srgbClr=color)
        
        # Apply color to series
        series.graphicalProperties = GraphicalProperties()
        series.graphicalProperties.solidFill = color_fill

    _apply_chart_margins(chart)
    ws.add_chart(chart, position)


def add_horizontal_bar_chart(ws: Any, title: str, position: str) -> None:
    """Add a horizontal stacked bar chart to the worksheet.

    Args:
        ws: Worksheet object.
        title: Chart title.
        position: Cell position for chart placement.
    """
    chart = BarChart()
    chart.type = "bar"
    chart.grouping = "stacked"
    chart.title = title
    chart.style = 11
    chart.height = 12
    chart.width = 23.4

    data = Reference(ws, min_col=3, min_row=1, max_col=5, max_row=ws.max_row)
    categories = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)
    
    # Ensure y-axis labels (module names) are visible
    chart.y_axis.title = "Module"
    chart.y_axis.delete = False

    # Add matching colors: Green for Automated, Blue for Planned, Gray for Not Automated
    colors = ["70AD47", "4472C4", "808080"]
    for idx, series in enumerate(chart.series):
        if idx < len(colors):
            color_fill = ColorChoice(srgbClr=colors[idx])
            series.graphicalProperties = GraphicalProperties()
            series.graphicalProperties.solidFill = color_fill

    _apply_chart_margins(chart)
    ws.add_chart(chart, position)
    
    # Add percentage labels as text in cells next to the chart
    # Position them to the right of where bars end
    chart_col = ord(position[0]) - ord('A') + 1
    label_col = chart_col + int(chart.width) + 1  # Position after chart width
    
    # Add header
    ws.cell(row=1, column=label_col, value="Automation %")
    ws.cell(row=1, column=label_col).font = Font(bold=True)
    
    # Add percentage values for each module
    for row_idx in range(2, ws.max_row + 1):
        pct_value = ws.cell(row=row_idx, column=6).value
        if pct_value and '%' in str(pct_value):
            ws.cell(row=row_idx, column=label_col, value=pct_value)
            ws.cell(row=row_idx, column=label_col).font = Font(bold=True, size=11)


def add_pct_line_chart(ws: Any, max_col: int, title: str, position: str, y_axis_title: str = "Automation %") -> None:
    """Add a line chart for percentage trends.

    Args:
        ws: Worksheet object.
        max_col: Maximum column index for data.
        title: Chart title.
        position: Cell position for chart placement.
        y_axis_title: Title for y-axis.
    """
    chart = LineChart()
    chart.title = title
    chart.style = 12
    chart.x_axis.title = "Date"
    chart.y_axis.title = y_axis_title
    chart.height = 10
    chart.width = 26

    data = Reference(ws, min_col=2, min_row=1, max_col=max_col, max_row=ws.max_row)
    dates = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(dates)
    
    # Ensure x-axis labels are visible
    chart.x_axis.tickLblPos = "low"
    chart.x_axis.delete = False
    
    # Ensure y-axis labels (numbers) are visible on the left
    chart.y_axis.tickLblPos = "nextTo"
    chart.y_axis.delete = False

    # Vibrant color palette for different modules
    colors = [
        "5B9BD5", "ED7D31", "A5A5A5", "FFC000", "4472C4",
        "70AD47", "255E91", "9E480E", "636363", "997300",
        "264478", "43682B", "FF5050", "9933FF", "00B0F0",
        "92D050"
    ]

    for idx, series in enumerate(chart.series):
        color = colors[idx % len(colors)]
        color_fill = ColorChoice(srgbClr=color)
        
        # Apply color to series
        series.graphicalProperties = GraphicalProperties()
        line_props = LineProperties()
        line_props.solidFill = color_fill
        series.graphicalProperties.line = line_props
        
        # Add markers
        series.marker = Marker(symbol="circle", size=5)
        series.marker.graphicalProperties = GraphicalProperties()
        series.marker.graphicalProperties.solidFill = color_fill
        marker_line = LineProperties()
        marker_line.solidFill = color_fill
        series.marker.graphicalProperties.line = marker_line

    _apply_chart_margins(chart)
    ws.add_chart(chart, position)


def add_overall_pct_chart(ws: Any, title: str, position: str) -> None:
    """Add a line chart for overall automation percentage trend.

    Args:
        ws: Worksheet object.
        title: Chart title.
        position: Cell position for chart placement.
    """
    chart = LineChart()
    chart.title = title
    chart.style = 12
    chart.x_axis.title = "Date"
    chart.y_axis.title = "Automation %"
    chart.height = 10
    chart.width = 26

    # Data from column 6 (automation_pct)
    data = Reference(ws, min_col=6, min_row=1, max_col=6, max_row=ws.max_row)
    dates = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(dates)
    
    # Ensure x-axis labels are visible
    chart.x_axis.tickLblPos = "low"
    chart.x_axis.delete = False
    
    # Ensure y-axis labels (numbers) are visible on the left
    chart.y_axis.tickLblPos = "nextTo"
    chart.y_axis.delete = False

    # Green color for automation percentage
    if chart.series:
        color_fill = ColorChoice(srgbClr="70AD47")
        chart.series[0].graphicalProperties = GraphicalProperties()
        line_props = LineProperties()
        line_props.solidFill = color_fill
        line_props.width = 30000
        chart.series[0].graphicalProperties.line = line_props
        
        # Add markers
        chart.series[0].marker = Marker(symbol="circle", size=7)
        chart.series[0].marker.graphicalProperties = GraphicalProperties()
        chart.series[0].marker.graphicalProperties.solidFill = color_fill
        marker_line = LineProperties()
        marker_line.solidFill = color_fill
        chart.series[0].marker.graphicalProperties.line = marker_line

    _apply_chart_margins(chart)
    ws.add_chart(chart, position)


def apply_table_formatting(ws: Any, header_row: int = 1) -> None:
    """Apply formatting to worksheet header and data.

    Args:
        ws: Worksheet object.
        header_row: Row number for headers.
    """
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for cell in ws[header_row]:
        cell.fill = header_fill
        cell.font = header_font

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[column].width = min(max_length + 2, 50)


def generate_dashboard(csv_path: str, output_path: str, plan_name: str) -> None:
    """Generate Excel dashboard with multiple charts from CSV data.

    Args:
        csv_path: Path to input CSV file.
        output_path: Path for output Excel file.
        plan_name: Name of the test plan for titles.
    """
    df = load_and_prepare_data(csv_path)

    overall_summary = create_overall_summary(df)
    module_trends = create_module_trends(df)
    module_pct_trends = create_module_pct_trends(df)
    current_snapshot = create_current_snapshot(df)

    wb = Workbook()
    wb.remove(wb.active)

    ws_summary = wb.create_sheet("Overall Progress")
    for row in dataframe_to_rows(overall_summary, index=False, header=True):
        ws_summary.append(row)
    apply_table_formatting(ws_summary)
    add_stacked_area_chart(
        ws_summary, "A1:D100", f"{plan_name} - Overall Automation Progress", "A10"
    )
    add_overall_pct_chart(
        ws_summary, f"{plan_name} - Overall Automation %", "A30"
    )

    ws_trends = wb.create_sheet("Module Trends")
    for row in dataframe_to_rows(module_trends, index=False, header=True):
        ws_trends.append(row)
    apply_table_formatting(ws_trends)
    add_line_chart(
        ws_trends, module_trends.shape[1], f"{plan_name} - Automation by Module", "A20"
    )

    ws_pct_trends = wb.create_sheet("Module % Trends")
    for row in dataframe_to_rows(module_pct_trends, index=False, header=True):
        ws_pct_trends.append(row)
    apply_table_formatting(ws_pct_trends)
    add_pct_line_chart(
        ws_pct_trends, module_pct_trends.shape[1], f"{plan_name} - Automation % by Module", "A20"
    )

    ws_snapshot = wb.create_sheet("Current Status")
    for row in dataframe_to_rows(current_snapshot, index=False, header=True):
        ws_snapshot.append(row)
    
    # Format automation_pct column (column F/6) to show percentage with % symbol
    for row_idx in range(2, ws_snapshot.max_row + 1):
        cell = ws_snapshot.cell(row=row_idx, column=6)
        if cell.value is not None:
            cell.value = f"{cell.value}%"
    
    apply_table_formatting(ws_snapshot)
    add_horizontal_bar_chart(
        ws_snapshot, f"{plan_name} - Current Status by Module", "H2"
    )

    ws_raw = wb.create_sheet("Raw Data")
    for row in dataframe_to_rows(df, index=False, header=True):
        ws_raw.append(row)
    apply_table_formatting(ws_raw)

    wb.save(output_path)


def main() -> None:
    """Generate dashboards for both test plans."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    regression_csv = os.path.join(script_dir, "automation_stats_regression.csv")
    release_csv = os.path.join(script_dir, "automation_stats_release.csv")

    timestamp = datetime.now().strftime("%Y%m%d")

    if os.path.exists(regression_csv):
        output_path = os.path.join(script_dir, f"dashboard_regression_{timestamp}.xlsx")
        generate_dashboard(regression_csv, output_path, "E2E - V5 Regression")
        print(f"Generated: {output_path}")

    if os.path.exists(release_csv):
        output_path = os.path.join(script_dir, f"dashboard_release_{timestamp}.xlsx")
        generate_dashboard(release_csv, output_path, "E2E - Release")
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
