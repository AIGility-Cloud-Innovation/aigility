"""
RAG 检索效果评估脚本

只测试检索结果，不生成答案。
用于评估优化前后的检索质量对比。

使用方式:
  python rag_retrieval_eval.py --direct             # 直接调用RAGService（推荐）
  python rag_retrieval_eval.py --baseline           # 运行 baseline 评估
  python rag_retrieval_eval.py --optimized          # 运行优化后评估
  python rag_retrieval_eval.py --compare            # 对比 baseline 和优化后
  python rag_retrieval_eval.py --display            # 只查看已有结果
"""

import csv
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# 配置
# ============================================================

@dataclass
class EvalConfig:
    """评估配置"""
    # RAG 系统配置（API模式）
    rag_base_url: str = "http://localhost:8000"
    rag_token: str = "dev_50Fl23ae91R9"
    merchant_id: str = "505"

    # 检索参数
    top_k: int = 5

    # 测试数据路径
    test_data_path: str = "baseline/ragas_test_cases_gaoyang_textile_cn.csv"

    # 结果输出路径
    output_dir: str = "baseline"


# ============================================================
# 检索评估指标（无需LLM）
# ============================================================

def calculate_context_precision(
    retrieved_contexts: List[str],
    question: str,
    ground_truth: str
) -> float:
    """
    计算上下文精度：检索到的内容与问题的相关性
    """
    if not retrieved_contexts:
        return 0.0

    # 将 ground_truth 拆分为关键词
    gt_keywords = set(ground_truth.lower().replace(",", " ").replace("，", " ").split())

    # 检查检索结果中包含多少 ground_truth 关键词
    all_retrieved_text = " ".join(retrieved_contexts).lower()
    matched = sum(1 for kw in gt_keywords if kw in all_retrieved_text)

    if len(gt_keywords) == 0:
        return 0.0

    return matched / len(gt_keywords)


def calculate_context_recall(
    retrieved_contexts: List[str],
    ground_truth: str
) -> float:
    """
    计算上下文召回率：检索结果是否覆盖了标准答案的信息
    """
    if not retrieved_contexts or not ground_truth:
        return 0.0

    # 将 ground_truth 拆分为关键片段
    gt_keywords = set(ground_truth.lower().replace(",", " ").replace("，", " ").split())

    # 检查检索结果中包含多少 ground_truth 关键词
    all_retrieved_text = " ".join(retrieved_contexts).lower()
    matched = sum(1 for kw in gt_keywords if kw in all_retrieved_text)

    if len(gt_keywords) == 0:
        return 0.0

    return matched / len(gt_keywords)


def calculate_hit_rate(
    retrieved_contexts: List[str],
    ground_truth: str
) -> float:
    """
    计算命中率：检索结果中是否包含 ground_truth 的核心信息
    """
    if not retrieved_contexts or not ground_truth:
        return 0.0

    gt_keywords = set(ground_truth.lower().replace(",", " ").replace("，", " ").split())
    all_retrieved_text = " ".join(retrieved_contexts).lower()

    # 只要包含任意一个关键词就算命中
    for kw in gt_keywords:
        if len(kw) > 1 and kw in all_retrieved_text:  # 忽略单字
            return 1.0

    return 0.0


# ============================================================
# RAG 检索调用
# ============================================================

def call_rag_search_direct(
    question: str,
    rag_service,
    top_k: int = 5
) -> List[str]:
    """
    直接调用 RAGService 检索（不通过API）

    Args:
        question: 查询问题
        rag_service: RAGService 实例
        top_k: 返回数量（未使用，使用配置中的值）

    Returns:
        检索到的上下文列表
    """
    try:
        # search() 返回格式化字符串
        result_str = rag_service.search(query=question)

        if not result_str:
            return []

        # 解析返回的文本，按 "--- [引用]" 分割各段
        import re
        # 匹配 "--- [引用] 来源: xxx (片段 N) ---"
        parts = re.split(r'---\s*\[引用\]\s*来源:.*?---', result_str)

        contexts = []
        for part in parts:
            part = part.strip()
            if part and len(part) > 20:  # 过滤太短的内容
                contexts.append(part)

        return contexts if contexts else [result_str] if result_str else []

    except Exception as e:
        print(f"  ⚠️ 检索失败: {e}")
        return []


def call_rag_search_api(
    question: str,
    config: EvalConfig,
    use_optimized: bool = False
) -> List[str]:
    """
    调用 RAG 系统的 API 接口
    """
    import requests

    try:
        endpoint = f"{config.rag_base_url}/api/v1/rag/search"
        payload = {
            "query": question,
            "merchant_id": config.merchant_id,
            "top_k": config.top_k
        }

        headers = {
            "Authorization": f"Bearer {config.rag_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        result = response.json()

        # 提取检索到的上下文
        contexts = []
        if "data" in result and "documents" in result["data"]:
            for doc in result["data"]["documents"]:
                contexts.append(doc.get("content", ""))
        elif "documents" in result:
            for doc in result["documents"]:
                contexts.append(doc.get("content", ""))

        return contexts

    except Exception as e:
        print(f"  ⚠️ 检索失败: {e}")
        return []


# ============================================================
# 评估流程
# ============================================================

@dataclass
class EvalResult:
    """单条评估结果"""
    question: str
    ground_truth: str
    retrieved_contexts: List[str]
    context_precision: float
    context_recall: float
    hit_rate: float
    retrieval_count: int
    retrieval_time_ms: float  # 检索耗时（毫秒）


def run_retrieval_evaluation(
    test_cases: List[Dict[str, str]],
    config: EvalConfig,
    use_optimized: bool = False,
    rag_service=None
) -> List[EvalResult]:
    """
    运行检索评估
    """
    import time

    results = []
    total = len(test_cases)

    mode = "opti_v1" if use_optimized else "Baseline"
    print(f"\n🔍 开始 {mode} 检索评估 (共 {total} 条)...")

    for i, case in enumerate(test_cases):
        question = case["question"]
        ground_truth = case.get("ground_truths", "")

        print(f"  [{i+1}/{total}] {question[:50]}...", end=" ")

        # 计时开始
        start_time = time.time()

        # 调用检索
        if rag_service:
            contexts = call_rag_search_direct(question, rag_service, config.top_k)
        else:
            contexts = call_rag_search_api(question, config, use_optimized)

        # 计时结束
        elapsed_ms = (time.time() - start_time) * 1000

        # 计算指标
        precision = calculate_context_precision(contexts, question, ground_truth)
        recall = calculate_context_recall(contexts, ground_truth)
        hit = calculate_hit_rate(contexts, ground_truth)

        result = EvalResult(
            question=question,
            ground_truth=ground_truth,
            retrieved_contexts=contexts,
            context_precision=precision,
            context_recall=recall,
            hit_rate=hit,
            retrieval_count=len(contexts),
            retrieval_time_ms=elapsed_ms
        )
        results.append(result)

        print(f"P={precision:.2f} R={recall:.2f} H={hit:.2f} T={elapsed_ms:.0f}ms")

    return results


def calculate_summary(results: List[EvalResult]) -> Dict[str, float]:
    """计算汇总指标"""
    if not results:
        return {}

    retrieval_times = [r.retrieval_time_ms for r in results]

    return {
        "context_precision": sum(r.context_precision for r in results) / len(results),
        "context_recall": sum(r.context_recall for r in results) / len(results),
        "hit_rate": sum(r.hit_rate for r in results) / len(results),
        "avg_retrieval_count": sum(r.retrieval_count for r in results) / len(results),
        "avg_retrieval_time_ms": sum(retrieval_times) / len(retrieval_times),
        "min_retrieval_time_ms": min(retrieval_times),
        "max_retrieval_time_ms": max(retrieval_times),
        "total_cases": len(results)
    }


def display_results(
    results: List[EvalResult],
    summary: Dict[str, float],
    mode: str = "Baseline"
):
    """展示评估结果"""
    print("\n" + "=" * 60)
    print(f"📊 {mode} 检索评估结果")
    print("=" * 60)

    print("\n📈 指标得分 (0-1分，越高越好):")
    print("-" * 50)

    metrics = [
        ("context_precision", "上下文精度"),
        ("context_recall", "上下文召回"),
        ("hit_rate", "命中率"),
    ]

    for key, name in metrics:
        score = summary.get(key, 0)
        pct = score * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {name:12s}: {score:6.3f} {bar} {pct:.1f}%")

    print("\n⏱️  检索速度:")
    print("-" * 50)
    print(f"  平均耗时: {summary.get('avg_retrieval_time_ms', 0):.0f} ms")
    print(f"  最快: {summary.get('min_retrieval_time_ms', 0):.0f} ms")
    print(f"  最慢: {summary.get('max_retrieval_time_ms', 0):.0f} ms")

    print(f"\n📊 平均检索数量: {summary.get('avg_retrieval_count', 0):.1f}")
    print(f"📊 总测试用例: {summary.get('total_cases', 0)}")

    print("\n" + "=" * 60)


def save_results(
    results: List[EvalResult],
    summary: Dict[str, float],
    output_path: Path,
    mode: str = "baseline"
):
    """保存评估结果"""
    # 保存详细结果
    detail_path = output_path / f"retrieval_eval_{mode}_details.csv"
    with open(detail_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "question", "ground_truth", "retrieval_count",
            "context_precision", "context_recall", "hit_rate",
            "retrieved_contexts"
        ])
        for r in results:
            writer.writerow([
                r.question, r.ground_truth, r.retrieval_count,
                r.context_precision, r.context_recall, r.hit_rate,
                " || ".join(r.retrieved_contexts[:3])  # 只保存前3个
            ])
    print(f"💾 详细结果: {detail_path}")

    # 保存汇总结果
    summary_path = output_path / f"retrieval_eval_{mode}_summary.json"
    summary["timestamp"] = datetime.now().isoformat()
    summary["mode"] = mode
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"💾 汇总结果: {summary_path}")


# ============================================================
# 对比分析
# ============================================================

def compare_results(
    baseline_path: Path,
    optimized_path: Path
):
    """对比 baseline 和优化后的结果"""
    # 读取汇总结果
    with open(baseline_path, 'r') as f:
        baseline = json.load(f)

    with open(optimized_path, 'r') as f:
        optimized = json.load(f)

    print("\n" + "=" * 70)
    print("📊 Baseline vs 优化后 对比")
    print("=" * 70)

    print(f"\n{'指标':<15} {'Baseline':>10} {'优化后':>10} {'提升':>10} {'提升%':>10}")
    print("-" * 70)

    # 质量指标
    metrics = ["context_precision", "context_recall", "hit_rate"]
    for key in metrics:
        base_val = baseline.get(key, 0)
        opt_val = optimized.get(key, 0)
        diff = opt_val - base_val
        pct = (diff / base_val * 100) if base_val > 0 else 0

        name = {
            "context_precision": "上下文精度",
            "context_recall": "上下文召回",
            "hit_rate": "命中率"
        }.get(key, key)

        print(f"{name:<15} {base_val:>10.3f} {opt_val:>10.3f} {diff:>+10.3f} {pct:>+9.1f}%")

    # 速度指标
    print("-" * 70)
    speed_metrics = ["avg_retrieval_time_ms"]
    for key in speed_metrics:
        base_val = baseline.get(key, 0)
        opt_val = optimized.get(key, 0)
        diff = opt_val - base_val
        pct = (diff / base_val * 100) if base_val > 0 else 0

        print(f"{'平均耗时(ms)':<15} {base_val:>10.0f} {opt_val:>10.0f} {diff:>+10.0f} {pct:>+9.1f}%")

    print("=" * 70)

    # 保存对比结果
    comparison = {
        "baseline": baseline,
        "optimized": optimized,
        "improvement": {
            key: optimized.get(key, 0) - baseline.get(key, 0)
            for key in metrics
        },
        "timestamp": datetime.now().isoformat()
    }

    comparison_path = baseline_path.parent / "retrieval_eval_comparison.json"
    with open(comparison_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    print(f"\n💾 对比结果: {comparison_path}")


# ============================================================
# 初始化 RAGService（直接调用模式）
# ============================================================

def init_rag_service():
    """初始化 RAGService 实例"""
    try:
        from aigility.rag.service import RAGService
        from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig

        # 从 .env 文件读取配置
        from dotenv import load_dotenv
        load_dotenv(project_root / ".env")

        # 使用高阳纺织专用 collection
        config = RAGConfig(
            embedding=EmbeddingConfig(
                provider="zhipuai",
                model_name="embedding-3",
                api_key=os.getenv("ZHIPUAI_API_KEY", ""),
            ),
            vector_store=VectorStoreConfig(
                provider="qdrant",
                collection_name="gaoyang_textile",
                url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            ),
            search_top_k=5,
        )

        service = RAGService(config=config)
        print("✅ RAGService 初始化成功")
        print(f"   Embedding: 智谱AI embedding-3")
        print(f"   Collection: gaoyang_textile")
        return service

    except Exception as e:
        print(f"❌ RAGService 初始化失败: {e}")
        print("\n请确保:")
        print("1. Qdrant 服务正在运行")
        print("2. .env 文件配置正确 (ZHIPUAI_API_KEY)")
        return None


def ensure_knowledge_base(rag_service):
    """确保高阳纺织文档已入库"""
    pdf_path = project_root / "docs" / "高阳纺织 AI创意设计生成 案例测试.pdf"

    if not pdf_path.exists():
        print(f"❌ 文档不存在: {pdf_path}")
        return False
    
    # 检查是否已有数据
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

        

        # 添加文档
        print(f"📦 添加文档: {pdf_path.name}")
        rag_service.clear_knowledge_base()
        result = rag_service.add_file(str(pdf_path), auto_build_bm25=True)
        print(f"✅ 文档添加成功")
        print(f"   文件哈希: {result.get('file_hash', 'N/A')[:16]}...")
        return True

    except Exception as e:
        print(f"❌ 添加文档失败: {e}")
        return False


# ============================================================
# 主程序
# ============================================================

def load_test_cases(csv_path: str) -> List[Dict[str, str]]:
    """加载测试用例"""
    cases = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append({
                "question": row["question"],
                "ground_truths": row.get("ground_truths", ""),
                "contexts": row.get("contexts", "")
            })
    return cases


def main():
    parser = argparse.ArgumentParser(description="RAG 检索效果评估")
    parser.add_argument("--direct", action="store_true", help="直接调用RAGService（推荐）")
    parser.add_argument("--baseline", action="store_true", help="运行 baseline 评估")
    parser.add_argument("--optimized", action="store_true", help="运行优化后评估")
    parser.add_argument("--compare", action="store_true", help="对比 baseline 和优化后")
    parser.add_argument("--display", action="store_true", help="只查看已有结果")
    parser.add_argument("--top-k", type=int, default=5, help="检索返回数量")
    parser.add_argument("--test-file", type=str, help="测试数据文件路径")
    parser.add_argument("--output-dir", type=str, help="结果输出目录（默认: baseline/）")
    args = parser.parse_args()

    # 配置
    config = EvalConfig()
    config.top_k = args.top_k

    # 路径
    script_dir = Path(__file__).parent
    test_file = args.test_file or str(script_dir / config.test_data_path)
    output_dir = script_dir / (args.output_dir or config.output_dir)

    print("\n" + "=" * 60)
    print("📊 RAG 检索效果评估工具")
    print("=" * 60)

    # 加载测试数据
    print(f"\n📂 加载测试数据: {test_file}")
    test_cases = load_test_cases(test_file)
    print(f"✅ 有效测试用例: {len(test_cases)} 条")

    # 只查看模式
    if args.display:
        baseline_summary = script_dir / "baseline" / "retrieval_eval_baseline_summary.json"
        optimized_summary = script_dir / "opti_v1" / "retrieval_eval_opti_v1_summary.json"

        if baseline_summary.exists():
            with open(baseline_summary) as f:
                data = json.load(f)
            print("\n📊 Baseline 结果:")
            for k, v in data.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.3f}")

        if optimized_summary.exists():
            with open(optimized_summary) as f:
                data = json.load(f)
            print("\n📊 优化后结果:")
            for k, v in data.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.3f}")

        if baseline_summary.exists() and optimized_summary.exists():
            compare_results(baseline_summary, optimized_summary)
        return

    # 对比模式
    if args.compare:
        baseline_summary = script_dir / "baseline" / "retrieval_eval_baseline_summary.json"
        optimized_summary = script_dir / "opti_v1" / "retrieval_eval_opti_v1_summary.json"

        if not baseline_summary.exists() or not optimized_summary.exists():
            print("❌ 请先运行 --baseline 和 --optimized 评估")
            return

        compare_results(baseline_summary, optimized_summary)
        return

    # 初始化 RAGService（直接调用模式）
    rag_service = None
    if args.direct or args.baseline or args.optimized:
        print("\n🔧 初始化 RAGService...")
        rag_service = init_rag_service()
        if not rag_service:
            print("❌ 无法初始化 RAGService，请检查配置")
            return

        # 确保知识库已添加文档
        print("\n📦 检查知识库...")
        if not ensure_knowledge_base(rag_service):
            print("❌ 知识库准备失败")
            return

    # 运行评估
    if args.optimized:
        results = run_retrieval_evaluation(test_cases, config, use_optimized=True, rag_service=rag_service)
        summary = calculate_summary(results)
        display_results(results, summary, "opti_v1")
        save_results(results, summary, output_dir, "opti_v1")
    else:
        # 默认运行 baseline
        results = run_retrieval_evaluation(test_cases, config, use_optimized=False, rag_service=rag_service)
        summary = calculate_summary(results)
        display_results(results, summary, "Baseline")
        save_results(results, summary, output_dir, "baseline")

    print("\n✅ 评估完成!")


if __name__ == "__main__":
    main()
