from pathlib import Path

import pandas as pd
from statsmodels.tsa.seasonal import STL


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_energy_indicators_monthly.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_energy_time_series_features.csv"
)

COVERAGE_PATH = (
    PROJECT_ROOT
    / "reports"
    / "tables"
    / "time_series_feature_coverage.csv"
)


# 对这些水平变量计算同比百分比变化
LEVEL_VARIABLES = [
    "residential_price",
    "commercial_price",
    "industrial_price",
    "total_generation",
    "renewable_generation",
    "fossil_generation",
    "residential_sales_per_customer_kwh",
    "commercial_sales_per_customer_kwh",
    "industrial_sales_per_customer_kwh",
]

# 对占比变量计算同比百分点变化
SHARE_VARIABLES = [
    "renewable_share",
    "fossil_share",
    "natural_gas_share",
    "wind_share",
    "solar_share",
    "coal_share",
    "nuclear_share",
]

# 进行 STL 分解的主要变量
STL_VARIABLES = [
    "residential_price",
    "residential_sales_per_customer_kwh",
    "renewable_share",
    "natural_gas_share",
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

    required_columns = {
        "period",
        *LEVEL_VARIABLES,
        *SHARE_VARIABLES,
        *STL_VARIABLES,
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Required variables are missing: "
            f"{sorted(missing_columns)}"
        )

    if df["period"].isna().any():
        raise ValueError(
            "Invalid period values were found."
        )

    if df["period"].duplicated().any():
        raise ValueError(
            "Duplicate monthly observations were found."
        )

    df = (
        df.sort_values("period")
        .reset_index(drop=True)
    )

    expected_months = pd.date_range(
        start=df["period"].min(),
        end=df["period"].max(),
        freq="MS",
    )

    missing_months = expected_months.difference(
        df["period"]
    )

    if len(missing_months) > 0:
        formatted = [
            month.strftime("%Y-%m")
            for month in missing_months
        ]

        raise ValueError(
            "The time series is not continuous. "
            f"Missing months: {formatted}"
        )

    numeric_columns = sorted(
        (
            set(LEVEL_VARIABLES)
            | set(SHARE_VARIABLES)
            | set(STL_VARIABLES)
        )
    )

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    missing_values = (
        df[numeric_columns]
        .isna()
        .sum()
    )

    missing_values = missing_values.loc[
        missing_values.gt(0)
    ]

    if not missing_values.empty:
        raise ValueError(
            "Missing numeric observations were found:\n"
            f"{missing_values.to_string()}"
        )

    return df


def add_calendar_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Add calendar variables for monthly analysis."""

    result = df.copy()

    result["year"] = result["period"].dt.year
    result["month"] = result["period"].dt.month
    result["quarter"] = result["period"].dt.quarter

    return result


def add_rolling_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Add trailing 12-month moving averages."""

    result = df.copy()

    variables = list(
        dict.fromkeys(
            LEVEL_VARIABLES
            + SHARE_VARIABLES
        )
    )

    for variable in variables:
        result[
            f"{variable}_ma12"
        ] = (
            result[variable]
            .rolling(
                window=12,
                min_periods=12,
            )
            .mean()
        )

    return result


def add_year_over_year_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Add year-over-year changes."""

    result = df.copy()

    for variable in LEVEL_VARIABLES:
        previous_year = result[
            variable
        ].shift(12)

        result[
            f"{variable}_yoy_pct"
        ] = (
            (
                result[variable]
                / previous_year
                - 1
            )
            * 100
        )

    for variable in SHARE_VARIABLES:
        result[
            f"{variable}_yoy_pp"
        ] = (
            result[variable]
            - result[variable].shift(12)
        ) * 100

    return result


def add_stl_components(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Add STL trend, seasonal, and residual components."""

    result = df.copy()

    for variable in STL_VARIABLES:
        series = (
            result[
                [
                    "period",
                    variable,
                ]
            ]
            .set_index("period")[variable]
            .asfreq("MS")
        )

        if series.isna().any():
            raise ValueError(
                f"{variable} contains missing monthly "
                "observations and cannot be decomposed."
            )

        decomposition = STL(
            series,
            period=12,
            robust=True,
        ).fit()

        components = pd.DataFrame(
            {
                "period": series.index,
                f"{variable}_stl_trend": (
                    decomposition.trend.values
                ),
                f"{variable}_stl_seasonal": (
                    decomposition.seasonal.values
                ),
                f"{variable}_stl_residual": (
                    decomposition.resid.values
                ),
            }
        )

        result = result.merge(
            components,
            on="period",
            how="left",
            validate="one_to_one",
        )

    return result


def build_feature_coverage(
    df: pd.DataFrame,
    original_columns: set[str],
) -> pd.DataFrame:
    """Summarize coverage of newly constructed features."""

    feature_columns = [
        column
        for column in df.columns
        if column not in original_columns
        and column != "period"
    ]

    rows: list[dict] = []

    for column in feature_columns:
        valid_mask = df[column].notna()

        rows.append(
            {
                "variable": column,
                "total_months": len(df),
                "observed_months": int(
                    valid_mask.sum()
                ),
                "missing_months": int(
                    df[column].isna().sum()
                ),
                "first_valid_period": (
                    df.loc[
                        valid_mask,
                        "period",
                    ].min()
                ),
                "last_valid_period": (
                    df.loc[
                        valid_mask,
                        "period",
                    ].max()
                ),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("variable")
        .reset_index(drop=True)
    )


def build_time_series_features() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Build the complete time-series feature dataset."""

    df = load_indicator_data()

    original_columns = set(df.columns)

    features = add_calendar_features(df)
    features = add_rolling_features(features)
    features = add_year_over_year_features(
        features
    )
    features = add_stl_components(features)

    coverage = build_feature_coverage(
        features,
        original_columns,
    )

    return features, coverage


def main() -> None:
    features, coverage = (
        build_time_series_features()
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    COVERAGE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    features.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    coverage.to_csv(
        COVERAGE_PATH,
        index=False,
    )

    print("\nTime-series features:")
    print(
        features[
            [
                "period",
                "residential_price",
                "residential_price_ma12",
                "residential_price_yoy_pct",
                "renewable_share",
                "renewable_share_ma12",
                "renewable_share_yoy_pp",
            ]
        ]
        .tail(15)
        .to_string(index=False)
    )

    print("\nFeature coverage:")
    print(
        coverage.to_string(
            index=False
        )
    )

    print(
        f"\nNumber of months: "
        f"{len(features)}"
    )

    print(
        f"Date range: "
        f"{features['period'].min():%Y-%m} to "
        f"{features['period'].max():%Y-%m}"
    )

    print(
        f"\nSaved time-series data to: "
        f"{OUTPUT_PATH}"
    )

    print(
        f"Saved feature coverage to: "
        f"{COVERAGE_PATH}"
    )


if __name__ == "__main__":
    main()