"""
One-off migration: recreate the `raw_data` BigQuery table with partitioning
and clustering.

BigQuery can't alter partitioning/clustering on an existing table in place,
so this drops the current (unpartitioned) table, recreates it via
`table_creation()` with the new layout, and reloads the same 1,000,000 rows
from the local synthetic parquet file. Mirrors the equivalent cells in
notebooks/big_query_dataset.ipynb.

Usage (from the repo root, with the dashboard venv that has
google-cloud-bigquery installed — python-dotenv is NOT installed there, so
this reads .env manually instead of depending on it):

    dashboard/venv/bin/python scripts/migrate_raw_data_partitioning.py
"""

import os
import re
import sys
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from bq_table_creation import table_creation  # noqa: E402


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line.strip())
        if match:
            key, value = match.groups()
            os.environ.setdefault(key, value.strip('"'))


def main() -> None:
    _load_dotenv(REPO_ROOT / ".env")
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    creds_path = REPO_ROOT / os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

    credentials = service_account.Credentials.from_service_account_file(creds_path)
    client = bigquery.Client(project=project, credentials=credentials)

    dataset_id = f"{project}.raw_data"
    full_table_id = f"{dataset_id}.raw_data"
    schemas_file = REPO_ROOT / "bigquery" / "schemas" / "raw_data.json"

    print(f"About to DROP and recreate: {full_table_id}")
    client.delete_table(full_table_id, not_found_ok=True)
    print(f"Dropped (if existed): {full_table_id}")

    table_creation(
        schemas_file,
        dataset_id,
        client,
        time_partitioning_field="Dt_Customer",
        time_partitioning_type="MONTH",
        clustering_fields=["Marital_Status", "Education"],
    )

    synthetic_data = REPO_ROOT / "data" / "synthetic_marketing_campaign.parquet"
    expanded_df = pd.read_parquet(synthetic_data)
    expanded_df["Dt_Customer"] = pd.to_datetime(expanded_df["Dt_Customer"]).dt.date

    load_job = client.load_table_from_dataframe(expanded_df, full_table_id)
    load_job.result()
    print(f"Loaded {load_job.output_rows:,} rows")

    table = client.get_table(full_table_id)
    print(f"time_partitioning: {table.time_partitioning}")
    print(f"clustering_fields: {table.clustering_fields}")
    print(f"num_rows: {table.num_rows}")


if __name__ == "__main__":
    main()
