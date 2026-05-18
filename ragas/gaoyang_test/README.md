# RAGAS 评估工具

对 RAG 系统进行 RAGAS 评估的工具集。

## 📁 文件说明

- `ragas_test_cases_gaoyang_textile.csv` - 测试用例（包含 question, contexts, ground_truths）
- `collect_rag_answers.py` - 收集 RAG 系统答案的脚本
- `ragas_evaluation.py` - 运行 RAGAS 评估的脚本
- `run_ragas_evaluation.py` - 一键运行完整评估流程

## 🚀 快速开始

### 方法 1: 一键运行（推荐）

```bash
# 1. 设置 OpenAI API 密钥（RAGAS评估需要）
export OPENAI_API_KEY='your-openai-api-key'

# 2. 确保 RAG 服务正在运行
# 在项目根目录运行: python main.py

# 3. 运行一键评估脚本
cd tests/ragas/gaoyang_test
python run_ragas_evaluation.py
```

### 方法 2: 分步运行

#### 步骤 1: 收集 RAG 系统答案

```bash
# 确保 RAG 服务正在运行
python main.py

# 在另一个终端运行
cd tests/ragas/gaoyang_test
python collect_rag_answers.py
```

这将:
- 从 `ragas_test_cases_gaoyang_textile.csv` 加载测试用例
- 调用 RAG API 获取每个问题的答案
- 保存结果到 `ragas_test_cases_with_answers.csv`

#### 步骤 2: 运行 RAGAS 评估

```bash
# 设置 OpenAI API 密钥
export OPENAI_API_KEY='your-openai-api-key'

# 运行评估
python ragas_evaluation.py
```

或者指定输入文件:

```bash
python ragas_evaluation.py \
    --input tests/ragas/gaoyang_test/ragas_test_cases_with_answers.csv \
    --output-dir tests/ragas/gaoyang_test/
```

## 📊 评估指标

RAGAS 评估包含以下指标:

| 指标 | 说明 | 范围 |
|------|------|------|
| **faithfulness** | 答案忠实度 - 答案是否完全基于给定的上下文 | 0-1 |
| **answer_relevancy** | 答案相关性 - 答案是否与问题相关 | 0-1 |
| **context_precision** | 上下文精度 - 检索的上下文是否与问题相关 | 0-1 |
| **context_recall** | 上下文召回 - 上下文是否包含 ground truth 的信息 | 0-1 |

## 📁 输出文件

评估完成后，会生成以下文件:

- `ragas_test_cases_with_answers.csv` - 包含 RAG 系统答案的测试用例
- `ragas_evaluation_results.csv` - 详细的评估结果
- `ragas_evaluation_results_summary.json` - 汇总的评估分数

## ⚙️ 配置

### 修改 RAG API 配置

编辑 `collect_rag_answers.py` 中的配置:

```python
BASE_URL = "http://localhost:8000"  # RAG API 地址
TOKEN = "dev_50Fl23ae91R9"           # 认证 Token
MERCHANT_ID = "505"                  # 商家 ID
CUSTOMER_ID_START = 200              # 客户 ID 起始值
```

### 使用其他测试数据

使用 `--input` 参数指定不同的 CSV 文件:

```bash
python ragas_evaluation.py --input /path/to/your/test_data.csv
```

CSV 文件必须包含以下列:
- `question` - 测试问题
- `contexts` - 检索的上下文
- `ground_truths` - 真实答案
- `answer` - RAG 系统生成的答案

## 🔧 故障排除

### 依赖安装

```bash
pip install ragas datasets aiohttp pandas
```

### API 连接失败

确保 RAG 服务正在运行:

```bash
python main.py
```

检查 API 地址和 Token 是否正确。

### OpenAI API 密钥错误

确保设置了正确的环境变量:

```bash
echo $OPENAI_API_KEY
```

### 空答案或错误答案

检查:
1. RAG 服务是否正常运行
2. 商家 ID (505) 是否存在
3. 知识库是否已配置
4. 查看 RAG 服务日志

## 📝 示例输出

```
============================================================
📈 RAGAS评估结果
============================================================

指标得分 (0-1分，越高越好):
----------------------------------------
faithfulness         :  0.856 ████████████████░░ 85.6%
answer_relevancy     :  0.892 █████████████████░ 89.2%
context_precision    :  0.767 ██████████████░░░░ 76.7%
context_recall       :  0.701 ███████████░░░░░░░ 70.1%

详细说明:
----------------------------------------
• faithfulness (忠实度):     答案是否完全基于给定的上下文
• answer_relevancy (相关性): 答案是否与问题相关
• context_precision (精度):  检索的上下文是否与问题相关
• context_recall (召回):     上下文是否包含ground truth的信息
============================================================
```
