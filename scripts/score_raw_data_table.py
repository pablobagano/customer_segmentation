"""
Batch-score every row of the `raw_data` BigQuery table with the trained RFM
KMeans models (models/kmeans_{freq,monetary,recency}.joblib) and write the
result to a new `customer_segments` table.

Requires the project venv created in step 0 (has both scikit-learn/joblib
AND google-cloud-bigquery):

    .venv/bin/python scripts/score_raw_data_table.py
"""

import os
import re
import sys
from pathlib import Path


import joblib
from google.cloud import bigquery
from google.oauth2 import service_account

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))


from bq_table_creation import table_creation # noqa: E402
from customer_scoring import score_rfm # noqa: E402

def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line.strip())
        if match:
            key, value = match.groups()
            os.environ.setdefault(key, value.strip('"'))


SOURCE_QUERY = """
SELECT
    ID,
    Dt_Customer,
    Marital_Status,
    Education,
    Recency,
    (MntWines + MntFruits + MntMeatProducts + MntFishProducts
     + MntSweetProducts + MntGoldProds) AS Total_Spent,
    (NumDealsPurchases + NumWebPurchases + NumCatalogPurchases
     + NumStorePurchases) AS Total_Purchases
FROM `{project}.raw_data.raw_data`
"""

def main() -> None:
    _load_dotenv(REPO_ROOT / ".env")
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    creds_path = REPO_ROOT / os.environ["GOOGLE_APPLICATION_CREDENTIALS"]


    credentials = service_account.Credentials.from_service_account_file(creds_path)
    client = bigquery.Client(project=project, credentials=credentials)

    print("Reading raw_data from BigQuery...")
    source_df = client.query(SOURCE_QUERY.format(project=project)).to_dataframe()
    print(f"Pulled {len(source_df):,} rows")

    kmeans_freq = joblib.load(REPO_ROOT / "models" / "kmeans_freq.joblib")
    kmeans_monetary = joblib.load(REPO_ROOT / "models" / "kmeans_monetary.joblib")
    kmeans_recency = joblib.load(REPO_ROOT / "models" / "kmeans_recency.joblib")


    scored_df = score_rfm(source_df, kmeans_freq, kmeans_monetary, kmeans_recency)
    print("Segmentation counts:")
    print(scored_df["Segmentation"].value_counts())

    dataset_id = f"{project}.raw_data"
    full_table_id = f"{dataset_id}.customer_segments"
    schemas_file = REPO_ROOT / "bigquery" / "schemas" / "customer_segments.json"


    # Recreate-on-run: safe to re-run any time raw_data or the models change.

    client.delete_table(full_table_id, not_found_ok=True)
    table_creation(
        schemas_file,
        dataset_id,
        client,
        time_partitioning_field="Dt_Customer",
        time_partitioning_type="MONTH",
        clustering_fields=["Segmentation"]
    )

    load_job = client.load_table_from_dataframe(scored_df, full_table_id)
    load_job.result()
    print(f"Loaded {load_job.output_rows:,} rows into {full_table_id}")


if __name__ == "__main__":
    main()