from pathlib import Path
from scipy import stats

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Any
from ..utils.func import insert_blank_rows_by_block


@dataclass
class NormalityResult:
    block: str  # 所属数据模块（IEG_Total / EEG / Knowledge）
    variable: str  # 变量名称（如 'immersion'）
    group: str  # 分组名称（如 '触觉组' 或 '手势组'）

    stat: float  # Shapiro-Wilk 检验统计量 W
    # W 越接近 1 表示越接近正态分布

    p_value: float  # 正态性检验的 p 值
    # 一般 p < 0.05 表示拒绝正态性假设

    is_normal: bool  # 是否判定为“正态”
    # True: p >= 0.05，视为正态
    # False: p < 0.05，不符合正态性
    # 用于选择 t-test 或 Mann-Whitney U


def check_normality(
        df: pd.DataFrame,
        group_col: str,
        variables: list[str],
        block_name: str,
        alpha: float = 0.05,
) -> list[NormalityResult]:
    """对每个变量，每个组做 Shapiro-Wilk 正态性检验"""
    results: list[NormalityResult] = []

    for var in variables:
        for g, g_df in df.groupby(group_col):
            x = g_df[var].dropna()
            if len(x) < 3:
                # 样本太少，无法可靠检验，这里直接标记为“看作正态”
                stat, p_val = np.nan, np.nan
                is_norm = True
            else:
                stat, p_val = stats.shapiro(x)
                is_norm = bool(p_val > alpha)

            results.append(
                NormalityResult(
                    block=block_name,
                    variable=var,
                    group=str(g),
                    stat=float(stat) if stat is not np.nan else np.nan,
                    p_value=float(p_val) if p_val is not np.nan else np.nan,
                    is_normal=is_norm,
                )
            )

    return results


def process(
        input_excel_path: str | Path,
        input_sheet_name: Any,
        normality_alpha: float,
        group_col: str,
        variable_blocks: dict[str, list[str]],
        output_excel_path: str | Path,
        add_blank_rows: bool = True,
):
    # 1. 读取数据
    df = pd.read_excel(input_excel_path, sheet_name=input_sheet_name)

    all_norm: list[NormalityResult] = []

    # 2~4. 对每个模块依次做描述性统计、正态性检验、两组检验
    for block_name, vars_in_block in variable_blocks.items():
        # 3. 正态性检验
        norm_block = check_normality(df, group_col, vars_in_block, block_name, alpha=normality_alpha)
        all_norm.extend(norm_block)

    # 6. 转成 DataFrame 方便查看/导出
    norm_df = pd.DataFrame([asdict(n) for n in all_norm])

    if add_blank_rows:
        norm_df = insert_blank_rows_by_block(norm_df, block_col="block")

    # 7. 打印汇总结果（你也可以保存为 Excel）
    print("\n===== 正态性检验（Shapiro-Wilk） =====")
    print(norm_df.sort_values(["block", "variable", "group"]))

    # 如需保存结果：
    if output_excel_path.exists():
        # 已存在文件 → “覆盖 sheet 或添加 sheet”
        with pd.ExcelWriter(
                output_excel_path,
                mode="a",
                if_sheet_exists="replace"  # 存在表就覆盖，不存在就自动新增
        ) as writer:
            norm_df.to_excel(writer, sheet_name="normality", index=False)
    else:
        # 文件不存在 → 创建新文件
        with pd.ExcelWriter(
                output_excel_path,
                mode="w"
        ) as writer:
            norm_df.to_excel(writer, sheet_name="normality", index=False)


def main(args: Any):
    process(
        input_excel_path=args.input_excel_path,
        input_sheet_name=args.input_sheet_name,
        normality_alpha=args.normality_alpha,
        group_col=args.group_col,
        variable_blocks=args.variable_blocks,
        output_excel_path=args.output_excel_path,
        add_blank_rows=args.add_blank_rows,
    )
