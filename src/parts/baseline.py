import numpy as np
import polars as pl
from scipy.stats import chi2_contingency, ttest_ind
from typing import Any
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
import matplotlib.pyplot as plt


@dataclass
class BaselineTestResult:
    """基线特征检验结果数据类"""
    variable: str  # 变量名（如：年龄、性别、VR使用经验、前测成绩）
    test: str  # 检验方法名称："Chi-square" 或 "Welch t-test"
    stat_name: str  # 统计量名称："chi2" 或 "t"
    stat: float  # 统计量值
    df: float  # 自由度（卡方检验为整数，Welch t 检验为浮点数）
    p_value: float  # 原始 p 值
    effect_size: Optional[float]  # 效应量：卡方检验为 Cramér's V，t 检验为 None
    n_total: Optional[int] = None  # 卡方检验的总样本量
    n_group_a: Optional[int] = None  # t 检验中组 A 的样本量
    n_group_b: Optional[int] = None  # t 检验中组 B 的样本量


def visualize_categorical_variable(
        df: pl.DataFrame,
        group_col: str,
        var: str,
        save_path: Path,
) -> None:
    """
    为分类变量生成分组条形图（符合顶级会议论文标准）。

    参数:
        df: Polars DataFrame
        group_col: 分组变量的列名
        var: 分类变量名称
        save_path: 保存图片的路径
    """
    # 转换为 pandas DataFrame 供绘图使用
    plot_df = df.select([group_col, var]).to_pandas()

    # 创建图形（适合双栏排版的尺寸：3.5英寸宽）
    fig, ax = plt.subplots(figsize=(3.5, 2.8))

    # 计算每组每类别的数量
    count_data = plot_df.groupby([var, group_col]).size().unstack(fill_value=0)

    # 设置颜色方案（色盲友好）
    colors = plt.cm.Set2.colors

    # 绘制分组条形图
    x = np.arange(len(count_data.index))
    width = 0.35
    groups = count_data.columns

    for i, group in enumerate(groups):
        offset = width * (i - len(groups) / 2 + 0.5)
        bars = ax.bar(
            x + offset,
            count_data[group],
            width,
            label=group,
            color=colors[i % len(colors)],
            edgecolor='black',
            linewidth=0.8)
        # 添加数值标签
        ax.bar_label(bars, fmt='%d', padding=2, fontsize=8)

    # 设置标题和标签（学术风格，简洁明了）
    ax.set_xlabel(var, fontweight='normal')
    ax.set_ylabel('Count', fontweight='normal')
    ax.set_title(f'{var}', fontweight='bold', pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(count_data.index)

    # 调整图例（放在最佳位置，避免遮挡数据）
    ax.legend(
        title=group_col,
        frameon=True,
        edgecolor='black',
        fancybox=False,
        shadow=False,
        loc='best'
    )

    # 优化网格线（淡化背景）
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # 调整spine样式
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
        spine.set_color('black')

    # 保存高质量图片
    fig.savefig(save_path, dpi=300, bbox_inches='tight', pad_inches=0.05)
    print(f"[Info] 分类变量可视化已保存: {save_path}")

    # 关闭图形释放内存
    plt.close(fig)


def visualize_continuous_variable(
        df: pl.DataFrame,
        group_col: str,
        var: str,
        save_path: Path,
) -> None:
    """
    为连续变量生成分组小提琴图+箱线图（符合顶级会议论文标准）。

    参数:
        df: Polars DataFrame
        group_col: 分组变量的列名
        var: 连续变量名称
        save_path: 保存图片的路径
    """
    # 转换为 pandas DataFrame
    plot_df = df.select([group_col, var]).to_pandas()

    # 创建图形（适合双栏排版的尺寸）
    fig, ax = plt.subplots(figsize=(3.5, 2.8))

    # 设置颜色方案
    colors = plt.cm.Set2.colors
    groups = plot_df[group_col].unique()

    # 为每组绘制小提琴图
    positions = np.arange(len(groups))
    violin_parts = ax.violinplot(
        [plot_df[plot_df[group_col] == g][var].dropna().values for g in groups],
        positions=positions,
        widths=0.7,
        showmeans=False,
        showmedians=False,
        showextrema=False
    )

    # 设置小提琴图颜色
    for i, pc in enumerate(violin_parts['bodies']):
        pc.set_facecolor(colors[i % len(colors)])
        pc.set_alpha(0.7)
        pc.set_edgecolor('black')
        pc.set_linewidth(1.0)

    # 添加箱线图
    for i, g in enumerate(groups):
        data = plot_df[plot_df[group_col] == g][var].dropna().values
        bp = ax.boxplot([data], positions=[positions[i]], widths=0.15,
                        patch_artist=True, showfliers=False,
                        boxprops=dict(facecolor='white', edgecolor='black', linewidth=1.0),
                        whiskerprops=dict(color='black', linewidth=1.0),
                        capprops=dict(color='black', linewidth=1.0),
                        medianprops=dict(color='red', linewidth=1.5))

    # 添加数据点（使用抖动避免重叠）
    for i, g in enumerate(groups):
        data = plot_df[plot_df[group_col] == g][var].dropna().values
        y = data
        x = np.random.normal(positions[i], 0.04, size=len(y))
        ax.scatter(x, y, alpha=0.4, s=20, color='black')

    # 设置标题和标签（学术风格）
    ax.set_xlabel(group_col, fontweight='normal')
    ax.set_ylabel("Score", fontweight='normal')
    ax.set_title(f'{var}', fontweight='bold', pad=10)
    ax.set_xticks(positions)
    ax.set_xticklabels(groups)

    # 优化网格线
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # 调整spine样式
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
        spine.set_color('black')

    # 保存高质量图片
    fig.savefig(save_path, dpi=300, bbox_inches='tight', pad_inches=0.05)
    print(f"[Info] 连续变量可视化已保存: {save_path}")

    # 关闭图形释放内存
    plt.close(fig)


def run_baseline_tests(
        df: pl.DataFrame,
        group_col: str,
        group_a: str,
        group_b: str,
        categorical_vars: list[str],
        continuous_vars: list[str],
        visualization_dir: Path | None = None,
) -> list[BaselineTestResult]:
    """
    对分类变量和连续变量执行基线特征检验。

    对分类变量使用卡方检验，对连续变量使用 Welch t 检验。
    如果指定了 visualization_dir，会为每个变量生成可视化图表。

    参数:
        df: Polars DataFrame，包含所有变量
        group_col: 分组变量的列名
        group_a: 第一组的标签
        group_b: 第二组的标签
        categorical_vars: 分类变量列表
        continuous_vars: 连续变量列表
        visualization_dir: 可视化图表保存目录（可选）

    返回:
        BaselineTestResult 对象列表
    """
    results: list[BaselineTestResult] = []

    # 创建可视化目录（如果指定）- 放在 baseline 子目录下
    baseline_vis_dir = None
    if visualization_dir is not None:
        baseline_vis_dir = visualization_dir / "baseline"
        baseline_vis_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Info] 基线特征可视化图表将保存到: {baseline_vis_dir}")

    # ----- 1) 分类变量：卡方检验 -----
    for var in categorical_vars:
        if var not in df.columns:
            print(f"[Warning] 分类变量 {var} 不存在，跳过")
            continue

        # 使用 Polars 计算交叉表
        ct_df = df.group_by([group_col, var]).agg(pl.len().alias("count"))
        ct_pivot = ct_df.pivot(var, index=group_col).fill_null(0)
        ct_values = ct_pivot.select(pl.all().exclude(group_col)).to_numpy()

        chi2, p, dof, expected = chi2_contingency(ct_values)

        # Cramér's V
        n = ct_values.sum()
        r, c = ct_values.shape
        if n > 0 and min(r - 1, c - 1) > 0:
            cramers_v = np.sqrt(chi2 / (n * min(r - 1, c - 1)))
        else:
            cramers_v = None

        results.append(
            BaselineTestResult(
                variable=var,
                test="Chi-square",
                stat_name="chi2",
                stat=float(chi2),
                df=float(dof),
                p_value=float(p),
                effect_size=cramers_v,
                n_total=int(n),
            )
        )

        # 生成可视化（如果指定目录）
        if baseline_vis_dir is not None:
            try:
                save_path = baseline_vis_dir / f"categorical_{var}.png"
                visualize_categorical_variable(df, group_col, var, save_path)
            except Exception as e:
                print(f"[Warning] 生成 {var} 可视化时出错: {e}")

    # ----- 2) 连续变量：Welch t 检验 -----
    for var in continuous_vars:
        if var not in df.columns:
            print(f"[Warning] 连续变量 {var} 不存在，跳过")
            continue

        a = df.filter(pl.col(group_col) == group_a).select(
            pl.col(var).drop_nulls().cast(pl.Float64)).to_numpy().flatten()
        b = df.filter(pl.col(group_col) == group_b).select(
            pl.col(var).drop_nulls().cast(pl.Float64)).to_numpy().flatten()

        n1, n2 = len(a), len(b)
        if n1 < 2 or n2 < 2:
            print(f"[Warning] 连续变量 {var} 样本量不足，跳过 Welch t-test")
            continue

        t_res = ttest_ind(a, b, equal_var=False)
        t_stat = float(t_res.statistic)
        p_val = float(t_res.pvalue)

        s1_sq, s2_sq = np.var(a, ddof=1), np.var(b, ddof=1)
        v1, v2 = s1_sq / n1, s2_sq / n2
        df_welch = float((v1 + v2) ** 2 / (v1 ** 2 /
                                           (n1 - 1) + v2 ** 2 / (n2 - 1)))

        results.append(
            BaselineTestResult(
                variable=var,
                test="Welch t-test",
                stat_name="t",
                stat=t_stat,
                df=df_welch,
                p_value=p_val,
                effect_size=None,
                n_group_a=n1,
                n_group_b=n2,
            )
        )

        # 生成可视化（如果指定目录）
        if baseline_vis_dir is not None:
            try:
                save_path = baseline_vis_dir / f"continuous_{var}.png"
                visualize_continuous_variable(df, group_col, var, save_path)
            except Exception as e:
                print(f"[Warning] 生成 {var} 可视化时出错: {e}")

    return results


def process(
        input_excel_path: str | Path,
        input_sheet_name: Any,
        group_col: str,
        group_a: str,
        group_b: str,
        categorical_vars: list[str],
        continuous_vars: list[str],
        visualization_dir: Path | None = None,
) -> tuple[pl.DataFrame, str]:
    """
    基线特征检验的主处理流程。

    从 Excel 读取数据，执行基线特征检验，并返回结果 DataFrame。

    参数:
        input_excel_path: 输入的 Excel 文件路径
        input_sheet_name: 工作表名称或索引
        group_col: 分组变量的列名
        group_a: 第一组的标签
        group_b: 第二组的标签
        categorical_vars: 分类变量列表
        continuous_vars: 连续变量列表

    返回:
        tuple: (结果 DataFrame, sheet名称)
    """
    # 1. 读取数据
    df = pl.read_excel(input_excel_path, sheet_name=input_sheet_name)

    # 2. 运行基线特征检验（包含可视化）
    baseline_results = run_baseline_tests(
        df=df,
        group_col=group_col,
        group_a=group_a,
        group_b=group_b,
        categorical_vars=categorical_vars,
        continuous_vars=continuous_vars,
        visualization_dir=visualization_dir,
    )

    # 3. 转换为 DataFrame并输出
    baseline_df = pl.DataFrame([asdict(r) for r in baseline_results])
    print("\n===== 基线特征检验（年龄 / 性别 / 前测 Welch t） =====")
    print(baseline_df)

    return baseline_df, "baseline"


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
        group_a=args.group_label_a,
        group_b=args.group_label_b,
        categorical_vars=args.baseline_categorical_vars,
        continuous_vars=args.baseline_continuous_vars,
        visualization_dir=args.visualization_dir,
    )
