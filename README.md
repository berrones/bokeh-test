# Hospital Catchment Map
## heading 2
A very simple Bokeh app: a hospital (red star) with drive-time rings and synthetic towns sized by stroke cases. Choose a catchment (15/30/45/60 min) to highlight the towns inside it.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bokeh serve app.py --show
```

Data is synthetic (`build_towns()` in `app.py`); coordinates are km offsets from the hospital, with no map tiles or network needed.
