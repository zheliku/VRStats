"""
两组比较自动分析脚本示例

功能：
1. 从 Excel 中读取数据
2. 对每个变量做描述性统计（按组）
3. 对每个变量做两组的正态性检验（Shapiro-Wilk）
4. 根据正态性结果自动选择：
   - 正态：独立样本 t 检验（Welch 版本，默认不假定方差齐性）
   - 非正态：Mann-Whitney U 检验
5. 对每一“模块”内的所有 p 值做 Holm-Bonferroni 校正
6. 输出结果为 pandas.DataFrame，并打印在控制台
"""

from src.parts import (
    baseline,
    descriptives,
    normality,
    two_group_tests,
)
from src.setting import args

if __name__ == "__main__":
    baseline.main(args)
    descriptives.main(args)
    normality.main(args)
    two_group_tests.main(args)
    print(args)
