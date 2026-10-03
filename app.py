"""Simple Bokeh catchment map.

Synthetic towns are scattered around a hospital. Pick a drive-time catchment
and the map highlights the towns inside it, with a summary and table beside it.
Replace `build_towns()` with real data (lat/lon -> km offsets) when ready.
"""

from __future__ import annotations

import math
import random

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource,
    DataTable,
    Div,
    HoverTool,
    HTMLTemplateFormatter,
    InlineStyleSheet,
    NumberFormatter,
    Select,
    TableColumn,
    Toggle,
)
from bokeh.plotting import figure

KM_PER_MINUTE = 1.0  # rough average drive speed of 60 km/h
CATCHMENTS = {"15": 15, "30": 30, "45": 45, "60": 60}
INSIDE = "#0f766e"
OUTSIDE = "#cbd5e1"
THEMES = {
    "light": {"bg": "#ffffff", "panel": "#ffffff", "fg": "#0f172a", "muted": "#64748b", "grid": "#e2e8f0",
              "outside": "#cbd5e1", "stripe": "#f0fdfa", "hover": "#ccfbf1", "bar": "#99f6e4", "accent": INSIDE},
    "dark": {"bg": "#0b1220", "panel": "#111a2e", "fg": "#e2e8f0", "muted": "#94a3b8", "grid": "#24324a",
             "outside": "#475569", "stripe": "#13203a", "hover": "#134e4a", "bar": "#0f766e", "accent": "#2dd4bf"},
}
RING = "#0f766e"

NAMES = [
    "Ashford", "Brook Hollow", "Cedar Point", "Dunmore", "Elmwood", "Fairview", "Glen Rock",
    "Harlan", "Ivy Ridge", "Juniper", "Kingsley", "Larkspur", "Millbrook", "Northgate",
    "Oakdale", "Pinecrest", "Quarry Bend", "Riverton", "Stonebridge", "Thornfield",
    "Union Mills", "Violet Creek", "Westover", "Yarrow", "Zephyr Falls", "Bellmont",
    "Crestview", "Dover Flats", "Eastlake", "Foxhall",
]


def build_towns() -> dict[str, list]:
    rng = random.Random(7)
    data: dict[str, list] = {"town": [], "x": [], "y": [], "minutes": [], "cases": [], "size": []}
    for name in NAMES:
        distance = 4 + 56 * math.sqrt(rng.random())  # km, denser near the hospital
        angle = rng.uniform(0, 2 * math.pi)
        cases = max(5, int(rng.gauss(60, 25) * (1.3 - distance / 80)))
        data["town"].append(name)
        data["x"].append(distance * math.cos(angle))
        data["y"].append(distance * math.sin(angle))
        data["minutes"].append(round(distance / KM_PER_MINUTE))
        data["cases"].append(cases)
        data["size"].append(8 + cases ** 0.5 * 2.2)
    return data


TOWNS = build_towns()
source = ColumnDataSource(TOWNS)
table_source = ColumnDataSource(data={"town": [], "minutes": [], "cases": [], "share": [], "bar": []})

select = Select(title="Drive-time catchment (minutes)", value="30", options=list(CATCHMENTS), width=240)
summary = Div(sizing_mode="stretch_width")
dark_toggle = Toggle(label="Dark mode", button_type="default", width=120)

plot = figure(
    title="Hospital catchment",
    width=640,
    height=640,
    x_range=(-70, 70),
    y_range=(-70, 70),
    match_aspect=True,
    tools="pan,wheel_zoom,reset",
    toolbar_location="right",
)
plot.toolbar.logo = None
plot.xaxis.axis_label = "km east of hospital"
plot.yaxis.axis_label = "km north of hospital"

# Rings for every drive-time band, faint; the selected one is drawn on top.
ring_source = ColumnDataSource(data={"r": [m * KM_PER_MINUTE for m in CATCHMENTS.values()]})
plot.circle(0, 0, radius="r", source=ring_source, fill_alpha=0, line_color=RING, line_alpha=0.25, line_dash="dashed")
selected_ring = plot.circle(0, 0, radius=30, fill_color=INSIDE, fill_alpha=0.12, line_color=RING, line_width=3)

towns = plot.scatter(
    "x", "y", size="size", source=source, fill_color="color", fill_alpha=0.85, line_color="white",
)
plot.scatter([0], [0], marker="star", size=26, fill_color="#dc2626", line_color="white", line_width=2)
plot.add_tools(HoverTool(renderers=[towns], tooltips=[("Town", "@town"), ("Drive time", "@minutes min"), ("Stroke cases", "@cases")]))

CASES_BAR = HTMLTemplateFormatter(
    template="""
    <div style="position:relative; height:100%">
      <div style="position:absolute; left:0; top:15%; bottom:15%; width:<%= bar * 100 %>%; background:var(--bar); border-radius:3px"></div>
      <span style="position:relative; padding-left:4px"><%= value %></span>
    </div>
    """
)

TABLE_CSS = """
.slick-header-columns { background: #0f766e !important; }
.slick-viewport, .grid-canvas, .slick-row { background: var(--panel) !important; color: var(--fg) !important; }
.slick-header-column { color: white !important; font-weight: 700 !important; border-right: 1px solid #14b8a6 !important; }
.slick-row.odd { background: var(--stripe) !important; }
.slick-row:hover { background: var(--hover) !important; }
.slick-cell { border-color: var(--grid) !important; }
"""

table = DataTable(
    source=table_source,
    columns=[
        TableColumn(field="town", title="Town", width=120),
        TableColumn(field="minutes", title="Min", width=50),
        TableColumn(field="cases", title="Cases", width=100, formatter=CASES_BAR),
        TableColumn(field="share", title="Share", width=60, formatter=NumberFormatter(format="0%")),
    ],
    width=330,
    height=420,
    row_height=28,
    index_position=None,
    sortable=True,
    stylesheets=[InlineStyleSheet(css=TABLE_CSS)],
)


def mode() -> str:
    return "dark" if dark_toggle.active else "light"


def apply_theme() -> None:
    t = THEMES[mode()]
    root.stylesheets = [InlineStyleSheet(css=f":host {{ --bg:{t['bg']}; --panel:{t['panel']}; --fg:{t['fg']}; --muted:{t['muted']}; "
                                              f"--grid:{t['grid']}; --stripe:{t['stripe']}; --hover:{t['hover']}; --bar:{t['bar']}; "
                                              f"--accent:{t['accent']}; background:var(--bg); color:var(--fg); display:block; padding:12px; }}")]
    plot.background_fill_color = t["panel"]
    plot.border_fill_color = t["bg"]
    plot.outline_line_color = t["grid"]
    plot.title.text_color = t["fg"]
    for grid in plot.grid:
        grid.grid_line_color = t["grid"]
    for axis in (*plot.xaxis, *plot.yaxis):
        axis.major_label_text_color = t["muted"]
        axis.axis_label_text_color = t["muted"]
        axis.axis_line_color = t["grid"]
        axis.major_tick_line_color = t["grid"]
        axis.minor_tick_line_color = t["grid"]
    update()


def update() -> None:
    limit = CATCHMENTS[select.value]
    inside = [m <= limit for m in TOWNS["minutes"]]
    source.data = {**TOWNS, "color": [INSIDE if i else THEMES[mode()]["outside"] for i in inside]}
    selected_ring.glyph.radius = limit * KM_PER_MINUTE

    picked = sorted(
        ((t, m, c) for t, m, c, i in zip(TOWNS["town"], TOWNS["minutes"], TOWNS["cases"], inside) if i),
        key=lambda r: r[1],
    )
    covered = sum(p[2] for p in picked)
    top = max((p[2] for p in picked), default=1)
    table_source.data = {
        "town": [p[0] for p in picked],
        "minutes": [p[1] for p in picked],
        "cases": [p[2] for p in picked],
        "share": [p[2] / covered for p in picked],
        "bar": [p[2] / top for p in picked],
    }
    total = sum(TOWNS["cases"])
    summary.text = (
        f"<h3 style='margin:0'>{len(picked)} of {len(NAMES)} towns within {limit} min</h3>"
        f"<p style='margin:4px 0 0'>{covered:,} of {total:,} stroke cases "
        f"({covered / total:.0%}) · synthetic data</p>"
    )


select.on_change("value", lambda attr, old, new: update())
dark_toggle.on_change("active", lambda attr, old, new: apply_theme())

select.stylesheets = [InlineStyleSheet(css=".bk-input { background: var(--panel); color: var(--fg); border-color: var(--grid); }")]
sidebar = column(select, summary, table, width=350)
header = Div(
    text=f"""
    <div style="border-left:6px solid var(--accent); padding:2px 0 2px 14px; font-family:sans-serif">
      <div style="font-size:30px; font-weight:800; color:var(--fg); letter-spacing:-0.5px">
        Hospital <span style="color:var(--accent)">Catchment</span>
      </div>
      <div style="font-size:13px; color:var(--muted); margin-top:2px">Stroke cases by drive time</div>
    </div>
    """,
    sizing_mode="stretch_width",
)

root = column(row(header, dark_toggle, sizing_mode="stretch_width"), row(plot, sidebar), sizing_mode="stretch_width")
apply_theme()

curdoc().add_root(root)
curdoc().title = "Hospital Catchment"
