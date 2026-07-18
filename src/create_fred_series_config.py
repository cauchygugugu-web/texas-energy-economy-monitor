from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    PROJECT_ROOT
    / "config"
    / "fred_series.csv"
)


FRED_SERIES = [
    {
        "series_id": "TXUR",
        "variable_name": "tx_unemployment_rate",
        "category": "labor_market",
    },
    {
        "series_id": "TXNA",
        "variable_name": "tx_total_nonfarm_employment",
        "category": "labor_market",
    },
    {
        "series_id": "MCOILWTICO",
        "variable_name": "wti_crude_oil_price",
        "category": "energy_price",
    },
    {
        "series_id": "MHHNGSP",
        "variable_name": "henry_hub_natural_gas_price",
        "category": "energy_price",
    },
    {
        "series_id": "CPIAUCSL",
        "variable_name": "us_cpi",
        "category": "price_index",
    },
]


def build_fred_series_config() -> pd.DataFrame:
    """Create and validate the FRED series configuration table."""

    config = pd.DataFrame(FRED_SERIES)

    required_columns = {
        "series_id",
        "variable_name",
        "category",
    }

    missing_columns = required_columns - set(config.columns)

    if missing_columns:
        raise ValueError(
            "Configuration columns are missing: "
            f"{sorted(missing_columns)}"
        )

    for column in required_columns:
        config[column] = config[column].astype(str).str.strip()

        if config[column].eq("").any():
            raise ValueError(
                f"Blank values were found in {column}."
            )

    config["series_id"] = config["series_id"].str.upper()

    if config["series_id"].duplicated().any():
        duplicated_ids = (
            config.loc[
                config["series_id"].duplicated(keep=False),
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
                config["variable_name"].duplicated(keep=False),
                "variable_name",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate variable names were found: "
            f"{duplicated_names}"
        )

    return (
        config
        .sort_values(["category", "series_id"])
        .reset_index(drop=True)
    )


def main() -> None:
    config = build_fred_series_config()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    config.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nFRED series configuration:")
    print(config.to_string(index=False))

    print(
        f"\nNumber of configured series: "
        f"{len(config)}"
    )

    print(
        f"Saved configuration to: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()