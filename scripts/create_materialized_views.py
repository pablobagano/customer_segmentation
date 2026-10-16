"""
Creates all materialized views for the customer segmentation dashboard.

Views are static (no auto-refresh) — they only need to be recreated when
customer_segments is rebuilt via score_raw_data_table.py.

Run with:
    .venv/bin/python scripts/create_materialized_views.py
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line.strip())
        if match:
            key, value = match.groups()
            os.environ.setdefault(key, value.strip('"'))


def create_view(
    client: bigquery.Client, project: str, name: str, query: str, dry_run: bool = False
) -> None:
    full_id = f"`{project}.raw_data.{name}`"
    print(f"\n{'Dry-running' if dry_run else 'Creating'} {name}...")
    ddl = f"""
    CREATE OR REPLACE MATERIALIZED VIEW {full_id}
    CLUSTER BY Segmentation
    OPTIONS (
        enable_refresh = false,
        allow_non_incremental_definition = true,
        max_staleness = INTERVAL 3 DAY
    )
    AS
    {query}
    """
    client.query(ddl, job_config=bigquery.QueryJobConfig(dry_run=dry_run)).result()
    print(f"  ✓ {name} {'validated' if dry_run else 'created'}")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    _load_dotenv(REPO_ROOT / ".env")
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    creds_path = REPO_ROOT / os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

    credentials = service_account.Credentials.from_service_account_file(creds_path)
    client = bigquery.Client(project=project, credentials=credentials)

    cs = f"`{project}.raw_data.customer_segments`"
    rd = f"`{project}.raw_data.raw_data`"
    current_year = date.today().year

    views = {

        # ------------------------------------------------------------------
        # 1. Segment distribution
        # ------------------------------------------------------------------
        "mv_segment_counts": f"""
            SELECT
                Segmentation,
                COUNT(*)                                                AS customer_count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)    AS pct_of_total
            FROM {cs}
            GROUP BY Segmentation
        """,

        # ------------------------------------------------------------------
        # 2. Core RFM metrics per segment
        # ------------------------------------------------------------------
        "mv_segment_metrics": f"""
            SELECT
                Segmentation,
                COUNT(*)                            AS customer_count,
                ROUND(AVG(RMF_Score), 2)            AS avg_rmf_score,
                ROUND(AVG(Recency_Score), 2)        AS avg_recency_score,
                ROUND(AVG(Frequency_Score), 2)      AS avg_frequency_score,
                ROUND(AVG(Monetary_Score), 2)       AS avg_monetary_score,
                ROUND(AVG(Recency), 1)              AS avg_recency_days,
                ROUND(AVG(Total_Purchases), 1)      AS avg_total_purchases,
                ROUND(AVG(Total_Spent), 2)          AS avg_total_spent,
                ROUND(AVG(APV), 2)                  AS avg_apv
            FROM {cs}
            GROUP BY Segmentation
        """,

        # ------------------------------------------------------------------
        # 3. Demographic breakdown
        #    Age bands based on Year_Birth; income bands in 5 tiers.
        #    Marital_Status and Education come from customer_segments
        #    (already carried over at scoring time) so the join only adds
        #    Income and Year_Birth from raw_data.
        #    Materialized views ban CURRENT_DATE()/non-deterministic
        #    functions, so the reference year is baked in at creation time
        #    (this view is recreate-on-run anyway, same as customer_segments).
        # ------------------------------------------------------------------
        "mv_segment_demo": f"""
            SELECT
                cs.Segmentation,
                cs.Marital_Status,
                cs.Education,
                CASE
                    WHEN {current_year} - r.Year_Birth < 35 THEN '18-34'
                    WHEN {current_year} - r.Year_Birth < 50 THEN '35-49'
                    WHEN {current_year} - r.Year_Birth < 65 THEN '50-64'
                    ELSE '65+'
                END                                             AS Age_Band,
                CASE
                    WHEN r.Income < 30000  THEN '<30k'
                    WHEN r.Income < 50000  THEN '30k-50k'
                    WHEN r.Income < 70000  THEN '50k-70k'
                    WHEN r.Income < 100000 THEN '70k-100k'
                    ELSE '100k+'
                END                                             AS Income_Band,
                r.Kidhome,
                r.Teenhome,
                COUNT(*)                                        AS customer_count,
                ROUND(AVG(cs.Total_Spent), 2)                  AS avg_total_spent,
                ROUND(AVG(r.Income), 2)                        AS avg_income
            FROM {cs} cs
            JOIN {rd} r ON cs.ID = r.ID
            GROUP BY
                cs.Segmentation,
                cs.Marital_Status,
                cs.Education,
                Age_Band,
                Income_Band,
                r.Kidhome,
                r.Teenhome
        """,

        # ------------------------------------------------------------------
        # 4. Product category spend per segment
        # ------------------------------------------------------------------
        "mv_segment_spend": f"""
            SELECT
                cs.Segmentation,
                COUNT(*)                                AS customer_count,
                ROUND(AVG(r.MntWines), 2)              AS avg_wines,
                ROUND(AVG(r.MntFruits), 2)             AS avg_fruits,
                ROUND(AVG(r.MntMeatProducts), 2)       AS avg_meat,
                ROUND(AVG(r.MntFishProducts), 2)       AS avg_fish,
                ROUND(AVG(r.MntSweetProducts), 2)      AS avg_sweets,
                ROUND(AVG(r.MntGoldProds), 2)          AS avg_gold,
                ROUND(AVG(cs.Total_Spent), 2)          AS avg_total_spent
            FROM {cs} cs
            JOIN {rd} r ON cs.ID = r.ID
            GROUP BY cs.Segmentation
        """,

        # ------------------------------------------------------------------
        # 5. Purchase channel mix per segment
        # ------------------------------------------------------------------
        "mv_segment_channels": f"""
            SELECT
                cs.Segmentation,
                COUNT(*)                                    AS customer_count,
                ROUND(AVG(r.NumWebPurchases), 2)           AS avg_web_purchases,
                ROUND(AVG(r.NumCatalogPurchases), 2)       AS avg_catalog_purchases,
                ROUND(AVG(r.NumStorePurchases), 2)         AS avg_store_purchases,
                ROUND(AVG(r.NumDealsPurchases), 2)         AS avg_deals_purchases,
                ROUND(AVG(r.NumWebVisitsMonth), 2)         AS avg_web_visits_month
            FROM {cs} cs
            JOIN {rd} r ON cs.ID = r.ID
            GROUP BY cs.Segmentation
        """,

        # ------------------------------------------------------------------
        # 6. Campaign acceptance rates + complaint rate per segment
        # ------------------------------------------------------------------
        "mv_segment_campaigns": f"""
            SELECT
                cs.Segmentation,
                COUNT(*)                                AS customer_count,
                ROUND(AVG(r.AcceptedCmp1), 4)          AS acceptance_rate_cmp1,
                ROUND(AVG(r.AcceptedCmp2), 4)          AS acceptance_rate_cmp2,
                ROUND(AVG(r.AcceptedCmp3), 4)          AS acceptance_rate_cmp3,
                ROUND(AVG(r.AcceptedCmp4), 4)          AS acceptance_rate_cmp4,
                ROUND(AVG(r.AcceptedCmp5), 4)          AS acceptance_rate_cmp5,
                ROUND(AVG(r.Response), 4)              AS acceptance_rate_last_cmp,
                ROUND(AVG(r.Complain), 4)              AS complaint_rate
            FROM {cs} cs
            JOIN {rd} r ON cs.ID = r.ID
            GROUP BY cs.Segmentation
        """,
    }

    for name, query in views.items():
        try:
            create_view(client, project, name, query, dry_run=dry_run)
        except Exception as e:
            print(f"  ✗ {name} failed: {e}")

    print("\n" + "--" * 45)
    print("Done.")


if __name__ == "__main__":
    main()
