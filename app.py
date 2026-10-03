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
from bokeh.models import ColumnDataSource, DataTable, Div, HoverTool, NumberFormatter, Select, TableColumn
from bokeh.plotting import figure

KM_PER_MINUTE = 1.0  # rough average drive speed of 60 km/h
CATCHMENTS = {"15": 15, "30": 30, "45": 45, "60": 60}
INSIDE = "#0f766e"
OUTSIDE = "#cbd5e1"
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
table_source = ColumnDataSource(data={"town": [], "minutes": [], "cases": []})

select = Select(title="Drive-time catchment (minutes)", value="30", options=list(CATCHMENTS), width=240)
summary = Div(sizing_mode="stretch_width")

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

table = DataTable(
    source=table_source,
    columns=[
        TableColumn(field="town", title="Town", width=140),
        TableColumn(field="minutes", title="Minutes", width=70),
        TableColumn(field="cases", title="Cases", width=70, formatter=NumberFormatter(format="0,0")),
    ],
    width=300,
    height=420,
    index_position=None,
)


def update() -> None:
    limit = CATCHMENTS[select.value]
    inside = [m <= limit for m in TOWNS["minutes"]]
    source.data = {**TOWNS, "color": [INSIDE if i else OUTSIDE for i in inside]}
    selected_ring.glyph.radius = limit * KM_PER_MINUTE

    picked = sorted(
        ((t, m, c) for t, m, c, i in zip(TOWNS["town"], TOWNS["minutes"], TOWNS["cases"], inside) if i),
        key=lambda r: r[1],
    )
    table_source.data = {
        "town": [p[0] for p in picked],
        "minutes": [p[1] for p in picked],
        "cases": [p[2] for p in picked],
    }
    covered = sum(p[2] for p in picked)
    total = sum(TOWNS["cases"])
    summary.text = (
        f"<h3 style='margin:0'>{len(picked)} of {len(NAMES)} towns within {limit} min</h3>"
        f"<p style='margin:4px 0 0'>{covered:,} of {total:,} stroke cases "
        f"({covered / total:.0%}) · synthetic data</p>"
    )


select.on_change("value", lambda attr, old, new: update())
update()

sidebar = column(select, summary, table, width=320)
header = Div(
    text=f"""
    <div style="border-left:6px solid {INSIDE}; padding:2px 0 2px 14px; font-family:sans-serif">
      <div style="font-size:30px; font-weight:800; color:#0f172a; letter-spacing:-0.5px">
        Hospital <span style="color:{INSIDE}">Catchment</span>
      </div>
      <div style="font-size:13px; color:#64748b; margin-top:2px">Stroke cases by drive time</div>
    </div>
    """,
    sizing_mode="stretch_width",
)

curdoc().add_root(column(header, row(plot, sidebar)))
curdoc().title = "Hospital Catchment"
