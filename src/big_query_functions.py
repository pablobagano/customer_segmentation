"""Helpers for generating a large synthetic marketing campaign dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


GROUP_COLUMNS = ["Marital_Status", "Education"]
EXCLUDED_RAW_COLUMNS = {"Z_CostContact", "Z_Revenue"}
DERIVED_COLUMNS = {"Age", "Total_Spent", "Highest_Spent", "Total_Purchases"}

BINARY_COLUMNS = [
    "AcceptedCmp3",
    "AcceptedCmp4",
    "AcceptedCmp5",
    "AcceptedCmp1",
    "AcceptedCmp2",
    "Complain",
    "Response",
]

DISCRETE_EMPIRICAL_COLUMNS = ["Kidhome", "Teenhome"]

INTEGER_NOISE_COLUMNS = [
    "Recency",
    "MntWines",
    "MntFruits",
    "MntMeatProducts",
    "MntFishProducts",
    "MntSweetProducts",
    "MntGoldProds",
    "NumDealsPurchases",
    "NumWebPurchases",
    "NumCatalogPurchases",
    "NumStorePurchases",
    "NumWebVisitsMonth",
]

FLOAT_NOISE_COLUMNS = ["Income"]


def get_synthetic_output_columns(raw_df: pd.DataFrame) -> list[str]:
    """Return the raw campaign columns used in the synthetic output."""
    return [
        column
        for column in raw_df.columns
        if column not in EXCLUDED_RAW_COLUMNS and column not in DERIVED_COLUMNS
    ]


def prepare_generation_metadata(
    treated_df: pd.DataFrame,
    grouped_mean_df: pd.DataFrame,
    grouped_std_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    *,
    min_group_size: int = 10,
    verbose: bool = True,
) -> dict[str, Any]:
    """Collect reusable metadata needed by the synthetic data generator."""
    output_columns = get_synthetic_output_columns(raw_df)
    missing_output_columns = set(output_columns) - set(treated_df.columns) - {"Dt_Customer"}
    if missing_output_columns:
        raise ValueError(
            "These output columns are not available for generation: "
            f"{sorted(missing_output_columns)}"
        )

    group_counts = treated_df.groupby(GROUP_COLUMNS).size().rename("count").reset_index()
    group_counts["proportion"] = group_counts["count"] / group_counts["count"].sum()
    _print_step(
        "Output columns selected",
        (
            f"{len(output_columns)} columns retained; "
            f"excluded {sorted(EXCLUDED_RAW_COLUMNS)}"
        ),
        verbose=verbose,
    )

    date_series = _parse_dates(raw_df["Dt_Customer"])
    age_bounds = _series_bounds(treated_df["Age"]) if "Age" in treated_df else (18, 100)

    numeric_source_columns = [
        column
        for column in INTEGER_NOISE_COLUMNS + FLOAT_NOISE_COLUMNS + ["Age"]
        if column in treated_df.columns
    ]
    bounds = {
        column: _series_bounds(treated_df[column])
        for column in numeric_source_columns
        if column in treated_df.columns
    }
    bounds["Dt_Customer"] = (date_series.min(), date_series.max())
    bounds["Age"] = age_bounds

    global_means = treated_df[numeric_source_columns].mean(numeric_only=True).to_dict()
    global_stds = treated_df[numeric_source_columns].std(numeric_only=True).to_dict()

    binary_probabilities = _build_group_probabilities(
        treated_df, BINARY_COLUMNS, min_group_size=min_group_size
    )
    discrete_distributions = {
        column: _build_group_distributions(
            treated_df, column, min_group_size=min_group_size
        )
        for column in DISCRETE_EMPIRICAL_COLUMNS
        if column in output_columns
    }
    _print_step(
        "Generation metadata prepared",
        (
            f"{len(group_counts)} marital/education groups; "
            f"date range {date_series.min().date()} to {date_series.max().date()}; "
            f"minimum group size for empirical fallback is {min_group_size}"
        ),
        verbose=verbose,
    )

    return {
        "output_columns": output_columns,
        "group_counts": group_counts,
        "grouped_means": grouped_mean_df.set_index(GROUP_COLUMNS),
        "grouped_stds": grouped_std_df.set_index(GROUP_COLUMNS),
        "global_means": global_means,
        "global_stds": global_stds,
        "bounds": bounds,
        "binary_probabilities": binary_probabilities,
        "discrete_distributions": discrete_distributions,
        "date_min": date_series.min(),
        "date_max": date_series.max(),
        "reference_year": 2026,
    }


def generate_synthetic_campaign_data(
    treated_df: pd.DataFrame,
    grouped_mean_df: pd.DataFrame,
    grouped_std_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    *,
    n_rows: int = 1_000_000,
    random_state: int = 42,
    noise_scale: float = 1.0,
    metadata: dict[str, Any] | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Generate a synthetic marketing campaign DataFrame."""
    if n_rows <= 0:
        raise ValueError("n_rows must be greater than zero.")
    if noise_scale < 0:
        raise ValueError("noise_scale must be non-negative.")

    rng = np.random.default_rng(random_state)
    if metadata is None:
        metadata = prepare_generation_metadata(
            treated_df,
            grouped_mean_df,
            grouped_std_df,
            raw_df,
            verbose=verbose,
        )
    else:
        _print_step(
            "Generation metadata loaded",
            "Using precomputed metadata supplied to the generator.",
            verbose=verbose,
        )

    group_allocations = _allocate_group_rows(metadata["group_counts"], n_rows)
    _print_step(
        "Group row allocation completed",
        (
            f"{n_rows:,} rows allocated across "
            f"{(group_allocations['synthetic_count'] > 0).sum()} active groups"
        ),
        verbose=verbose,
    )
    frames: list[pd.DataFrame] = []

    for group_row in group_allocations.itertuples(index=False):
        count = int(group_row.synthetic_count)
        if count == 0:
            continue

        group_key = (group_row.Marital_Status, group_row.Education)
        frame = pd.DataFrame(
            {
                "Marital_Status": np.repeat(group_key[0], count),
                "Education": np.repeat(group_key[1], count),
            }
        )

        ages = _sample_noisy_numeric(
            "Age", group_key, count, metadata, rng, noise_scale=noise_scale
        )
        ages = _round_and_clip(ages, metadata["bounds"]["Age"]).astype("int64")
        frame["Year_Birth"] = metadata["reference_year"] - ages

        frame["Dt_Customer"] = _sample_dates(
            metadata["date_min"], metadata["date_max"], count, rng
        )

        for column in FLOAT_NOISE_COLUMNS:
            if column in metadata["output_columns"]:
                values = _sample_noisy_numeric(
                    column, group_key, count, metadata, rng, noise_scale=noise_scale
                )
                frame[column] = np.round(
                    _clip(values, metadata["bounds"][column]), 2
                )

        for column in INTEGER_NOISE_COLUMNS:
            if column in metadata["output_columns"]:
                values = _sample_noisy_numeric(
                    column, group_key, count, metadata, rng, noise_scale=noise_scale
                )
                frame[column] = _round_and_clip(
                    values, metadata["bounds"][column]
                ).astype("int64")

        for column, distributions in metadata["discrete_distributions"].items():
            frame[column] = _sample_from_distribution(distributions, group_key, count, rng)

        for column in BINARY_COLUMNS:
            if column in metadata["output_columns"]:
                probabilities = metadata["binary_probabilities"][column]
                probability = probabilities["by_group"].get(
                    group_key, probabilities["global"]
                )
                frame[column] = rng.binomial(1, probability, size=count).astype("int64")

        frames.append(frame)

    synthetic_df = pd.concat(frames, ignore_index=True)
    _print_step(
        "Synthetic rows generated",
        (
            f"{len(synthetic_df):,} rows created with grouped means, "
            f"grouped stds, and noise_scale={noise_scale}"
        ),
        verbose=verbose,
    )
    synthetic_df = synthetic_df.iloc[rng.permutation(len(synthetic_df))].reset_index(
        drop=True
    )
    synthetic_df.insert(0, "ID", np.arange(1, len(synthetic_df) + 1, dtype=np.int64))
    synthetic_df = synthetic_df[metadata["output_columns"]]
    _print_step(
        "Final synthetic DataFrame assembled",
        (
            f"Rows shuffled, sequential IDs assigned, "
            f"and {len(metadata['output_columns'])} output columns ordered"
        ),
        verbose=verbose,
    )

    synthetic_df = _enforce_output_types(synthetic_df, metadata["output_columns"])
    _print_step(
        "Output types enforced",
        (
            "Integer, float, string, and date-compatible columns prepared "
            "for Parquet/BigQuery usage"
        ),
        verbose=verbose,
    )

    return synthetic_df


def write_synthetic_dataset(
    df: pd.DataFrame,
    output_path: str | Path,
    *,
    file_format: str = "parquet",
    index: bool = False,
    verbose: bool = True,
) -> Path:
    """Write synthetic data as Parquet or CSV and return the output path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if file_format == "parquet":
        df.to_parquet(output_path, index=index)
    elif file_format == "csv":
        df.to_csv(output_path, index=index)
    else:
        raise ValueError("file_format must be either 'parquet' or 'csv'.")

    _print_step(
        "Synthetic dataset written",
        (
            f"{len(df):,} rows saved as {file_format} at {output_path} "
            f"({output_path.stat().st_size / 1024 / 1024:.2f} MB)"
        ),
        verbose=verbose,
    )

    return output_path


def validate_synthetic_campaign_data(
    synthetic_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    *,
    expected_rows: int | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """Return validation checks for the generated campaign dataset."""
    expected_columns = get_synthetic_output_columns(raw_df)
    checks: dict[str, Any] = {
        "row_count": len(synthetic_df),
        "columns_match": list(synthetic_df.columns) == expected_columns,
        "unexpected_derived_columns": sorted(
            set(synthetic_df.columns).intersection(DERIVED_COLUMNS)
        ),
        "excluded_raw_columns_present": sorted(
            set(synthetic_df.columns).intersection(EXCLUDED_RAW_COLUMNS)
        ),
    }

    if expected_rows is not None:
        checks["expected_row_count_match"] = len(synthetic_df) == expected_rows

    non_negative_columns = [
        column
        for column in INTEGER_NOISE_COLUMNS + FLOAT_NOISE_COLUMNS + DISCRETE_EMPIRICAL_COLUMNS
        if column in synthetic_df.columns
    ]
    checks["negative_value_columns"] = [
        column for column in non_negative_columns if (synthetic_df[column] < 0).any()
    ]
    checks["invalid_binary_columns"] = [
        column
        for column in BINARY_COLUMNS
        if column in synthetic_df.columns
        and not set(synthetic_df[column].dropna().unique()).issubset({0, 1})
    ]

    raw_dates = _parse_dates(raw_df["Dt_Customer"])
    synthetic_dates = _parse_dates(synthetic_df["Dt_Customer"])
    checks["date_range_valid"] = (
        synthetic_dates.min() >= raw_dates.min()
        and synthetic_dates.max() <= raw_dates.max()
    )
    passed_checks = [
        key
        for key, value in checks.items()
        if value is True or value == [] or (key == "row_count" and value > 0)
    ]
    failed_checks = [
        key
        for key, value in checks.items()
        if value is False or (isinstance(value, list) and len(value) > 0)
    ]
    _print_step(
        "Synthetic dataset validation completed",
        f"{len(passed_checks)} checks passed; {len(failed_checks)} checks need review",
        verbose=verbose,
    )

    return checks


def summarize_group_proportions(
    original_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare original and synthetic marital/education group proportions."""
    original = _group_proportions(original_df).rename(
        columns={"proportion": "original_proportion"}
    )
    synthetic = _group_proportions(synthetic_df).rename(
        columns={"proportion": "synthetic_proportion"}
    )
    comparison = original.merge(synthetic, on=GROUP_COLUMNS, how="outer").fillna(0)
    comparison["difference"] = (
        comparison["synthetic_proportion"] - comparison["original_proportion"]
    )
    return comparison.sort_values(GROUP_COLUMNS).reset_index(drop=True)


def _allocate_group_rows(group_counts: pd.DataFrame, n_rows: int) -> pd.DataFrame:
    allocations = group_counts.copy()
    exact_counts = allocations["proportion"] * n_rows
    allocations["synthetic_count"] = np.floor(exact_counts).astype("int64")

    remainder = int(n_rows - allocations["synthetic_count"].sum())
    if remainder > 0:
        largest_fractions = (exact_counts - np.floor(exact_counts)).nlargest(
            remainder
        ).index
        allocations.loc[largest_fractions, "synthetic_count"] += 1

    return allocations


def _build_group_probabilities(
    df: pd.DataFrame,
    columns: list[str],
    *,
    min_group_size: int,
) -> dict[str, dict[str, Any]]:
    probabilities: dict[str, dict[str, Any]] = {}
    group_sizes = df.groupby(GROUP_COLUMNS).size()

    for column in columns:
        if column not in df.columns:
            continue
        group_means = df.groupby(GROUP_COLUMNS)[column].mean()
        by_group = {
            group_key: float(probability)
            for group_key, probability in group_means.items()
            if group_sizes.loc[group_key] >= min_group_size
        }
        probabilities[column] = {
            "global": float(df[column].mean()),
            "by_group": by_group,
        }

    return probabilities


def _build_group_distributions(
    df: pd.DataFrame,
    column: str,
    *,
    min_group_size: int,
) -> dict[str, Any]:
    global_distribution = _value_distribution(df[column])
    group_sizes = df.groupby(GROUP_COLUMNS).size()
    by_group = {}

    for group_key, group_df in df.groupby(GROUP_COLUMNS):
        if group_sizes.loc[group_key] >= min_group_size:
            by_group[group_key] = _value_distribution(group_df[column])

    return {"global": global_distribution, "by_group": by_group}


def _value_distribution(series: pd.Series) -> dict[str, np.ndarray]:
    proportions = series.value_counts(normalize=True).sort_index()
    return {
        "values": proportions.index.to_numpy(),
        "probabilities": proportions.to_numpy(dtype=float),
    }


def _sample_from_distribution(
    distributions: dict[str, Any],
    group_key: tuple[str, str],
    count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    distribution = distributions["by_group"].get(group_key, distributions["global"])
    return rng.choice(
        distribution["values"],
        size=count,
        p=distribution["probabilities"],
    ).astype("int64")


def _sample_noisy_numeric(
    column: str,
    group_key: tuple[str, str],
    count: int,
    metadata: dict[str, Any],
    rng: np.random.Generator,
    *,
    noise_scale: float,
) -> np.ndarray:
    mean = _lookup_group_value(
        metadata["grouped_means"], group_key, column, metadata["global_means"][column]
    )
    std = _lookup_group_value(
        metadata["grouped_stds"], group_key, column, metadata["global_stds"][column]
    )
    fallback_std = metadata["global_stds"].get(column, 1)
    if not np.isfinite(std) or std <= 0:
        std = fallback_std
    if not np.isfinite(std) or std <= 0:
        std = 1

    return rng.normal(loc=mean, scale=std * noise_scale, size=count)


def _lookup_group_value(
    frame: pd.DataFrame,
    group_key: tuple[str, str],
    column: str,
    fallback: float,
) -> float:
    try:
        value = frame.loc[group_key, column]
    except KeyError:
        return float(fallback)
    if pd.isna(value):
        return float(fallback)
    return float(value)


def _round_and_clip(values: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return np.rint(_clip(values, bounds))


def _clip(values: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    lower, upper = bounds
    return np.clip(values, lower, upper)


def _series_bounds(series: pd.Series) -> tuple[float, float]:
    return float(series.min()), float(series.max())


def _parse_dates(series: pd.Series) -> pd.Series:
    text_series = series.astype(str)
    if text_series.str.match(r"^\d{4}-\d{2}-\d{2}$").all():
        parsed = pd.to_datetime(series, errors="coerce")
    else:
        parsed = pd.to_datetime(series, dayfirst=True, errors="coerce")
    if parsed.isna().any():
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.isna().any():
            raise ValueError("Unable to parse all Dt_Customer values as dates.")
    return parsed


def _sample_dates(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    count: int,
    rng: np.random.Generator,
) -> pd.Series:
    day_span = int((end_date - start_date).days)
    offsets = rng.integers(0, day_span + 1, size=count)
    return pd.Series(start_date + pd.to_timedelta(offsets, unit="D")).dt.normalize()


def _enforce_output_types(
    df: pd.DataFrame,
    output_columns: list[str],
) -> pd.DataFrame:
    integer_columns = [
        column
        for column in output_columns
        if column not in {"Income", "Education", "Marital_Status", "Dt_Customer"}
    ]
    for column in integer_columns:
        df[column] = df[column].astype("int64")

    if "Income" in df.columns:
        df["Income"] = df["Income"].astype("float64")
    if "Dt_Customer" in df.columns:
        df["Dt_Customer"] = pd.to_datetime(df["Dt_Customer"]).dt.normalize()

    return df


def _group_proportions(df: pd.DataFrame) -> pd.DataFrame:
    proportions = df.groupby(GROUP_COLUMNS).size().rename("count").reset_index()
    proportions["proportion"] = proportions["count"] / proportions["count"].sum()
    return proportions.drop(columns="count")


def _print_step(title: str, detail: str, *, verbose: bool) -> None:
    if not verbose:
        return

    border = "=" * 72
    print(f"\n{border}")
    print(f"[DONE] {title}")
    print(f"{detail}")
    print(border)
