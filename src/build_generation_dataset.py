from pathlib import Path

import pandas as pd

from fetch_generation import (
    fetch_generation_data,
    validate_generation_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOCATION = "TX"


def build_generation_dataset(
    start: str = "2015-01",
    end: str | None = None,
) -> pd.DataFrame:
    """Build Texas monthly generation data."""

    df = fetch_generation_data(
        location=LOCATION,
        start=start,
        end=end,
    )

    validate_generation_data(
        df=df,
        location=LOCATION,
    )

    return df


def build_fuel_coverage_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Summarize time coverage for each fuel type.
    """

    results: list[dict] = []

    for fuel_id, group in df.groupby(
        "fueltypeid"
    ):
        periods = group["period"].drop_duplicates()

        fuel_description = ""

        if "fuelTypeDescription" in group.columns:
            descriptions = (
                group["fuelTypeDescription"]
                .dropna()
                .unique()
            )

            if len(descriptions) > 0:
                fuel_description = descriptions[0]

        results.append(
            {
                "fueltypeid": fuel_id,
                "fuel_description": (
                    fuel_description
                ),
                "first_period": periods.min(),
                "last_period": periods.max(),
                "observed_months": periods.nunique(),
                "missing_generation_values": (
                    group["generation"]
                    .isna()
                    .sum()
                ),
            }
        )

    return (
        pd.DataFrame(results)
        .sort_values("fueltypeid")
        .reset_index(drop=True)
    )


def main() -> None:
    df = build_generation_dataset(
        start="2015-01",
    )

    coverage_report = (
        build_fuel_coverage_report(df)
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
        / "eia_tx_generation_by_fuel.csv"
    )

    coverage_path = (
        output_directory
        / "eia_tx_generation_fuel_coverage.csv"
    )

    df.to_csv(
        dataset_path,
        index=False,
    )

    coverage_report.to_csv(
        coverage_path,
        index=False,
    )

    print("\nGeneration dataset:")
    print(df.head(20))

    print("\nFuel coverage:")
    print(
        coverage_report.to_string(
            index=False
        )
    )

    print(
        f"\nNumber of observations: {len(df)}"
    )

    print(
        f"Number of fuel types: "
        f"{df['fueltypeid'].nunique()}"
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


if __name__ == "__main__":
    main()