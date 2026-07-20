from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from fetch_weather import create_session, fetch_weather_series


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = PROJECT_ROOT / "config" / "weather_series.csv"
PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "tables"

OUTPUT_PATH = PROCESSED_DIRECTORY / "tx_weather_monthly.csv"
METADATA_REPORT_PATH = REPORT_DIRECTORY / "weather_series_metadata.csv"
COVERAGE_REPORT_PATH = REPORT_DIRECTORY / "weather_series_coverage.csv"

DEFAULT_START_YEAR = 2015


def load_weather_config() -> pd.DataFrame:
    """Load and validate the weather-series configuration."""

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Weather-series configuration was not found. "
            "Run create_weather_series_config.py first."
        )

    config = pd.read_csv(
        CONFIG_PATH,
        dtype=str,
        encoding="utf-8-sig",
    )

    required_columns = {
        "location_code",
        "parameter",
        "variable_name",
        "unit",
        "category",
        "geography",
    }

    missing_columns = required_columns - set(config.columns)

    if missing_columns:
        raise ValueError(
            "Weather configuration columns are missing: "
            f"{sorted(missing_columns)}"
        )

    for column in required_columns:
        config[column] = (
            config[column]
            .fillna("")
            .str.strip()
        )

        if config[column].eq("").any():
            raise ValueError(
                f"Blank configuration values were found in {column}."
            )

    config["parameter"] = config["parameter"].str.lower()

    if config["parameter"].duplicated().any():
        duplicated_parameters = (
            config.loc[
                config["parameter"].duplicated(keep=False),
                "parameter",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate NOAA parameters were found: "
            f"{duplicated_parameters}"
        )

    if config["variable_name"].duplicated().any():
        duplicated_variables = (
            config.loc[
                config["variable_name"].duplicated(keep=False),
                "variable_name",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate project variable names were found: "
            f"{duplicated_variables}"
        )

    return config.reset_index(drop=True)


def build_series_coverage(
    observations: pd.DataFrame,
    location_code: str,
    parameter: str,
    variable_name: str,
    category: str,
    geography: str,
) -> dict[str, Any]:
    """Build a monthly coverage record for one weather series."""

    first_period = observations["period"].min()
    last_period = observations["period"].max()

    expected_months = pd.date_range(
        start=first_period,
        end=last_period,
        freq="MS",
    )

    returned_periods = pd.DatetimeIndex(
        observations["period"].drop_duplicates()
    )

    missing_calendar_months = expected_months.difference(
        returned_periods
    )

    missing_value_periods = (
        observations.loc[
            observations["value"].isna(),
            "period",
        ]
        .dt.strftime("%Y-%m")
        .tolist()
    )

    missing_departure_periods = (
        observations.loc[
            observations["departure"].isna(),
            "period",
        ]
        .dt.strftime("%Y-%m")
        .tolist()
    )

    return {
        "location_code": location_code,
        "parameter": parameter,
        "variable_name": variable_name,
        "category": category,
        "geography": geography,
        "first_period": first_period,
        "last_period": last_period,
        "expected_months": len(expected_months),
        "returned_months": observations["period"].nunique(),
        "missing_calendar_months": len(missing_calendar_months),
        "missing_calendar_periods": ", ".join(
            period.strftime("%Y-%m")
            for period in missing_calendar_months
        ),
        "missing_values": int(
            observations["value"].isna().sum()
        ),
        "missing_value_periods": ", ".join(
            missing_value_periods
        ),
        "missing_departures": int(
            observations["departure"].isna().sum()
        ),
        "missing_departure_periods": ", ".join(
            missing_departure_periods
        ),
    }


def build_metadata_record(
    api_metadata: dict[str, Any],
    config_row: Any,
) -> dict[str, Any]:
    """Combine API metadata with local configuration metadata."""

    api_units = str(
        api_metadata.get("units", "")
    ).strip()

    configured_unit = str(
        config_row.unit
    ).strip()

    return {
        "location_code": config_row.location_code,
        "parameter": config_row.parameter,
        "variable_name": config_row.variable_name,
        "title": api_metadata.get("title", ""),
        "api_units": api_units,
        "configured_unit": configured_unit,
        "unit_match": (
            api_units.lower()
            == configured_unit.lower()
        ),
        "base_period": api_metadata.get(
            "base_period",
            "",
        ),
        "category": config_row.category,
        "geography": config_row.geography,
        "requested_start_year": api_metadata.get(
            "requested_start_year",
            "",
        ),
        "requested_end_year": api_metadata.get(
            "requested_end_year",
            "",
        ),
        "source": api_metadata.get(
            "source",
            "",
        ),
    }


def build_weather_dataset(
    start_year: int = DEFAULT_START_YEAR,
    end_year: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Download configured NOAA series and build monthly outputs."""

    config = load_weather_config()

    value_frames: list[pd.DataFrame] = []
    departure_frames: list[pd.DataFrame] = []
    metadata_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []

    with create_session() as session:
        for row in config.itertuples(index=False):
            print(
                f"Fetching {row.parameter} "
                f"as {row.variable_name}..."
            )

            observations, api_metadata = fetch_weather_series(
                location_code=row.location_code,
                parameter=row.parameter,
                start_year=start_year,
                end_year=end_year,
                session=session,
            )

            value_frames.append(
                observations[
                    ["period", "value"]
                ].rename(
                    columns={
                        "value": row.variable_name,
                    }
                )
            )

            departure_frames.append(
                observations[
                    ["period", "departure"]
                ].rename(
                    columns={
                        "departure": (
                            f"{row.variable_name}_departure"
                        ),
                    }
                )
            )

            metadata_rows.append(
                build_metadata_record(
                    api_metadata=api_metadata,
                    config_row=row,
                )
            )

            coverage_rows.append(
                build_series_coverage(
                    observations=observations,
                    location_code=row.location_code,
                    parameter=row.parameter,
                    variable_name=row.variable_name,
                    category=row.category,
                    geography=row.geography,
                )
            )

    if not value_frames:
        raise ValueError(
            "No configured weather series were downloaded."
        )

    weather = value_frames[0]

    for frame in value_frames[1:]:
        weather = weather.merge(
            frame,
            on="period",
            how="outer",
            validate="one_to_one",
        )

    for frame in departure_frames:
        weather = weather.merge(
            frame,
            on="period",
            how="left",
            validate="one_to_one",
        )

    weather = (
        weather
        .sort_values("period")
        .reset_index(drop=True)
    )

    if weather["period"].duplicated().any():
        raise ValueError(
            "Duplicate months were found in the "
            "combined weather dataset."
        )

    configured_variables = config[
        "variable_name"
    ].tolist()

    departure_variables = [
        f"{variable}_departure"
        for variable in configured_variables
    ]

    weather = weather.reindex(
        columns=[
            "period",
            *configured_variables,
            *departure_variables,
        ]
    )

    metadata = (
        pd.DataFrame(metadata_rows)
        .sort_values(
            ["category", "parameter"]
        )
        .reset_index(drop=True)
    )

    coverage = (
        pd.DataFrame(coverage_rows)
        .sort_values(
            ["category", "parameter"]
        )
        .reset_index(drop=True)
    )

    return weather, metadata, coverage


def main() -> None:
    weather, metadata, coverage = (
        build_weather_dataset()
    )

    PROCESSED_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    weather.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    metadata.to_csv(
        METADATA_REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    coverage.to_csv(
        COVERAGE_REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nTexas monthly weather data:")
    print(weather.head().to_string(index=False))

    print("\nLatest observations:")
    print(weather.tail().to_string(index=False))

    print("\nWeather-series metadata:")
    print(
        metadata[
            [
                "parameter",
                "variable_name",
                "api_units",
                "configured_unit",
                "unit_match",
                "base_period",
            ]
        ].to_string(index=False)
    )

    mismatched_units = metadata.loc[
        ~metadata["unit_match"]
    ]

    if not mismatched_units.empty:
        print(
            "\nWarning: configured units do not exactly "
            "match NOAA metadata:"
        )

        print(
            mismatched_units[
                [
                    "parameter",
                    "api_units",
                    "configured_unit",
                ]
            ].to_string(index=False)
        )

    print("\nWeather-series coverage:")
    print(coverage.to_string(index=False))

    print(
        f"\nNumber of monthly rows: "
        f"{len(weather)}"
    )

    print(
        f"Date range: "
        f"{weather['period'].min():%Y-%m} to "
        f"{weather['period'].max():%Y-%m}"
    )

    print(
        f"\nSaved weather data to: "
        f"{OUTPUT_PATH}"
    )

    print(
        f"Saved metadata report to: "
        f"{METADATA_REPORT_PATH}"
    )

    print(
        f"Saved coverage report to: "
        f"{COVERAGE_REPORT_PATH}"
    )


if __name__ == "__main__":
    main()
