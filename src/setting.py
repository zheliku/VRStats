from typing import Dict, List
import argparse
from pathlib import Path
import seaborn as sns
from matplotlib import rcParams


def setup_publication_style():
    """
    设置符合顶级会议论文标准的绘图风格（CHI、IEEE VR等）。
    
    特点：
    - 使用 Times New Roman 字体（学术期刊标准）
    - 支持中文显示（SimHei 黑体）
    - 高分辨率、清晰的线条和边框
    - 适合双栏排版的字号设置
    
    建议在程序入口处调用一次即可。
    """
    # 设置中文字体支持
    rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 中文字体
    rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    # 设置学术论文标准字体
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.size'] = 10
    rcParams['axes.labelsize'] = 10
    rcParams['axes.titlesize'] = 11
    rcParams['xtick.labelsize'] = 9
    rcParams['ytick.labelsize'] = 9
    rcParams['legend.fontsize'] = 9
    
    # 设置线条和边框样式（清晰、专业）
    rcParams['axes.linewidth'] = 1.0
    rcParams['grid.linewidth'] = 0.5
    rcParams['lines.linewidth'] = 1.5
    rcParams['patch.linewidth'] = 1.0
    
    # 设置图形边距和布局
    rcParams['figure.autolayout'] = False
    rcParams['savefig.bbox'] = 'tight'
    rcParams['savefig.pad_inches'] = 0.05
    
    # 设置高质量输出
    rcParams['savefig.dpi'] = 300
    rcParams['figure.dpi'] = 100
    
    # 设置颜色和样式
    sns.set_palette("colorblind")  # 使用色盲友好的配色方案


INPUT_EXCEL_PATH = Path(__file__).parent.parent / "data/Origin.xlsx"  # TODO: 改成你的 Excel 文件路径
OUTPUT_EXCEL_PATH = Path(__file__).parent.parent / "output/Analysis.xlsx"  # TODO: 输出报告文件名
VISUALIZATION_DIR = Path(__file__).parent.parent / "output/visualization"
SHEET_NAME = "Sheet1"  # 可以是 sheet 名，也可以是索引 0,1,...

# 分组信息
GROUP_COL = "Group"  # TODO: 分组变量列名，例如 'group'
GROUP_LABEL_A = "Haptic"  # TODO: 触觉组在 Excel 里的取值
GROUP_LABEL_B = "Gesture"  # TODO: 手势组在 Excel 里的取值

# ========= 基线特征检验（多个卡方变量） =========
BASELINE_CATEGORICAL_VARS = [
    "Age",
    "Gender",
    "VR_Experience",  # 新增
]

# 前测成绩（连续变量 → Welch t）
BASELINE_CONTINUOUS_VARS = [
    "Pre_test",
    "Post_test",
    "Gain",
]

# 正态性检验的 alpha
NORMALITY_ALPHA = 0.05

TEST_FUNC_NAME = "mannwhitney"

# 变量模块（方便分别做校正与汇报）
VARIABLE_BLOCKS: Dict[str, List[str]] = {
    # 问卷量表
    "IEG_Total": [
        "Intrinsic",  # 认知负荷
        "Extraneous",  # 学习动机
        "Germane",  # 沉浸感
        "IEG_Total"
    ],
    "ARCS_Total": [
        "Attention",  # 注意
        "Relevance",  # 相关性
        "Confidence",  # 信心
        "Satisfaction",  # 满意度
        "ARCS_Total"
    ],
    "PIR_Total": [
        "Presence",  # 存在感
        "Involvement",  # 参与度
        "Realism",  # 真实感
        "PIR_Total"
    ],
    # 知识测试
    "Knowledge": [
        "Pre_test",  # 知识测试前测分数
        "Post_test",  # 知识测试后测分数
        "Gain",  # 知识测试提升
    ],
    # EEG 指标（示例）
    "EEG": [
        "Alpha_Fz",
        "Alpha_Cz",
        "Alpha_Pz",
        "Alpha_Oz",
        "Beta_Fz",
        "Beta_Cz",
        "Beta_Pz",
        "Beta_Oz",
        "Theta_Fz",
        "Theta_Cz",
        "Theta_Pz",
        "Theta_Oz",
        # ... 自行补充
    ],
}

parser = argparse.ArgumentParser()  # 不要叫 parse_args
parser.add_argument(
    "--input_excel_path",
    type=Path,
    default=INPUT_EXCEL_PATH,
    help="输入的 Excel 数据文件路径"
)
parser.add_argument(
    "--input_sheet_name",
    type=str,
    default=SHEET_NAME,
    help="输入的 Excel 工作表名称或索引，默认为第一个工作表"
)
parser.add_argument(
    "--group_col",
    type=str,
    default=GROUP_COL,
    help="分组变量列名，例如 '组别'"
)
parser.add_argument(
    "--variable_blocks",
    type=lambda s: eval(s),
    default=VARIABLE_BLOCKS,
    help="变量块字典"
)
parser.add_argument(
    "--output_excel_path",
    type=Path,
    default=OUTPUT_EXCEL_PATH,
    help="输出的 Excel 文件路径"
)
parser.add_argument(
    "--normality_alpha",
    type=float,
    default=NORMALITY_ALPHA,
    help="正态性检验的显著性水平 alpha"
)
parser.add_argument(
    "--group_label_a",
    type=str,
    default=GROUP_LABEL_A,
    help="触觉组在 Excel 里的取值"
)
parser.add_argument(
    "--group_label_b",
    type=str,
    default=GROUP_LABEL_B,
    help="手势组在 Excel 里的取值"
)
parser.add_argument(
    "--test_func_name",
    type=str,
    default="mannwhitney",
    help="两组比较的检验方法，支持 'ttest' 或 'mannwhitney'"
)
parser.add_argument(
    "--baseline_categorical_vars",
    type=eval,
    default=BASELINE_CATEGORICAL_VARS,
    help="基线特征检验的分类变量列表"
)
parser.add_argument(
    "--baseline_continuous_vars",
    type=eval,
    default=BASELINE_CONTINUOUS_VARS,
    help="基线特征检验的连续变量"
)
parser.add_argument(
    "--add_blank_rows",
    type=eval,
    default=True,
    help="是否在输出的描述性统计表中添加空行以区分不同模块"
)
parser.add_argument(
    "--apply_timestamp",
    type=eval,
    default=True,
    help="是否在输出的描述性统计表文件名中添加时间戳"
)
parser.add_argument(
    "--visualization_dir",
    type=Path,
    default=VISUALIZATION_DIR,
    help="可视化结果保存目录"
)


args = parser.parse_args()  # ★★ 关键
