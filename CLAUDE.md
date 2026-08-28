# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

End-to-end customer segmentation pipeline on the Kaggle "Customer Personality
Analysis" dataset (~2,240 rows). The pipeline runs entirely through Jupyter
notebooks (no test suite, no build step) and produces CSV/Parquet artifacts
consumed by a Streamlit dashboard and a BigQuery upload path:

```
Raw customer data → EDA & cleaning → RFM scoring (K-Means) → Segmentation
                                                    │
                                                    ├── Synthetic expansion → BigQuery
                                                    └── Streamlit dashboard
```

Each notebook stage is self-contained and writes its output to `data/` or
`models/`, so later stages (or the dashboard) can be run independently once
the upstream CSVs exist.

## Commands

```bash
# Environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt              # notebook / analysis deps
pip install -r dashboard/requirements.txt     # dashboard-only deps (separate, pinned)

# Run the notebook pipeline (in order)
jupyter lab notebooks/
# notebooks/exploratory_analysis.ipynb  → data/treated_data.csv
# notebooks/customer_kmeans.ipynb       → data/segmented_data.csv, models/kmeans_*.joblib
# notebooks/database_expansion.ipynb    → data/synthetic_marketing_campaign.parquet
# notebooks/big_query_dataset.ipynb     → BigQuery dataset/table creation + upload

# Run the dashboard
streamlit run dashboard/app.py
```

There is no lint/test/build tooling configured in this repo — don't invent
`pytest`/`ruff`/etc. invocations.

## Architecture

### Notebook pipeline → data contracts

The notebooks are the source of truth for data transformations; `src/` and
`dashboard/` only *consume* their outputs. When changing a notebook, keep the
downstream CSV schema stable or update every consumer listed below.

- **`exploratory_analysis.ipynb`** — cleans `data/marketing_campaign.csv`
  (outlier treatment, `Income` imputation, `Marital_Status` consolidation —
  `Alone`/`Absurd`/`YOLO` merged into `Single`), engineers `Total_Spent`,
  `Total_Purchases`, `Highest_Spent`, `Age`. Produces `data/treated_data.csv`.
- **`customer_kmeans.ipynb`** — three independent K-Means models (Recency,
  Frequency, Monetary), tuned via `RandomizedSearchCV`, saved to
  `models/kmeans_{recency,freq,monetary}.joblib`. Each customer gets a 0–3
  score per component, combined into `RMF_Score` (0–9), and mapped to a
  segment: `Inactive`, `Occasional`, `Moderate`, `Loyal`, `Premium` (this
  five-value order — `SEGMENT_ORDER` in `dashboard/charts.py` — is used
  everywhere segments are sorted/colored). Produces `data/segmented_data.csv`,
  which is the dashboard's primary data source.
- **`database_expansion.ipynb`** — synthesizes large-scale data (default
  1,000,000 rows) by sampling from per-group (`Marital_Status` ×
  `Education`) means/stds computed from `treated_data.csv`
  (`data/grouped_data_mean.csv`, `data/grouped_data_std.csv`), plus
  `data/proportions_highest_spent.csv` for categorical assignment. The actual
  generation/validation logic lives in `src/big_query_functions.py`
  (`generate_synthetic_campaign_data`, `validate_synthetic_campaign_data`,
  `write_synthetic_dataset`) — the notebook orchestrates, the module does the
  work. Output: `data/synthetic_marketing_campaign.parquet` (the one
  `*.parquet` file not gitignored — see `.gitignore`).
- **`big_query_dataset.ipynb`** — creates the BigQuery dataset/table and
  uploads the synthetic parquet, using `src/bq_table_creation.py`
  (`table_creation`, driven by JSON schema files in `bigquery/schemas/`; the
  `raw_data` table is partitioned by month on `Dt_Customer` and clustered on
  `Marital_Status, Education` — pass `time_partitioning_field` /
  `clustering_fields` to `table_creation()` for other tables).
  `bigquery/instructions.json` / `bigquery/bq_instructions.json` are
  local-only planning notes (gitignored) — read them for pipeline context
  but don't treat them as authoritative once the code diverges.

### `src/` — shared helpers imported by notebooks (via `sys.path.append('../src')`)

- `custom_functions.py` — `error_handling()`, a traceback-printing helper
  used in notebook exception handlers.
- `big_query_functions.py` — synthetic data generation/validation (see
  above). Pure functions operating on DataFrames; no notebook or Streamlit
  state.
- `bq_table_creation.py` — `table_creation()`, idempotent BigQuery table
  creation from a JSON schema file (skips if the table already exists;
  accepts optional `time_partitioning_field`/`time_partitioning_type`/
  `clustering_fields` kwargs).

### `dashboard/` — Streamlit app

Multi-page app; `app.py` is the landing page, `pages/1..4_*.py` are the
analytical views, loaded by Streamlit's file-based page routing. Structure:

- `data_paths.py` — single source of truth for `data/*.csv` paths, resolved
  relative to `dashboard/` (`../data/...`). Import from here rather than
  hardcoding paths in a page.
- `charts.py` — **all** figure-factory functions. Convention: every public
  function takes a DataFrame (plus a few optional dimension args) and returns
  a Plotly `Figure` or a `dict` of KPI values — functions are pure and never
  call `st.*`. Naming prefixes group functions by dashboard section:
  `kpi_*`, `demo_*`, `spend_*`, `channel_*`, `campaign_*`, `cross_*`,
  `cluster_*`/`segment_*`/`segments_*` (Cluster Explorer page), `lookup_*`
  (Customer Lookup page). Page modules own layout/filters/rendering and call
  into this module for every chart — new charts should follow the same
  pattern (pure function in `charts.py`, section-prefixed name, ends with
  `return _apply_theme(fig)`).
- `helpers.py` — small non-chart utilities (currently `dataset_info()` for a
  column-summary table used on the Raw Data page).
- Pages 1–2 (`Raw_Data`, `Cleaned_Data`) work off `treated_data.csv`; pages
  3–4 (`Cluster_Explorer`, `Customer_Lookup`) work off `segmented_data.csv`
  and share the `SEGMENT_ORDER`/`SEGMENT_PALETTE`/personas-and-actions
  conventions defined in `charts.py` — keep the `PERSONAS`/`ACTIONS` dicts in
  `4_Customer_Lookup.py` in sync with `3_Cluster_Explorer.py` (noted in that
  file's module docstring).
- `dashboard/requirements.txt` is a separate, fully-pinned dependency set
  used for deploying the Streamlit app in isolation (e.g. Streamlit Cloud) —
  distinct from the top-level `requirements.txt`.

### Directories to ignore

`dash_junk/`, `rag_tests/`, `drafts/`, `anaconda_projects/`, `keys/`, and
`.ipynb_checkpoints/` are all gitignored — scratch/exploratory work, not part
of the shipped pipeline. `keys/` holds a live GCP service-account credential;
never read or print its contents.
