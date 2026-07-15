import pandas as pd


def derive_missing_petroleum(
    generation: pd.DataFrame,
) -> pd.DataFrame:
    """
    Derive missing aggregate petroleum generation.

    For months where PET is unavailable, calculate:

        PET = FOS - COW - NG - OOG

    Existing PET observations are never overwritten.
    """

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
            "Required generation columns are missing: "
            f"{sorted(missing_columns)}"
        )

    df = generation.copy()

    df["period"] = pd.to_datetime(
        df["period"],
        errors="coerce",
    )

    df["generation"] = pd.to_numeric(
        df["generation"],
        errors="coerce",
    )

    key_columns = ["period"]

    for optional_column in [
        "location",
        "sectorid",
    ]:
        if optional_column in df.columns:
            key_columns.append(optional_column)

    duplicate_mask = df.duplicated(
        subset=key_columns + ["fueltypeid"]
    )

    if duplicate_mask.any():
        raise ValueError(
            "Duplicate observations prevent "
            "petroleum derivation."
        )

    wide = df.pivot(
        index=key_columns,
        columns="fueltypeid",
        values="generation",
    )

    required_fuel_codes = {
        "FOS",
        "COW",
        "NG",
        "OOG",
    }

    missing_fuel_codes = (
        required_fuel_codes - set(wide.columns)
    )

    if missing_fuel_codes:
        raise ValueError(
            "Cannot derive petroleum because these "
            "fuel codes are missing: "
            f"{sorted(missing_fuel_codes)}"
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

    derived["fueltypeid"] = "PET"

    derived["derivation_method"] = (
        "FOS - COW - NG - OOG"
    )

    derived["is_derived"] = True

    return derived