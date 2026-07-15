from pathlib import Path

import pandas as pd

from fetch_eia import (
    DEFAULT_DATA_FIELDS,
    fetch_retail_electricity_data,
    validate_electricity_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

STATE = "TX"

SECTORS = [
    "RES",
    "COM",
    "IND",
]


def check_month_coverage(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produce a summary of missing months by sector.
    """

    expected_months = pd.date_range(
        start=df["period"].min(),
        end=df["period"].max(),
        freq="MS",
    )

    results: list[dict] = []

    for sector in SECTORS:
        sector_months = df.loc[
            df["sectorid"].eq(sector),
            "period",
        ]

        missing_months = (
            expected_months.difference(
                sector_months
            )
        )

        results.append(
            {
                "sectorid": sector,
                "expected_months": len(
                    expected_months
                ),
                "observed_months": (
                    sector_months.nunique()
                ),
                "missing_months": len(
                    missing_months
                ),
                "missing_periods": ", ".join(
                    month.strftime("%Y-%m")
                    for month in missing_months
                ),
            }
        )

    return pd.DataFrame(results)


def build_retail_dataset(
    start: str = "2015-01",
    end: str | None = None,
) -> pd.DataFrame:
    """
    Build the complete Texas retail electricity dataset.
    """

    df = fetch_retail_electricity_data(
        state=STATE,
        sectors=SECTORS,
        start=start,
        end=end,
        data_fields=DEFAULT_DATA_FIELDS,
    )

    validate_electricity_data(
        df=df,
        state=STATE,
        sectors=SECTORS,
        required_fields=DEFAULT_DATA_FIELDS,
    )

    return df


def main() -> None:
    df = build_retail_dataset(
        start="2015-01",
    )

    coverage_report = check_month_coverage(
        df
    )

    missing_value_report = (
        df[
            DEFAULT_DATA_FIELDS
        ]
        .isna()
        .sum()
        .rename("missing_values")
        .reset_index()
        .rename(
            columns={
                "index": "variable",
            }
        )
    )

    output_directory = (
        PROJECT_ROOT
        / "data"
        / "processed"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset_path = (
        output_directory
        / "eia_tx_retail_electricity.csv"
    )

    coverage_path = (
        output_directory
        / "eia_tx_month_coverage.csv"
    )

    missing_values_path = (
        output_directory
        / "eia_tx_missing_values.csv"
    )

    df.to_csv(
        dataset_path,
        index=False,
    )

    coverage_report.to_csv(
        coverage_path,
        index=False,
    )

    missing_value_report.to_csv(
        missing_values_path,
        index=False,
    )

    print("\nComplete retail electricity data:")
    print(df.head(9))

    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nData types:")
    print(df.dtypes)

    print("\nMonth coverage:")
    print(
        coverage_report.to_string(
            index=False
        )
    )

    print("\nMissing values:")
    print(
        missing_value_report.to_string(
            index=False
        )
    )

    print(
        f"\nNumber of observations: "
        f"{len(df)}"
    )

    print(
        f"Date range: "
        f"{df['period'].min():%Y-%m} to "
        f"{df['period'].max():%Y-%m}"
    )

    print(
        f"\nSaved dataset to: "
        f"{dataset_path}"
    )

    print(
        f"Saved coverage report to: "
        f"{coverage_path}"
    )

    print(
        f"Saved missing-value report to: "
        f"{missing_values_path}"
    )


if __name__ == "__main__":
    main()