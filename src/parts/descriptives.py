from pathlib import Path
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Any
from ..utils.func import insert_blank_rows_by_block


@dataclass
class DescriptiveStats:
    block: str  # 所属数据模块（例如 IEG_Total / Knowledge / EEG）
    variable: str  # 变量名称（如 'cognitive_load'）
    group: str  # 分组名称（如 '触觉组' 或 '手势组'）

    n: int  # 样本量 n（用于判断统计检验是否足够）
    mean: float  # 均值（适用于正态或近似正态分布）
    std: float  # 标准差（样本标准差，用于衡量离散程度）

    median: float  # 中位数（对偏态分布更稳健）
    q1: float  # 第 1 四分位数（25% 分位，用于描述分布形态）
    q3: float  # 第 3 四分位数（75% 分位，用于描述分布形态）

    minimum: float  # 最小值（用于检测潜在异常值）
    maximum: float  # 最大值（用于检测潜在异常值）


def compute_descriptives(
        df: pd.DataFrame,
        group_col: str,
        variables: list[str],
        block_name: str
) -> list[DescriptiveStats]:
    """按组计算每个变量的描述性统计"""
    results: list[DescriptiveStats] = []

    # 只保留相关列
    sub = df[[group_col] + variables].copy()

    for var in variables:
        for g, g_df in sub.groupby(group_col):
            x = g_df[var].dropna()
            if x.empty:
                continue
            desc = DescriptiveStats(
                block=block_name,
                variable=var,
                group=str(g),
                n=int(x.count()),
                mean=float(x.mean()),
                std=float(x.std(ddof=1)),
                median=float(x.median()),
                q1=float(x.quantile(0.25)),
                q3=float(x.quantile(0.75)),
                minimum=float(x.min()),
                maximum=float(x.max()),
            )
            results.append(desc)

    return results


def process(
        input_excel_path: str | Path,
        input_sheet_name: Any,
        group_col: str,
        variable_blocks: dict[str, list[str]],
        output_excel_path: str | Path,
        add_blank_rows: bool = True,
):
    # 1. 读取数据
    df = pd.read_excel(input_excel_path, sheet_name=input_sheet_name)

    all_desc: list[DescriptiveStats] = []

    # 2~4. 对每个模块依次做描述性统计、正态性检验、两组检验
    for block_name, vars_in_block in variable_blocks.items():
        # 2. 描述性统计
        desc_block = compute_descriptives(df, group_col, vars_in_block, block_name)
        all_desc.extend(desc_block)

    # 6. 转成 DataFrame 方便查看/导出
    desc_df = pd.DataFrame([asdict(d) for d in all_desc])

    if add_blank_rows:
        desc_df = insert_blank_rows_by_block(desc_df, block_col="block")

    # 7. 打印汇总结果（你也可以保存为 Excel）
    print("\n===== 描述性统计（Descriptives） =====")
    print(desc_df.sort_values(["block", "variable", "group"]))

    Path(output_excel_path).parent.mkdir(parents=True, exist_ok=True)

    # 如需保存结果：
    if output_excel_path.exists():
        # 已存在文件 → “覆盖 sheet 或添加 sheet”
        with pd.ExcelWriter(
                output_excel_path,
                mode="a",
                if_sheet_exists="replace"  # 存在表就覆盖，不存在就自动新增
        ) as writer:
            desc_df.to_excel(writer, sheet_name="descriptives", index=False)
    else:
        # 文件不存在 → 创建新文件
        with pd.ExcelWriter(
                output_excel_path,
                mode="w"
        ) as writer:
            desc_df.to_excel(writer, sheet_name="descriptives", index=False)


def main(args: Any):
    process(
        input_excel_path=args.input_excel_path,
        input_sheet_name=args.input_sheet_name,
        group_col=args.group_col,
        variable_blocks=args.variable_blocks,
        output_excel_path=args.output_excel_path,
        add_blank_rows=args.add_blank_rows,
    )

