from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GENERATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_generation_by_fuel.csv"
)

MAPPING_PATH = (
    PROJECT_ROOT
    / "config"
    / "fuel_mapping.csv"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

TOLERANCE = 0.001


def parse_boolean_column(
    series: pd.Series,
    column_name: str,
) -> pd.Series:
    """Convert common text and numeric representations to booleans."""

    boolean_map = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
    }

    parsed = (
        series
        .astype(str)
        .str.strip()
        .str.lower()
        .map(boolean_map)
    )

    if parsed.isna().any():
        invalid_values = (
            series.loc[parsed.isna()]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            f"Invalid values in {column_name}: "
            f"{invalid_values}"
        )

    return parsed.astype(bool)


def load_generation_data() -> pd.DataFrame:
    """Load and validate the original EIA generation dataset."""

    if not GENERATION_PATH.exists():
        raise FileNotFoundError(
            "Generation data were not found. "
            "Run the generation-download script first."
        )

    generation = pd.read_csv(
        GENERATION_PATH,
        dtype={
            "fueltypeid": str,
            "location": str,
            "sectorid": str,
        },
    )

    required_columns = {
        "period",
        "fueltypeid",
        "generation",
    }

    missing_columns = (
        required_columns - set(generation.columns)
    )

    if missing_columns:
        raise ValueError(
            "Generation columns are missing: "
            f"{sorted(missing_columns)}"
        )

    generation["fueltypeid"] = (
        generation["fueltypeid"]
        .str.strip()
        .str.upper()
    )

    generation["period"] = pd.to_datetime(
        generation["period"],
        errors="coerce",
    )

    generation["generation"] = pd.to_numeric(
        generation["generation"],
        errors="coerce",
    )

    if generation["period"].isna().any():
        raise ValueError(
            "Invalid period values were found."
        )

    if generation["generation"].isna().any():
        raise ValueError(
            "Missing or invalid generation values "
            "were found."
        )

    key_columns = ["period"]

    for optional_column in [
        "location",
        "sectorid",
    ]:
        if optional_column in generation.columns:
            key_columns.append(optional_column)

    duplicate_mask = generation.duplicated(
        subset=key_columns + ["fueltypeid"]
    )

    if duplicate_mask.any():
        duplicated_rows = generation.loc[
            duplicate_mask,
            key_columns + ["fueltypeid"],
        ]

        raise ValueError(
            "Duplicate generation observations were "
            "found:\n"
            f"{duplicated_rows.to_string(index=False)}"
        )

    if "generation-units" in generation.columns:
        units = (
            generation["generation-units"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

        if len(units) > 1:
            raise ValueError(
                "Multiple generation units were found: "
                f"{units.tolist()}"
            )

    return generation


def load_fuel_mapping() -> pd.DataFrame:
    """Load and validate the manually reviewed fuel mapping."""

    if not MAPPING_PATH.exists():
        raise FileNotFoundError(
            "Fuel mapping was not found. "
            "Create config/fuel_mapping.csv first."
        )

    mapping = pd.read_csv(
        MAPPING_PATH,
        dtype={
            "fueltypeid": str,
        },
    )

    required_columns = {
        "fueltypeid",
        "analysis_group",
        "is_reported_total",
        "include_in_mix",
    }

    missing_columns = (
        required_columns - set(mapping.columns)
    )

    if missing_columns:
        raise ValueError(
            "Mapping columns are missing: "
            f"{sorted(missing_columns)}"
        )

    mapping["fueltypeid"] = (
        mapping["fueltypeid"]
        .str.strip()
        .str.upper()
    )

    if mapping["fueltypeid"].duplicated().any():
        duplicated_ids = (
            mapping.loc[
                mapping["fueltypeid"].duplicated(
                    keep=False
                ),
                "fueltypeid",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate fuel IDs in mapping: "
            f"{duplicated_ids}"
        )

    mapping["is_reported_total"] = (
        parse_boolean_column(
            mapping["is_reported_total"],
            "is_reported_total",
        )
    )

    mapping["include_in_mix"] = (
        parse_boolean_column(
            mapping["include_in_mix"],
            "include_in_mix",
        )
    )

    mapping["analysis_group"] = (
        mapping["analysis_group"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    unclassified = mapping.loc[
        mapping["analysis_group"].isin(
            [
                "",
                "Unclassified",
            ]
        )
    ]

    if not unclassified.empty:
        raise ValueError(
            "Unclassified fuel types remain in "
            "fuel_mapping.csv:\n"
            f"{unclassified.to_string(index=False)}"
        )

    invalid_included_rows = mapping.loc[
        mapping["include_in_mix"]
        & mapping["analysis_group"].isin(
            [
                "Total",
                "Fossil Fuels Total",
                "Renewables Total",
                "Renewables Excluding Hydro Total",
            ]
        )
    ]

    if not invalid_included_rows.empty:
        raise ValueError(
            "Aggregate totals must not be marked "
            "include_in_mix=True:\n"
            f"{invalid_included_rows.to_string(index=False)}"
        )

    return mapping


def derive_missing_petroleum(
    generation: pd.DataFrame,
) -> pd.DataFrame:
    """
    Derive missing aggregate petroleum generation.

    For months where PET is unavailable:

        PET = FOS - COW - NG - OOG

    Existing PET observations are never overwritten.
    """

    key_columns = ["period"]

    for optional_column in [
        "location",
        "sectorid",
    ]:
        if optional_column in generation.columns:
            key_columns.append(optional_column)

    wide = generation.pivot(
        index=key_columns,
        columns="fueltypeid",
        values="generation",
    )

    required_codes = {
        "FOS",
        "COW",
        "NG",
        "OOG",
    }

    missing_codes = (
        required_codes - set(wide.columns)
    )

    if missing_codes:
        raise ValueError(
            "Petroleum cannot be derived because "
            "these fuel codes are missing: "
            f"{sorted(missing_codes)}"
        )

    petroleum_residual = (
        wide["FOS"]
        - wide["COW"]
        - wide["NG"]
        - wide["OOG"]
    )

    if "PET" in wide.columns:
        observed_petroleum = wide["PET"]
    else:
        observed_petroleum = pd.Series(
            index=wide.index,
            dtype=float,
        )

    overlap_mask = (
        observed_petroleum.notna()
        & petroleum_residual.notna()
    )

    if overlap_mask.any():
        overlap_difference = (
            observed_petroleum.loc[overlap_mask]
            - petroleum_residual.loc[overlap_mask]
        ).abs()

        maximum_overlap_difference = (
            overlap_difference.max()
        )

        if maximum_overlap_difference > TOLERANCE:
            raise ValueError(
                "Observed PET values are inconsistent "
                "with FOS - COW - NG - OOG. "
                "Maximum difference: "
                f"{maximum_overlap_difference:.8f}"
            )

    derivation_mask = (
        observed_petroleum.isna()
        & petroleum_residual.notna()
    )

    derived = (
        petroleum_residual.loc[
            derivation_mask
        ]
        .rename("generation")
        .reset_index()
    )

    if derived.empty:
        return pd.DataFrame(
            columns=[
                *key_columns,
                "fueltypeid",
                "analysis_group",
                "generation",
                "is_derived",
                "derivation_method",
            ]
        )

    derived["fueltypeid"] = "PET"
    derived["analysis_group"] = "Petroleum"
    derived["is_derived"] = True
    derived["derivation_method"] = (
        "FOS - COW - NG - OOG"
    )

    return derived


def build_coverage_report(
    long_df: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize monthly coverage for each analysis group."""

    expected_months = pd.date_range(
        start=long_df["period"].min(),
        end=long_df["period"].max(),
        freq="MS",
    )

    coverage_rows: list[dict] = []

    for group_name, group in long_df.groupby(
        "analysis_group"
    ):
        observed_months = (
            group["period"]
            .drop_duplicates()
        )

        missing_months = (
            expected_months.difference(
                observed_months
            )
        )

        coverage_rows.append(
            {
                "analysis_group": group_name,
                "expected_months": len(
                    expected_months
                ),
                "observed_months": (
                    observed_months.nunique()
                ),
                "missing_months": len(
                    missing_months
                ),
                "missing_periods": ", ".join(
                    month.strftime("%Y-%m")
                    for month in missing_months
                ),
            }
        )

    return (
        pd.DataFrame(coverage_rows)
        .sort_values("analysis_group")
        .reset_index(drop=True)
    )


def build_reconciliation_report(
    generation: pd.DataFrame,
    long_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare selected fuel components with EIA's ALL total."""

    reported_total = (
        generation.loc[
            generation["fueltypeid"].eq("ALL"),
            [
                "period",
                "generation",
            ],
        ]
        .rename(
            columns={
                "generation": "reported_total",
            }
        )
        .drop_duplicates(
            subset=["period"]
        )
    )

    if reported_total.empty:
        raise ValueError(
            "The reported ALL generation series "
            "was not found."
        )

    component_total = (
        long_df
        .groupby(
            "period",
            as_index=False,
        )["generation"]
        .sum(min_count=1)
        .rename(
            columns={
                "generation": "component_total",
            }
        )
    )

    report = reported_total.merge(
        component_total,
        on="period",
        how="outer",
        validate="one_to_one",
    )

    if report[
        [
            "reported_total",
            "component_total",
        ]
    ].isna().any().any():
        incomplete_rows = report.loc[
            report[
                [
                    "reported_total",
                    "component_total",
                ]
            ].isna().any(axis=1)
        ]

        raise ValueError(
            "Some months are missing reported or "
            "component totals:\n"
            f"{incomplete_rows.to_string(index=False)}"
        )

    report["difference"] = (
        report["component_total"]
        - report["reported_total"]
    )

    report["absolute_difference"] = (
        report["difference"].abs()
    )

    report["difference_percent"] = (
        report["difference"]
        / report["reported_total"]
        * 100
    )

    report = (
        report
        .sort_values("period")
        .reset_index(drop=True)
    )

    maximum_difference = report[
        "absolute_difference"
    ].max()

    if maximum_difference > TOLERANCE:
        largest_errors = report.nlargest(
            10,
            "absolute_difference",
        )

        raise ValueError(
            "Selected fuel components do not match "
            "the reported EIA total.\n"
            f"Maximum difference: "
            f"{maximum_difference:.8f}\n\n"
            "Largest discrepancies:\n"
            f"{largest_errors.to_string(index=False)}"
        )

    return report


def build_generation_dataset() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Build clean long and wide generation datasets.

    Returns
    -------
    long_df:
        One row per month and standardized fuel group.

    wide_df:
        One row per month with fuel groups in columns.

    coverage_df:
        Monthly coverage report by fuel group.

    derived_petroleum:
        Audit table for derived PET observations.

    reconciliation_df:
        Comparison of selected components with EIA ALL.
    """

    generation = load_generation_data()
    mapping = load_fuel_mapping()

    merged = generation.merge(
        mapping[
            [
                "fueltypeid",
                "analysis_group",
                "is_reported_total",
                "include_in_mix",
            ]
        ],
        on="fueltypeid",
        how="left",
        validate="many_to_one",
    )

    missing_mapping = (
        merged.loc[
            merged["analysis_group"].isna(),
            "fueltypeid",
        ]
        .drop_duplicates()
        .tolist()
    )

    if missing_mapping:
        raise ValueError(
            "Fuel IDs are missing from the mapping: "
            f"{missing_mapping}"
        )

    included = merged.loc[
        merged["include_in_mix"]
    ].copy()

    if included.empty:
        raise ValueError(
            "No fuel types are marked "
            "include_in_mix=True."
        )

    observed_long = (
        included
        .groupby(
            [
                "period",
                "analysis_group",
            ],
            as_index=False,
        )["generation"]
        .sum(min_count=1)
    )

    derived_petroleum = (
        derive_missing_petroleum(
            generation
        )
    )

    long_parts = [observed_long]

    if not derived_petroleum.empty:
        derived_long = derived_petroleum[
            [
                "period",
                "analysis_group",
                "generation",
            ]
        ].copy()

        long_parts.append(
            derived_long
        )

    long_df = (
        pd.concat(
            long_parts,
            ignore_index=True,
        )
        .groupby(
            [
                "period",
                "analysis_group",
            ],
            as_index=False,
        )["generation"]
        .sum(min_count=1)
        .sort_values(
            [
                "period",
                "analysis_group",
            ]
        )
        .reset_index(drop=True)
    )

    duplicate_mask = long_df.duplicated(
        subset=[
            "period",
            "analysis_group",
        ]
    )

    if duplicate_mask.any():
        raise ValueError(
            "Duplicate month-group observations "
            "remain after aggregation."
        )

    wide_df = (
        long_df
        .pivot(
            index="period",
            columns="analysis_group",
            values="generation",
        )
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )

    wide_df.columns.name = None

    coverage_df = build_coverage_report(
        long_df
    )

    reconciliation_df = (
        build_reconciliation_report(
            generation=generation,
            long_df=long_df,
        )
    )

    return (
        long_df,
        wide_df,
        coverage_df,
        derived_petroleum,
        reconciliation_df,
    )


def main() -> None:
    (
        long_df,
        wide_df,
        coverage_df,
        derived_petroleum,
        reconciliation_df,
    ) = build_generation_dataset()

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    long_path = (
        OUTPUT_DIRECTORY
        / "eia_tx_generation_clean_long.csv"
    )

    wide_path = (
        OUTPUT_DIRECTORY
        / "eia_tx_generation_clean_wide.csv"
    )

    coverage_path = (
        OUTPUT_DIRECTORY
        / "eia_tx_generation_group_coverage.csv"
    )

    derived_path = (
        OUTPUT_DIRECTORY
        / "eia_tx_generation_derived_petroleum.csv"
    )

    reconciliation_path = (
        OUTPUT_DIRECTORY
        / "eia_tx_generation_reconciliation.csv"
    )

    long_df.to_csv(
        long_path,
        index=False,
    )

    wide_df.to_csv(
        wide_path,
        index=False,
    )

    coverage_df.to_csv(
        coverage_path,
        index=False,
    )

    derived_petroleum.to_csv(
        derived_path,
        index=False,
    )

    reconciliation_df.to_csv(
        reconciliation_path,
        index=False,
    )

    maximum_difference = reconciliation_df[
        "absolute_difference"
    ].max()

    print("\nClean long-format generation data:")
    print(
        long_df.head(20).to_string(
            index=False
        )
    )

    print("\nWide-format columns:")
    print(wide_df.columns.tolist())

    print("\nFuel-group coverage:")
    print(
        coverage_df.to_string(
            index=False
        )
    )

    print("\nDerived petroleum observations:")
    if derived_petroleum.empty:
        print("No petroleum observations required derivation.")
    else:
        print(
            derived_petroleum.to_string(
                index=False
            )
        )

    print("\nGeneration reconciliation:")
    print(
        reconciliation_df.head().to_string(
            index=False
        )
    )

    print(
        f"\nNumber of compared months: "
        f"{len(reconciliation_df)}"
    )

    print(
        f"Maximum absolute difference: "
        f"{maximum_difference:.8f}"
    )

    print(
        f"Tolerance: {TOLERANCE}"
    )

    print(
        "\nValidation passed: selected fuel "
        "components reproduce reported total generation."
    )

    print(
        f"\nNumber of long-format rows: "
        f"{len(long_df)}"
    )

    print(
        f"Date range: "
        f"{long_df['period'].min():%Y-%m} to "
        f"{long_df['period'].max():%Y-%m}"
    )

    print(f"\nSaved long data to: {long_path}")
    print(f"Saved wide data to: {wide_path}")
    print(f"Saved coverage report to: {coverage_path}")
    print(f"Saved derivation report to: {derived_path}")
    print(
        f"Saved reconciliation report to: "
        f"{reconciliation_path}"
    )


if __name__ == "__main__":
    main()