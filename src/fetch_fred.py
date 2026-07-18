from pathlib import Path
import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

FRED_API_KEY = os.getenv("FRED_API_KEY")

OBSERVATIONS_URL = (
    "https://api.stlouisfed.org/fred/"
    "series/observations"
)

SERIES_METADATA_URL = (
    "https://api.stlouisfed.org/fred/"
    "series"
)


def create_session() -> requests.Session:
    """Create a requests session with automatic retries."""

    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_policy
    )

    session = requests.Session()
    session.mount(
        "https://",
        adapter,
    )

    return session


def check_api_key() -> None:
    """Ensure that the local FRED API key is available."""

    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY was not found. "
            "Add it to the project's .env file."
        )


def request_fred_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
) -> dict:
    """Send a FRED request and return the JSON payload."""

    check_api_key()

    request_params = {
        **params,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }

    try:
        response = session.get(
            url,
            params=request_params,
            timeout=30,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        response_text = ""

        if (
            "response" in locals()
            and response is not None
        ):
            response_text = response.text[:500]

        raise RuntimeError(
            "The FRED API request failed. "
            f"URL: {url}. "
            f"Response: {response_text}"
        ) from error

    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        raise ValueError(
            "FRED returned a non-JSON response."
        ) from error

    if "error_code" in payload:
        raise ValueError(
            "FRED API error "
            f"{payload.get('error_code')}: "
            f"{payload.get('error_message')}"
        )

    return payload


def fetch_fred_observations(
    series_id: str,
    observation_start: str = "2015-01-01",
    observation_end: str | None = None,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """
    Fetch observations for one FRED series.

    Missing values represented by FRED as "." are retained
    as pandas NaN rather than being converted to zero.
    """

    series_id = series_id.strip().upper()

    if not series_id:
        raise ValueError(
            "series_id must not be blank."
        )

    owns_session = session is None

    if session is None:
        session = create_session()

    params: dict[str, Any] = {
        "series_id": series_id,
        "observation_start": observation_start,
        "sort_order": "asc",
    }

    if observation_end is not None:
        params["observation_end"] = (
            observation_end
        )

    try:
        payload = request_fred_json(
            session=session,
            url=OBSERVATIONS_URL,
            params=params,
        )
    finally:
        if owns_session:
            session.close()

    observations = payload.get(
        "observations",
        [],
    )

    if not observations:
        raise ValueError(
            "No FRED observations were returned for "
            f"{series_id}."
        )

    df = pd.DataFrame(observations)

    required_columns = {
        "date",
        "value",
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            "FRED observation columns are missing: "
            f"{sorted(missing_columns)}"
        )

    df = df.rename(
        columns={
            "date": "period",
        }
    )

    df["period"] = pd.to_datetime(
        df["period"],
        errors="coerce",
    )

    if df["period"].isna().any():
        raise ValueError(
            f"Invalid dates were returned for {series_id}."
        )

    # Standardize all monthly dates to the first day
    # of their calendar month.
    df["period"] = (
        df["period"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    df["series_id"] = series_id

    selected_columns = [
        "period",
        "series_id",
        "value",
    ]

    for optional_column in [
        "realtime_start",
        "realtime_end",
    ]:
        if optional_column in df.columns:
            selected_columns.append(
                optional_column
            )

    df = (
        df[selected_columns]
        .sort_values("period")
        .reset_index(drop=True)
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
            .dt.strftime("%Y-%m")
            .tolist()
        )

        raise ValueError(
            f"Duplicate months were returned for "
            f"{series_id}: {duplicated_periods}"
        )

    return df


def fetch_fred_metadata(
    series_id: str,
    session: requests.Session | None = None,
) -> dict:
    """Fetch metadata for one FRED series."""

    series_id = series_id.strip().upper()

    if not series_id:
        raise ValueError(
            "series_id must not be blank."
        )

    owns_session = session is None

    if session is None:
        session = create_session()

    try:
        payload = request_fred_json(
            session=session,
            url=SERIES_METADATA_URL,
            params={
                "series_id": series_id,
            },
        )
    finally:
        if owns_session:
            session.close()

    # FRED names this response field "seriess".
    records = payload.get(
        "seriess",
        [],
    )

    if len(records) != 1:
        raise ValueError(
            "Expected one metadata record for "
            f"{series_id}, but received {len(records)}."
        )

    metadata = records[0].copy()
    metadata["series_id"] = series_id

    return metadata


def main() -> None:
    """Run a small connection test."""

    test_series = "TXUR"

    with create_session() as session:
        metadata = fetch_fred_metadata(
            series_id=test_series,
            session=session,
        )

        observations = fetch_fred_observations(
            series_id=test_series,
            observation_start="2015-01-01",
            session=session,
        )

    print("\nFRED metadata:")
    for field in [
        "series_id",
        "title",
        "frequency",
        "units",
        "seasonal_adjustment",
        "observation_start",
        "observation_end",
        "last_updated",
    ]:
        print(
            f"{field}: "
            f"{metadata.get(field, '')}"
        )

    print("\nObservations:")
    print(
        observations.head().to_string(
            index=False
        )
    )

    print(
        f"\nNumber of observations: "
        f"{len(observations)}"
    )

    print(
        f"Date range: "
        f"{observations['period'].min():%Y-%m} to "
        f"{observations['period'].max():%Y-%m}"
    )

    print(
        f"Missing values: "
        f"{observations['value'].isna().sum()}"
    )


if __name__ == "__main__":
    main()