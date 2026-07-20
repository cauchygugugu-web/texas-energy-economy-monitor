from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    PROJECT_ROOT
    / "config"
    / "weather_series.csv"
)


WEATHER_SERIES = [
    {
        "location_code": "41",
        "parameter": "tavg",
        "variable_name": "tx_average_temperature",
        "unit": "degrees Fahrenheit",
        "category": "temperature",
        "geography": "Texas statewide",
    },
    {
        "location_code": "41",
        "parameter": "pcp",
        "variable_name": "tx_precipitation",
        "unit": "inches",
        "category": "precipitation",
        "geography": "Texas statewide",
    },
    {
        "location_code": "41",
        "parameter": "hdd",
        "variable_name": "tx_heating_degree_days",
        "unit": "Degrees Days Fahrenheit",
        "category": "energy demand",
        "geography": "Texas statewide",
    },
    {
        "location_code": "41",
        "parameter": "cdd",
        "variable_name": "tx_cooling_degree_days",
        "unit": "Degrees Days Fahrenheit",
        "category": "energy demand",
        "geography": "Texas statewide",
    },
]


def build_weather_series_config() -> pd.DataFrame:
    """Create and validate the weather-series configuration."""

    config = pd.DataFrame(
        WEATHER_SERIES
    )

    required_columns = {
        "location_code",
        "parameter",
        "variable_name",
        "unit",
        "category",
        "geography",
    }

    missing_columns = (
        required_columns
        - set(config.columns)
    )

    if missing_columns:
        raise ValueError(
            "Weather configuration columns "
            "are missing: "
            f"{sorted(missing_columns)}"
        )

    for column in required_columns:
        config[column] = (
            config[column]
            .astype(str)
            .str.strip()
        )

        if config[column].eq("").any():
            raise ValueError(
                f"Blank values were found "
                f"in {column}."
            )

    if config["parameter"].duplicated().any():
        duplicated_parameters = (
            config.loc[
                config["parameter"].duplicated(
                    keep=False
                ),
                "parameter",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate NOAA parameters "
            "were found: "
            f"{duplicated_parameters}"
        )

    if config[
        "variable_name"
    ].duplicated().any():
        duplicated_variables = (
            config.loc[
                config[
                    "variable_name"
                ].duplicated(
                    keep=False
                ),
                "variable_name",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate project variable "
            "names were found: "
            f"{duplicated_variables}"
        )

    allowed_parameters = {
        "tavg",
        "pcp",
        "hdd",
        "cdd",
    }

    invalid_parameters = sorted(
        set(config["parameter"])
        - allowed_parameters
    )

    if invalid_parameters:
        raise ValueError(
            "Unsupported weather parameters "
            "were found: "
            f"{invalid_parameters}"
        )

    return (
        config
        .sort_values(
            [
                "category",
                "parameter",
            ]
        )
        .reset_index(drop=True)
    )


def main() -> None:
    config = (
        build_weather_series_config()
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    config.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        "\nWeather-series configuration:"
    )

    print(
        config.to_string(
            index=False
        )
    )

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