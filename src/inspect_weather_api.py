from pprint import pprint

import requests


BASE_URL = (
    "https://www.ncei.noaa.gov/access/monitoring/"
    "climate-at-a-glance/statewide/time-series"
)

LOCATION_CODE = "41"
PARAMETER = "tavg"

# 1-month time scale
TIME_SCALE = "1"

# NOAA 页面中的 All Months
MONTH = "0"

START_YEAR = 2015
END_YEAR = 2026


def build_api_url() -> str:
    """Build the NOAA Climate at a Glance JSON endpoint."""

    return (
        f"{BASE_URL}/"
        f"{LOCATION_CODE}/"
        f"{PARAMETER}/"
        f"{TIME_SCALE}/"
        f"{MONTH}/"
        f"{START_YEAR}-{END_YEAR}/"
        "data.json"
    )


def inspect_weather_api() -> None:
    """Request one NOAA series and inspect its JSON structure."""

    url = build_api_url()

    params = {
        "base_prd": "true",
        "begbaseyear": 1901,
        "endbaseyear": 2000,
    }

    print("Requesting NOAA data...")
    print(f"URL: {url}")
    print(f"Parameters: {params}")

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
        )

        print(
            f"\nHTTP status: "
            f"{response.status_code}"
        )

        print(
            f"Content type: "
            f"{response.headers.get('content-type')}"
        )

        print(
            f"Final request URL: "
            f"{response.url}"
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise RuntimeError(
            "The NOAA request failed. "
            "Check the internet connection and API URL."
        ) from error

    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        print("\nResponse preview:")
        print(response.text[:1000])

        raise ValueError(
            "NOAA did not return valid JSON."
        ) from error

    print("\nTop-level JSON type:")
    print(type(payload).__name__)

    if isinstance(payload, dict):
        print("\nTop-level keys:")
        print(list(payload.keys()))

        for key, value in payload.items():
            print(
                f"\nKey: {key}"
            )

            print(
                f"Value type: "
                f"{type(value).__name__}"
            )

            if isinstance(value, dict):
                print(
                    f"Number of entries: "
                    f"{len(value)}"
                )

                print("First three entries:")

                for entry_number, (
                    entry_key,
                    entry_value,
                ) in enumerate(
                    value.items(),
                    start=1,
                ):
                    print(
                        f"{entry_key}: "
                        f"{entry_value}"
                    )

                    if entry_number >= 3:
                        break

            elif isinstance(value, list):
                print(
                    f"Number of entries: "
                    f"{len(value)}"
                )

                print("First three entries:")
                pprint(value[:3])

            else:
                pprint(value)

    else:
        print("\nPayload preview:")
        pprint(payload)

    print(
        "\nNOAA API inspection completed."
    )


if __name__ == "__main__":
    inspect_weather_api()