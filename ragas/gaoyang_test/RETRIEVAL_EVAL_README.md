# RAG 检索效果评估工具

专门用于评估 RAG 系统检索结果质量的工具，**不生成答案**，只测试检索效果。

## 🎯 适用场景

- 优化前后的检索质量对比
- 不同检索策略的效果评估
- 快速验证 Small-to-Big、HyDE 等优化的收益

## 📊 评估指标

| 指标 | 说明 | 范围 |
|------|------|------|
| **context_precision** | 上下文精度 - 检索结果与问题的相关性 | 0-1 |
| **context_recall** | 上下文召回 - 检索结果是否覆盖标准答案 | 0-1 |
| **hit_rate** | 命中率 - 检索结果中是否包含标准答案的核心信息 | 0-1 |

## 🚀 快速开始

### 1. 运行 Baseline 评估（当前系统）

```bash
cd ragas/gaoyang_test

# 确保 RAG 服务正在运行
# python main.py

# 运行 baseline 评估
python rag_retrieval_eval.py --baseline
```

### 2. 优化后运行评估

```bash
# 运行优化后的评估
python rag_retrieval_eval.py --optimized
```

### 3. 对比结果

```bash
# 对比 baseline 和优化后
python rag_retrieval_eval.py --compare
```

### 4. 查看结果

```bash
# 只查看已有结果
python rag_retrieval_eval.py --display
```

## 📁 输出文件

| 文件 | 说明 |
|------|------|
| `retrieval_eval_baseline_details.csv` | Baseline 详细结果 |
| `retrieval_eval_baseline_summary.json` | Baseline 汇总指标 |
| `retrieval_eval_optimized_details.csv` | 优化后详细结果 |
| `retrieval_eval_optimized_summary.json` | 优化后汇总指标 |
| `retrieval_eval_comparison.json` | 对比结果 |

## 📋 示例输出

```
============================================================
📊 Baseline 检索评估结果
============================================================

📈 指标得分 (0-1分，越高越好):
--------------------------------------------------
  上下文精度  :  0.720 ██████████████░░░░░░ 72.0%
  上下文召回  :  0.680 █████████████░░░░░░░ 68.0%
  命中率      :  0.850 █████████████████░░░ 85.0%

📊 平均检索数量: 5.0
📊 总测试用例: 30
============================================================

======================================================================
📊 Baseline vs 优化后 对比
======================================================================

指标              Baseline       优化后         提升       提升%
----------------------------------------------------------------------
上下文精度           0.720        0.810     +0.090     +12.5%
上下文召回           0.680        0.790     +0.110     +16.2%
命中率               0.850        0.920     +0.070      +8.2%
======================================================================
```

## 🔧 配置说明

编辑 `rag_retrieval_eval.py` 中的 `EvalConfig` 类：

```python
@dataclass
class EvalConfig:
    # RAG 系统配置
    rag_base_url: str = "http://localhost:8000"
    rag_token: str = "dev_50Fl23ae91R9"
    merchant_id: str = "505"

    # 检索参数
    top_k: int = 5  # 可调整检索数量
```

## 🔄 与优化方案配合使用

### Phase 1: Payload Index + Metadata

```bash
# 1. 建立 baseline
python rag_retrieval_eval.py --baseline

# 2. 实施优化
# ... 建立 Payload Index，补充 Metadata ...

# 3. 验证优化效果
python rag_retrieval_eval.py --optimized
python rag_retrieval_eval.py --compare
```

### Phase 2: Small-to-Big

```bash
# 1. 确保 baseline 已有
python rag_retrieval_eval.py --display

# 2. 实施 Small-to-Big
# ... 实现父子chunk，SQLite存储 ...

# 3. 验证优化效果
python rag_retrieval_eval.py --optimized
python rag_retrieval_eval.py --compare
```

### Phase 3: HyDE（可选）

```bash
# 1. 确保 baseline 已有
python rag_retrieval_eval.py --display

# 2. 实施 HyDE
# ... 实现 HyDE 增强 ...

# 3. 验证优化效果
python rag_retrieval_eval.py --optimized
python rag_retrieval_eval.py --compare
```

## 🛠️ 自定义扩展

### 添加新的评估指标

在 `rag_retrieval_eval.py` 中添加新函数：

```python
def calculate_my_metric(retrieved_contexts, question, ground_truth):
    """自定义评估指标"""
    # 你的计算逻辑
    return score
```

然后在 `run_retrieval_evaluation` 中调用。

### 使用不同的检索接口

修改 `call_rag_search` 函数，适配你的 RAG 系统接口。

## 📝 注意事项

1. **确保 RAG 服务运行**：评估前需要启动 RAG 服务
2. **测试数据格式**：CSV 文件需要包含 `question` 和 `ground_truths` 列
3. **指标解读**：
   - `context_precision` 和 `context_recall` 越高越好
   - `hit_rate` 反映检索的鲁棒性
4. **优化效果**：通常 Small-to-Big 能提升 context_recall，Payload Index 主要提升性能而非指标
