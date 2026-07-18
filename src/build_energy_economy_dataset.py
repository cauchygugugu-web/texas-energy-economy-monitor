from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EIA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_energy_time_series_features.csv"
)

FRED_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "fred_tx_macro_energy_wide.csv"
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
    / "tx_energy_economy_monthly.csv"
)

MERGE_REPORT_PATH = (
    REPORT_DIRECTORY
    / "energy_economy_merge_report.csv"
)

COVERAGE_REPORT_PATH = (
    REPORT_DIRECTORY
    / "energy_economy_variable_coverage.csv"
)

BASE_CPI_PERIOD = pd.Timestamp("2025-01-01")

REQUIRED_FRED_COLUMNS = [
    "tx_unemployment_rate",
    "tx_total_nonfarm_employment",
    "wti_crude_oil_price",
    "henry_hub_natural_gas_price",
    "us_cpi",
]

NOMINAL_RETAIL_PRICE_COLUMNS = [
    "residential_price",
    "commercial_price",
    "industrial_price",
]


def standardize_monthly_period(
    df: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:
    """Convert period to month-start dates and validate uniqueness."""

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
        invalid_rows = result.loc[
            result["period"].isna()
        ]

        raise ValueError(
            f"Invalid dates were found in {dataset_name}:\n"
            f"{invalid_rows.to_string(index=False)}"
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


def load_eia_features() -> pd.DataFrame:
    """Load and validate the EIA time-series feature dataset."""

    if not EIA_PATH.exists():
        raise FileNotFoundError(
            "The EIA time-series feature dataset was not found. "
            "Run build_time_series_features.py first."
        )

    eia = pd.read_csv(
        EIA_PATH
    )

    eia = standardize_monthly_period(
        eia,
        dataset_name="EIA feature data",
    )

    missing_price_columns = (
        set(NOMINAL_RETAIL_PRICE_COLUMNS)
        - set(eia.columns)
    )

    if missing_price_columns:
        raise ValueError(
            "Required EIA retail-price columns are missing: "
            f"{sorted(missing_price_columns)}"
        )

    for column in NOMINAL_RETAIL_PRICE_COLUMNS:
        eia[column] = pd.to_numeric(
            eia[column],
            errors="coerce",
        )

    return eia


def load_fred_data() -> pd.DataFrame:
    """Load and validate the monthly FRED wide-format dataset."""

    if not FRED_PATH.exists():
        raise FileNotFoundError(
            "The FRED wide-format dataset was not found. "
            "Run build_fred_dataset.py first."
        )

    fred = pd.read_csv(
        FRED_PATH
    )

    fred = standardize_monthly_period(
        fred,
        dataset_name="FRED data",
    )

    missing_columns = (
        set(REQUIRED_FRED_COLUMNS)
        - set(fred.columns)
    )

    if missing_columns:
        raise ValueError(
            "Required FRED variables are missing: "
            f"{sorted(missing_columns)}"
        )

    for column in REQUIRED_FRED_COLUMNS:
        fred[column] = pd.to_numeric(
            fred[column],
            errors="coerce",
        )

    return fred


def merge_eia_and_fred(
    eia: pd.DataFrame,
    fred: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Merge EIA and FRED data by month.

    The outer merge is retained for the merge report.
    The main dataset keeps months available in both source tables.
    """

    merged = eia.merge(
        fred,
        on="period",
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    merge_report = merged[
        [
            "period",
            "_merge",
        ]
    ].copy()

    merge_report["eia_available"] = (
        merge_report["_merge"]
        .isin(
            [
                "both",
                "left_only",
            ]
        )
    )

    merge_report["fred_available"] = (
        merge_report["_merge"]
        .isin(
            [
                "both",
                "right_only",
            ]
        )
    )

    matched = (
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

    if matched.empty:
        raise ValueError(
            "The EIA and FRED datasets have no overlapping months."
        )

    return matched, merge_report


def add_macro_energy_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Construct monthly macroeconomic and energy-price features."""

    result = df.copy()

    result[
        "tx_nonfarm_employment_yoy_pct"
    ] = (
        result[
            "tx_total_nonfarm_employment"
        ]
        .pct_change(
            periods=12,
            fill_method=None,
        )
        .mul(100)
    )

    result[
        "tx_unemployment_rate_yoy_pp"
    ] = (
        result[
            "tx_unemployment_rate"
        ]
        .diff(12)
    )

    result[
        "wti_crude_oil_price_yoy_pct"
    ] = (
        result[
            "wti_crude_oil_price"
        ]
        .pct_change(
            periods=12,
            fill_method=None,
        )
        .mul(100)
    )

    result[
        "henry_hub_natural_gas_price_yoy_pct"
    ] = (
        result[
            "henry_hub_natural_gas_price"
        ]
        .pct_change(
            periods=12,
            fill_method=None,
        )
        .mul(100)
    )

    feature_columns = [
        "tx_nonfarm_employment_yoy_pct",
        "tx_unemployment_rate_yoy_pp",
        "wti_crude_oil_price_yoy_pct",
        "henry_hub_natural_gas_price_yoy_pct",
    ]

    result[feature_columns] = (
        result[feature_columns]
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
    )

    return result


def add_real_retail_prices(
    df: pd.DataFrame,
    base_period: pd.Timestamp = BASE_CPI_PERIOD,
) -> tuple[pd.DataFrame, float]:
    """
    Convert nominal retail electricity prices to base-period prices.

    real_price_t = nominal_price_t * CPI_base / CPI_t
    """

    result = df.copy()

    base_rows = result.loc[
        result["period"].eq(base_period),
        "us_cpi",
    ]

    if len(base_rows) != 1:
        raise ValueError(
            "The CPI base period could not be identified uniquely. "
            f"Requested base period: {base_period:%Y-%m}; "
            f"matching rows: {len(base_rows)}."
        )

    base_cpi = float(
        base_rows.iloc[0]
    )

    if pd.isna(base_cpi) or base_cpi <= 0:
        raise ValueError(
            "The CPI base-period value is missing or non-positive."
        )

    invalid_cpi_mask = (
        result["us_cpi"].isna()
        | result["us_cpi"].le(0)
    )

    suffix = base_period.strftime(
        "%Y_%m"
    )

    for nominal_column in NOMINAL_RETAIL_PRICE_COLUMNS:
        real_column = (
            f"{nominal_column}_real_{suffix}"
        )

        result[real_column] = (
            result[nominal_column]
            * base_cpi
            / result["us_cpi"]
        )

        result.loc[
            invalid_cpi_mask,
            real_column,
        ] = np.nan

    return result, base_cpi


def build_variable_coverage(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize valid monthly coverage for every column."""

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


def build_energy_economy_dataset() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    float,
]:
    """Build the integrated Texas energy-and-economy dataset."""

    eia = load_eia_features()
    fred = load_fred_data()

    matched, merge_report = (
        merge_eia_and_fred(
            eia=eia,
            fred=fred,
        )
    )

    features = add_macro_energy_features(
        matched
    )

    features, base_cpi = (
        add_real_retail_prices(
            features,
            base_period=BASE_CPI_PERIOD,
        )
    )

    coverage_report = (
        build_variable_coverage(
            features
        )
    )

    return (
        features,
        merge_report,
        coverage_report,
        base_cpi,
    )


def main() -> None:
    (
        dataset,
        merge_report,
        coverage_report,
        base_cpi,
    ) = build_energy_economy_dataset()

    PROCESSED_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset.to_csv(
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

    merge_counts = (
        merge_report["_merge"]
        .value_counts()
    )

    unmatched = merge_report.loc[
        ~merge_report["_merge"].eq(
            "both"
        )
    ]

    display_columns = [
        "period",
        "residential_price",
        "residential_price_real_2025_01",
        "tx_unemployment_rate",
        "tx_total_nonfarm_employment",
        "tx_nonfarm_employment_yoy_pct",
        "wti_crude_oil_price",
        "henry_hub_natural_gas_price",
        "us_cpi",
    ]

    available_display_columns = [
        column
        for column in display_columns
        if column in dataset.columns
    ]

    print(
        "\nIntegrated Texas energy-and-economy data:"
    )

    print(
        dataset[
            available_display_columns
        ]
        .head(15)
        .to_string(index=False)
    )

    print("\nMerge results:")
    print(
        merge_counts.to_string()
    )

    if unmatched.empty:
        print(
            "\nAll source-table months matched."
        )
    else:
        print("\nUnmatched source-table months:")
        print(
            unmatched.to_string(
                index=False
            )
        )

    print(
        f"\nNumber of matched months: "
        f"{len(dataset)}"
    )

    print(
        f"Matched date range: "
        f"{dataset['period'].min():%Y-%m} to "
        f"{dataset['period'].max():%Y-%m}"
    )

    print(
        f"CPI base period: "
        f"{BASE_CPI_PERIOD:%Y-%m}"
    )

    print(
        f"CPI base value: "
        f"{base_cpi:.6f}"
    )

    new_feature_columns = [
        "tx_nonfarm_employment_yoy_pct",
        "tx_unemployment_rate_yoy_pp",
        "wti_crude_oil_price_yoy_pct",
        "henry_hub_natural_gas_price_yoy_pct",
        "residential_price_real_2025_01",
        "commercial_price_real_2025_01",
        "industrial_price_real_2025_01",
    ]

    print("\nNew feature coverage:")
    print(
        coverage_report.loc[
            coverage_report["variable"].isin(
                new_feature_columns
            )
        ].to_string(
            index=False
        )
    )

    print(
        f"\nSaved integrated dataset to: "
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