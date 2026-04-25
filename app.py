"""Simple Bokeh app for AHA stroke quality metrics.

The data in this demo is synthetic. Replace `build_demo_rows()` with a database,
CSV, or API-backed data source before using it for operational reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import random
from statistics import mean

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource,
    DataTable,
    Div,
    HoverTool,
    InlineStyleSheet,
    NumberFormatter,
    Select,
    Span,
    TableColumn,
)
from bokeh.plotting import figure


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    target: float
    description: str


METRICS = [
    Metric(
        "nihss_documented",
        "Initial NIHSS documented",
        0.95,
        "Percent of ischemic stroke encounters with an initial NIHSS score documented.",
    ),
    Metric(
        "dysphagia_screen",
        "Dysphagia screen before PO",
        0.95,
        "Percent screened for swallowing safety before oral intake.",
    ),
    Metric(
        "antithrombotic_eod2",
        "Antithrombotic by end of day 2",
        0.90,
        "Eligible ischemic stroke encounters receiving antithrombotic therapy by hospital day 2.",
    ),
    Metric(
        "vte_prophylaxis",
        "VTE prophylaxis",
        0.90,
        "Eligible non-ambulatory stroke encounters receiving venous thromboembolism prophylaxis.",
    ),
    Metric(
        "door_to_needle_60",
        "Door-to-needle <= 60 min",
        0.85,
        "IV thrombolytic-treated patients with door-to-needle time of 60 minutes or less.",
    ),
    Metric(
        "statin_discharge",
        "Statin prescribed at discharge",
        0.90,
        "Eligible ischemic stroke or TIA encounters discharged on statin therapy.",
    ),
    Metric(
        "smoking_counseling",
        "Smoking cessation counseling",
        0.90,
        "Current or recent smokers receiving cessation counseling or medication at discharge.",
    ),
]

METRIC_BY_KEY = {metric.key: metric for metric in METRICS}
HOSPITALS = ["All Hospitals", "North Medical Center", "Central Stroke Institute", "East Valley Hospital"]
MONTHS = [date(2025, month, 1) for month in range(1, 13)]


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def build_demo_rows() -> list[dict[str, object]]:
    rng = random.Random(42)
    hospitals = HOSPITALS[1:]
    rows: list[dict[str, object]] = []

    for hospital_index, hospital in enumerate(hospitals):
        hospital_shift = [-0.025, 0.01, -0.005][hospital_index]
        for month_index, month in enumerate(MONTHS):
            trend = month_index * 0.004
            volume_base = [74, 91, 58][hospital_index]

            for metric_index, metric in enumerate(METRICS):
                denominator = max(16, volume_base + rng.randint(-13, 15) - metric_index * 3)
                baseline = metric.target - 0.045 + hospital_shift + trend
                seasonal = [0.0, -0.014, 0.009, 0.006][(month_index + metric_index) % 4]
                observed_rate = min(0.995, max(0.58, baseline + seasonal + rng.uniform(-0.025, 0.025)))
                numerator = round(denominator * observed_rate)
                rate = numerator / denominator

                rows.append(
                    {
                        "hospital": hospital,
                        "month": month,
                        "month_label": month.strftime("%b %Y"),
                        "metric_key": metric.key,
                        "metric": metric.label,
                        "target": metric.target,
                        "numerator": numerator,
                        "denominator": denominator,
                        "rate": rate,
                    }
                )
    return rows


ROWS = build_demo_rows()


def rows_for(metric_key: str, hospital: str) -> list[dict[str, object]]:
    selected = [row for row in ROWS if row["metric_key"] == metric_key]
    if hospital != "All Hospitals":
        selected = [row for row in selected if row["hospital"] == hospital]
    return selected


def aggregate_by_month(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    aggregated = []
    for month in MONTHS:
        month_rows = [row for row in rows if row["month"] == month]
        numerator = sum(int(row["numerator"]) for row in month_rows)
        denominator = sum(int(row["denominator"]) for row in month_rows)
        rate = numerator / denominator if denominator else 0
        aggregated.append(
            {
                "month": month,
                "month_label": month.strftime("%b %Y"),
                "rate": rate,
                "target": float(month_rows[0]["target"]) if month_rows else 0,
                "numerator": numerator,
                "denominator": denominator,
            }
        )
    return aggregated


def aggregate_by_hospital(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    aggregated = []
    for hospital in HOSPITALS[1:]:
        hospital_rows = [row for row in rows if row["hospital"] == hospital]
        numerator = sum(int(row["numerator"]) for row in hospital_rows)
        denominator = sum(int(row["denominator"]) for row in hospital_rows)
        rate = numerator / denominator if denominator else 0
        aggregated.append(
            {
                "hospital": hospital,
                "rate": rate,
                "target": float(hospital_rows[0]["target"]) if hospital_rows else 0,
                "gap": rate - (float(hospital_rows[0]["target"]) if hospital_rows else 0),
                "numerator": numerator,
                "denominator": denominator,
            }
        )
    return aggregated


def metric_table_rows(hospital: str) -> list[dict[str, object]]:
    rows = []
    for metric in METRICS:
        selected = rows_for(metric.key, hospital)
        numerator = sum(int(row["numerator"]) for row in selected)
        denominator = sum(int(row["denominator"]) for row in selected)
        rate = numerator / denominator if denominator else 0
        rows.append(
            {
                "metric": metric.label,
                "rate": rate,
                "target": metric.target,
                "gap": rate - metric.target,
                "numerator": numerator,
                "denominator": denominator,
            }
        )
    return rows


def build_kpi_cards(metric: Metric, rows: list[dict[str, object]]) -> str:
    numerator = sum(int(row["numerator"]) for row in rows)
    denominator = sum(int(row["denominator"]) for row in rows)
    rate = numerator / denominator if denominator else 0
    latest_rows = [row for row in rows if row["month"] == MONTHS[-1]]
    latest_rate = (
        sum(int(row["numerator"]) for row in latest_rows) / sum(int(row["denominator"]) for row in latest_rows)
        if latest_rows and sum(int(row["denominator"]) for row in latest_rows)
        else 0
    )
    gap = rate - metric.target
    gap_class = "good" if gap >= 0 else "watch"
    gap_label = f"{gap * 100:+.1f} pts"

    return f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Selected metric</div>
        <div class="kpi-title">{metric.label}</div>
        <div class="kpi-note">{metric.description}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Year-to-date performance</div>
        <div class="kpi-value">{pct(rate)}</div>
        <div class="kpi-note">{numerator:,} of {denominator:,} eligible encounters</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">AHA-style target</div>
        <div class="kpi-value">{pct(metric.target)}</div>
        <div class="kpi-note {gap_class}">{gap_label} versus target</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Latest month</div>
        <div class="kpi-value">{pct(latest_rate)}</div>
        <div class="kpi-note">{MONTHS[-1].strftime('%B %Y')}</div>
      </div>
    </div>
    """


metric_select = Select(
    title="AHA stroke metric",
    value=METRICS[0].key,
    options=[(metric.key, metric.label) for metric in METRICS],
    width=330,
)
hospital_select = Select(title="Hospital", value="All Hospitals", options=HOSPITALS, width=260)

trend_source = ColumnDataSource(data={})
bar_source = ColumnDataSource(data={})
table_source = ColumnDataSource(data={})
summary_div = Div(width=1180)

trend_plot = figure(
    title="Monthly performance trend",
    x_axis_type="datetime",
    height=330,
    sizing_mode="stretch_width",
    tools="pan,wheel_zoom,box_zoom,reset,save",
    toolbar_location="above",
)
trend_plot.line("month", "rate", source=trend_source, line_width=3, color="#165a72", legend_label="Observed")
trend_plot.scatter("month", "rate", source=trend_source, size=9, color="#165a72")
trend_plot.line("month", "target", source=trend_source, line_width=2, color="#ba3b46", line_dash="dashed", legend_label="Target")
trend_plot.yaxis.axis_label = "Rate"
trend_plot.y_range.start = 0.55
trend_plot.y_range.end = 1.0
trend_plot.legend.location = "bottom_right"
trend_plot.add_tools(
    HoverTool(
        tooltips=[
            ("Month", "@month_label"),
            ("Rate", "@rate{0.0%}"),
            ("Target", "@target{0.0%}"),
            ("Cases", "@numerator / @denominator"),
        ]
    )
)

bar_plot = figure(
    title="Hospital comparison",
    x_range=HOSPITALS[1:],
    height=330,
    sizing_mode="stretch_width",
    tools="pan,wheel_zoom,box_zoom,reset,save",
    toolbar_location="above",
)
bar_plot.vbar(x="hospital", top="rate", source=bar_source, width=0.62, color="#2a9d8f")
bar_plot.yaxis.axis_label = "Rate"
bar_plot.y_range.start = 0.55
bar_plot.y_range.end = 1.0
bar_plot.xaxis.major_label_orientation = 0.35
bar_plot.add_tools(
    HoverTool(
        tooltips=[
            ("Hospital", "@hospital"),
            ("Rate", "@rate{0.0%}"),
            ("Gap", "@gap{+0.0%}"),
            ("Cases", "@numerator / @denominator"),
        ]
    )
)
target_span = Span(location=METRICS[0].target, dimension="width", line_color="#ba3b46", line_dash="dashed", line_width=2)
bar_plot.add_layout(target_span)

metric_table = DataTable(
    source=table_source,
    columns=[
        TableColumn(field="metric", title="Metric", width=310),
        TableColumn(field="rate", title="YTD Rate", formatter=NumberFormatter(format="0.0%"), width=100),
        TableColumn(field="target", title="Target", formatter=NumberFormatter(format="0.0%"), width=90),
        TableColumn(field="gap", title="Gap", formatter=NumberFormatter(format="+0.0%"), width=80),
        TableColumn(field="numerator", title="Numerator", width=90),
        TableColumn(field="denominator", title="Denominator", width=100),
    ],
    height=275,
    sizing_mode="stretch_width",
    index_position=None,
)

header = Div(
    text="""
    <div class="hero">
      <div class="eyebrow">Synthetic demo dashboard</div>
      <h1>AHA Stroke Metrics</h1>
      <p>Track core stroke quality measures across hospitals, compare performance to simple targets, and identify measures needing follow-up.</p>
    </div>
    """,
    sizing_mode="stretch_width",
)

footer = Div(
    text="""
    <div class="footer">
      Demo data is synthetic and is not endorsed by the American Heart Association. Replace the in-memory generator with validated source data before clinical or regulatory use.
    </div>
    """,
    sizing_mode="stretch_width",
)

APP_CSS = """
:host {
  --ink: #17313b;
  --muted: #5f7279;
  --paper: #f7f3eb;
  --card: #fffdf8;
  --teal: #165a72;
  --red: #ba3b46;
  --green: #2a9d8f;
  --line: rgba(23, 49, 59, 0.14);
  display: block;
  color: var(--ink);
  background:
    radial-gradient(circle at 16% 8%, rgba(42, 157, 143, 0.18), transparent 26rem),
    linear-gradient(135deg, #f9f2e4 0%, #eef6f4 100%);
  font-family: Georgia, 'Times New Roman', serif;
  padding: 24px;
  box-sizing: border-box;
}
.hero {
  border: 1px solid var(--line);
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(255,253,248,0.96), rgba(242,248,246,0.88));
  padding: 28px 32px;
  box-shadow: 0 18px 45px rgba(23, 49, 59, 0.10);
}
.eyebrow {
  color: var(--red);
  font-family: Verdana, sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
h1 {
  margin: 8px 0 6px;
  font-size: clamp(34px, 6vw, 62px);
  line-height: 0.98;
}
p {
  color: var(--muted);
  font-family: Verdana, sans-serif;
  font-size: 15px;
  max-width: 860px;
}
.kpi-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  margin: 8px 0 2px;
}
.kpi-card {
  min-height: 112px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--card);
  padding: 18px;
  box-shadow: 0 10px 28px rgba(23, 49, 59, 0.08);
}
.kpi-label {
  color: var(--muted);
  font-family: Verdana, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.kpi-title {
  margin-top: 9px;
  font-size: 24px;
  line-height: 1.05;
}
.kpi-value {
  margin-top: 8px;
  color: var(--teal);
  font-size: 38px;
  line-height: 1;
}
.kpi-note {
  margin-top: 10px;
  color: var(--muted);
  font-family: Verdana, sans-serif;
  font-size: 12px;
  line-height: 1.4;
}
.kpi-note.good { color: var(--green); font-weight: 700; }
.kpi-note.watch { color: var(--red); font-weight: 700; }
.footer {
  color: var(--muted);
  font-family: Verdana, sans-serif;
  font-size: 12px;
  padding: 10px 0 22px;
}
@media (max-width: 900px) {
  :host { padding: 14px; }
  .hero { padding: 22px; border-radius: 18px; }
  .kpi-grid { grid-template-columns: 1fr; }
}
"""


def update() -> None:
    metric = METRIC_BY_KEY[metric_select.value]
    selected_rows = rows_for(metric.key, hospital_select.value)
    monthly = aggregate_by_month(selected_rows)
    hospitals = aggregate_by_hospital(rows_for(metric.key, "All Hospitals"))

    trend_source.data = {
        "month": [row["month"] for row in monthly],
        "month_label": [row["month_label"] for row in monthly],
        "rate": [row["rate"] for row in monthly],
        "target": [row["target"] for row in monthly],
        "numerator": [row["numerator"] for row in monthly],
        "denominator": [row["denominator"] for row in monthly],
    }
    bar_source.data = {
        "hospital": [row["hospital"] for row in hospitals],
        "rate": [row["rate"] for row in hospitals],
        "target": [row["target"] for row in hospitals],
        "gap": [row["gap"] for row in hospitals],
        "numerator": [row["numerator"] for row in hospitals],
        "denominator": [row["denominator"] for row in hospitals],
    }
    table_rows = metric_table_rows(hospital_select.value)
    table_source.data = {
        "metric": [row["metric"] for row in table_rows],
        "rate": [row["rate"] for row in table_rows],
        "target": [row["target"] for row in table_rows],
        "gap": [row["gap"] for row in table_rows],
        "numerator": [row["numerator"] for row in table_rows],
        "denominator": [row["denominator"] for row in table_rows],
    }

    trend_plot.title.text = f"Monthly performance trend: {metric.label}"
    bar_plot.title.text = f"Hospital comparison: {metric.label}"
    target_span.location = metric.target
    summary_div.text = build_kpi_cards(metric, selected_rows)


metric_select.on_change("value", lambda attr, old, new: update())
hospital_select.on_change("value", lambda attr, old, new: update())
update()

controls = row(metric_select, hospital_select, sizing_mode="stretch_width")
charts = row(trend_plot, bar_plot, sizing_mode="stretch_width")
layout = column(header, controls, summary_div, charts, metric_table, footer, sizing_mode="stretch_width")
layout.stylesheets = [InlineStyleSheet(css=APP_CSS)]

curdoc().add_root(layout)
curdoc().title = "AHA Stroke Metrics"
