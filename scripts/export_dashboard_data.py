"""
Exports the data behind the customer-segmentation dashboard to static JSON,
for the Next.js port at webcv_frontend (Story + Customer Lookup pages).

Reads the 6 BigQuery materialized views (scripts/create_materialized_views.py)
plus data/segmented_data.csv, and writes JSON to data/export/. These files
are committed here and copied into webcv_frontend by hand/script — this repo
owns "what the pipeline produces"; webcv_frontend just consumes static data,
no BigQuery credentials needed at build time there.

Run with:
    .venv/bin/python scripts/export_dashboard_data.py
"""

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "dashboard"))

from data_paths import SEGMENTED_DATA  # noqa: E402

EXPORT_DIR = REPO_ROOT / "data" / "export"

SEGMENT_ORDER = ["Inactive", "Occasional", "Moderate", "Loyal", "Premium"]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line.strip())
        if match:
            key, value = match.groups()
            os.environ.setdefault(key, value.strip('"'))


def _to_jsonable(value):
    """BigQuery to_dataframe() can yield Decimal/Timestamp/NaN — normalize."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
    if hasattr(value, "isoformat"):  # date/datetime/Timestamp
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 4)
    return value


def _records(df: pd.DataFrame) -> list[dict]:
    return [
        {col: _to_jsonable(val) for col, val in row.items()}
        for row in df.to_dict(orient="records")
    ]


def export_customers() -> None:
    df = pd.read_csv(SEGMENTED_DATA, parse_dates=["Dt_Customer"])
    df = df.drop(columns=["Year_Birth", "Complain"])

    rename = {
        "ID": "id",
        "Education": "education",
        "Marital_Status": "maritalStatus",
        "Income": "income",
        "Kidhome": "kidhome",
        "Teenhome": "teenhome",
        "Dt_Customer": "dtCustomer",
        "Recency": "recency",
        "MntWines": "mntWines",
        "MntFruits": "mntFruits",
        "MntMeatProducts": "mntMeatProducts",
        "MntFishProducts": "mntFishProducts",
        "MntSweetProducts": "mntSweetProducts",
        "MntGoldProds": "mntGoldProds",
        "NumDealsPurchases": "numDealsPurchases",
        "NumWebPurchases": "numWebPurchases",
        "NumCatalogPurchases": "numCatalogPurchases",
        "NumStorePurchases": "numStorePurchases",
        "NumWebVisitsMonth": "numWebVisitsMonth",
        "AcceptedCmp1": "acceptedCmp1",
        "AcceptedCmp2": "acceptedCmp2",
        "AcceptedCmp3": "acceptedCmp3",
        "AcceptedCmp4": "acceptedCmp4",
        "AcceptedCmp5": "acceptedCmp5",
        "Response": "response",
        "Total_Spent": "totalSpent",
        "Highest_Spent": "highestSpent",
        "Age": "age",
        "Total_Purchases": "totalPurchases",
        "Cluster_Frequency": "clusterFrequency",
        "Cluster_Monetary": "clusterMonetary",
        "Cluster_Recency": "clusterRecency",
        "Frequency_Score": "frequencyScore",
        "Recency_Score": "recencyScore",
        "Monetary_Score": "monetaryScore",
        "RMF_Score": "rmfScore",
        "Segmentation": "segmentation",
        "APV": "apv",
    }
    df = df.rename(columns=rename)
    df["dtCustomer"] = df["dtCustomer"].dt.strftime("%Y-%m-%d")

    records = _records(df)
    _write("customers.json", records)
    print(f"  customers.json: {len(records):,} rows")


def export_segment_summary(client: bigquery.Client, project: str) -> None:
    tables = {
        "counts": "mv_segment_counts",
        "metrics": "mv_segment_metrics",
        "spend": "mv_segment_spend",
        "channels": "mv_segment_channels",
        "campaigns": "mv_segment_campaigns",
    }
    by_segment: dict[str, dict] = {seg: {"segment": seg} for seg in SEGMENT_ORDER}

    for key, table in tables.items():
        df = client.query(f"SELECT * FROM `{project}.raw_data.{table}`").to_dataframe()
        for row in _records(df):
            seg = row.pop("Segmentation")
            if key == "counts":
                by_segment[seg]["customerCount"] = row["customer_count"]
                by_segment[seg]["pctOfTotal"] = row["pct_of_total"]
            elif key == "metrics":
                by_segment[seg].update(
                    {
                        "avgRmfScore": row["avg_rmf_score"],
                        "avgRecencyScore": row["avg_recency_score"],
                        "avgFrequencyScore": row["avg_frequency_score"],
                        "avgMonetaryScore": row["avg_monetary_score"],
                        "avgRecencyDays": row["avg_recency_days"],
                        "avgTotalPurchases": row["avg_total_purchases"],
                        "avgTotalSpent": row["avg_total_spent"],
                        "avgApv": row["avg_apv"],
                    }
                )
            elif key == "spend":
                by_segment[seg]["spend"] = {
                    "avgWines": row["avg_wines"],
                    "avgFruits": row["avg_fruits"],
                    "avgMeat": row["avg_meat"],
                    "avgFish": row["avg_fish"],
                    "avgSweets": row["avg_sweets"],
                    "avgGold": row["avg_gold"],
                }
            elif key == "channels":
                by_segment[seg]["channels"] = {
                    "avgWebPurchases": row["avg_web_purchases"],
                    "avgCatalogPurchases": row["avg_catalog_purchases"],
                    "avgStorePurchases": row["avg_store_purchases"],
                    "avgDealsPurchases": row["avg_deals_purchases"],
                    "avgWebVisitsMonth": row["avg_web_visits_month"],
                }
            elif key == "campaigns":
                by_segment[seg]["campaigns"] = {
                    "acceptanceRateCmp1": row["acceptance_rate_cmp1"],
                    "acceptanceRateCmp2": row["acceptance_rate_cmp2"],
                    "acceptanceRateCmp3": row["acceptance_rate_cmp3"],
                    "acceptanceRateCmp4": row["acceptance_rate_cmp4"],
                    "acceptanceRateCmp5": row["acceptance_rate_cmp5"],
                    "acceptanceRateLastCmp": row["acceptance_rate_last_cmp"],
                    "complaintRate": row["complaint_rate"],
                }

    segments = [by_segment[seg] for seg in SEGMENT_ORDER]
    total_customers = sum(seg["customerCount"] for seg in segments)
    total_pct = round(sum(seg["pctOfTotal"] for seg in segments), 2)

    _write(
        "segment-summary.json",
        {"generatedAt": pd.Timestamp.now("UTC").isoformat(), "segments": segments},
    )
    print(f"  segment-summary.json: {len(segments)} segments, "
          f"{total_customers:,} customers ({total_pct}% total)")


def _weighted_avg(df: pd.DataFrame, value_col: str, weight_col: str) -> float:
    return (df[value_col] * df[weight_col]).sum() / df[weight_col].sum()


def _rollup(df: pd.DataFrame, dim_col: str, dim_key: str) -> list[dict]:
    """Collapse the fully-crossed mv_segment_demo rows down to one dimension
    at a time (segment x dim_col), weighting spend/income averages by
    customer_count. The MV's full cross-tab (segment x marital x education x
    age band x income band x kidhome x teenhome) is ~10k rows / a couple MB —
    far more than any single chart needs, since each demo_* chart only ever
    groups by segment + one dimension."""
    grouped = (
        df.groupby(["Segmentation", dim_col])
        .apply(
            lambda g: pd.Series(
                {
                    "customerCount": int(g["customer_count"].sum()),
                    "avgTotalSpent": round(_weighted_avg(g, "avg_total_spent", "customer_count"), 2),
                    "avgIncome": round(_weighted_avg(g, "avg_income", "customer_count"), 2),
                }
            ),
            include_groups=False,
        )
        .reset_index()
        .rename(columns={"Segmentation": "segment", dim_col: dim_key})
    )
    return _records(grouped)


def export_segment_demographics(client: bigquery.Client, project: str) -> None:
    df = client.query(f"SELECT * FROM `{project}.raw_data.mv_segment_demo`").to_dataframe()

    demographics = {
        "byAgeBand": _rollup(df, "Age_Band", "ageBand"),
        "byIncomeBand": _rollup(df, "Income_Band", "incomeBand"),
        "byMaritalStatus": _rollup(df, "Marital_Status", "maritalStatus"),
        "byEducation": _rollup(df, "Education", "education"),
    }
    # Household heatmap needs both Kidhome and Teenhome — roll up on the pair.
    household = (
        df.groupby(["Segmentation", "Kidhome", "Teenhome"])["customer_count"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "Segmentation": "segment",
                "Kidhome": "kidhome",
                "Teenhome": "teenhome",
                "customer_count": "customerCount",
            }
        )
    )
    demographics["byHousehold"] = _records(household)

    _write("segment-demographics.json", demographics)
    total_rows = sum(len(v) for v in demographics.values())
    print(f"  segment-demographics.json: {total_rows:,} rows across {len(demographics)} breakdowns")


def _write(filename: str, data) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / filename
    path.write_text(json.dumps(data, indent=2))


def main() -> None:
    _load_dotenv(REPO_ROOT / ".env")
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    creds_path = REPO_ROOT / os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

    credentials = service_account.Credentials.from_service_account_file(creds_path)
    client = bigquery.Client(project=project, credentials=credentials)

    print("Exporting dashboard data...")
    export_customers()
    export_segment_summary(client, project)
    export_segment_demographics(client, project)
    print(f"\nDone. Output in {EXPORT_DIR}")


if __name__ == "__main__":
    main()
