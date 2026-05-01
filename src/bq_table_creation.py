import json
import traceback
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery


def table_creation(json_file, dataset, client=None):
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
            result = client.create_table(table, exists_ok=True)
            print(f"{table_ref} successfully created")
            print(
                f"{result.full_table_id} | {len(result.schema)} fields | "
                f"created: {result.created}"
            )
    except Exception as e:
        traceback.extract_tb(e.__traceback__)
        print(type(e).__name__, str(e))
    finally:
        print("--" * 45)
        print("Finished")
