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
    "electricity/electric-power-operational-data/"
    "data/"
)


def find_all_sector_id() -> str:
    """
    Read the saved sector metadata and find the
    sector code representing all sectors.
    """

    metadata_path = (
        PROJECT_ROOT
        / "data"
        / "metadata"
        / "generation_sectorid.csv"
    )

    if not metadata_path.exists():
        raise FileNotFoundError(
            "Sector metadata was not found. "
            "Run inspect_generation_metadata.py first."
        )

    metadata = pd.read_csv(
        metadata_path,
        dtype=str,
    ).fillna("")

    if "id" not in metadata.columns:
        raise ValueError(
            "The sector metadata does not contain "
            "an 'id' column."
        )

    searchable_text = (
        metadata
        .astype(str)
        .agg(" ".join, axis=1)
        .str.lower()
    )

    matches = metadata.loc[
        searchable_text.str.contains(
            "all sectors",
            regex=False,
        )
    ]

    if len(matches) != 1:
        raise ValueError(
            "Could not uniquely identify the "
            "all-sectors code from the metadata."
        )

    return matches.iloc[0]["id"]


def fetch_generation_data(
    location: str,
    start: str,
    end: str | None = None,
    sector_id: str | None = None,
    page_size: int = 5000,
) -> pd.DataFrame:
    """
    Fetch monthly electricity generation by fuel type.

    Parameters
    ----------
    location:
        Two-letter state code, such as "TX".

    start:
        Start month in YYYY-MM format.

    end:
        Optional end month in YYYY-MM format.

    sector_id:
        EIA electric power sector code. If omitted,
        the all-sectors code is read from metadata.

    page_size:
        Number of observations requested per page.

    Returns
    -------
    pd.DataFrame
        Monthly generation observations by fuel type.
    """

    if not API_KEY:
        raise RuntimeError(
            "EIA_API_KEY was not found in .env."
        )

    location = location.strip().upper()

    if len(location) != 2:
        raise ValueError(
            "location must be a two-letter "
            "state code such as 'TX'."
        )

    if not 1 <= page_size <= 5000:
        raise ValueError(
            "page_size must be between 1 and 5000."
        )

    if sector_id is None:
        sector_id = find_all_sector_id()

    all_records: list[dict] = []
    offset = 0
    total_rows: int | None = None

    with requests.Session() as session:
        while True:
            params: list[tuple[str, str]] = [
                ("api_key", API_KEY),
                ("frequency", "monthly"),
                ("data[]", "generation"),
                (
                    "facets[location][]",
                    location,
                ),
                (
                    "facets[sectorid][]",
                    str(sector_id),
                ),
                ("start", start),
                (
                    "sort[0][column]",
                    "period",
                ),
                (
                    "sort[0][direction]",
                    "asc",
                ),
                (
                    "sort[1][column]",
                    "fueltypeid",
                ),
                (
                    "sort[1][direction]",
                    "asc",
                ),
                ("offset", str(offset)),
                ("length", str(page_size)),
            ]

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
                    "The EIA generation request failed."
                ) from error

            payload = response.json()

            response_data = payload.get("response")

            if response_data is None:
                raise ValueError(
                    "Unexpected EIA response: "
                    f"{payload}"
                )

            page_records = response_data.get(
                "data",
                [],
            )

            if total_rows is None:
                total_rows = int(
                    response_data.get("total", 0)
                )

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
            "No generation observations were returned "
            f"for location={location}, "
            f"sector_id={sector_id}, "
            f"start={start}, end={end}."
        )

    df = pd.DataFrame(all_records)

    required_columns = {
        "period",
        "location",
        "sectorid",
        "fueltypeid",
        "generation",
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Required columns are missing: "
            f"{sorted(missing_columns)}"
        )

    candidate_columns = [
        "period",
        "location",
        "stateDescription",
        "sectorid",
        "sectorDescription",
        "sectorName",
        "fueltypeid",
        "fuelTypeDescription",
        "generation",
        "generation-units",
    ]

    selected_columns = [
        column
        for column in candidate_columns
        if column in df.columns
    ]

    df = df[selected_columns].copy()

    df["period"] = pd.to_datetime(
        df["period"],
        format="%Y-%m",
        errors="coerce",
    )

    df["generation"] = pd.to_numeric(
        df["generation"],
        errors="coerce",
    )

    df = (
        df.dropna(
            subset=[
                "period",
                "fueltypeid",
                "generation",
            ]
        )
        .drop_duplicates(
            subset=[
                "period",
                "location",
                "sectorid",
                "fueltypeid",
            ]
        )
        .sort_values(
            [
                "period",
                "fueltypeid",
            ]
        )
        .reset_index(drop=True)
    )

    return df


def validate_generation_data(
    df: pd.DataFrame,
    location: str,
) -> None:
    """Run basic structural checks."""

    location = location.strip().upper()

    if df.empty:
        raise ValueError(
            "The generation DataFrame is empty."
        )

    if not df["location"].eq(location).all():
        raise ValueError(
            "The dataset contains observations "
            f"outside {location}."
        )

    duplicate_mask = df.duplicated(
        subset=[
            "period",
            "location",
            "sectorid",
            "fueltypeid",
        ]
    )

    if duplicate_mask.any():
        raise ValueError(
            "Duplicate month-location-sector-fuel "
            "observations were found."
        )

    if df["generation"].isna().any():
        raise ValueError(
            "Missing generation values were found."
        )


def main() -> None:
    df = fetch_generation_data(
        location="TX",
        start="2015-01",
    )

    validate_generation_data(
        df=df,
        location="TX",
    )

    print("\nGeneration data:")
    print(df.head(20))

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFuel types:")
    fuel_columns = [
        column
        for column in [
            "fueltypeid",
            "fuelTypeDescription",
        ]
        if column in df.columns
    ]

    print(
        df[fuel_columns]
        .drop_duplicates()
        .sort_values("fueltypeid")
        .to_string(index=False)
    )

    print(
        f"\nNumber of observations: {len(df)}"
    )

    print(
        f"Date range: "
        f"{df['period'].min():%Y-%m} to "
        f"{df['period'].max():%Y-%m}"
    )


if __name__ == "__main__":
    main()