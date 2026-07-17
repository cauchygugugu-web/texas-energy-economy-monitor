from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_integrated_energy_monthly.csv"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

OUTPUT_PATH = (
    OUTPUT_DIRECTORY
    / "eia_tx_energy_indicators_monthly.csv"
)

VALIDATION_PATH = (
    OUTPUT_DIRECTORY
    / "eia_tx_retail_price_validation.csv"
)


RENEWABLE_COLUMNS = [
    "Wind",
    "Solar",
    "Hydroelectric",
    "Biomass",
]

FOSSIL_COLUMNS = [
    "Coal",
    "Natural Gas",
    "Other Gases",
    "Petroleum",
]

OTHER_GENERATION_COLUMNS = [
    "Nuclear",
    "Other",
]

GENERATION_COLUMNS = (
    RENEWABLE_COLUMNS
    + FOSSIL_COLUMNS
    + OTHER_GENERATION_COLUMNS
)

SECTORS = [
    "residential",
    "commercial",
    "industrial",
]


def load_integrated_data() -> pd.DataFrame:
    """Load and validate the integrated monthly dataset."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "The integrated energy dataset was not found. "
            "Run build_integrated_energy_dataset.py first."
        )

    df = pd.read_csv(INPUT_PATH)

    if "period" not in df.columns:
        raise ValueError(
            "The integrated dataset does not contain "
            "a period column."
        )

    df["period"] = pd.to_datetime(
        df["period"],
        errors="coerce",
    )

    if df["period"].isna().any():
        raise ValueError(
            "Invalid period values were found."
        )

    if df["period"].duplicated().any():
        duplicated_periods = (
            df.loc[
                df["period"].duplicated(
                    keep=False
                ),
                "period",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate monthly observations were found: "
            f"{duplicated_periods}"
        )

    required_columns = {
        *GENERATION_COLUMNS,
    }

    for sector in SECTORS:
        required_columns.update(
            {
                f"{sector}_price",
                f"{sector}_sales",
                f"{sector}_revenue",
                f"{sector}_customers",
            }
        )

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Required integrated-data columns are missing: "
            f"{sorted(missing_columns)}"
        )

    numeric_columns = list(
        required_columns
    )

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    missing_numeric_values = (
        df[numeric_columns]
        .isna()
        .sum()
    )

    missing_numeric_values = (
        missing_numeric_values.loc[
            missing_numeric_values.gt(0)
        ]
    )

    if not missing_numeric_values.empty:
        raise ValueError(
            "Missing or invalid numeric values were found:\n"
            f"{missing_numeric_values.to_string()}"
        )

    invalid_customers = []

    for sector in SECTORS:
        customer_column = (
            f"{sector}_customers"
        )

        if not df[
            customer_column
        ].gt(0).all():
            invalid_customers.append(
                customer_column
            )

    if invalid_customers:
        raise ValueError(
            "Non-positive customer counts were found in: "
            f"{invalid_customers}"
        )

    return (
        df.sort_values("period")
        .reset_index(drop=True)
    )


def add_generation_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Construct generation totals and generation shares."""

    result = df.copy()

    result["total_generation"] = (
        result[GENERATION_COLUMNS]
        .sum(axis=1)
    )

    if not result[
        "total_generation"
    ].gt(0).all():
        raise ValueError(
            "Non-positive total generation values "
            "were found."
        )

    result["renewable_generation"] = (
        result[RENEWABLE_COLUMNS]
        .sum(axis=1)
    )

    result["fossil_generation"] = (
        result[FOSSIL_COLUMNS]
        .sum(axis=1)
    )

    result["non_fossil_generation"] = (
        result["renewable_generation"]
        + result["Nuclear"]
    )

    result["renewable_share"] = (
        result["renewable_generation"]
        / result["total_generation"]
    )

    result["fossil_share"] = (
        result["fossil_generation"]
        / result["total_generation"]
    )

    result["nuclear_share"] = (
        result["Nuclear"]
        / result["total_generation"]
    )

    result["other_share"] = (
        result["Other"]
        / result["total_generation"]
    )

    fuel_column_names = {
        "Coal": "coal",
        "Natural Gas": "natural_gas",
        "Other Gases": "other_gases",
        "Petroleum": "petroleum",
        "Nuclear": "nuclear",
        "Hydroelectric": "hydroelectric",
        "Wind": "wind",
        "Solar": "solar",
        "Biomass": "biomass",
        "Other": "other",
    }

    for source_column, variable_name in (
        fuel_column_names.items()
    ):
        result[
            f"{variable_name}_share"
        ] = (
            result[source_column]
            / result["total_generation"]
        )

    share_columns = [
        "renewable_share",
        "fossil_share",
        "nuclear_share",
        "other_share",
    ]

    share_columns.extend(
        [
            f"{name}_share"
            for name in fuel_column_names.values()
        ]
    )

    for column in share_columns:
        invalid_share = (
            result[column].lt(-0.01)
            | result[column].gt(1.01)
        )

        if invalid_share.any():
            raise ValueError(
                f"Unexpected generation-share values "
                f"were found in {column}."
            )

    return result


def add_retail_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construct per-customer retail measures.

    EIA retail sales are measured in million kWh and
    revenue is measured in million dollars. Multiplying
    by 1,000,000 converts them to kWh and dollars.
    """

    result = df.copy()

    for sector in SECTORS:
        sales_column = (
            f"{sector}_sales"
        )

        revenue_column = (
            f"{sector}_revenue"
        )

        customers_column = (
            f"{sector}_customers"
        )

        result[
            f"{sector}_sales_per_customer_kwh"
        ] = (
            result[sales_column]
            * 1_000_000
            / result[customers_column]
        )

        result[
            f"{sector}_revenue_per_customer_dollars"
        ] = (
            result[revenue_column]
            * 1_000_000
            / result[customers_column]
        )

        result[
            f"{sector}_reconstructed_price"
        ] = (
            result[revenue_column]
            / result[sales_column]
            * 100
        )

        result[
            f"{sector}_price_difference"
        ] = (
            result[
                f"{sector}_reconstructed_price"
            ]
            - result[
                f"{sector}_price"
            ]
        )

    result[
        "selected_sector_sales"
    ] = sum(
        result[
            f"{sector}_sales"
        ]
        for sector in SECTORS
    )

    result[
        "selected_sector_revenue"
    ] = sum(
        result[
            f"{sector}_revenue"
        ]
        for sector in SECTORS
    )

    result[
        "selected_sector_customers"
    ] = sum(
        result[
            f"{sector}_customers"
        ]
        for sector in SECTORS
    )

    return result


def build_price_validation_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Create an audit report for reconstructed prices."""

    reports = []

    for sector in SECTORS:
        sector_report = df[
            [
                "period",
                f"{sector}_price",
                f"{sector}_reconstructed_price",
                f"{sector}_price_difference",
            ]
        ].copy()

        sector_report["sector"] = sector

        sector_report = sector_report.rename(
            columns={
                f"{sector}_price": (
                    "reported_price"
                ),
                f"{sector}_reconstructed_price": (
                    "reconstructed_price"
                ),
                f"{sector}_price_difference": (
                    "difference"
                ),
            }
        )

        reports.append(
            sector_report
        )

    validation = (
        pd.concat(
            reports,
            ignore_index=True,
        )
        .sort_values(
            [
                "period",
                "sector",
            ]
        )
        .reset_index(drop=True)
    )

    validation[
        "absolute_difference"
    ] = validation["difference"].abs()

    return validation


def build_energy_indicators() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Build analysis-ready monthly energy indicators."""

    integrated = load_integrated_data()

    indicators = add_generation_indicators(
        integrated
    )

    indicators = add_retail_indicators(
        indicators
    )

    price_validation = (
        build_price_validation_report(
            indicators
        )
    )

    return indicators, price_validation


def main() -> None:
    (
        indicators,
        price_validation,
    ) = build_energy_indicators()

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    indicators.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    price_validation.to_csv(
        VALIDATION_PATH,
        index=False,
    )

    maximum_price_difference = (
        price_validation[
            "absolute_difference"
        ].max()
    )

    print("\nEnergy indicators:")
    print(
        indicators.head().to_string(
            index=False
        )
    )

    print("\nNew indicator columns:")

    original_columns = set(
        load_integrated_data().columns
    )

    new_columns = [
        column
        for column in indicators.columns
        if column not in original_columns
    ]

    for column in new_columns:
        print(column)

    print(
        f"\nNumber of months: "
        f"{len(indicators)}"
    )

    print(
        f"Date range: "
        f"{indicators['period'].min():%Y-%m} to "
        f"{indicators['period'].max():%Y-%m}"
    )

    print(
        f"\nMaximum retail-price reconstruction "
        f"difference: "
        f"{maximum_price_difference:.8f}"
    )

    print(
        f"\nSaved indicator dataset to: "
        f"{OUTPUT_PATH}"
    )

    print(
        f"Saved price-validation report to: "
        f"{VALIDATION_PATH}"
    )


if __name__ == "__main__":
    main()