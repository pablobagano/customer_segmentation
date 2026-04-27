# Customer Segmentation

End-to-end customer segmentation pipeline built on the
[Customer Personality Analysis](https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis)
dataset. The project covers exploratory analysis, RFM scoring with K-Means,
synthetic data expansion for BigQuery, and an interactive Streamlit dashboard
aimed at a business audience.

## Streamlit Apps
Streamlit App for K-Means Segmentation: (https://pablobagano-customersegmentation.streamlit.app/)

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
├── dashboard/            # Streamlit app (in progress)
├── notebooks/            # Analysis and modeling notebooks
│   ├── exploratory_analysis.ipynb
│   ├── customer_kmeans.ipynb
│   ├── database_expansion.ipynb
│   └── drafts.ipynb          (local-only, gitignored)
├── data/                 # CSVs used and produced by the notebooks
├── models/               # Trained K-Means artefacts (.joblib)
├── src/                  # Shared Python helpers
│   └── custom_functions.py
├── bigquery/             # BigQuery pipeline instructions (gitignored)
├── requirements.txt      # Top-level dependencies
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

**`database_expansion.ipynb`** — synthesizes hundreds of thousands of rows
from the group means and standard deviations (`Marital_Status` × `Education`)
of the cleaned data, preserving realistic variability. The expanded dataset
is intended for upload to BigQuery to demonstrate the pipeline at scale.

## Dashboard

A Streamlit dashboard will live in `dashboard/`. The goal is to translate
the technical output of the segmentation into clear, actionable visualizations
for stakeholders — exploring segments, monitoring KPIs, and filtering by
customer attributes without touching the underlying code. It will consume
`data/segmented_data.csv` and the trained `models/*.joblib` files.

## Roadmap

- [x] Exploratory data analysis and cleaning
- [x] RFM scoring with K-Means
- [x] Dashboard For Clustering Segmentation
- [ ] Database expansion for scale testing
- [ ] XGBoost regression to predict `Total_Spent` for new customers
- [ ] BigQuery ML pipeline (KMeans + XGBoost + segmentation SQL)
- [ ] Streamlit dashboard

## Dataset

The original dataset is the
[Customer Personality Analysis](https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis)
dataset on Kaggle (~2,200 rows). Features cover demographics (age, income,
marital status, education, household composition), product spend across six
categories, campaign acceptance history, and purchase channels (web,
catalog, store).
