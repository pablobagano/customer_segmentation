# Customer Segmentation

End-to-end customer segmentation pipeline built on the
[Customer Personality Analysis](https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis)
dataset. The project covers exploratory analysis, RFM scoring with K-Means,
synthetic data expansion for BigQuery, and an interactive Streamlit dashboard
aimed at a business audience.

## Streamlit Apps
[Streamlit App for K-Means Segmentation](https://pablobagano-customersegmentation.streamlit.app/)

Streamlit App For `Total_Spent` Predicition: Model under construction

## Pipeline

```
Raw customer data → EDA & cleaning → RFM scoring (K-Means) → Segmentation
                                                    │
                                                    ├── XGBoost regression (predict Total_Spent)
                                                    ├── Synthetic expansion → BigQuery ML
                                                    └── Streamlit dashboard
```

Each stage is self-contained in its own notebook so the pipeline can be rerun
end-to-end or picked up at any intermediate step.

## Repository structure

```
customer_segmentation/
├── dashboard/            # Streamlit app (live)
│   ├── app.py
│   └── pages/            # Raw data · Cleaned data · Cluster explorer · Customer lookup
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
│   └── score_raw_data_table.py  # scores raw_data at scale -> customer_segments table
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

## Dashboard

A multi-page Streamlit dashboard lives in `dashboard/` — see the live link
above. It translates the segmentation output into visualizations for a
business audience:

- **Raw data explorer** — browse the original dataset with filters and
  column views.
- **Cleaned data** — demographics, spending, channels, and campaign
  performance charts on the cleaned dataset.
- **Cluster explorer** — interactive 2D/3D scatter of customers colored by
  RFM segment.
- **Customer lookup** — find a customer by ID and see their RFM profile
  against their segment and the full population.

Run it locally with:

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

## Roadmap

- [x] Exploratory data analysis and cleaning
- [x] RFM scoring with K-Means
- [x] Interactive Streamlit dashboard (raw data, cleaned data, cluster
      explorer, customer lookup)
- [x] Database expansion for scale testing (1M synthetic rows, uploaded to a
      partitioned + clustered BigQuery table)
- [ ] Apply the trained K-Means models to `raw_data` at scale
      (`scripts/score_raw_data_table.py` → a separate `customer_segments`
      table; code-complete, not yet run against the live table)
- [ ] XGBoost regression to predict `Total_Spent` for new customers
- [ ] BigQuery ML pipeline (KMeans + XGBoost + segmentation SQL)

## Dataset

The original dataset is the
[Customer Personality Analysis](https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis)
dataset on Kaggle (~2,200 rows). Features cover demographics (age, income,
marital status, education, household composition), product spend across six
categories, campaign acceptance history, and purchase channels (web,
catalog, store).
