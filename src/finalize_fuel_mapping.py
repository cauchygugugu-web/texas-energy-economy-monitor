from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MAPPING_PATH = (
    PROJECT_ROOT
    / "config"
    / "fuel_mapping.csv"
)


GROUP_BY_CODE = {
    # Overall aggregates
    "ALL": "Total",
    "FOS": "Fossil Fuels Total",
    "REN": "Renewables Total",
    "AOR": "Renewables Excluding Hydro Total",

    # Coal
    "ANT": "Coal",
    "BIS": "Coal",
    "BIT": "Coal",
    "COL": "Coal",
    "COW": "Coal",
    "LIG": "Coal",
    "RC": "Coal",
    "SUB": "Coal",

    # Natural gas and other gases
    "NG": "Natural Gas",
    "NGO": "Natural Gas and Other Gases",
    "OOG": "Other Gases",

    # Petroleum
    "DFO": "Petroleum",
    "PC": "Petroleum",
    "PEL": "Petroleum",
    "PET": "Petroleum",
    "RFO": "Petroleum",
    "WOO": "Petroleum",

    # Nuclear and hydro
    "NUC": "Nuclear",
    "HYC": "Hydroelectric",

    # Wind
    "WND": "Wind",
    "WNT": "Wind",

    # Solar
    "DPV": "Solar",
    "SPV": "Solar",
    "SUN": "Solar",
    "TPV": "Solar Total",
    "TSN": "Solar Total",

    # Biomass
    "BIO": "Biomass",
    "LFG": "Biomass",
    "MLG": "Biomass",
    "OB2": "Biomass",
    "OBW": "Biomass",
    "ORW": "Biomass",
    "WAS": "Biomass",
    "WWW": "Biomass",

    # Remaining category
    "OTH": "Other",
}


# These are the mutually non-overlapping components
# used to construct the electricity generation mix.
INCLUDED_CODES = {
    "COW",
    "NG",
    "OOG",
    "PET",
    "NUC",
    "HYC",
    "WND",
    "SUN",
    "BIO",
    "OTH",
}


# These are reported aggregate totals and must not
# be added to their own component categories.
REPORTED_TOTAL_CODES = {
    "ALL",
    "FOS",
    "REN",
    "AOR",
    "TPV",
    "TSN",
}


SPECIAL_NOTES = {
    "ALL": (
        "Reported all-fuels total; excluded from "
        "component sum."
    ),
    "FOS": (
        "Aggregate fossil-fuel total; equals coal, "
        "natural gas and other gases, and petroleum."
    ),
    "REN": (
        "Aggregate renewable total; includes "
        "hydroelectric generation."
    ),
    "AOR": (
        "Aggregate non-hydro renewable total; equals "
        "wind, utility-scale solar, and biomass."
    ),
    "DPV": (
        "Estimated small-scale solar; excluded because "
        "it is not included in the reported ALL total."
    ),
    "TPV": (
        "Total photovoltaic generation including "
        "small-scale solar; excluded to avoid overlap."
    ),
    "TSN": (
        "Total solar generation including small-scale "
        "solar; excluded to avoid overlap."
    ),
    "PET": (
        "Selected aggregate petroleum category. "
        "Some recent months may be missing."
    ),
    "OTH": (
        "Selected residual other category; negative "
        "values are preserved."
    ),
}


def finalize_fuel_mapping() -> pd.DataFrame:
    """Apply manually verified fuel mapping decisions."""

    if not MAPPING_PATH.exists():
        raise FileNotFoundError(
            "fuel_mapping.csv was not found."
        )

    mapping = pd.read_csv(
        MAPPING_PATH,
        dtype={
            "fueltypeid": str,
        },
    )

    mapping["fueltypeid"] = (
        mapping["fueltypeid"]
        .str.strip()
        .str.upper()
    )

    unknown_codes = (
        set(mapping["fueltypeid"])
        - set(GROUP_BY_CODE)
    )

    if unknown_codes:
        raise ValueError(
            "Fuel codes are missing from GROUP_BY_CODE: "
            f"{sorted(unknown_codes)}"
        )

    unused_rules = (
        set(GROUP_BY_CODE)
        - set(mapping["fueltypeid"])
    )

    if unused_rules:
        print(
            "Warning: mapping rules without matching "
            f"data rows: {sorted(unused_rules)}"
        )

    mapping["analysis_group"] = (
        mapping["fueltypeid"]
        .map(GROUP_BY_CODE)
    )

    mapping["is_reported_total"] = (
        mapping["fueltypeid"]
        .isin(REPORTED_TOTAL_CODES)
    )

    mapping["include_in_mix"] = (
        mapping["fueltypeid"]
        .isin(INCLUDED_CODES)
    )

    mapping["notes"] = mapping[
        "fueltypeid"
    ].map(SPECIAL_NOTES)

    included_mask = mapping[
        "include_in_mix"
    ]

    mapping.loc[
        included_mask
        & mapping["notes"].isna(),
        "notes",
    ] = (
        "Selected non-overlapping component for "
        "generation mix."
    )

    excluded_mask = (
        ~mapping["include_in_mix"]
        & mapping["notes"].isna()
    )

    mapping.loc[
        excluded_mask,
        "notes",
    ] = (
        "Subcategory or duplicate aggregate; excluded "
        "to avoid double counting."
    )

    mapping = mapping.sort_values(
        "fueltypeid"
    ).reset_index(drop=True)

    return mapping


def main() -> None:
    mapping = finalize_fuel_mapping()

    mapping.to_csv(
        MAPPING_PATH,
        index=False,
    )

    print("\nIncluded fuel codes:")
    print(
        mapping.loc[
            mapping["include_in_mix"],
            [
                "fueltypeid",
                "fuel_description",
                "analysis_group",
            ],
        ].to_string(index=False)
    )

    print("\nReported totals:")
    print(
        mapping.loc[
            mapping["is_reported_total"],
            [
                "fueltypeid",
                "fuel_description",
                "analysis_group",
            ],
        ].to_string(index=False)
    )

    unclassified = mapping.loc[
        mapping["analysis_group"].isna()
        | mapping["analysis_group"].eq(
            "Unclassified"
        )
    ]

    if not unclassified.empty:
        raise ValueError(
            "Unclassified fuel types remain."
        )

    print(
        f"\nUpdated mapping saved to: "
        f"{MAPPING_PATH}"
    )


if __name__ == "__main__":
    main()