from pathlib import Path
import json
import os

import pandas as pd
import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("EIA_API_KEY")

BASE_ROUTE = (
    "https://api.eia.gov/v2/"
    "electricity/electric-power-operational-data/"
)


def request_eia_json(
    url: str,
) -> dict:
    """Send an EIA API request and return JSON."""

    if not API_KEY:
        raise RuntimeError(
            "EIA_API_KEY was not found in .env."
        )

    response = requests.get(
        url,
        params={
            "api_key": API_KEY,
        },
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    if "response" not in payload:
        raise ValueError(
            f"Unexpected EIA response: {payload}"
        )

    return payload


def fetch_route_metadata() -> dict:
    """Retrieve metadata for the generation route."""

    payload = request_eia_json(
        BASE_ROUTE
    )

    return payload["response"]


def fetch_facet_values(
    facet_id: str,
) -> pd.DataFrame:
    """Retrieve available values for an EIA facet."""

    facet_url = (
        f"{BASE_ROUTE}"
        f"facet/{facet_id}/"
    )

    payload = request_eia_json(
        facet_url
    )

    facet_records = (
        payload["response"]
        .get("facets", [])
    )

    if not facet_records:
        raise ValueError(
            f"No values were returned "
            f"for facet {facet_id!r}."
        )

    return pd.DataFrame(
        facet_records
    )


def main() -> None:
    metadata = fetch_route_metadata()

    print("Route description:")
    print(metadata.get("description"))

    print("\nAvailable frequencies:")
    for frequency in metadata.get(
        "frequency", []
    ):
        print(
            frequency.get("id"),
            "-",
            frequency.get("description"),
        )

    print("\nAvailable data fields:")
    for field_name, field_metadata in (
        metadata.get("data", {}).items()
    ):
        print(
            field_name,
            "-",
            field_metadata.get("alias"),
            "-",
            field_metadata.get("units"),
        )

    print("\nAvailable facets:")

    facet_ids: list[str] = []

    for facet in metadata.get(
        "facets", []
    ):
        facet_id = facet.get("id")

        if facet_id:
            facet_ids.append(facet_id)

        print(
            facet_id,
            "-",
            facet.get("description"),
        )

    output_directory = (
        PROJECT_ROOT
        / "data"
        / "metadata"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata_path = (
        output_directory
        / "generation_route_metadata.json"
    )

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )

    for facet_id in facet_ids:
        facet_df = fetch_facet_values(
            facet_id
        )

        facet_path = (
            output_directory
            / f"generation_{facet_id}.csv"
        )

        facet_df.to_csv(
            facet_path,
            index=False,
        )

        print(
            f"\nFacet values: {facet_id}"
        )

        print(
            facet_df.to_string(
                index=False
            )
        )

        print(
            f"Saved to: {facet_path}"
        )

    print(
        f"\nSaved route metadata to: "
        f"{metadata_path}"
    )


if __name__ == "__main__":
    main()