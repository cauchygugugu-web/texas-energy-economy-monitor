from pathlib import Path

import pandas as pd

from fetch_eia import (
    fetch_retail_electricity_prices,
    validate_electricity_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

STATE = "TX"
SECTORS = [
    "RES",
    "COM",
    "IND",
]


def build_texas_price_panel(
    start: str = "2015-01",
    end: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build Texas retail electricity price datasets.

    Returns
    -------
    long_df:
        One row for each month-sector observation.

    wide_df:
        One row for each month, with separate price
        columns for residential, commercial, and
        industrial sectors.
    """

    long_df = fetch_retail_electricity_prices(
        state=STATE,
        sectors=SECTORS,
        start=start,
        end=end,
    )

    validate_electricity_data(
        df=long_df,
        state=STATE,
        sectors=SECTORS,
    )

    wide_df = (
        long_df
        .pivot(
            index="period",
            columns="sectorid",
            values="price",
        )
        .rename(
            columns={
                "RES": "residential_price",
                "COM": "commercial_price",
                "IND": "industrial_price",
            }
        )
        .reset_index()
        .sort_values("period")
        .reset_index(drop=True)
    )

    # 清除 pivot 产生的列索引名称
    wide_df.columns.name = None

    return long_df, wide_df


def main() -> None:
    # 1. 获取长表和宽表
    long_df, wide_df = build_texas_price_panel(
        start="2015-01",
    )

    # 2. 检查三个部门是否缺少月份
    expected_months = pd.date_range(
        start=long_df["period"].min(),
        end=long_df["period"].max(),
        freq="MS",
    )

    for sector in SECTORS:
        sector_months = long_df.loc[
            long_df["sectorid"].eq(sector),
            "period",
        ]

        missing_months = expected_months.difference(
            sector_months
        )

        print(
            f"{sector} missing months: "
            f"{len(missing_months)}"
        )

        if len(missing_months) > 0:
            print(missing_months)

    # 3. 设置输出文件夹
    output_directory = (
        PROJECT_ROOT
        / "data"
        / "processed"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 4. 设置两个 CSV 的保存路径
    long_path = (
        output_directory
        / "eia_tx_retail_prices_long.csv"
    )

    wide_path = (
        output_directory
        / "eia_tx_retail_prices_wide.csv"
    )

    # 5. 保存数据
    long_df.to_csv(
        long_path,
        index=False,
    )

    wide_df.to_csv(
        wide_path,
        index=False,
    )

    # 6. 输出检查结果
    print("\nLong-format data:")
    print(long_df.head(9))

    print("\nWide-format data:")
    print(wide_df.head())

    print(
        f"\nNumber of long-format rows: "
        f"{len(long_df)}"
    )

    print(
        f"Date range: "
        f"{long_df['period'].min():%Y-%m} to "
        f"{long_df['period'].max():%Y-%m}"
    )

    print(
        f"Sectors: "
        f"{sorted(long_df['sectorid'].unique())}"
    )

    print(f"\nSaved long data to: {long_path}")
    print(f"Saved wide data to: {wide_path}")


if __name__ == "__main__":
    main()