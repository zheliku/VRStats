import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Any, Callable
from pathlib import Path
from ..utils.func import (
    independent_ttest,
    mannwhitney_u,
    holm_bonferroni,
    benjamini_hochberg
)
from ..utils.func import insert_blank_rows_by_block


@dataclass
class TestResult:
    block: str  # 所属数据模块（例如 IEG_Total/EEG/Knowledge）
    variable: str  # 被检验的变量名称（如 cognitive_load）
    test_name: str  # 使用的检验方法名称（如 'mannwhitney' 或 'ttest'）
    group_a: str  # 第一组名称（如 '触觉组'）
    group_b: str  # 第二组名称（如 '手势组'）
    n_a: int  # 组 A 的样本量
    n_b: int  # 组 B 的样本量

    statistic: float  # 检验统计量：
    # - t 检验：t 值
    # - M-W 检验：U 值

    z_value: float | None  # 标准化统计量 Z：
    # - 只在 Mann–Whitney U 中计算
    # - 便于报告效应量和推导 p 值
    # - t-test 无 Z，则为 None

    p_value: float  # 原始（未校正）p 值
    # 用于多重比较校正前的显著性判断

    effect_size: float | None  # 效应量：
    # - t-test：Cohen's d
    # - M-W：Z-based r
    # - 若不适用则为 None

    p_holm: float | None  # Holm-Bonferroni 校正后的 p 值
    # 控制 FWER（家族错误率）

    rejects_holm: bool | None  # 在 Holm-Bonferroni 下是否拒绝原假设
    # True=显著差异；False=不显著；None=未计算

    # ----------- 新增 Benjamini-Hochberg FDR 字段 -----------
    p_bh: float | None  # Benjamini-Hochberg FDR 校正后的 p 值（q-value）
    # 控制 FDR（错误发现率）

    rejects_bh: bool | None  # 在 BH-FDR 下是否拒绝原假设
    # True=显著差异；False=不显著；None=未计算


def run_two_group_test(
        df: pd.DataFrame,
        group_col: str,
        variable: str,
        block_name: str,
        group_a: str,
        group_b: str,
        test_func_name: str,
) -> TestResult | None:
    """
    对单个变量做两组比较，自动根据正态性选择检验方法。
    """

    # 取出两组数据
    a = df[df[group_col] == group_a][variable].dropna().to_numpy()
    b = df[df[group_col] == group_b][variable].dropna().to_numpy()

    if len(a) == 0 or len(b) == 0:
        # 有一组没有数据，跳过
        return None

    key_a = (variable, str(group_a))
    key_b = (variable, str(group_b))

    # 选择检验函数
    if test_func_name == "ttest":
        test_func: Callable[[np.ndarray, np.ndarray], tuple[float, float, float, float]] = independent_ttest
    elif test_func_name == "mannwhitney":
        test_func = mannwhitney_u
    else:
        raise ValueError(f"未知的检验方法：{test_func_name}")

    # 检验
    stat, p_val, eff, z_val = test_func(a, b)

    return TestResult(
        block=block_name,
        variable=variable,
        test_name=test_func_name,
        group_a=str(group_a),
        group_b=str(group_b),
        n_a=len(a),
        n_b=len(b),
        statistic=stat,
        p_value=p_val,
        z_value=z_val,
        effect_size=eff,
        p_holm=None,
        rejects_holm=None,
        p_bh=None,
        rejects_bh=None,
    )


def process(
        input_excel_path: str | Path,
        input_sheet_name: Any,
        group_col: str,
        group_label_a: str,
        group_label_b: str,
        test_func_name: str,
        variable_blocks: dict[str, list[str]],
        output_excel_path: str | Path,
        add_blank_rows: bool = True,
):
    # 1. 读取数据
    df = pd.read_excel(input_excel_path, sheet_name=input_sheet_name)

    all_tests: list[TestResult] = []

    # 2~4. 对每个模块依次做描述性统计、正态性检验、两组检验
    for block_name, vars_in_block in variable_blocks.items():
        # 4. 两组比较检验
        tests_block: list[TestResult] = []
        for var in vars_in_block:
            tr = run_two_group_test(
                df,
                group_col=group_col,
                variable=var,
                group_a=group_label_a,
                group_b=group_label_b,
                block_name=block_name,
                test_func_name=test_func_name,
            )
            if tr is not None:
                tests_block.append(tr)

        # 5. Holm-Bonferroni 校正
        if tests_block:
            p_vals = [t.p_value for t in tests_block]
            rejects_holm, pvals_holm_adj = holm_bonferroni(p_vals)
            for t, p_h, rejects_holm in zip(tests_block, rejects_holm, pvals_holm_adj):
                t.p_holm = p_h
                t.rejects_holm = rejects_holm
        else:
            # 不分块校正常见的另一种做法：你也可以在所有 block 结束后一次性校正
            pass

        # 6. BH FDR（Benjamini-Hochberg）
        p_vals = [t.p_value for t in tests_block]
        pvals_bh_adj, rejects_bh = benjamini_hochberg(p_vals)

        for t, pbh, qv in zip(tests_block, pvals_bh_adj, rejects_bh):
            t.p_bh = pbh  # BH 校正的 p
            t.rejects_bh = qv  # BH 是否拒绝原假设

        all_tests.extend(tests_block)

    # 如果你想对所有变量的 p 值一起做 Holm-Bonferroni，可在这里重算：
    # p_vals_all = [t.p_value for t in all_tests]
    # p_adj_all = holm_bonferroni_correction(p_vals_all)
    # for t, p_h in zip(all_tests, p_adj_all):
    #     t.p_holm = p_h

    # 6. 转成 DataFrame 方便查看/导出
    test_df = pd.DataFrame([asdict(t) for t in all_tests])

    if add_blank_rows:
        test_df = insert_blank_rows_by_block(test_df, block_col="block")

    # 7. 打印汇总结果（你也可以保存为 Excel）
    print("\n===== 两组比较检验（Tests） =====")
    print(test_df.sort_values(["block", "variable"]))

    # 如需保存结果：
    if output_excel_path.exists():
        # 已存在文件 → “覆盖 sheet 或添加 sheet”
        with pd.ExcelWriter(
                output_excel_path,
                mode="a",
                if_sheet_exists="replace"  # 存在表就覆盖，不存在就自动新增
        ) as writer:
            test_df.to_excel(writer, sheet_name="tests", index=False)
    else:
        # 文件不存在 → 创建新文件
        with pd.ExcelWriter(
                output_excel_path,
                mode="w"
        ) as writer:
            test_df.to_excel(writer, sheet_name="tests", index=False)


def main(args: Any):
    process(
        input_excel_path=args.input_excel_path,
        input_sheet_name=args.input_sheet_name,
        group_col=args.group_col,
        group_label_a=args.group_label_a,
        group_label_b=args.group_label_b,
        test_func_name=args.test_func_name,
        variable_blocks=args.variable_blocks,
        output_excel_path=args.output_excel_path,
        add_blank_rows=args.add_blank_rows,
    )

