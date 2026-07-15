from pathlib import Path
import os
from typing import Iterable

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

VALID_DATA_FIELDS = {
    "price",
    "sales",
    "revenue",
    "customers",
}

DEFAULT_DATA_FIELDS = [
    "price",
    "sales",
    "revenue",
    "customers",
]


def normalize_sectors(
    sectors: str | Iterable[str],
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

    # 去重，同时保留输入顺序
    return list(dict.fromkeys(sector_list))


def normalize_data_fields(
    data_fields: str | Iterable[str],
) -> list[str]:
    """Normalize and validate requested EIA data fields."""

    if isinstance(data_fields, str):
        field_list = [data_fields]
    else:
        field_list = list(data_fields)

    field_list = [
        field.strip().lower()
        for field in field_list
    ]

    if not field_list:
        raise ValueError(
            "At least one data field must be provided."
        )

    invalid_fields = (
        set(field_list) - VALID_DATA_FIELDS
    )

    if invalid_fields:
        raise ValueError(
            f"Invalid data fields: "
            f"{sorted(invalid_fields)}"
        )

    return list(dict.fromkeys(field_list))


def fetch_retail_electricity_data(
    state: str,
    sectors: str | Iterable[str],
    start: str,
    end: str | None = None,
    data_fields: str | Iterable[str] = (
        DEFAULT_DATA_FIELDS
    ),
    page_size: int = 5000,
) -> pd.DataFrame:
    """
    Fetch monthly retail electricity data from EIA.

    Parameters
    ----------
    state:
        Two-letter state code, such as "TX".

    sectors:
        One sector code or several sector codes.

    start:
        Start month in YYYY-MM format.

    end:
        Optional end month in YYYY-MM format.

    data_fields:
        EIA variables to retrieve. Supported values are
        price, sales, revenue, and customers.

    page_size:
        Number of rows requested on each API page.

    Returns
    -------
    pd.DataFrame
        Clean monthly retail electricity data.
    """

    if not API_KEY:
        raise RuntimeError(
            "EIA_API_KEY was not found. "
            "Add it to the project's .env file."
        )

    state = state.strip().upper()
    sector_list = normalize_sectors(sectors)
    field_list = normalize_data_fields(data_fields)

    if len(state) != 2:
        raise ValueError(
            "State must be a two-letter code, "
            "such as 'TX'."
        )

    if not 1 <= page_size <= 5000:
        raise ValueError(
            "page_size must be between 1 and 5000."
        )

    all_records: list[dict] = []
    offset = 0
    total_rows: int | None = None

    with requests.Session() as session:
        while True:
            params: list[tuple[str, str]] = [
                ("api_key", API_KEY),
                ("frequency", "monthly"),
                ("facets[stateid][]", state),
                ("start", start),
                ("sort[0][column]", "period"),
                ("sort[0][direction]", "asc"),
                ("sort[1][column]", "sectorid"),
                ("sort[1][direction]", "asc"),
                ("offset", str(offset)),
                ("length", str(page_size)),
            ]

            for field in field_list:
                params.append(
                    ("data[]", field)
                )

            for sector in sector_list:
                params.append(
                    (
                        "facets[sectorid][]",
                        sector,
                    )
                )

            if end is not None:
                params.append(("end", end))

            try:
                response = session.get(
                    BASE_URL,
                    params=params,
                    timeout=30,
                )

                response.raise_for_status()

            except requests.RequestException as error:
                raise RuntimeError(
                    "The EIA API request failed."
                ) from error

            payload = response.json()

            response_data = payload.get("response")

            if response_data is None:
                raise ValueError(
                    "Unexpected EIA API response: "
                    f"{payload}"
                )

            page_records = response_data.get(
                "data",
                [],
            )

            if total_rows is None:
                total_value = response_data.get(
                    "total",
                    0,
                )
                total_rows = int(total_value)

            if not page_records:
                break

            all_records.extend(page_records)

            offset += len(page_records)

            print(
                f"Retrieved {offset} of "
                f"{total_rows} rows."
            )

            if offset >= total_rows:
                break

    if not all_records:
        raise ValueError(
            "No observations were returned for "
            f"state={state}, "
            f"sectors={sector_list}, "
            f"start={start}, end={end}."
        )

    df = pd.DataFrame(all_records)

    required_columns = {
        "period",
        "stateid",
        "sectorid",
        *field_list,
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Required columns are missing: "
            f"{sorted(missing_columns)}"
        )

    identifier_columns = [
        "period",
        "stateid",
        "stateDescription",
        "sectorid",
        "sectorName",
    ]

    value_columns: list[str] = []

    for field in field_list:
        value_columns.append(field)

        units_column = f"{field}-units"

        if units_column in df.columns:
            value_columns.append(units_column)

    selected_columns = [
        column
        for column in (
            identifier_columns + value_columns
        )
        if column in df.columns
    ]

    df = df[selected_columns].copy()

    df["period"] = pd.to_datetime(
        df["period"],
        format="%Y-%m",
        errors="coerce",
    )

    for field in field_list:
        df[field] = pd.to_numeric(
            df[field],
            errors="coerce",
        )

    df = (
        df.dropna(subset=["period"])
        .drop_duplicates(
            subset=[
                "period",
                "stateid",
                "sectorid",
            ]
        )
        .sort_values(
            [
                "period",
                "sectorid",
            ]
        )
        .reset_index(drop=True)
    )

    return df


def fetch_retail_electricity_prices(
    state: str,
    sectors: str | Iterable[str],
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """
    Fetch only monthly retail electricity prices.

    This wrapper is retained so that earlier scripts
    and notebooks continue to work.
    """

    return fetch_retail_electricity_data(
        state=state,
        sectors=sectors,
        start=start,
        end=end,
        data_fields=["price"],
    )


def validate_electricity_data(
    df: pd.DataFrame,
    state: str,
    sectors: str | Iterable[str],
    required_fields: Iterable[str] | None = None,
) -> None:
    """Run structural validation checks."""

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
        df["sectorid"].dropna().unique()
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
            "Duplicate month-state-sector "
            "observations were found."
        )

    if not df["period"].is_monotonic_increasing:
        raise ValueError(
            "The observations are not sorted "
            "chronologically."
        )

    if required_fields is not None:
        missing_fields = (
            set(required_fields) - set(df.columns)
        )

        if missing_fields:
            raise ValueError(
                "Required fields are missing: "
                f"{sorted(missing_fields)}"
            )


def main() -> None:
    state = "TX"

    sectors = [
        "RES",
        "COM",
        "IND",
    ]

    df = fetch_retail_electricity_data(
        state=state,
        sectors=sectors,
        start="2015-01",
    )

    validate_electricity_data(
        df=df,
        state=state,
        sectors=sectors,
        required_fields=DEFAULT_DATA_FIELDS,
    )

    print(df.head(9))
    print()
    print(df.tail(9))
    print()
    print(f"Number of observations: {len(df)}")


if __name__ == "__main__":
    main()