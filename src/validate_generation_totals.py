from generation_transform import (
    derive_missing_petroleum,
)

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

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_generation_reconciliation.csv"
)

TOLERANCE = 0.001


def parse_boolean(series: pd.Series) -> pd.Series:
    """Convert common boolean representations."""

    values = (
        series.astype(str)
        .str.strip()
        .str.lower()
    )

    parsed = values.map(
        {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
        }
    )

    if parsed.isna().any():
        invalid = (
            series.loc[parsed.isna()]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            f"Invalid boolean values: {invalid}"
        )

    return parsed.astype(bool)


def build_reconciliation_report() -> pd.DataFrame:
    """Compare selected components with EIA total generation."""

    if not GENERATION_PATH.exists():
        raise FileNotFoundError(
            "Generation data were not found."
        )

    if not MAPPING_PATH.exists():
        raise FileNotFoundError(
            "Fuel mapping was not found."
        )

    generation = pd.read_csv(
        GENERATION_PATH,
        dtype={"fueltypeid": str},
    )

    mapping = pd.read_csv(
        MAPPING_PATH,
        dtype={"fueltypeid": str},
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
            "Invalid dates were found."
        )

    if generation["generation"].isna().any():
        raise ValueError(
            "Invalid generation values were found."
        )

    mapping["include_in_mix"] = parse_boolean(
        mapping["include_in_mix"]
    )

    merged = generation.merge(
        mapping[
            [
                "fueltypeid",
                "include_in_mix",
            ]
        ],
        on="fueltypeid",
        how="left",
        validate="many_to_one",
    )

    if merged["include_in_mix"].isna().any():
        missing_codes = (
            merged.loc[
                merged["include_in_mix"].isna(),
                "fueltypeid",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            f"Fuel codes missing from mapping: "
            f"{missing_codes}"
        )

    selected_components = merged.loc[
        merged["include_in_mix"],
        [
            "period",
            "generation",
        ],
    ].copy()

    derived_petroleum = (
        derive_missing_petroleum(
            generation
        )
    )

    if not derived_petroleum.empty:
        selected_components = pd.concat(
            [
                selected_components,
                derived_petroleum[
                    [
                        "period",
                        "generation",
                    ]
                ],
            ],
            ignore_index=True,
        )

    component_total = (
        selected_components
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
        .drop_duplicates(subset=["period"])
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
        raise ValueError(
            "Some months are missing either reported "
            "or component totals."
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

    return report.sort_values(
        "period"
    ).reset_index(drop=True)


def main() -> None:
    report = build_reconciliation_report()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    maximum_difference = report[
        "absolute_difference"
    ].max()

    print("\nGeneration reconciliation:")
    print(report.head().to_string(index=False))

    print(
        f"\nNumber of compared months: "
        f"{len(report)}"
    )

    print(
        f"Maximum absolute difference: "
        f"{maximum_difference:.8f}"
    )

    print(
        f"Tolerance: {TOLERANCE}"
    )

    if maximum_difference > TOLERANCE:
        largest_errors = (
            report.nlargest(
                10,
                "absolute_difference",
            )
        )

        print("\nLargest discrepancies:")
        print(
            largest_errors.to_string(
                index=False
            )
        )

        raise ValueError(
            "Component totals do not match the "
            "reported EIA total."
        )

    print(
        "\nValidation passed: selected fuel "
        "components reproduce reported total generation."
    )

    print(
        f"Saved reconciliation report to: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()