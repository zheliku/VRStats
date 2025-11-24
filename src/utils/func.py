import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def insert_blank_rows_by_block(df: pd.DataFrame, block_col: str = "block") -> pd.DataFrame:
    """
    在每个 block 之间插入“空行”（第一列为 ""，其它列为 NA），
    避免 FutureWarning 和 True/False 被转成 0/1 的问题。
    """

    # 1. 构建“伪空行”：（至少有一列是 ""）
    row_data = {col: "" for col in df.columns}

    blank_row = pd.DataFrame([row_data], columns=df.columns)

    # 2. 逐 block 插入 blank_row
    new_rows = []
    for block, sub in df.groupby(block_col):
        new_rows.append(sub)
        new_rows.append(blank_row.copy())

    # 3. concat 不再包含 all-NA DataFrame → 不会有 FutureWarning
    return pd.concat(new_rows, ignore_index=True)


# ---------- 具体检验方法封装（方便扩展/替换） ----------

def independent_ttest(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float, float]:
    """
    Welch t 检验（默认不假定方差齐性）
    返回 (statistic, p_value, effect_size_d)
    """
    t_stat, p_val = stats.ttest_ind(a, b, equal_var=False)

    # 计算 Cohen's d（使用 pooled SD）
    na, nb = len(a), len(b)
    sa, sb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled_sd = np.sqrt(((na - 1) * sa + (nb - 1) * sb) / (na + nb - 2)) if na + nb - 2 > 0 else np.nan
    d = (np.mean(a) - np.mean(b)) / pooled_sd if pooled_sd > 0 else np.nan

    z_val = np.nan  # t 检验不返回 Z 值

    return float(t_stat), float(p_val), float(d), z_val


def mannwhitney_u(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float, float]:
    """
    Mann-Whitney U 检验（两独立样本非参数检验）
    返回 (U_statistic, p_value, rank_biserial_r, Z_value)
    Z 使用连续性校正 + ties 修正
    """
    # --- 原始 SciPy M-W ---
    res = stats.mannwhitneyu(a, b, alternative="two-sided")
    U = float(res.statistic)
    p_val = float(res.pvalue)

    n1, n2 = len(a), len(b)

    # ============================================================
    #            ----------- Z 值计算部分 -----------
    # ============================================================

    # 合并数据并计算秩（用于 tie 修正）
    combined = np.concatenate([a, b])
    N = n1 + n2
    ranks = stats.rankdata(combined)

    # 计算 ties（重复值）
    _, counts = np.unique(combined, return_counts=True)
    tie_term = np.sum(counts ** 3 - counts)

    # 均值 μ_U
    mu_U = n1 * n2 / 2

    # 方差 σ_U²（包含 ties 修正）
    sigma_U_sq = (n1 * n2 / 12) * ((N + 1) - tie_term / (N * (N - 1)))
    sigma_U = np.sqrt(sigma_U_sq)

    # 连续性校正
    if U > mu_U:
        cc = -0.5
    elif U < mu_U:
        cc = +0.5
    else:
        cc = 0.0

    # Z 值
    Z = (U - mu_U + cc) / sigma_U

    # --- Z-based r ---
    r_rb = abs(Z) / np.sqrt(N)

    # print("U:", U, "mu_U:", mu_U, "cc:", cc, "sigma_U:", sigma_U, "Z:", Z, "n1:", n1, "n2:", n2, "r_rb:", r_rb)

    # 返回 4 个值
    return U, p_val, r_rb, float(Z)


# ---------- Holm-Bonferroni 校正 ----------

def holm_bonferroni(p_values: list[float], alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    rejects_holm, pvals_holm_adj, _, _ = multipletests(p_values, alpha=alpha, method="holm")
    return pvals_holm_adj, rejects_holm


# ---------- Benjamini-Hochberg FDR 校正 ----------

def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    rejects_bh, pvals_bh_adj, _, _ = multipletests(p_values, alpha=alpha, method="fdr_bh")
    return pvals_bh_adj, rejects_bh
