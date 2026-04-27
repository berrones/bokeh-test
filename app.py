"""Simple Bokeh app for AHA stroke quality metrics.

The data in this demo is synthetic. Replace `build_demo_rows()` with a database,
CSV, or API-backed data source before using it for operational reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import random

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource,
    DataTable,
    DatetimeTickFormatter,
    Div,
    HoverTool,
    InlineStyleSheet,
    NumeralTickFormatter,
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

PANEL_BG = "#0f172a"
TEXT_PRIMARY = "#f8fafc"
TEXT_MUTED = "#94a3b8"
GRID_LINE = "#24324a"
EDGE_LINE = "#334155"
ACCENT_CYAN = "#22d3ee"
ACCENT_ORANGE = "#f97316"
ACCENT_LIME = "#a3e635"
ACCENT_ROSE = "#fb7185"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def performance_status(gap: float) -> tuple[str, str]:
    if gap >= 0.03:
        return "Ahead of target", "good"
    if gap >= 0:
        return "On target", "good"
    if gap >= -0.02:
        return "Watch closely", "watch"
    return "Needs intervention", "alert"


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
    monthly = aggregate_by_month(rows)
    numerator = sum(int(row["numerator"]) for row in rows)
    denominator = sum(int(row["denominator"]) for row in rows)
    rate = numerator / denominator if denominator else 0
    latest_rate = float(monthly[-1]["rate"]) if monthly else 0
    previous_rate = float(monthly[-2]["rate"]) if len(monthly) > 1 else latest_rate
    delta = latest_rate - previous_rate
    best_month = max(monthly, key=lambda month: float(month["rate"])) if monthly else None
    gap = rate - metric.target
    status_label, status_class = performance_status(gap)
    gap_class = "good" if gap >= 0 else "alert"
    gap_label = f"{gap * 100:+.1f} pts"
    delta_class = "good" if delta >= 0 else "alert"
    delta_label = f"{delta * 100:+.1f} pts vs prior month"

    return f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Selected metric</div>
        <div class="status-pill {status_class}">{status_label}</div>
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
        <div class="kpi-label">Latest month momentum</div>
        <div class="kpi-value">{pct(latest_rate)}</div>
        <div class="kpi-note {delta_class}">{delta_label}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Best month</div>
        <div class="kpi-value">{pct(float(best_month["rate"]) if best_month else 0)}</div>
        <div class="kpi-note">{best_month["month_label"] if best_month else "No data"}</div>
      </div>
    </div>
    """


def style_plot(plot: figure) -> None:
    plot.background_fill_color = PANEL_BG
    plot.border_fill_color = PANEL_BG
    plot.outline_line_color = EDGE_LINE
    plot.min_border_left = 12
    plot.min_border_right = 12
    plot.min_border_top = 14
    plot.min_border_bottom = 10
    plot.toolbar.autohide = True
    plot.toolbar.logo = None

    plot.title.text_color = TEXT_PRIMARY
    plot.title.text_font = "Trebuchet MS"
    plot.title.text_font_size = "16pt"
    plot.title.text_font_style = "bold"
    plot.title.align = "left"

    for grid in plot.grid:
        grid.grid_line_color = GRID_LINE
        grid.grid_line_alpha = 0.7
        grid.minor_grid_line_color = None

    for axis in [*plot.xaxis, *plot.yaxis]:
        axis.axis_line_color = EDGE_LINE
        axis.major_tick_line_color = EDGE_LINE
        axis.minor_tick_line_color = None
        axis.major_label_text_color = TEXT_MUTED
        axis.major_label_text_font = "Avenir Next"
        axis.major_label_text_font_size = "10pt"
        axis.axis_label_text_color = TEXT_MUTED
        axis.axis_label_text_font = "Avenir Next"
        axis.axis_label_text_font_style = "bold"

    plot.yaxis.formatter = NumeralTickFormatter(format="0%")


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
summary_div = Div(sizing_mode="stretch_width")

trend_plot = figure(
    title="Monthly performance trend",
    x_axis_type="datetime",
    height=330,
    sizing_mode="stretch_width",
    tools="pan,wheel_zoom,box_zoom,reset,save",
    toolbar_location="above",
)
trend_plot.varea(x="month", y1="rate", y2="target", source=trend_source, fill_color=ACCENT_CYAN, fill_alpha=0.10)
trend_plot.line("month", "rate", source=trend_source, line_width=4, color=ACCENT_CYAN, legend_label="Observed")
trend_plot.scatter("month", "rate", source=trend_source, size=10, fill_color=ACCENT_CYAN, line_color=TEXT_PRIMARY)
trend_plot.line("month", "target", source=trend_source, line_width=2, color=ACCENT_ORANGE, line_dash="dashed", legend_label="Target")
trend_plot.yaxis.axis_label = "Rate"
trend_plot.y_range.start = 0.55
trend_plot.y_range.end = 1.0
trend_plot.legend.location = "bottom_right"
trend_plot.legend.background_fill_color = PANEL_BG
trend_plot.legend.background_fill_alpha = 0.9
trend_plot.legend.label_text_color = TEXT_PRIMARY
trend_plot.legend.border_line_color = EDGE_LINE
trend_plot.xaxis.formatter = DatetimeTickFormatter(months="%b", years="%b %Y")
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
style_plot(trend_plot)

bar_plot = figure(
    title="Hospital comparison",
    x_range=HOSPITALS[1:],
    height=330,
    sizing_mode="stretch_width",
    tools="pan,wheel_zoom,box_zoom,reset,save",
    toolbar_location="above",
)
bar_plot.vbar(
    x="hospital",
    top="rate",
    source=bar_source,
    width=0.62,
    fill_color="color",
    line_color="line_color",
    line_width=2,
)
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
target_span = Span(location=METRICS[0].target, dimension="width", line_color=ACCENT_ORANGE, line_dash="dashed", line_width=2)
bar_plot.add_layout(target_span)
style_plot(bar_plot)

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
    css_classes=["metric-table"],
)

header = Div(
    text="""
    <div class="hero">
      <div class="eyebrow">Synthetic demo dashboard</div>
      <h1>AHA Stroke Metrics</h1>
      <p>Monitor stroke quality performance with a darker command-center view, faster monthly trend reads, and immediate visibility into which measures are beating or missing target.</p>
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
  --bg: #050816;
  --panel: #0f172a;
  --panel-alt: #111c34;
  --ink: #f8fafc;
  --muted: #94a3b8;
  --card: rgba(15, 23, 42, 0.9);
  --cyan: #22d3ee;
  --orange: #f97316;
  --lime: #a3e635;
  --rose: #fb7185;
  --line: rgba(148, 163, 184, 0.18);
  display: block;
  color: var(--ink);
  background:
    radial-gradient(circle at 12% 10%, rgba(34, 211, 238, 0.24), transparent 24rem),
    radial-gradient(circle at 84% 4%, rgba(249, 115, 22, 0.20), transparent 18rem),
    radial-gradient(circle at 70% 82%, rgba(251, 113, 133, 0.14), transparent 22rem),
    linear-gradient(145deg, #050816 0%, #081122 45%, #0b1630 100%);
  font-family: 'Avenir Next', 'Trebuchet MS', sans-serif;
  padding: 24px;
  box-sizing: border-box;
}
.hero {
  border: 1px solid var(--line);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(34, 211, 238, 0.12), transparent 42%),
    linear-gradient(160deg, rgba(15, 23, 42, 0.96), rgba(17, 28, 52, 0.94));
  padding: 28px 32px;
  box-shadow: 0 24px 60px rgba(2, 6, 23, 0.48);
  position: relative;
  overflow: hidden;
}
.hero::after {
  content: "";
  position: absolute;
  inset: auto -6% -40% auto;
  width: 22rem;
  height: 22rem;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(249, 115, 22, 0.22), transparent 68%);
  pointer-events: none;
}
.eyebrow {
  color: var(--orange);
  font-family: 'Avenir Next', sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
h1 {
  margin: 8px 0 6px;
  font-size: clamp(34px, 6vw, 62px);
  line-height: 0.94;
  letter-spacing: -0.03em;
}
p {
  color: var(--muted);
  font-family: 'Avenir Next', sans-serif;
  font-size: 15px;
  max-width: 860px;
}
.bk-Row.controls-shell {
  margin: 8px 0 4px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.76);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
}
.kpi-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(5, minmax(160px, 1fr));
  margin: 8px 0 2px;
}
.kpi-card {
  min-height: 112px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(17, 28, 52, 0.96), rgba(15, 23, 42, 0.92));
  padding: 18px;
  box-shadow: 0 14px 36px rgba(2, 6, 23, 0.35);
}
.kpi-label {
  color: var(--muted);
  font-family: 'Avenir Next', sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  margin-top: 10px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.status-pill.good {
  color: #d9f99d;
  background: rgba(163, 230, 53, 0.14);
  border: 1px solid rgba(163, 230, 53, 0.32);
}
.status-pill.watch {
  color: #fde68a;
  background: rgba(249, 115, 22, 0.14);
  border: 1px solid rgba(249, 115, 22, 0.30);
}
.status-pill.alert {
  color: #fecdd3;
  background: rgba(251, 113, 133, 0.14);
  border: 1px solid rgba(251, 113, 133, 0.30);
}
.kpi-title {
  margin-top: 9px;
  font-size: 24px;
  line-height: 1.05;
}
.kpi-value {
  margin-top: 8px;
  color: var(--cyan);
  font-size: 38px;
  line-height: 1;
  font-weight: 800;
}
.kpi-note {
  margin-top: 10px;
  color: var(--muted);
  font-family: 'Avenir Next', sans-serif;
  font-size: 12px;
  line-height: 1.4;
}
.kpi-note.good { color: var(--lime); font-weight: 700; }
.kpi-note.watch { color: #fde68a; font-weight: 700; }
.kpi-note.alert { color: var(--rose); font-weight: 700; }
.bk-input,
select.bk-input {
  background: rgba(8, 17, 34, 0.92);
  color: var(--ink);
  border: 1px solid rgba(34, 211, 238, 0.20);
  border-radius: 12px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
}
.bk-input option {
  background: #081122;
  color: var(--ink);
}
.bk-input:focus,
select.bk-input:focus {
  outline: none;
  border-color: rgba(34, 211, 238, 0.56);
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.16);
}
.bk-input-group label,
.bk-InputGroup label {
  color: var(--muted);
  font-family: 'Avenir Next', sans-serif;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.metric-table .slick-header-columns {
  background: #101a30 !important;
  border-bottom: 1px solid var(--line) !important;
}
.metric-table .slick-header-column {
  color: var(--muted) !important;
  font-weight: 700 !important;
}
.metric-table .grid-canvas {
  background: rgba(15, 23, 42, 0.74) !important;
}
.metric-table .slick-row {
  background: transparent !important;
}
.metric-table .slick-cell {
  color: var(--ink) !important;
  border-color: rgba(148, 163, 184, 0.08) !important;
}
.footer {
  color: var(--muted);
  font-family: 'Avenir Next', sans-serif;
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
        "color": [ACCENT_CYAN if float(row["gap"]) >= 0 else ACCENT_ROSE for row in hospitals],
        "line_color": [ACCENT_LIME if float(row["gap"]) >= 0 else ACCENT_ORANGE for row in hospitals],
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

controls = row(metric_select, hospital_select, sizing_mode="stretch_width", css_classes=["controls-shell"])
charts = row(trend_plot, bar_plot, sizing_mode="stretch_width")
layout = column(header, controls, summary_div, charts, metric_table, footer, sizing_mode="stretch_width")
layout.stylesheets = [InlineStyleSheet(css=APP_CSS)]

curdoc().add_root(layout)
curdoc().title = "AHA Stroke Metrics"
