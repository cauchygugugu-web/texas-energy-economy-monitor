from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "variable_dictionary.csv"
)

INDICATOR_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_energy_indicators_monthly.csv"
)


def build_variable_dictionary() -> pd.DataFrame:
    """Build the project variable dictionary."""

    rows: list[dict[str, str]] = [
        {
            "variable": "period",
            "category": "identifier",
            "unit": "month",
            "source": "EIA",
            "definition": "Observation month",
            "construction": "Original monthly date",
            "notes": "Stored as YYYY-MM-DD",
        },
        {
            "variable": "total_generation",
            "category": "generation",
            "unit": "thousand MWh",
            "source": "Derived from EIA",
            "definition": (
                "Total electricity generation from selected "
                "non-overlapping fuel categories"
            ),
            "construction": (
                "Sum of Coal, Natural Gas, Other Gases, "
                "Petroleum, Nuclear, Hydroelectric, Wind, "
                "Solar, Biomass, and Other"
            ),
            "notes": (
                "Validated against the EIA reported "
                "all-fuels total"
            ),
        },
        {
            "variable": "renewable_generation",
            "category": "generation",
            "unit": "thousand MWh",
            "source": "Derived from EIA",
            "definition": "Electricity generation from renewable sources",
            "construction": (
                "Wind + Solar + Hydroelectric + Biomass"
            ),
            "notes": "",
        },
        {
            "variable": "fossil_generation",
            "category": "generation",
            "unit": "thousand MWh",
            "source": "Derived from EIA",
            "definition": "Electricity generation from fossil fuels",
            "construction": (
                "Coal + Natural Gas + Other Gases + Petroleum"
            ),
            "notes": "",
        },
        {
            "variable": "non_fossil_generation",
            "category": "generation",
            "unit": "thousand MWh",
            "source": "Derived from EIA",
            "definition": "Renewable and nuclear electricity generation",
            "construction": "renewable_generation + Nuclear",
            "notes": "",
        },
        {
            "variable": "renewable_share",
            "category": "generation share",
            "unit": "proportion",
            "source": "Derived",
            "definition": "Share of generation from renewable sources",
            "construction": (
                "renewable_generation / total_generation"
            ),
            "notes": "Multiply by 100 for percentage units",
        },
        {
            "variable": "fossil_share",
            "category": "generation share",
            "unit": "proportion",
            "source": "Derived",
            "definition": "Share of generation from fossil fuels",
            "construction": (
                "fossil_generation / total_generation"
            ),
            "notes": "Multiply by 100 for percentage units",
        },
        {
            "variable": "nuclear_share",
            "category": "generation share",
            "unit": "proportion",
            "source": "Derived",
            "definition": "Share of generation from nuclear energy",
            "construction": "Nuclear / total_generation",
            "notes": "",
        },
        {
            "variable": "other_share",
            "category": "generation share",
            "unit": "proportion",
            "source": "Derived",
            "definition": "Share of generation classified as Other",
            "construction": "Other / total_generation",
            "notes": "",
        },
    ]

    rows.extend(
        [
            {
                "variable": "tx_unemployment_rate",
                "category": "labor market",
                "unit": "percent",
                "source": "FRED: TXUR",
                "definition": (
                    "Texas unemployment rate."
                ),
                "construction": (
                    "Original monthly FRED series."
                ),
                "notes": (
                    "Seasonal-adjustment information is "
                    "recorded in fred_series_metadata.csv."
                ),
            },
            {
                "variable": "tx_total_nonfarm_employment",
                "category": "labor market",
                "unit": "thousands of persons",
                "source": "FRED: TXNA",
                "definition": (
                    "Total nonfarm employment in Texas."
                ),
                "construction": (
                    "Original monthly FRED series."
                ),
                "notes": (
                    "Seasonal-adjustment information is "
                    "recorded in fred_series_metadata.csv."
                ),
            },
            {
                "variable": "wti_crude_oil_price",
                "category": "energy price",
                "unit": "dollars per barrel",
                "source": "FRED: MCOILWTICO",
                "definition": (
                    "Monthly West Texas Intermediate "
                    "crude-oil price."
                ),
                "construction": (
                    "Original monthly FRED series."
                ),
                "notes": "",
            },
            {
                "variable": "henry_hub_natural_gas_price",
                "category": "energy price",
                "unit": "dollars per million Btu",
                "source": "FRED: MHHNGSP",
                "definition": (
                    "Monthly Henry Hub natural-gas "
                    "spot price."
                ),
                "construction": (
                    "Original monthly FRED series."
                ),
                "notes": "",
            },
            {
                "variable": "us_cpi",
                "category": "price index",
                "unit": "index",
                "source": "FRED: CPIAUCSL",
                "definition": (
                    "U.S. Consumer Price Index for "
                    "All Urban Consumers."
                ),
                "construction": (
                    "Original monthly FRED series."
                ),
                "notes": (
                    "Used to convert nominal retail "
                    "electricity prices into January "
                    "2025 price levels."
                ),
            },
        ]
    )

    rows.extend(
        [
            {
                "variable": (
                    "tx_nonfarm_employment_yoy_pct"
                ),
                "category": "labor market",
                "unit": "percent",
                "source": "Derived from FRED: TXNA",
                "definition": (
                    "Year-over-year percentage change "
                    "in Texas total nonfarm employment."
                ),
                "construction": (
                    "(tx_total_nonfarm_employment_t / "
                    "tx_total_nonfarm_employment_t_minus_12 "
                    "- 1) * 100"
                ),
                "notes": (
                    "The first 12 months are missing "
                    "because no prior-year comparison "
                    "is available."
                ),
            },
            {
                "variable": (
                    "tx_unemployment_rate_yoy_pp"
                ),
                "category": "labor market",
                "unit": "percentage points",
                "source": "Derived from FRED: TXUR",
                "definition": (
                    "Year-over-year change in the Texas "
                    "unemployment rate."
                ),
                "construction": (
                    "tx_unemployment_rate_t - "
                    "tx_unemployment_rate_t_minus_12"
                ),
                "notes": (
                    "This is a percentage-point change, "
                    "not a percentage change."
                ),
            },
            {
                "variable": (
                    "wti_crude_oil_price_yoy_pct"
                ),
                "category": "energy price",
                "unit": "percent",
                "source": (
                    "Derived from FRED: MCOILWTICO"
                ),
                "definition": (
                    "Year-over-year percentage change "
                    "in the WTI crude-oil price."
                ),
                "construction": (
                    "(wti_crude_oil_price_t / "
                    "wti_crude_oil_price_t_minus_12 "
                    "- 1) * 100"
                ),
                "notes": (
                    "The first 12 months are missing."
                ),
            },
            {
                "variable": (
                    "henry_hub_natural_gas_price_yoy_pct"
                ),
                "category": "energy price",
                "unit": "percent",
                "source": (
                    "Derived from FRED: MHHNGSP"
                ),
                "definition": (
                    "Year-over-year percentage change "
                    "in the Henry Hub natural-gas price."
                ),
                "construction": (
                    "(henry_hub_natural_gas_price_t / "
                    "henry_hub_natural_gas_price_t_minus_12 "
                    "- 1) * 100"
                ),
                "notes": (
                    "The first 12 months are missing."
                ),
            },
        ]
    )

    for sector in [
        "residential",
        "commercial",
        "industrial",
    ]:
        rows.append(
            {
                "variable": (
                    f"{sector}_price_real_2025_01"
                ),
                "category": (
                    "real retail electricity price"
                ),
                "unit": (
                    "January 2025 cents per kWh"
                ),
                "source": (
                    "Derived from EIA retail data "
                    "and FRED CPIAUCSL"
                ),
                "definition": (
                    f"Inflation-adjusted {sector} "
                    "retail electricity price, "
                    "expressed in January 2025 "
                    "price levels."
                ),
                "construction": (
                    f"{sector}_price_t * "
                    "CPI_2025_01 / us_cpi_t"
                ),
                "notes": (
                    "The nominal and real price are "
                    "equal in the January 2025 base "
                    "period, apart from possible "
                    "floating-point rounding."
                ),
            }
        )

    sectors = {
        "residential": "Residential",
        "commercial": "Commercial",
        "industrial": "Industrial",
    }

    for sector_id, sector_name in sectors.items():
        rows.extend(
            [
                {
                    "variable": f"{sector_id}_price",
                    "category": "retail electricity",
                    "unit": "cents per kWh",
                    "source": "EIA Retail Sales",
                    "definition": (
                        f"Average {sector_name.lower()} "
                        "retail electricity price"
                    ),
                    "construction": "Original EIA variable",
                    "notes": (
                        "Average retail revenue per unit "
                        "of electricity sold"
                    ),
                },
                {
                    "variable": f"{sector_id}_sales",
                    "category": "retail electricity",
                    "unit": "million kWh",
                    "source": "EIA Retail Sales",
                    "definition": (
                        f"{sector_name} electricity sales"
                    ),
                    "construction": "Original EIA variable",
                    "notes": "",
                },
                {
                    "variable": f"{sector_id}_revenue",
                    "category": "retail electricity",
                    "unit": "million dollars",
                    "source": "EIA Retail Sales",
                    "definition": (
                        f"{sector_name} retail electricity revenue"
                    ),
                    "construction": "Original EIA variable",
                    "notes": "",
                },
                {
                    "variable": f"{sector_id}_customers",
                    "category": "retail electricity",
                    "unit": "customers",
                    "source": "EIA Retail Sales",
                    "definition": (
                        f"Number of {sector_name.lower()} customers"
                    ),
                    "construction": "Original EIA variable",
                    "notes": "",
                },
                {
                    "variable": (
                        f"{sector_id}_sales_per_customer_kwh"
                    ),
                    "category": "retail indicator",
                    "unit": "kWh per customer per month",
                    "source": "Derived",
                    "definition": (
                        f"Average monthly {sector_name.lower()} "
                        "electricity sales per customer"
                    ),
                    "construction": (
                        f"{sector_id}_sales * 1,000,000 / "
                        f"{sector_id}_customers"
                    ),
                    "notes": "",
                },
                {
                    "variable": (
                        f"{sector_id}_revenue_per_customer_dollars"
                    ),
                    "category": "retail indicator",
                    "unit": "dollars per customer per month",
                    "source": "Derived",
                    "definition": (
                        f"Average monthly {sector_name.lower()} "
                        "revenue per customer"
                    ),
                    "construction": (
                        f"{sector_id}_revenue * 1,000,000 / "
                        f"{sector_id}_customers"
                    ),
                    "notes": "",
                },
                {
                    "variable": (
                        f"{sector_id}_reconstructed_price"
                    ),
                    "category": "validation",
                    "unit": "cents per kWh",
                    "source": "Derived",
                    "definition": (
                        f"{sector_name} price reconstructed from "
                        "revenue and sales"
                    ),
                    "construction": (
                        f"{sector_id}_revenue / "
                        f"{sector_id}_sales * 100"
                    ),
                    "notes": (
                        "Used to validate the reported EIA price"
                    ),
                },
                {
                    "variable": f"{sector_id}_price_difference",
                    "category": "validation",
                    "unit": "cents per kWh",
                    "source": "Derived",
                    "definition": (
                        "Difference between reconstructed "
                        "and reported price"
                    ),
                    "construction": (
                        f"{sector_id}_reconstructed_price - "
                        f"{sector_id}_price"
                    ),
                    "notes": "",
                },
            ]
        )

    generation_variables = {
        "Biomass": "Biomass electricity generation",
        "Coal": "Coal electricity generation",
        "Hydroelectric": "Conventional hydroelectric generation",
        "Natural Gas": "Natural-gas electricity generation",
        "Nuclear": "Nuclear electricity generation",
        "Other": "Generation classified by EIA as Other",
        "Other Gases": "Electricity generation from other gases",
        "Petroleum": "Petroleum electricity generation",
        "Solar": "Utility-scale solar electricity generation",
        "Wind": "Wind electricity generation",
    }

    for variable, definition in generation_variables.items():
        rows.append(
            {
                "variable": variable,
                "category": "generation",
                "unit": "thousand MWh",
                "source": "EIA Electric Power Operational Data",
                "definition": definition,
                "construction": (
                    "Original or aggregated EIA fuel series "
                    "selected through fuel_mapping.csv"
                ),
                "notes": (
                    "Selected categories are mutually "
                    "non-overlapping"
                ),
            }
        )

    share_variables = {
        "biomass_share": "Biomass",
        "coal_share": "Coal",
        "hydroelectric_share": "Hydroelectric",
        "natural_gas_share": "Natural Gas",
        "other_gases_share": "Other Gases",
        "petroleum_share": "Petroleum",
        "solar_share": "Solar",
        "wind_share": "Wind",
    }

    for variable, generation_column in share_variables.items():
        rows.append(
            {
                "variable": variable,
                "category": "generation share",
                "unit": "proportion",
                "source": "Derived",
                "definition": (
                    f"Share of total generation from "
                    f"{generation_column}"
                ),
                "construction": (
                    f"{generation_column} / total_generation"
                ),
                "notes": "Multiply by 100 for percentage units",
            }
        )

    rows.extend(
        [
            {
                "variable": "selected_sector_sales",
                "category": "retail aggregate",
                "unit": "million kWh",
                "source": "Derived",
                "definition": (
                    "Combined electricity sales for residential, "
                    "commercial, and industrial sectors"
                ),
                "construction": (
                    "residential_sales + commercial_sales "
                    "+ industrial_sales"
                ),
                "notes": "",
            },
            {
                "variable": "selected_sector_revenue",
                "category": "retail aggregate",
                "unit": "million dollars",
                "source": "Derived",
                "definition": (
                    "Combined retail revenue for the three "
                    "selected sectors"
                ),
                "construction": (
                    "residential_revenue + commercial_revenue "
                    "+ industrial_revenue"
                ),
                "notes": "",
            },
            {
                "variable": "selected_sector_customers",
                "category": "retail aggregate",
                "unit": "customers",
                "source": "Derived",
                "definition": (
                    "Combined customer count for the three "
                    "selected sectors"
                ),
                "construction": (
                    "residential_customers + commercial_customers "
                    "+ industrial_customers"
                ),
                "notes": "",
            },
        ]
    )

    dictionary = pd.DataFrame(rows)

    duplicate_mask = dictionary[
        "variable"
    ].duplicated(
        keep=False
    )

    if duplicate_mask.any():
        duplicated_variables = (
            dictionary.loc[
                duplicate_mask,
                "variable",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate variables were found in "
            "the variable dictionary: "
            f"{duplicated_variables}"
        )

    if dictionary["variable"].duplicated().any():
        duplicated = (
            dictionary.loc[
                dictionary["variable"].duplicated(
                    keep=False
                ),
                "variable",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            f"Duplicate variables in dictionary: {duplicated}"
        )

    return (
        dictionary
        .sort_values(
            ["category", "variable"]
        )
        .reset_index(drop=True)
    )


def check_dictionary_coverage(
    dictionary: pd.DataFrame,
) -> None:
    """Compare documented variables with the indicator dataset."""

    if not INDICATOR_DATA_PATH.exists():
        print(
            "Indicator dataset was not found; "
            "coverage check was skipped."
        )
        return

    data_columns = set(
        pd.read_csv(
            INDICATOR_DATA_PATH,
            nrows=0,
        ).columns
    )

    documented_variables = set(
        dictionary["variable"]
    )

    undocumented = sorted(
        data_columns - documented_variables
    )

    unused_entries = sorted(
        documented_variables - data_columns
    )

    if undocumented:
        print("\nVariables not yet documented:")
        for variable in undocumented:
            print(f"- {variable}")

    if unused_entries:
        print("\nDictionary entries not found in dataset:")
        for variable in unused_entries:
            print(f"- {variable}")

    if not undocumented and not unused_entries:
        print(
            "\nDictionary coverage check passed: "
            "all dataset columns are documented."
        )


def main() -> None:
    dictionary = build_variable_dictionary()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dictionary.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(dictionary.to_string(index=False))

    print(
        f"\nNumber of documented variables: "
        f"{len(dictionary)}"
    )

    print(
        f"Saved variable dictionary to: "
        f"{OUTPUT_PATH}"
    )

    check_dictionary_coverage(
        dictionary
    )


if __name__ == "__main__":
    main()