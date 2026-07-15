from pathlib import Path
import os

import pandas as pd
import requests
from dotenv import load_dotenv


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 读取项目根目录中的 .env
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("EIA_API_KEY")

BASE_URL = (
    "https://api.eia.gov/v2/"
    "electricity/retail-sales/data/"
)


def fetch_texas_residential_prices() -> pd.DataFrame:
    """Fetch monthly Texas residential electricity prices from EIA."""

    if not API_KEY:
        raise RuntimeError(
            "EIA_API_KEY was not found. "
            "Please add it to the project's .env file."
        )

    params = [
        ("api_key", API_KEY),
        ("frequency", "monthly"),
        ("data[]", "price"),
        ("facets[stateid][]", "TX"),
        ("facets[sectorid][]", "RES"),
        ("start", "2015-01"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", "0"),
        ("length", "5000"),
    ]

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()

    if "response" not in payload:
        raise ValueError(
            f"Unexpected API response: {payload}"
        )

    records = payload["response"].get("data", [])

    if not records:
        raise ValueError("The API returned no observations.")

    df = pd.DataFrame(records)

    # 只保留第一阶段需要的字段
    columns = [
        "period",
        "stateid",
        "stateDescription",
        "sectorid",
        "sectorName",
        "price",
        "price-units",
    ]

    available_columns = [
        column for column in columns
        if column in df.columns
    ]
    df = df[available_columns].copy()

    # 转换数据类型
    df["period"] = pd.to_datetime(
        df["period"],
        format="%Y-%m",
    )
    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce",
    )

    df = (
        df.dropna(subset=["period", "price"])
        .sort_values("period")
        .reset_index(drop=True)
    )

    return df


def main() -> None:
    df = fetch_texas_residential_prices()

    output_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "eia_tx_residential_price.csv"
    )
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_path,
        index=False,
    )

    print(df.head())
    print()
    print(df.tail())
    print()
    print(f"Number of observations: {len(df)}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()