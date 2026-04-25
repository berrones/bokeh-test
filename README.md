# AHA Stroke Metrics Bokeh App

A small Bokeh server app for demoing AHA-style stroke quality metrics. The data is synthetic and generated in `app.py`.

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bokeh serve app.py --show
```

## Posit Connect

This project is intentionally deployment-friendly:

- `app.py` is the Bokeh server entry point.
- `requirements.txt` declares the Python dependency.
- The app does not need a database, secrets, or external files for the demo.

One common deployment path is `rsconnect-python`:

```bash
pip install rsconnect-python
rsconnect deploy bokeh --server <connect-server-name> app.py
```

Before using the app for real reporting, replace `build_demo_rows()` with validated encounter-level or aggregate quality data and confirm metric definitions with your organization's stroke quality team.
