# Customer Segmentation

End-to-end customer segmentation pipeline built on the
[Customer Personality Analysis](https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis)
dataset. The project covers exploratory analysis, RFM scoring with K-Means,
synthetic data expansion for BigQuery, and an interactive dashboard aimed at
a business audience — live at
[pablobagano.app/datalab/customer-segmentation](https://pablobagano.app/datalab/customer-segmentation).

## Pipeline

```
Raw customer data → EDA & cleaning → RFM scoring (K-Means) → Segmentation
                                                    │
                                                    ├── XGBoost regression (predict Total_Spent)
                                                    └── Synthetic expansion → BigQuery
                                                          ├── score_raw_data_table.py → customer_segments table
                                                          ├── create_materialized_views.py → mv_segment_* views
                                                          └── export_dashboard_data.py → static JSON
                                                                └── Next.js dashboard (pablobagano.app)
```

Each stage is self-contained in its own notebook so the pipeline can be rerun
end-to-end or picked up at any intermediate step.

## Repository structure

```
customer_segmentation/
├── dashboard/            # Streamlit app (superseded by the Next.js dashboard
│                         #   at pablobagano.app — kept for local exploration)
├── notebooks/            # Analysis and modeling notebooks
│   ├── exploratory_analysis.ipynb
│   ├── customer_kmeans.ipynb
│   ├── database_expansion.ipynb
│   ├── big_query_dataset.ipynb
│   └── drafts.ipynb          (local-only, gitignored)
├── data/                 # CSVs/Parquet used and produced by the notebooks
├── models/               # Trained K-Means artefacts (.joblib)
├── src/                  # Shared Python helpers
│   ├── custom_functions.py
│   ├── big_query_functions.py   # synthetic data generation/validation
│   ├── bq_table_creation.py     # BigQuery table creation (schema, partitioning, clustering)
│   └── customer_scoring.py      # apply the trained K-Means models to a DataFrame (RFM scoring)
├── scripts/              # One-off / re-runnable maintenance scripts
│   ├── migrate_raw_data_partitioning.py
│   ├── score_raw_data_table.py     # scores raw_data at scale -> customer_segments table
│   ├── create_materialized_views.py  # builds the mv_segment_* BigQuery views
│   └── export_dashboard_data.py    # exports the views + segmented_data.csv
│                                    #   to static JSON for the Next.js dashboard
├── bigquery/             # BigQuery schemas + pipeline notes (some files gitignored)
├── requirements.txt      # Top-level dependencies
├── pyrightconfig.json    # points the editor's type checker at .venv + src/
├── .gitignore
└── README.md
```

Notebook code resolves paths relative to `notebooks/`, so `../data/...`,
`../models/...`, and `sys.path.append('../src')` are used throughout.

## Getting started

Clone the repo and install dependencies:

```bash
git clone <repo-url>
cd customer_segmentation
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Launch Jupyter and run the notebooks in order from the `notebooks/` folder:

```bash
jupyter lab notebooks/
```

## Notebooks

**`exploratory_analysis.ipynb`** — data cleaning, outlier treatment, feature
engineering (`Total_Spent`, `Total_Purchases`, `Highest_Spent`, `Age`),
imputation of missing `Income` values, and univariate/bivariate analysis of
customer demographics and purchasing behavior. Produces `treated_data.csv`.

**`customer_kmeans.ipynb`** — RFM scoring with three independent K-Means
models (one per component: Frequency, Monetary, Recency). Hyperparameters are
selected via `RandomizedSearchCV`. Each customer is scored 0–3 per component,
combined into an `RMF_Score`, and assigned to a segment (`Inactive`,
`Occasional`, `Moderate`, `Loyal`, `Premium`). Also computes Average Purchase
Value per segment. Produces `segmented_data.csv` and the three trained
K-Means models in `models/`.

**`database_expansion.ipynb`** — synthesizes 1,000,000 rows from the group
means and standard deviations (`Marital_Status` × `Education`) of the cleaned
data, preserving realistic variability. Produces
`data/synthetic_marketing_campaign.parquet`.

**`big_query_dataset.ipynb`** — creates the `raw_data` BigQuery dataset/table
from `bigquery/schemas/raw_data.json` and loads the synthetic parquet into
it. The table is partitioned by month on `Dt_Customer` and clustered on
`Marital_Status, Education`.

## BigQuery tables

- **`raw_data`** — 1M synthetic rows, partitioned by month on `Dt_Customer`,
  clustered on `Marital_Status, Education`. Source of truth; never mutated.
- **`customer_segments`** — output of `scripts/score_raw_data_table.py`.
  Every row of `raw_data` scored with the trained K-Means models, producing
  `RMF_Score` and `Segmentation`. Partitioned by month on `Dt_Customer`,
  clustered on `Segmentation`. Join back to `raw_data` on `ID` for full
  customer attributes.
- **`mv_segment_counts`, `mv_segment_metrics`, `mv_segment_demo`,
  `mv_segment_spend`, `mv_segment_channels`, `mv_segment_campaigns`** — six
  static materialized views (`scripts/create_materialized_views.py`),
  pre-aggregating `customer_segments` (joined to `raw_data` where needed) by
  `Segmentation` — segment sizes/RFM metrics, demographic breakdowns, product
  spend, channel mix, and campaign acceptance. Recreated on demand, not
  auto-refreshing; they're the source for the dashboard's segment-level data.

## Dashboard

Live at
[pablobagano.app/datalab/customer-segmentation](https://pablobagano.app/datalab/customer-segmentation)
— a Next.js app in a separate repo (`webcv_frontend`, part of the
[pablobagano.app](https://pablobagano.app) portfolio site), replacing the
original Streamlit app. `scripts/export_dashboard_data.py` exports the six
materialized views above plus `data/segmented_data.csv` to static JSON,
which is copied into `webcv_frontend` — no live BigQuery credentials or
runtime queries in production, just static data and instant page loads.

Pages:

- **Customer Segmentation** (`/datalab/customer-segmentation`) — RFM
  methodology, a 3D cluster view over the real 2,237-customer training set,
  a per-segment deep-dive (personas, scorecards, demographics, spend/channel/
  campaign breakdowns) and a segment comparison table + parallel-coordinates
  chart — the latter two computed against the model re-scored at
  1,000,000-row scale through the BigQuery pipeline above.
- **Customer Lookup** (`/datalab/customer-segmentation/lookup`) — find a
  real customer by ID and see their RFM profile against their segment and
  population medians.

The Streamlit app under `dashboard/` still works locally
(`streamlit run dashboard/app.py`) for ad hoc exploration, but is no longer
the deployed dashboard.

## Roadmap

- [x] Exploratory data analysis and cleaning
- [x] RFM scoring with K-Means
- [x] Database expansion for scale testing (1M synthetic rows, uploaded to a
      partitioned + clustered BigQuery table)
- [x] Apply the trained K-Means models to `raw_data` at scale
      (`scripts/score_raw_data_table.py` → `customer_segments` table)
- [x] Materialized views for segment-level BigQuery aggregates
      (`scripts/create_materialized_views.py`)
- [x] Next.js dashboard, live at pablobagano.app (replaces Streamlit)
- [ ] XGBoost regression to predict `Total_Spent` for new customers
- [ ] BigQuery ML pipeline (KMeans + XGBoost + segmentation SQL)

## Dataset

The original dataset is the
[Customer Personality Analysis](https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis)
dataset on Kaggle (~2,200 rows). Features cover demographics (age, income,
marital status, education, household composition), product spend across six
categories, campaign acceptance history, and purchase channels (web,
catalog, store).
