from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_URL = (
    "https://www.ncei.noaa.gov/access/monitoring/"
    "climate-at-a-glance/statewide/time-series"
)

DEFAULT_START_YEAR = 2015
DEFAULT_BASE_START_YEAR = 1901
DEFAULT_BASE_END_YEAR = 2000


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


def build_weather_url(
    location_code: str,
    parameter: str,
    start_year: int,
    end_year: int,
    time_scale: int = 1,
    month: int = 0,
) -> str:
    """Build a NOAA statewide time-series JSON URL."""

    location_code = str(
        location_code
    ).strip()

    parameter = str(
        parameter
    ).strip().lower()

    if not location_code:
        raise ValueError(
            "location_code must not be blank."
        )

    if not parameter:
        raise ValueError(
            "parameter must not be blank."
        )

    if start_year > end_year:
        raise ValueError(
            "start_year must not be later than end_year."
        )

    return (
        f"{BASE_URL}/"
        f"{location_code}/"
        f"{parameter}/"
        f"{time_scale}/"
        f"{month}/"
        f"{start_year}-{end_year}/"
        "data.json"
    )


def request_weather_json(
    session: requests.Session,
    url: str,
    base_start_year: int = DEFAULT_BASE_START_YEAR,
    base_end_year: int = DEFAULT_BASE_END_YEAR,
) -> dict[str, Any]:
    """Request and validate a NOAA JSON payload."""

    params = {
        "base_prd": "true",
        "begbaseyear": base_start_year,
        "endbaseyear": base_end_year,
    }

    try:
        response = session.get(
            url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        response_preview = ""

        if (
            "response" in locals()
            and response is not None
        ):
            response_preview = (
                response.text[:500]
            )

        raise RuntimeError(
            "The NOAA weather request failed. "
            f"URL: {url}. "
            f"Response: {response_preview}"
        ) from error

    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        raise ValueError(
            "NOAA returned a non-JSON response."
        ) from error

    if not isinstance(payload, dict):
        raise ValueError(
            "The NOAA payload is not a JSON object."
        )

    required_keys = {
        "description",
        "data",
    }

    missing_keys = (
        required_keys - set(payload)
    )

    if missing_keys:
        raise ValueError(
            "Required NOAA payload fields are missing: "
            f"{sorted(missing_keys)}"
        )

    if not isinstance(
        payload["description"],
        dict,
    ):
        raise ValueError(
            "NOAA description must be a JSON object."
        )

    if not isinstance(
        payload["data"],
        dict,
    ):
        raise ValueError(
            "NOAA data must be a JSON object."
        )

    return payload


def parse_weather_data(
    payload: dict[str, Any],
    location_code: str,
    parameter: str,
) -> pd.DataFrame:
    """Convert NOAA YYYYMM-keyed observations to a tidy DataFrame."""

    rows: list[dict[str, Any]] = []

    for period_key, observation in (
        payload["data"].items()
    ):
        if not isinstance(
            observation,
            dict,
        ):
            raise ValueError(
                "Each NOAA observation must be "
                "a JSON object."
            )

        rows.append(
            {
                "period_key": str(
                    period_key
                ),
                "value": observation.get(
                    "value"
                ),
                "departure": observation.get(
                    "departure"
                ),
            }
        )

    if not rows:
        raise ValueError(
            "NOAA returned no weather observations."
        )

    df = pd.DataFrame(rows)

    valid_period_format = (
        df["period_key"]
        .str.fullmatch(r"\d{6}")
    )

    if not valid_period_format.all():
        invalid_periods = (
            df.loc[
                ~valid_period_format,
                "period_key",
            ]
            .tolist()
        )

        raise ValueError(
            "Invalid NOAA YYYYMM period keys "
            f"were found: {invalid_periods}"
        )

    df["period"] = pd.to_datetime(
        df["period_key"],
        format="%Y%m",
        errors="coerce",
    )

    if df["period"].isna().any():
        raise ValueError(
            "Some NOAA period keys could not "
            "be converted to dates."
        )

    for column in [
        "value",
        "departure",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["location_code"] = str(
        location_code
    )

    df["parameter"] = str(
        parameter
    ).strip().lower()

    df = (
        df[
            [
                "period",
                "location_code",
                "parameter",
                "value",
                "departure",
            ]
        ]
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
            "Duplicate NOAA months were found: "
            f"{duplicated_periods}"
        )

    return df


def parse_weather_metadata(
    payload: dict[str, Any],
    location_code: str,
    parameter: str,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    """Create a standardized metadata record."""

    description = payload[
        "description"
    ]

    return {
        "location_code": str(
            location_code
        ),
        "parameter": str(
            parameter
        ).strip().lower(),
        "title": description.get(
            "title",
            "",
        ),
        "units": description.get(
            "units",
            "",
        ),
        "base_period": description.get(
            "base_period",
            "",
        ),
        "requested_start_year": (
            start_year
        ),
        "requested_end_year": (
            end_year
        ),
        "source": (
            "NOAA NCEI Climate at a Glance "
            "Statewide Time Series"
        ),
    }


def fetch_weather_series(
    location_code: str,
    parameter: str,
    start_year: int = DEFAULT_START_YEAR,
    end_year: int | None = None,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Fetch one monthly NOAA statewide weather series.

    Returns
    -------
    observations
        Monthly tidy observations with period, value,
        and departure from the selected base period.
    metadata
        Standardized series metadata.
    """

    if end_year is None:
        end_year = pd.Timestamp.today().year

    url = build_weather_url(
        location_code=location_code,
        parameter=parameter,
        start_year=start_year,
        end_year=end_year,
    )

    owns_session = session is None

    if session is None:
        session = create_session()

    try:
        payload = request_weather_json(
            session=session,
            url=url,
        )
    finally:
        if owns_session:
            session.close()

    observations = parse_weather_data(
        payload=payload,
        location_code=location_code,
        parameter=parameter,
    )

    metadata = parse_weather_metadata(
        payload=payload,
        location_code=location_code,
        parameter=parameter,
        start_year=start_year,
        end_year=end_year,
    )

    return observations, metadata


def main() -> None:
    """Run a small Texas average-temperature connection test."""

    observations, metadata = (
        fetch_weather_series(
            location_code="41",
            parameter="tavg",
            start_year=2015,
        )
    )

    print("\nNOAA weather metadata:")

    for key, value in metadata.items():
        print(f"{key}: {value}")

    print("\nFirst observations:")

    print(
        observations.head().to_string(
            index=False
        )
    )

    print("\nLast observations:")

    print(
        observations.tail().to_string(
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

    print(
        f"Missing departures: "
        f"{observations['departure'].isna().sum()}"
    )


if __name__ == "__main__":
    main()