[toc]



# VRStats：两组比较自动统计分析脚本

---

## 1. 项目简介

VRStats 是一个用 Python 写的**两组比较自动统计分析小工具**，主要用于：

- 实验组 vs 控制组
- 触觉反馈 vs 手势交互
- 条件 A vs 条件 B

你只需要：

1. 把实验数据整理成一个 Excel 文件 `all.xlsx`
2. 放到 `data` 文件夹
3. 在终端里跑一条命令

脚本会自动完成：

- 从 Excel 读取数据
- 按组做描述性统计（均值、标准差等）
- 对每个变量做正态性检验（如 Shapiro–Wilk）
- 根据正态性自动选择：
  - 正态：独立样本 t 检验（Welch，默认不假定方差齐性）
  - 非正态：Mann–Whitney U 检验
- 对同一模块里的多个 p 值做 Holm-Bonferroni 校正
- 生成 Markdown 和 Excel 报告，保存在 `output/` 目录

非常适合：心理学实验、HCI/VR 用户研究、教育实验等需要两组比较的情境。

---

## 2. 运行环境与安装

> 下面以 **Windows + PowerShell** 为例（你当前环境）。

### 2.1 必备环境

- 操作系统：
  - Windows 10 / 11
- Python：
  - 推荐 Python 3.11 或 3.12（以你实际安装为准）
- 依赖管理：
  - 本项目使用 [`uv`](https://github.com/astral-sh/uv) 来管理依赖（根据 `pyproject.toml` 和 `uv.lock`）

### 2.2 获取项目代码

如果你已经在 `P:\Python Project\VRStats` 下有代码，可以跳过本小节。

1. 选择一个放项目的文件夹，例如：

   ```powershell
   cd "P:\Python Project"
   ```

2. 使用 Git 克隆（如果项目托管在 GitHub / Gitee 等）：

   ```powershell
   git clone <你的仓库地址> VRStats
   cd "P:\Python Project\VRStats"
   ```

   或者直接把压缩包解压到 `P:\Python Project\VRStats`。

项目根目录结构大致如下：

```text
pyproject.toml
uv.lock
data/
    all.xlsx          # 你的数据文件（需要自己准备）
output/              # 自动生成的报告会放在这里
src/
    main.py           # 主入口脚本
    setting.py        # 参数与路径配置
    parts/
        baseline.py
        descriptives.py
        normality.py
        two_group_tests.py
    utils/
        func.py
```

### 2.3 安装依赖

在项目根目录（和 `pyproject.toml` 同级）执行：

```powershell
cd "P:\Python Project\VRStats"
uv sync
```

- 第一次会自动创建虚拟环境并安装项目所需的库（pandas、scipy 等）。
- 只要 `pyproject.toml` 没变，以后一般不需要重复安装。

你可以简单测试一下环境是否可用：

```powershell
uv run python -c "print('VRStats env OK')"
```

看到 `VRStats env OK` 就说明环境正常。

---

## 3. Excel 数据准备（`data/all.xlsx`）

> **核心：Excel 列名要和配置里的一致，尤其是分组列和指标列。**

### 3.1 文件位置与命名

- 默认数据文件路径：`data/all.xlsx`
- 支持格式：`.xlsx`
- 推荐做法：
  1. 在项目根目录下找到（或创建）`data` 文件夹
  2. 把你的数据文件保存/另存为 `all.xlsx`
  3. 确认路径为：`P:\Python Project\VRStats\data\all.xlsx`

目录示例：

```text
VRStats/
  data/
    all.xlsx
  src/
  output/
```

### 3.2 必要列说明

你的 Excel 应该满足：

- 第一行是**列名（表头）**
- 至少包含以下几类列：

1. **被试 ID 列**（示例：`subject_id`）
   - 每行唯一标识一个被试/样本
   - 例如：`S01`、`S02`、`P001` …

2. **分组变量列**（示例：`group`）
   - 指明该行数据属于哪一组
   - 例如：`haptic` / `gesture`，或 `control` / `experiment`，或 `0` / `1`

3. **一个或多个指标变量列**（比如你要比较的结果指标）
   - 示例：
     - `accuracy`（正确率）
     - `reaction_time`（反应时）
     - `score`（得分）

一个简单的表头示例（仅示意，列名请与实际代码/配置保持一致）：

| subject_id | group   | accuracy | reaction_time |
|-----------:|--------:|---------:|--------------:|
| S01        | haptic  | 0.85     | 350           |
| S02        | gesture | 0.78     | 420           |
| S03        | haptic  | 0.92     | 310           |

**注意：**

- 列名建议使用英文+下划线，避免中文和空格（如果你一定要用中文列名，需要在 `setting.py` 里对应改成中文）。
- 中间不要随便插入空行。
- 一列的数据类型要尽量统一（比如指标列都应该是数值）。

### 3.3 多条件 / 多任务（如有）

如果你的实验有多个任务/场景，也可以在 Excel 里增加一个列来区分，例如：

- 列名：`condition` 或 `task`
- 取值示例：`baseline`、`task1`、`task2` …

是否以及如何使用这个列进行分层分析，取决于你实际在 `setting.py` 和各模块中的配置/代码逻辑，可以按需要扩展。

---

## 4. 代码结构简介

### 4.1 入口脚本：`src/main.py`

核心内容如下：

- 从 `src.parts` 导入四个分析模块：
  - `baseline`
  - `descriptives`
  - `normality`
  - `two_group_tests`
- 从 `src.setting` 导入分析参数 `args`
- 在 `__main__` 中依次调用：

  ```python
  baseline.main(args)
  descriptives.main(args)
  normality.main(args)
  two_group_tests.main(args)
  print(args)
  ```

也就是说，运行一次 `main.py` 会按顺序执行：

1. 基线分析
2. 描述性统计
3. 正态性检验
4. 两组比较（自动选择 t 检验或 Mann-Whitney U 等）

### 4.2 配置：`src/setting.py`

`src/setting.py` 就是**配置中心**，主要负责：

* 告诉程序：Excel 在哪里、Sheet 叫什么、分组列叫什么、各指标列名是什么；
* 把这些配置，做成命令行参数，方便以后用 `--xxx` 临时覆盖。

你主要会改的是**上半部分的一堆常量**，下面的 `parser.add_argument(...)` 一般不用动。

**1) Excel 路径和 Sheet**

* `INPUT_EXCEL_PATH`：输入数据
* `OUTPUT_EXCEL_PATH`：输出结果
* `SHEET_NAME`：Excel 里的工作表

按你的项目结构，通常只要保证：

* `data/all.xlsx` 放的是你的原始数据
* `output/report.xlsx` 是你想生成的报告名字
* 如果只有一个 Sheet，就保持 `SHEET_NAME = 0` 不改

---

**2) 分组信息（两组比较用）**

你现在是用中文列名：

* `GROUP_COL = "组别"`：Excel 里分组那一列的列名，比如这一列的表头写的是 `组别`
* `GROUP_LABEL_A = "触觉组"`：这一列里，表示“触觉组”的文字
* `GROUP_LABEL_B = "手势组"`：这一列里，表示“手势组”的文字

**如果你 Excel 长这样：**

| 组别   | 年龄 | 性别 | Pre\_test | Intrinsic | ...  |
| ------ | ---- | ---- | --------- | --------- | ---- |
| 触觉组 | 20   | 男   | 80        | 5.2       | ...  |
| 手势组 | 22   | 女   | 78        | 4.9       | ...  |

那就完全可以保持现在的配置不动。

如果你 Excel 的列头/取值不一样，比如：

* 列名是 `group`，取值是 `haptic` / `gesture`，就改成：

```python
GROUP_COL = "group"
GROUP_LABEL_A = "haptic"
GROUP_LABEL_B = "gesture"
```

---

**3) 基线特征变量**

**分类变量（卡方）**

`BASELINE_CATEGORICAL_VARS` 是一个列表，里面写的是**需要做卡方检验的分类变量列名**，必须和 Excel 表头一模一样：

* 现在是：
  * `年龄`
  * `性别`
  * `VR使用情况`

如果你 Excel 里这些列叫：

* `Age`、`Gender`、`VR_usage`，就改成：

```python
BASELINE_CATEGORICAL_VARS = [
    "Age",
    "Gender",
    "VR_usage",
]
```

**连续变量（基线 t 检验）**

`BASELINE_CONTINUOUS_VAR = "Pre_test"` 表示：

* 你有一列是前测分数，列名叫 `Pre_test`
* 会做一个组间的 Welch t 检验，看基线是否平衡

如果你的前测列叫 `PreScore`，就改成：

```python
BASELINE_CONTINUOUS_VAR = "PreScore"
```

---

**4) 正态性检验和检验方法**

* `NORMALITY_ALPHA = 0.05`：Shapiro 等正态性检验的显著性水平，一般 0\.05 不用改
* `TEST_FUNC_NAME = "mannwhitney"`：两组比较用什么检验
  * `"ttest"`：独立样本 t 检验
  * `"mannwhitney"`：Mann\-Whitney U 检验（非参数）

如果你数据接近正态、方差齐，可以改成：

```python
TEST_FUNC_NAME = "ttest"
```

---

**5) 指标模块 `VARIABLE_BLOCKS`**

`VARIABLE_BLOCKS` 是一个“字典”，结构大致是：

* 外层 key：模块名（比如 IEG 总分、ARCS 总分、EEG 指标等）
* 内层列表：这一模块下的具体列名（必须和 Excel 表头一致）

你当前的结构是按四类组织的：

* `IEG_Total`：一组问卷条目 \+ 总分
* `ARCS_Total`
* `PIR_Total`
* `Knowledge`
* `EEG`

**如果你只是列名不一样：**

比如 Excel 里：

* 把 `Intrinsic` 改写成 `IEG_Intrinsic`
* 把 `Post_test` 改成 `Knowledge_Post`

那就把列表里的字符串改掉即可，注意不要少逗号、不要多引号。

**如果你想删掉一个模块：**

比如你这次实验没有 EEG 数据，可以直接把 `EEG` 这一整个块删掉：

```python
VARIABLE_BLOCKS: Dict[str, List[str]] = {
    "IEG_Total": [
        "Intrinsic",
        "Extraneous",
        "Germane",
        "IEG_Total"
    ],
    "ARCS_Total": [
        "Attention",
        "Relevance",
        "Confidence",
        "Satisfaction",
        "ARCS_Total"
    ],
    "PIR_Total": [
        "Presence",
        "Involvement",
        "Realism",
        "PIR_Total"
    ],
    "Knowledge": [
        "Pre_test",
        "Post_test",
        "Improvement",
    ],
    # 把 EEG 这一段整个删掉
}
```

**如果你想新加一个模块：**

比如你有一个新问卷 `Flow`，包含 `Flow_Absorption`、`Flow_Enjoyment` 和总分 `Flow_Total`，可以加在字典里：

```python
VARIABLE_BLOCKS: Dict[str, List[str]] = {
    "IEG_Total": [
        "Intrinsic",
        "Extraneous",
        "Germane",
        "IEG_Total"
    ],
    "ARCS_Total": [
        "Attention",
        "Relevance",
        "Confidence",
        "Satisfaction",
        "ARCS_Total"
    ],
    "PIR_Total": [
        "Presence",
        "Involvement",
        "Realism",
        "PIR_Total"
    ],
    "Knowledge": [
        "Pre_test",
        "Post_test",
        "Improvement",
    ],
    "Flow_Total": [
        "Flow_Absorption",
        "Flow_Enjoyment",
        "Flow_Total",
    ],
}
```

---

**6) 输出样式的小开关**

* `add_blank_rows` 参数（在 `parser.add_argument` 部分）：
  * 默认 `True`，会在输出表中模块之间插空行
  * 如果你不想加空行，可以改默认值：

```python
parser.add_argument(
    "--add_blank_rows",
    type=eval,
    default=False,
    help="是否在输出的描述性统计表中添加空行以区分不同模块"
)
```

---

**命令行“临时改配置”**

上面说的是**直接改脚本里的默认值**。

你也可以保持脚本不动，在运行时用参数覆盖，例如：

* 临时用另一个 Excel 文件：

```powershell
uv run -m src.main --input_excel_path data/another.xlsx
```

* 临时换分组列名：

```powershell
uv run -m src.main --group_col 组别2
```

* 临时只跑一个很简单的变量块（示例，注意要能被 `eval` 解析）：

```powershell
uv run -m src.main --variable_blocks "{'Simple': ['Score1', 'Score2']}"
```

### 4.3 工具函数：`src/utils/func.py`

封装一些通用工具，比如各种统计计算和格式化等。

你一般不需要修改这里的代码，除非你想扩展功能。

### 4.4 分析模块：`src/parts/`

> 每个模块通常都有一个 `main(args)` 函数，负责完整跑完该部分分析，并输出结果。

- `baseline.py`：
  - 针对基线（如实验前）的数据进行组间比较，检查两组是否在起点上是可比的。

- `descriptives.py`：
  - 计算各组的均值、标准差、样本量等描述统计量。

- `normality.py`：
  - 对每个指标进行正态性检验（例如 Shapiro–Wilk），结果会影响后面选用哪种检验方法。

- `two_group_tests.py`：
  - 根据前面正态性检验的结果自动选择：
    - 正态：独立样本 t 检验（Welch，默认不假定方差齐）
    - 非正态：Mann–Whitney U 检验等
  - 对多指标/多比较进行 Holm-Bonferroni 校正，控制多重比较带来的第一类错误率。

---

## 5. 使用步骤（一步一步操作指南）

> 假设你的项目路径为：`P:\Python Project\VRStats`

### 5.1 准备好代码和环境

1. 确保目录中已经有本项目代码（`pyproject.toml` 等文件）。
2. 在 PowerShell 中进入项目根目录：

   ```powershell
   cd "P:\Python Project\VRStats"
   ```

3. 安装依赖（只需第一次）：

   ```powershell
   uv sync
   ```

### 5.2 准备 Excel 数据

1. 打开你的原始数据 Excel 文件。
2. 按 **3. Excel 数据准备** 中的要求整理列名和数据：
   - 确保有被试 ID 列
   - 确保有分组列
   - 确保有要分析的指标列
3. 另存为 `all.xlsx`：
   - 位置：`P:\Python Project\VRStats\data\all.xlsx`

### 5.3 检查并修改配置（可选但推荐）

1. 用你熟悉的编辑器（如 VS Code / PyCharm / 记事本）打开：

   - `src/setting.py`

2. 按注释检查和修改：
   - `data` 文件路径是否指向 `data/all.xlsx`
   - `group` 列名是否与你 Excel 表头一致
   - 被试 ID 列名是否一致
   - `VARIABLE_BLOCKS`是否包含你实际想分析的列名

3. 保存文件。

### 5.4 运行主程序

在 **项目根目录** 执行：

```powershell
cd "P:\Python Project\VRStats"
uv run -m src.main
```

- 第一次运行可能会稍慢一些。
- 运行过程中，控制台会输出程序进度或一些信息（取决于你代码里的 `print`）。
- 正常结束后不会报错，`output/` 目录下会生成或更新若干报告文件。

---

## 6. 输出结果（`output/` 目录）

运行成功后，你会在 `output/` 文件夹中看到：

- `report.xlsx`

用 Excel 打开 `report.xlsx`，一般会包含多个工作表（具体以你的代码为准），例如：

- `Descriptives`：描述性统计结果
- `Normality`：每个指标的正态性检验结果
- `Test`：两组比较的 p 值、统计量和效应量

**用途：**

- 方便你在 Excel 中继续做图、筛选、排序
- 可以导入到 SPSS / R / Prism 中做进一步分析

