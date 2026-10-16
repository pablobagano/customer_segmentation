import json
import traceback
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery


def table_creation(
    json_file,
    dataset,
    client=None,
    *,
    time_partitioning_field=None,
    time_partitioning_type="MONTH",
    clustering_fields=None,
):
    try:
        if client is None:
            client = bigquery.Client()

        json_file = Path(json_file)
        with open(json_file, encoding="utf-8") as f:
            fields = json.load(f)

        name = json_file.stem
        table_ref = f"{dataset}.{name}"
        try:
            client.get_table(table_ref)
            print(f"{table_ref} already exists. Skipping")
            return
        except NotFound:
            schema = [
                bigquery.SchemaField(
                    name=field["name"],
                    field_type=field["type"],
                    mode=field.get("mode", "NULLABLE"),
                    description=field.get("description", ""),
                )
                for field in fields
            ]
            table = bigquery.Table(table_ref, schema=schema)
            if time_partitioning_field:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=getattr(bigquery.TimePartitioningType, time_partitioning_type),
                    field=time_partitioning_field,
                )
            if clustering_fields:
                table.clustering_fields = clustering_fields
            result = client.create_table(table, exists_ok=True)
            print(f"{table_ref} successfully created")
            print(
                f"{result.full_table_id} | {len(result.schema)} fields | "
                f"created: {result.created}"
            )
            if result.time_partitioning:
                print(
                    f"Partitioned by {result.time_partitioning.type_} "
                    f"on {result.time_partitioning.field}"
                )
            if result.clustering_fields:
                print(f"Clustered by {result.clustering_fields}")
    except Exception as e:
        traceback.extract_tb(e.__traceback__)
        print(type(e).__name__, str(e))
    finally:
        print("--" * 45)
        print("Finished")


