# Construction Cost Estimator

A local web tool for fast, itemized construction cost estimates across six property types, with location cost adjustments and one-click Excel export.

Cost data and formulas were extracted and generalized from the ["Quick Estimate" feature](https://github.com/Bryant-blip/Self-Storage-Analysis-Suite) of the Self-Storage Analysis Suite.

## Property Types

- Self-Storage: Drive-Up
- Self-Storage: Climate Controlled
- Retail / QSR (Shell)
- Warehouse / Distribution
- Medical Office
- Multifamily — Garden Style

Each type has its own itemized per-square-foot cost breakdown (site work, foundation, structure, roofing, electrical, etc.) plus lump-sum line items, sourced from RSMeans 2024/2025 national averages and adjusted by a location cost factor.

## How it works

Enter a building type, square footage, quality tier, and city — the estimator computes an itemized per-SF cost breakdown adjusted for location, and can export the result as a formatted Excel workbook.

## Setup

```bash
pip install -r requirements.txt
python server.py   # → opens http://127.0.0.1:8000
```

No API keys, no database, no accounts — it's a standard-library `http.server` app (only third-party dependency is `openpyxl` for the Excel export), intentionally kept simple as a single-user local tool.

## Tech Stack

Python 3.11 · standard-library `http.server` · openpyxl

## Design Notes

This deliberately skips a web framework, database, and auth layer — a single-user local estimator doesn't need any of them, so it doesn't carry the weight. `estimator.py` (pure calculation logic, no I/O) is kept separate from `excel_export.py` and `server.py`, so the cost model can be tested or reused independently of the web layer.
