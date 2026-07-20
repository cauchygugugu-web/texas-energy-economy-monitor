from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ENERGY_ECONOMY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "tx_energy_economy_monthly.csv"
)

WEATHER_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "tx_weather_monthly.csv"
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

OUTPUT_PATH = (
    PROCESSED_DIRECTORY
    / "tx_energy_economy_analysis_sample.csv"
)

MERGE_REPORT_PATH = (
    REPORT_DIRECTORY
    / "analysis_sample_merge_report.csv"
)

COVERAGE_REPORT_PATH = (
    REPORT_DIRECTORY
    / "analysis_sample_coverage.csv"
)


def standardize_monthly_period(
    df: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:
    """Standardize period to month-start dates and validate uniqueness."""

    if "period" not in df.columns:
        raise ValueError(
            f"{dataset_name} does not contain a period column."
        )

    result = df.copy()

    result["period"] = pd.to_datetime(
        result["period"],
        errors="coerce",
    )

    if result["period"].isna().any():
        raise ValueError(
            f"Invalid dates were found in {dataset_name}."
        )

    result["period"] = (
        result["period"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    duplicate_mask = result["period"].duplicated(
        keep=False
    )

    if duplicate_mask.any():
        duplicated_periods = (
            result.loc[
                duplicate_mask,
                "period",
            ]
            .drop_duplicates()
            .dt.strftime("%Y-%m")
            .tolist()
        )

        raise ValueError(
            f"Duplicate months were found in {dataset_name}: "
            f"{duplicated_periods}"
        )

    return (
        result
        .sort_values("period")
        .reset_index(drop=True)
    )


def load_energy_economy_data() -> pd.DataFrame:
    """Load the integrated EIA–FRED monthly dataset."""

    if not ENERGY_ECONOMY_PATH.exists():
        raise FileNotFoundError(
            "The energy-and-economy dataset was not found. "
            "Run build_energy_economy_dataset.py first."
        )

    data = pd.read_csv(
        ENERGY_ECONOMY_PATH
    )

    return standardize_monthly_period(
        data,
        dataset_name="energy-and-economy data",
    )


def load_weather_data() -> pd.DataFrame:
    """Load the NOAA monthly Texas weather dataset."""

    if not WEATHER_PATH.exists():
        raise FileNotFoundError(
            "The Texas weather dataset was not found. "
            "Run build_weather_dataset.py first."
        )

    data = pd.read_csv(
        WEATHER_PATH
    )

    return standardize_monthly_period(
        data,
        dataset_name="weather data",
    )


def merge_analysis_sample(
    energy_economy: pd.DataFrame,
    weather: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Merge energy-economy and weather data by month.

    An outer merge is used to produce the coverage report.
    The main analysis sample keeps months available in both datasets.
    """

    overlapping_columns = (
        set(energy_economy.columns)
        & set(weather.columns)
    ) - {"period"}

    if overlapping_columns:
        raise ValueError(
            "Unexpected overlapping non-key columns were found: "
            f"{sorted(overlapping_columns)}"
        )

    merged = energy_economy.merge(
        weather,
        on="period",
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    merge_report = (
        merged[
            [
                "period",
                "_merge",
            ]
        ]
        .sort_values("period")
        .reset_index(drop=True)
    )

    merge_report["energy_economy_available"] = (
        merge_report["_merge"].isin(
            [
                "both",
                "left_only",
            ]
        )
    )

    merge_report["weather_available"] = (
        merge_report["_merge"].isin(
            [
                "both",
                "right_only",
            ]
        )
    )

    analysis_sample = (
        merged.loc[
            merged["_merge"].eq("both")
        ]
        .drop(columns="_merge")
        .sort_values("period")
        .reset_index(drop=True)
    )

    if analysis_sample.empty:
        raise ValueError(
            "The energy-economy and weather datasets "
            "have no overlapping months."
        )

    return analysis_sample, merge_report


def build_variable_coverage(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize valid monthly coverage for every variable."""

    rows: list[dict] = []

    for column in df.columns:
        if column == "period":
            continue

        valid_mask = df[column].notna()

        first_valid_period = (
            df.loc[
                valid_mask,
                "period",
            ].min()
        )

        last_valid_period = (
            df.loc[
                valid_mask,
                "period",
            ].max()
        )

        rows.append(
            {
                "variable": column,
                "total_months": len(df),
                "observed_months": int(
                    valid_mask.sum()
                ),
                "missing_months": int(
                    (~valid_mask).sum()
                ),
                "first_valid_period": (
                    first_valid_period
                ),
                "last_valid_period": (
                    last_valid_period
                ),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("variable")
        .reset_index(drop=True)
    )


def build_analysis_sample() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Build the final monthly Texas analysis sample."""

    energy_economy = (
        load_energy_economy_data()
    )

    weather = load_weather_data()

    analysis_sample, merge_report = (
        merge_analysis_sample(
            energy_economy=energy_economy,
            weather=weather,
        )
    )

    coverage_report = (
        build_variable_coverage(
            analysis_sample
        )
    )

    return (
        analysis_sample,
        merge_report,
        coverage_report,
    )


def main() -> None:
    (
        analysis_sample,
        merge_report,
        coverage_report,
    ) = build_analysis_sample()

    PROCESSED_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    analysis_sample.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    merge_report.to_csv(
        MERGE_REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    coverage_report.to_csv(
        COVERAGE_REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "\nTexas energy-economy-weather analysis sample:"
    )

    display_columns = [
        "period",
        "residential_price_real_2025_01",
        "henry_hub_natural_gas_price",
        "renewable_share",
        "tx_nonfarm_employment_yoy_pct",
        "tx_average_temperature",
        "tx_precipitation",
        "tx_heating_degree_days",
        "tx_cooling_degree_days",
    ]

    available_display_columns = [
        column
        for column in display_columns
        if column in analysis_sample.columns
    ]

    print(
        analysis_sample[
            available_display_columns
        ]
        .head(15)
        .to_string(index=False)
    )

    print("\nMerge results:")

    print(
        merge_report["_merge"]
        .value_counts()
        .to_string()
    )

    unmatched = merge_report.loc[
        ~merge_report["_merge"].eq("both")
    ]

    if unmatched.empty:
        print(
            "\nAll source-table months matched."
        )
    else:
        print(
            "\nUnmatched source-table months:"
        )

        print(
            unmatched.to_string(
                index=False
            )
        )

    weather_variables = [
        "tx_average_temperature",
        "tx_precipitation",
        "tx_heating_degree_days",
        "tx_cooling_degree_days",
    ]

    print(
        "\nWeather-variable coverage:"
    )

    print(
        coverage_report.loc[
            coverage_report["variable"].isin(
                weather_variables
            )
        ].to_string(
            index=False
        )
    )

    print(
        f"\nNumber of matched months: "
        f"{len(analysis_sample)}"
    )

    print(
        f"Date range: "
        f"{analysis_sample['period'].min():%Y-%m} to "
        f"{analysis_sample['period'].max():%Y-%m}"
    )

    print(
        f"\nSaved analysis sample to: "
        f"{OUTPUT_PATH}"
    )

    print(
        f"Saved merge report to: "
        f"{MERGE_REPORT_PATH}"
    )

    print(
        f"Saved coverage report to: "
        f"{COVERAGE_REPORT_PATH}"
    )


if __name__ == "__main__":
    main()
