from pathlib import Path
import os

import pandas as pd
import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("EIA_API_KEY")

BASE_URL = (
    "https://api.eia.gov/v2/"
    "electricity/retail-sales/data/"
)

VALID_SECTORS = {
    "RES",
    "COM",
    "IND",
    "OTH",
    "TRA",
    "ALL",
}


def normalize_sectors(
    sectors: str | list[str],
) -> list[str]:
    """Normalize and validate EIA sector codes."""

    if isinstance(sectors, str):
        sector_list = [sectors]
    else:
        sector_list = list(sectors)

    sector_list = [
        sector.strip().upper()
        for sector in sector_list
    ]

    if not sector_list:
        raise ValueError(
            "At least one sector must be provided."
        )

    invalid_sectors = (
        set(sector_list) - VALID_SECTORS
    )

    if invalid_sectors:
        raise ValueError(
            f"Invalid sector codes: "
            f"{sorted(invalid_sectors)}"
        )

    # 去重，同时保留原来的排列顺序
    return list(dict.fromkeys(sector_list))

def fetch_retail_electricity_prices(
    state: str,
    sectors: str | list[str],
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """
    Fetch monthly retail electricity prices from the EIA API.

    Parameters
    ----------
    state:
        Two-letter U.S. state code, such as "TX".
    sector:
        EIA electricity sector code, such as "RES".
    start:
        Start month in YYYY-MM format.
    end:
        Optional end month in YYYY-MM format.

    Returns
    -------
    pd.DataFrame
        Clean monthly electricity price data.
    """

    if not API_KEY:
        raise RuntimeError(
            "EIA_API_KEY was not found. "
            "Please add it to the project's .env file."
        )

    state = state.strip().upper()
    sector_list = normalize_sectors(sectors)

    if len(state) != 2:
        raise ValueError(
            "State must be a two-letter code, such as 'TX'."
        )

    params = [
        ("api_key", API_KEY),
        ("frequency", "monthly"),
        ("data[]", "price"),
        ("facets[stateid][]", state),
        ("start", start),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", "0"),
        ("length", "5000"),
    ]

    for sector in sector_list:
        params.append(
            ("facets[sectorid][]", sector)
        )

    if end is not None:
        params.append(("end", end))

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()

    if "response" not in payload:
        raise ValueError(
            f"Unexpected EIA response structure: {payload}"
        )

    records = payload["response"].get("data", [])

    if not records:
        raise ValueError(
            f"No observations were returned for "
            f"state={state}, "
            f"sectors={sector_list}, "
            f"start={start}, end={end}."
        )

    df = pd.DataFrame(records)

    required_columns = {
        "period",
        "stateid",
        "sectorid",
        "price",
    }

    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        raise ValueError(
            f"Required columns are missing: "
            f"{sorted(missing_columns)}"
        )

    selected_columns = [
        "period",
        "stateid",
        "stateDescription",
        "sectorid",
        "sectorName",
        "price",
        "price-units",
    ]

    available_columns = [
        column
        for column in selected_columns
        if column in df.columns
    ]

    df = df[available_columns].copy()

    df["period"] = pd.to_datetime(
        df["period"],
        format="%Y-%m",
        errors="coerce",
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce",
    )

    df = (
        df.dropna(subset=["period", "price"])
        .drop_duplicates(
            subset=[
                "period",
                "stateid",
                "sectorid",
            ]
        )
        .sort_values(
            ["period", "stateid"],
        )
        .reset_index(drop=True)
    )

    return df


def validate_electricity_data(
    df: pd.DataFrame,
    state: str,
    sectors: str | list[str],
) -> None:
    """Run basic validation checks on electricity data."""

    state = state.strip().upper()
    expected_sectors = set(
        normalize_sectors(sectors)
    )

    if df.empty:
        raise ValueError(
            "The cleaned DataFrame is empty."
        )

    if not df["stateid"].eq(state).all():
        raise ValueError(
            f"The data contain observations "
            f"outside {state}."
        )

    actual_sectors = set(
        df["sectorid"].unique()
    )

    if actual_sectors != expected_sectors:
        raise ValueError(
            f"Expected sectors "
            f"{sorted(expected_sectors)}, "
            f"but received "
            f"{sorted(actual_sectors)}."
        )

    duplicate_mask = df.duplicated(
        subset=[
            "period",
            "stateid",
            "sectorid",
        ]
    )

    if duplicate_mask.any():
        raise ValueError(
            "Duplicate monthly observations "
            "were found."
        )

    if not df["price"].gt(0).all():
        raise ValueError(
            "Non-positive electricity prices "
            "were found."
        )


def main() -> None:
    state = "TX"
    sector = "RES"

    df = fetch_retail_electricity_prices(
        state=state,
        sector=sector,
        start="2015-01",
    )

    validate_electricity_data(
        df=df,
        state=state,
        sector=sector,
    )

    output_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "eia_tx_residential_price.csv"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_path,
        index=False,
    )

    print(df.head())
    print()
    print(df.tail())
    print()
    print(f"Number of observations: {len(df)}")
    print(
        f"Date range: "
        f"{df['period'].min():%Y-%m} to "
        f"{df['period'].max():%Y-%m}"
    )
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()