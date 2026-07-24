from __future__ import annotations

import importlib
import os
import sys
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import Callable

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = Path(__file__).resolve().parent

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


GENERATION_DOWNLOAD_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eia_tx_generation_by_fuel.csv"
)


REQUIRED_FILES = [
    PROJECT_ROOT / "config" / "fuel_mapping.csv",
    PROJECT_ROOT / "config" / "fred_series.csv",
    PROJECT_ROOT / "config" / "weather_series.csv",
    (
        PROJECT_ROOT
        / "data"
        / "metadata"
        / "generation_sectorid.csv"
    ),
]


def run_preflight_checks() -> None:
    """Check API credentials and required configuration files."""

    load_dotenv(
        PROJECT_ROOT / ".env"
    )

    required_api_keys = [
        "EIA_API_KEY",
        "FRED_API_KEY",
    ]

    missing_api_keys = [
        key
        for key in required_api_keys
        if not os.getenv(key)
    ]

    if missing_api_keys:
        raise RuntimeError(
            "Missing required API keys: "
            f"{missing_api_keys}. "
            "Add them to the project .env file."
        )

    missing_files = [
        path
        for path in REQUIRED_FILES
        if not path.exists()
    ]

    if missing_files:
        formatted_paths = "\n".join(
            f"- {path.relative_to(PROJECT_ROOT)}"
            for path in missing_files
        )

        raise FileNotFoundError(
            "Required configuration or metadata files "
            f"were not found:\n{formatted_paths}"
        )


def run_module_main(
    module_name: str,
) -> None:
    """Import a project module and execute its main function."""

    module = importlib.import_module(
        module_name
    )

    main_function = getattr(
        module,
        "main",
        None,
    )

    if not callable(main_function):
        raise AttributeError(
            f"{module_name}.py does not contain "
            "a callable main() function."
        )

    main_function()


def download_generation_data() -> None:
    """
    Download and save the generation data required by
    build_generation_dataset.py.
    """

    from fetch_generation import (
        fetch_generation_data,
        validate_generation_data,
    )

    generation = fetch_generation_data(
        location="TX",
        start="2015-01",
    )

    validate_generation_data(
        df=generation,
        location="TX",
    )

    GENERATION_DOWNLOAD_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    generation.to_csv(
        GENERATION_DOWNLOAD_PATH,
        index=False,
    )

    print(
        "\nSaved generation download to: "
        f"{GENERATION_DOWNLOAD_PATH}"
    )

    print(
        "Generation observations: "
        f"{len(generation)}"
    )

    print(
        "Generation date range: "
        f"{generation['period'].min():%Y-%m} to "
        f"{generation['period'].max():%Y-%m}"
    )


def run_step(
    step_number: int,
    total_steps: int,
    step_name: str,
    action: Callable[[], None],
) -> None:
    """Execute one pipeline step and report its duration."""

    print("\n" + "=" * 72)

    print(
        f"Step {step_number}/{total_steps}: "
        f"{step_name}"
    )

    print("=" * 72)

    start_time = perf_counter()

    try:
        action()
    except Exception:
        print(
            f"\nPipeline stopped during: "
            f"{step_name}"
        )

        raise

    elapsed_seconds = (
        perf_counter() - start_time
    )

    print(
        f"\nCompleted in "
        f"{elapsed_seconds:.2f} seconds."
    )


def main() -> None:
    """Run the complete Texas energy-and-economy data pipeline."""

    print(
        "Texas Energy & Economy Monitor"
    )

    print(
        "Running preflight checks..."
    )

    run_preflight_checks()

    print(
        "Preflight checks passed."
    )

    steps: list[
        tuple[str, Callable[[], None]]
    ] = [
        (
            "Build retail electricity dataset",
            partial(
                run_module_main,
                "build_retail_dataset",
            ),
        ),
        (
            "Download generation data",
            download_generation_data,
        ),
        (
            "Build clean generation dataset",
            partial(
                run_module_main,
                "build_generation_dataset",
            ),
        ),
        (
            "Build integrated monthly energy dataset",
            partial(
                run_module_main,
                "build_integrated_energy_dataset",
            ),
        ),
        (
            "Build analysis-ready energy indicators",
            partial(
                run_module_main,
                "build_energy_indicators",
            ),
        ),
        (
            "Generate descriptive summaries",
            partial(
                run_module_main,
                "build_descriptive_summary",
            ),
        ),
        (
            "Build time-series features",
            partial(
                run_module_main,
                "build_time_series_features",
            ),
        ),
        (
            "Build FRED dataset",
            partial(
                run_module_main,
                "build_fred_dataset",
            ),
        ),
        (
            "Build energy-and-economy dataset",
            partial(
                run_module_main,
                "build_energy_economy_dataset",
            ),
        ),
        (
            "Build Texas weather dataset",
            partial(
                run_module_main,
                "build_weather_dataset",
            ),
        ),
        (
            "Build final analysis sample",
            partial(
                run_module_main,
                "build_analysis_sample",
            ),
        ),
        (
            "Build variable dictionary",
            partial(
                run_module_main,
                "build_variable_dictionary",
            ),
        ),
    ]

    pipeline_start = perf_counter()
    total_steps = len(steps)

    for step_number, (
        step_name,
        action,
    ) in enumerate(
        steps,
        start=1,
    ):
        run_step(
            step_number=step_number,
            total_steps=total_steps,
            step_name=step_name,
            action=action,
        )

    total_seconds = (
        perf_counter() - pipeline_start
    )

    print("\n" + "=" * 72)

    print(
        "Pipeline completed successfully."
    )

    print(
        f"Total running time: "
        f"{total_seconds:.2f} seconds."
    )

    print("=" * 72)


if __name__ == "__main__":
    main()