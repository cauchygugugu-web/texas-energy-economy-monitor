from pathlib import Path

import pandas as pd

from fetch_fred import (
    create_session,
    fetch_fred_metadata,
    fetch_fred_observations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "fred_series.csv"
)

PROCESSED_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "tables"
)

DEFAULT_START = "2015-01-01"


def load_series_config() -> pd.DataFrame:
    """Load and validate the FRED series configuration."""

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "FRED series configuration was not found. "
            "Run create_fred_series_config.py first."
        )

    config = pd.read_csv(
        CONFIG_PATH,
        dtype=str,
        encoding="utf-8-sig",
    )

    required_columns = {
        "series_id",
        "variable_name",
        "category",
    }

    missing_columns = (
        required_columns - set(config.columns)
    )

    if missing_columns:
        raise ValueError(
            "FRED configuration columns are missing: "
            f"{sorted(missing_columns)}"
        )

    for column in required_columns:
        config[column] = (
            config[column]
            .fillna("")
            .str.strip()
        )

        if config[column].eq("").any():
            raise ValueError(
                f"Blank configuration values were "
                f"found in {column}."
            )

    config["series_id"] = (
        config["series_id"]
        .str.upper()
    )

    if config["series_id"].duplicated().any():
        duplicated_ids = (
            config.loc[
                config["series_id"].duplicated(
                    keep=False
                ),
                "series_id",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate FRED series IDs were found: "
            f"{duplicated_ids}"
        )

    if config["variable_name"].duplicated().any():
        duplicated_names = (
            config.loc[
                config["variable_name"].duplicated(
                    keep=False
                ),
                "variable_name",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate project variable names were "
            f"found: {duplicated_names}"
        )

    return config.reset_index(
        drop=True
    )


def build_coverage_record(
    observations: pd.DataFrame,
    series_id: str,
    variable_name: str,
    category: str,
) -> dict:
    """Build a monthly coverage record for one series."""

    first_period = observations[
        "period"
    ].min()

    last_period = observations[
        "period"
    ].max()

    expected_months = pd.date_range(
        start=first_period,
        end=last_period,
        freq="MS",
    )

    observed_periods = pd.DatetimeIndex(
        observations["period"].drop_duplicates()
    )

    missing_calendar_months = (
        expected_months.difference(
            observed_periods
        )
    )

    missing_value_periods = (
        observations.loc[
            observations["value"].isna(),
            "period",
        ]
        .dt.strftime("%Y-%m")
        .tolist()
    )

    return {
        "series_id": series_id,
        "variable_name": variable_name,
        "category": category,
        "first_period": first_period,
        "last_period": last_period,
        "expected_months": len(
            expected_months
        ),
        "returned_months": (
            observations["period"].nunique()
        ),
        "missing_calendar_months": len(
            missing_calendar_months
        ),
        "missing_calendar_periods": ", ".join(
            period.strftime("%Y-%m")
            for period in missing_calendar_months
        ),
        "missing_values": int(
            observations["value"].isna().sum()
        ),
        "missing_value_periods": ", ".join(
            missing_value_periods
        ),
    }


def select_metadata_fields(
    metadata: dict,
    variable_name: str,
    category: str,
) -> dict:
    """Keep the metadata fields used by this project."""

    fields = [
        "series_id",
        "title",
        "frequency",
        "frequency_short",
        "units",
        "units_short",
        "seasonal_adjustment",
        "seasonal_adjustment_short",
        "observation_start",
        "observation_end",
        "last_updated",
        "notes",
    ]

    record = {
        field: metadata.get(field, "")
        for field in fields
    }

    record["variable_name"] = variable_name
    record["category"] = category

    return record


def build_fred_dataset(
    observation_start: str = DEFAULT_START,
    observation_end: str | None = None,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Download configured FRED series and build long,
    wide, metadata, and coverage tables.
    """

    config = load_series_config()

    long_parts: list[pd.DataFrame] = []
    metadata_rows: list[dict] = []
    coverage_rows: list[dict] = []

    with create_session() as session:
        for row in config.itertuples(
            index=False
        ):
            print(
                f"Fetching {row.series_id} "
                f"as {row.variable_name}..."
            )

            metadata = fetch_fred_metadata(
                series_id=row.series_id,
                session=session,
            )

            frequency_short = str(
                metadata.get(
                    "frequency_short",
                    "",
                )
            ).strip()

            if frequency_short != "M":
                raise ValueError(
                    f"{row.series_id} is not monthly. "
                    f"Reported frequency: "
                    f"{metadata.get('frequency', '')}"
                )

            observations = (
                fetch_fred_observations(
                    series_id=row.series_id,
                    observation_start=(
                        observation_start
                    ),
                    observation_end=(
                        observation_end
                    ),
                    session=session,
                )
            )

            series_long = observations[
                [
                    "period",
                    "series_id",
                    "value",
                ]
            ].copy()

            series_long[
                "variable_name"
            ] = row.variable_name

            series_long[
                "category"
            ] = row.category

            long_parts.append(
                series_long
            )

            metadata_rows.append(
                select_metadata_fields(
                    metadata=metadata,
                    variable_name=(
                        row.variable_name
                    ),
                    category=row.category,
                )
            )

            coverage_rows.append(
                build_coverage_record(
                    observations=observations,
                    series_id=row.series_id,
                    variable_name=(
                        row.variable_name
                    ),
                    category=row.category,
                )
            )

    long_df = (
        pd.concat(
            long_parts,
            ignore_index=True,
        )
        .sort_values(
            [
                "period",
                "variable_name",
            ]
        )
        .reset_index(drop=True)
    )

    duplicate_mask = long_df.duplicated(
        subset=[
            "period",
            "variable_name",
        ]
    )

    if duplicate_mask.any():
        duplicated_rows = long_df.loc[
            duplicate_mask,
            [
                "period",
                "variable_name",
            ],
        ]

        raise ValueError(
            "Duplicate month-variable observations "
            "were found:\n"
            f"{duplicated_rows.to_string(index=False)}"
        )

    wide_df = (
        long_df
        .pivot(
            index="period",
            columns="variable_name",
            values="value",
        )
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )

    wide_df.columns.name = None

    configured_variables = (
        config["variable_name"].tolist()
    )

    ordered_columns = [
        "period",
        *configured_variables,
    ]

    wide_df = wide_df.reindex(
        columns=ordered_columns
    )

    metadata_df = (
        pd.DataFrame(metadata_rows)
        .sort_values("series_id")
        .reset_index(drop=True)
    )

    coverage_df = (
        pd.DataFrame(coverage_rows)
        .sort_values("series_id")
        .reset_index(drop=True)
    )

    return (
        long_df,
        wide_df,
        metadata_df,
        coverage_df,
    )


def main() -> None:
    (
        long_df,
        wide_df,
        metadata_df,
        coverage_df,
    ) = build_fred_dataset(
        observation_start=DEFAULT_START,
    )

    PROCESSED_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    long_path = (
        PROCESSED_DIRECTORY
        / "fred_tx_macro_energy_long.csv"
    )

    wide_path = (
        PROCESSED_DIRECTORY
        / "fred_tx_macro_energy_wide.csv"
    )

    metadata_path = (
        PROCESSED_DIRECTORY
        / "fred_series_metadata.csv"
    )

    processed_coverage_path = (
        PROCESSED_DIRECTORY
        / "fred_series_coverage.csv"
    )

    report_metadata_path = (
        REPORT_DIRECTORY
        / "fred_series_metadata.csv"
    )

    report_coverage_path = (
        REPORT_DIRECTORY
        / "fred_series_coverage.csv"
    )

    long_df.to_csv(
        long_path,
        index=False,
    )

    wide_df.to_csv(
        wide_path,
        index=False,
    )

    metadata_df.to_csv(
        metadata_path,
        index=False,
        encoding="utf-8-sig",
    )

    coverage_df.to_csv(
        processed_coverage_path,
        index=False,
        encoding="utf-8-sig",
    )

    # Small metadata and coverage reports are copied to
    # reports/tables so they can be committed to Git.
    metadata_df.to_csv(
        report_metadata_path,
        index=False,
        encoding="utf-8-sig",
    )

    coverage_df.to_csv(
        report_coverage_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nFRED wide-format data:")
    print(
        wide_df.head().to_string(
            index=False
        )
    )

    print("\nSeries metadata:")
    print(
        metadata_df[
            [
                "series_id",
                "variable_name",
                "frequency",
                "units",
                "seasonal_adjustment",
            ]
        ].to_string(index=False)
    )

    print("\nSeries coverage:")
    print(
        coverage_df.to_string(
            index=False
        )
    )

    print(
        f"\nNumber of long-format rows: "
        f"{len(long_df)}"
    )

    print(
        f"Number of monthly dates in wide data: "
        f"{len(wide_df)}"
    )

    print(
        f"Wide-data date range: "
        f"{wide_df['period'].min():%Y-%m} to "
        f"{wide_df['period'].max():%Y-%m}"
    )

    print(
        f"\nSaved long data to: "
        f"{long_path}"
    )

    print(
        f"Saved wide data to: "
        f"{wide_path}"
    )

    print(
        f"Saved metadata report to: "
        f"{report_metadata_path}"
    )

    print(
        f"Saved coverage report to: "
        f"{report_coverage_path}"
    )


if __name__ == "__main__":
    main()