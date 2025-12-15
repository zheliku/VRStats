from pathlib import Path
import polars as pl
from dataclasses import dataclass, asdict
from typing import Any
from utils.func import insert_blank_rows_by_block
import matplotlib.pyplot as plt
import numpy as np


@dataclass
class DescriptiveStats:
    """描述性统计结果数据类"""
    block: str  # 所属数据模块（例如 IEG_Total / Knowledge / EEG）
    variable: str  # 变量名称（如 'cognitive_load'）
    group: str  # 分组名称（如 '触觉组' 或 '手势组'）

    n: int  # 样本量
    mean: float  # 均值
    std: float  # 样本标准差

    median: float  # 中位数（对偏态分布更稳健）
    q1: float  # 第 1 四分位数（25% 分位）
    q3: float  # 第 3 四分位数（75% 分位）

    minimum: float  # 最小值
    maximum: float  # 最大值


def compute_descriptives(
        df: pl.DataFrame,
        group_col: str,
        variables: list[str],
        block_name: str
) -> list[DescriptiveStats]:
    """
    按组计算每个变量的描述性统计。
    
    参数:
        df: Polars DataFrame，包含所有变量
        group_col: 分组变量的列名
        variables: 需要计算描述性统计的变量列表
        block_name: 所属数据模块名称
    
    返回:
        DescriptiveStats 对象列表
    """
    results: list[DescriptiveStats] = []

    # 只保留相关列
    sub = df.select([group_col] + variables)

    for var in variables:
        for g_df in sub.partition_by(group_col):
            g = g_df[group_col][0]
            x = g_df.select(pl.col(var).drop_nulls())[var]
            if x.is_empty():
                continue
            desc = DescriptiveStats(
                block=block_name,
                variable=var,
                group=str(g),
                n=int(x.len()),
                mean=float(x.mean()), # type: ignore
                std=float(x.std()), # type: ignore
                median=float(x.median()), # type: ignore
                q1=float(x.quantile(0.25)), # type: ignore
                q3=float(x.quantile(0.75)), # type: ignore
                minimum=float(x.min()), # type: ignore
                maximum=float(x.max()), # type: ignore
            )
            results.append(desc)

    return results


def visualize_descriptives(
        df: pl.DataFrame,
        group_col: str,
        variables: list[str],
        block_name: str,
        save_dir: Path,
) -> None:
    """
    为描述性统计结果生成分组对比柱状图（均值±标准误）。
    
    参数:
        df: Polars DataFrame，包含所有变量
        group_col: 分组变量的列名
        variables: 需要可视化的变量列表
        block_name: 所属数据模块名称
        save_dir: 保存图片的目录
    """
    import pandas as pd
    
    # 为每个变量创建一个图表
    for var in variables:
        if var not in df.columns:
            continue
            
        # 计算每组的均值和标准误
        stats_list = []
        for g_df in df.partition_by(group_col):
            g = g_df[group_col][0]
            x = g_df.select(pl.col(var).drop_nulls())[var]
            if x.is_empty():
                continue
            stats_list.append({
                group_col: str(g),
                'mean': float(x.mean()),  # type: ignore
                'sem': float(x.std() / np.sqrt(x.len()))  # type: ignore
            })
        
        if not stats_list:
            continue
            
        plot_df = pd.DataFrame(stats_list)
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(3.5, 2.8))
        
        # 设置颜色方案
        colors = plt.cm.Set2.colors
        
        # 绘制柱状图
        x_pos = np.arange(len(plot_df))
        bars = ax.bar(
            x_pos,
            plot_df['mean'],
            color=[colors[i % len(colors)] for i in range(len(plot_df))],
            edgecolor='black',
            linewidth=0.8,
            alpha=0.8
        )
        
        # 添加误差线（标准误）
        ax.errorbar(
            x_pos,
            plot_df['mean'],
            yerr=plot_df['sem'],
            fmt='none',
            ecolor='black',
            elinewidth=1.5,
            capsize=4,
            capthick=1.5
        )
        
        # 设置标题和标签
        ax.set_xlabel(group_col, fontweight='normal')
        ax.set_ylabel(f'{var} (Mean±SEM)', fontweight='normal')
        ax.set_title(f'{var}组间对比', fontweight='bold', pad=10)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(plot_df[group_col])
        
        # 优化网格线
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)
        
        # 调整spine样式
        for spine in ax.spines.values():
            spine.set_linewidth(1.0)
            spine.set_color('black')
        
        # 保存图片
        save_path = save_dir / f"{var}_comparison.png"
        fig.savefig(save_path, dpi=300, bbox_inches='tight', pad_inches=0.05)
        print(f"[Info] 描述性统计可视化已保存: {save_path}")
        
        plt.close(fig)


def process(
        input_excel_path: str | Path,
        input_sheet_name: Any,
        group_col: str,
        variable_blocks: dict[str, list[str]],
        add_blank_rows: bool = True,
        visualization_dir: Path | None = None,
) -> tuple[pl.DataFrame, str]:
    """
    描述性统计的主处理流程。
    
    从 Excel 读取数据，对每个数据模块计算描述性统计，并返回结果 DataFrame。
    
    参数:
        input_excel_path: 输入的 Excel 文件路径
        input_sheet_name: 工作表名称或索引
        group_col: 分组变量的列名
        variable_blocks: 数据模块字典，键为模块名，值为变量列表
        add_blank_rows: 是否在不同模块间添加空行
        visualization_dir: 可视化图表保存目录（可选）
    
    返回:
        tuple: (结果 DataFrame, sheet名称)
    """
    # 1. 读取数据
    df = pl.read_excel(input_excel_path, sheet_name=input_sheet_name)

    all_desc: list[DescriptiveStats] = []
    
    # 创建可视化目录（如果指定）- 放在 descriptives 子目录下
    desc_vis_dir = None
    if visualization_dir is not None:
        desc_vis_dir = visualization_dir / "descriptives"
        desc_vis_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Info] 描述性统计可视化图表将保存到: {desc_vis_dir}")

    # 2. 对每个模块计算描述性统计
    for block_name, vars_in_block in variable_blocks.items():
        # 计算此模块的描述性统计
        desc_block = compute_descriptives(df, group_col, vars_in_block, block_name)
        all_desc.extend(desc_block)
        
        # 生成可视化（如果指定目录）
        if desc_vis_dir is not None:
            try:
                block_dir = desc_vis_dir / block_name
                block_dir.mkdir(parents=True, exist_ok=True)
                visualize_descriptives(df, group_col, vars_in_block, block_name, block_dir)
            except Exception as e:
                print(f"[Warning] 生成 {block_name} 可视化时出错: {e}")

    # 3. 转换为 DataFrame
    desc_df = pl.DataFrame([asdict(d) for d in all_desc])

    # 4. 添加空行分隔（如果需要）
    if add_blank_rows:
        desc_df = insert_blank_rows_by_block(desc_df, block_col="block")

    # 5. 打印结果
    print("\n===== 描述性统计（Descriptives） =====")
    print(desc_df.sort(["block", "variable", "group"]))

    return desc_df, "descriptives"


def process_with_args(args: Any) -> tuple[pl.DataFrame, str]:
    """
    从命令行参数对象调用 process 函数。
    
    参数:
        args: 包含所有必要参数的对象
    
    返回:
        tuple: (结果 DataFrame, sheet名称)
    """
    return process(
        input_excel_path=args.input_excel_path,
        input_sheet_name=args.input_sheet_name,
        group_col=args.group_col,
        variable_blocks=args.variable_blocks,
        add_blank_rows=args.add_blank_rows,
        visualization_dir=args.visualization_dir,
    )

