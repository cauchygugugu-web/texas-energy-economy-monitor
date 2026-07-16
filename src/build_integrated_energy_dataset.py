from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RETAIL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_retail_electricity.csv"
)

GENERATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_generation_clean_wide.csv"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

SECTOR_NAMES = {
    "RES": "residential",
    "COM": "commercial",
    "IND": "industrial",
}

RETAIL_VARIABLES = [
    "price",
    "sales",
    "revenue",
    "customers",
]


def load_retail_data() -> pd.DataFrame:
    """Load and validate monthly retail electricity data."""

    if not RETAIL_PATH.exists():
        raise FileNotFoundError(
            "Retail electricity data were not found. "
            "Run build_retail_dataset.py first."
        )

    retail = pd.read_csv(
        RETAIL_PATH,
        dtype={
            "stateid": str,
            "sectorid": str,
        },
    )

    required_columns = {
        "period",
        "stateid",
        "sectorid",
        *RETAIL_VARIABLES,
    }

    missing_columns = (
        required_columns - set(retail.columns)
    )

    if missing_columns:
        raise ValueError(
            "Retail data columns are missing: "
            f"{sorted(missing_columns)}"
        )

    retail["period"] = pd.to_datetime(
        retail["period"],
        errors="coerce",
    )

    if retail["period"].isna().any():
        raise ValueError(
            "Invalid retail-data dates were found."
        )

    retail["sectorid"] = (
        retail["sectorid"]
        .str.strip()
        .str.upper()
    )

    retail = retail.loc[
        retail["sectorid"].isin(
            SECTOR_NAMES
        )
    ].copy()

    for variable in RETAIL_VARIABLES:
        retail[variable] = pd.to_numeric(
            retail[variable],
            errors="coerce",
        )

    duplicate_mask = retail.duplicated(
        subset=[
            "period",
            "stateid",
            "sectorid",
        ]
    )

    if duplicate_mask.any():
        duplicated_rows = retail.loc[
            duplicate_mask,
            [
                "period",
                "stateid",
                "sectorid",
            ],
        ]

        raise ValueError(
            "Duplicate retail observations were found:\n"
            f"{duplicated_rows.to_string(index=False)}"
        )

    actual_sectors = set(
        retail["sectorid"].unique()
    )

    expected_sectors = set(
        SECTOR_NAMES
    )

    if actual_sectors != expected_sectors:
        raise ValueError(
            f"Expected sectors "
            f"{sorted(expected_sectors)}, "
            f"but found "
            f"{sorted(actual_sectors)}."
        )

    return retail


def build_retail_wide(
    retail: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert retail data to one row per month.

    Example columns:
        residential_price
        commercial_sales
        industrial_customers
    """

    retail_long = retail[
        [
            "period",
            "sectorid",
            *RETAIL_VARIABLES,
        ]
    ].copy()

    retail_long["sector_name"] = (
        retail_long["sectorid"]
        .map(SECTOR_NAMES)
    )

    melted = retail_long.melt(
        id_vars=[
            "period",
            "sector_name",
        ],
        value_vars=RETAIL_VARIABLES,
        var_name="variable",
        value_name="value",
    )

    melted["column_name"] = (
        melted["sector_name"]
        + "_"
        + melted["variable"]
    )

    retail_wide = (
        melted
        .pivot(
            index="period",
            columns="column_name",
            values="value",
        )
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )

    retail_wide.columns.name = None

    return retail_wide


def load_generation_data() -> pd.DataFrame:
    """Load and validate the clean generation dataset."""

    if not GENERATION_PATH.exists():
        raise FileNotFoundError(
            "Clean generation data were not found. "
            "Run build_generation_dataset.py first."
        )

    generation = pd.read_csv(
        GENERATION_PATH
    )

    if "period" not in generation.columns:
        raise ValueError(
            "Generation data do not contain "
            "a period column."
        )

    generation["period"] = pd.to_datetime(
        generation["period"],
        errors="coerce",
    )

    if generation["period"].isna().any():
        raise ValueError(
            "Invalid generation-data dates were found."
        )

    if generation["period"].duplicated().any():
        duplicated_periods = (
            generation.loc[
                generation["period"].duplicated(
                    keep=False
                ),
                "period",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate generation months were found: "
            f"{duplicated_periods}"
        )

    for column in generation.columns:
        if column != "period":
            generation[column] = pd.to_numeric(
                generation[column],
                errors="coerce",
            )

    return (
        generation
        .sort_values("period")
        .reset_index(drop=True)
    )


def build_integrated_dataset() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Merge retail electricity and generation data.

    Returns
    -------
    integrated:
        Months available in both datasets.

    merge_report:
        Coverage and matching information for all months.
    """

    retail = load_retail_data()

    retail_wide = build_retail_wide(
        retail
    )

    generation = load_generation_data()

    merged = retail_wide.merge(
        generation,
        on="period",
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    merge_report = merged[
        [
            "period",
            "_merge",
        ]
    ].copy()

    merge_report["retail_available"] = (
        merge_report["_merge"].isin(
            [
                "both",
                "left_only",
            ]
        )
    )

    merge_report["generation_available"] = (
        merge_report["_merge"].isin(
            [
                "both",
                "right_only",
            ]
        )
    )

    integrated = (
        merged.loc[
            merged["_merge"].eq("both")
        ]
        .drop(columns="_merge")
        .sort_values("period")
        .reset_index(drop=True)
    )

    merge_report = (
        merge_report
        .sort_values("period")
        .reset_index(drop=True)
    )

    if integrated.empty:
        raise ValueError(
            "The retail and generation datasets "
            "have no overlapping months."
        )

    return integrated, merge_report


def main() -> None:
    integrated, merge_report = (
        build_integrated_dataset()
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    integrated_path = (
        OUTPUT_DIRECTORY
        / "eia_tx_integrated_energy_monthly.csv"
    )

    merge_report_path = (
        OUTPUT_DIRECTORY
        / "eia_tx_integrated_merge_report.csv"
    )

    integrated.to_csv(
        integrated_path,
        index=False,
    )

    merge_report.to_csv(
        merge_report_path,
        index=False,
    )

    match_counts = (
        merge_report["_merge"]
        .value_counts()
    )

    unmatched = merge_report.loc[
        ~merge_report["_merge"].eq("both")
    ]

    print("\nIntegrated monthly energy data:")
    print(
        integrated.head().to_string(
            index=False
        )
    )

    print("\nColumns:")
    print(integrated.columns.tolist())

    print(
        f"\nNumber of integrated months: "
        f"{len(integrated)}"
    )

    print(
        f"Date range: "
        f"{integrated['period'].min():%Y-%m} to "
        f"{integrated['period'].max():%Y-%m}"
    )

    print("\nMerge results:")
    print(match_counts.to_string())

    if unmatched.empty:
        print(
            "\nAll months are available in both datasets."
        )
    else:
        print("\nUnmatched months:")
        print(
            unmatched.to_string(
                index=False
            )
        )

    print(
        f"\nSaved integrated dataset to: "
        f"{integrated_path}"
    )

    print(
        f"Saved merge report to: "
        f"{merge_report_path}"
    )


if __name__ == "__main__":
    main()