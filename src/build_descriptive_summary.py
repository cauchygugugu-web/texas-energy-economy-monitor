from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_energy_indicators_monthly.csv"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "tables"
)


SUMMARY_VARIABLES = [
    "residential_price",
    "commercial_price",
    "industrial_price",
    "total_generation",
    "renewable_share",
    "fossil_share",
    "natural_gas_share",
    "coal_share",
    "wind_share",
    "solar_share",
    "residential_sales_per_customer_kwh",
    "commercial_sales_per_customer_kwh",
    "industrial_sales_per_customer_kwh",
]


def load_indicator_data() -> pd.DataFrame:
    """Load and validate the monthly indicator dataset."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Indicator data were not found. "
            "Run build_energy_indicators.py first."
        )

    df = pd.read_csv(
        INPUT_PATH,
        parse_dates=["period"],
    )

    if df["period"].isna().any():
        raise ValueError(
            "Invalid period values were found."
        )

    if df["period"].duplicated().any():
        raise ValueError(
            "Duplicate monthly observations were found."
        )

    missing_columns = (
        set(SUMMARY_VARIABLES)
        - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Summary variables are missing: "
            f"{sorted(missing_columns)}"
        )

    return (
        df.sort_values("period")
        .reset_index(drop=True)
    )


def build_summary_statistics(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Create a standard descriptive-statistics table."""

    summary = (
        df[SUMMARY_VARIABLES]
        .describe(
            percentiles=[
                0.25,
                0.50,
                0.75,
            ]
        )
        .transpose()
        .reset_index()
        .rename(
            columns={
                "index": "variable",
                "50%": "median",
            }
        )
    )

    return summary


def build_coverage_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize coverage and missingness by variable."""

    rows = []

    for variable in SUMMARY_VARIABLES:
        valid = df.loc[
            df[variable].notna(),
            [
                "period",
                variable,
            ],
        ]

        rows.append(
            {
                "variable": variable,
                "total_months": len(df),
                "observed_months": len(valid),
                "missing_months": (
                    df[variable].isna().sum()
                ),
                "first_period": (
                    valid["period"].min()
                ),
                "last_period": (
                    valid["period"].max()
                ),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    df = load_indicator_data()

    summary = build_summary_statistics(df)

    coverage = build_coverage_report(df)

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_path = (
        OUTPUT_DIRECTORY
        / "energy_indicator_summary.csv"
    )

    coverage_path = (
        OUTPUT_DIRECTORY
        / "energy_indicator_coverage.csv"
    )

    summary.to_csv(
        summary_path,
        index=False,
    )

    coverage.to_csv(
        coverage_path,
        index=False,
    )

    print("\nDescriptive statistics:")
    print(
        summary.to_string(
            index=False
        )
    )

    print("\nVariable coverage:")
    print(
        coverage.to_string(
            index=False
        )
    )

    print(
        f"\nSaved summary statistics to: "
        f"{summary_path}"
    )

    print(
        f"Saved coverage report to: "
        f"{coverage_path}"
    )


if __name__ == "__main__":
    main()