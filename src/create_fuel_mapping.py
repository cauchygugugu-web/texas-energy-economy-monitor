from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_generation_by_fuel.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "config"
    / "fuel_mapping.csv"
)


def suggest_analysis_group(
    description: str,
) -> str:
    """
    Suggest a standardized fuel group based on
    the EIA fuel description.

    The result must still be reviewed manually.
    """

    text = description.strip().lower()

    if (
        "total" in text
        or "all fuel" in text
        or "all energy" in text
    ):
        return "Total"

    if "natural gas" in text:
        return "Natural Gas"

    if "coal" in text:
        return "Coal"

    if "nuclear" in text:
        return "Nuclear"

    if "wind" in text:
        return "Wind"

    if "solar" in text:
        return "Solar"

    if (
        "hydroelectric" in text
        or "conventional hydro" in text
    ):
        return "Hydroelectric"

    if "pumped storage" in text:
        return "Pumped Storage"

    if (
        "wood" in text
        or "biomass" in text
    ):
        return "Biomass"

    if "geothermal" in text:
        return "Geothermal"

    if (
        "petroleum" in text
        or "oil" in text
    ):
        return "Petroleum"

    if "other" in text:
        return "Other"

    return "Unclassified"


def create_fuel_mapping() -> pd.DataFrame:
    """Create a reviewable fuel mapping table."""

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Generation data were not found. "
            "Run build_generation_dataset.py first."
        )

    df = pd.read_csv(
        INPUT_PATH,
        dtype={
            "fueltypeid": str,
        },
    )

    if "fueltypeid" not in df.columns:
        raise ValueError(
            "The generation dataset does not contain "
            "'fueltypeid'."
        )

    description_column = (
        "fuelTypeDescription"
        if "fuelTypeDescription" in df.columns
        else None
    )

    if description_column is None:
        df["fuel_description"] = df[
            "fueltypeid"
        ]
    else:
        df["fuel_description"] = df[
            description_column
        ].fillna(df["fueltypeid"])

    mapping = (
        df[
            [
                "fueltypeid",
                "fuel_description",
            ]
        ]
        .drop_duplicates()
        .sort_values("fueltypeid")
        .reset_index(drop=True)
    )

    mapping["analysis_group"] = mapping[
        "fuel_description"
    ].map(suggest_analysis_group)

    mapping["is_reported_total"] = (
        mapping["analysis_group"].eq("Total")
    )

    mapping["include_in_mix"] = ~mapping[
        "analysis_group"
    ].isin(
        [
            "Total",
            "Unclassified",
        ]
    )

    mapping["notes"] = ""

    return mapping


def main() -> None:
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"{OUTPUT_PATH} already exists. "
            "Delete or rename it only if you intend "
            "to regenerate the mapping."
        )

    mapping = create_fuel_mapping()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mapping.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nGenerated fuel mapping:")
    print(
        mapping.to_string(
            index=False
        )
    )

    unclassified = mapping.loc[
        mapping["analysis_group"].eq(
            "Unclassified"
        )
    ]

    if not unclassified.empty:
        print(
            "\nWARNING: Some fuel types remain "
            "unclassified:"
        )
        print(
            unclassified.to_string(
                index=False
            )
        )

    print(
        f"\nSaved mapping to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()