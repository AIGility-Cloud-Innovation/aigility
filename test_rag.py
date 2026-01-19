#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 参数调优测试脚本

测试不同参数组合（chunk_size、chunk_overlap、top_k）对 RAG 检索效果的影响。
评估指标：精准率、召回率、F1 分数

使用方法:
    python test_rag.py
"""

import os
import sys
import shutil
import time
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass
from itertools import product

# 添加包路径
current_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.join(current_dir, "aigility-python")
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig
from aigility.rag.config import IngestionConfig


# ============================================================
# 测试数据集：问题 + 预期关键词（用于评估检索质量）
# ============================================================
TEST_CASES = [
    {
        "question": "就业前毕业生需要做好哪些准备？",
        "expected_keywords": ["就业前准备", "一个中心", "两份材料", "四个关注", "求职目标", "简历", "就业形势"],
        "min_match": 3
    },
    {
        "question": "毕业生就业一定要选择大城市和风口行业吗？",
        "expected_keywords": ["大城市", "风口行业", "个人专业", "职业发展", "国家战略布局", "新经济形态"],
        "min_match": 3
    },
    {
        "question": "怎样发现适合自己的职业？",
        "expected_keywords": ["适合职业", "职业定位", "长远规划", "专业课程", "就业规划能力", "职业发展目标"],
        "min_match": 2
    },
    {
        "question": "毕业生可以通过哪些渠道收集招聘信息？",
        "expected_keywords": ["招聘信息渠道", "学校途径", "亲友途径", "雇主途径", "政府公共就业服务机构", "社会专业招聘网站"],
        "min_match": 3
    },
    {
        "question": "毕业生的毕业去向主要分为哪几类？",
        "expected_keywords": ["毕业去向", "就业", "升学", "未就业", "协议就业", "自主创业", "灵活就业"],
        "min_match": 3
    },
    {
        "question": "什么是毕业生就业推荐表？",
        "expected_keywords": ["就业推荐表", "学校推荐", "就业资格证明", "加盖公章", "国家计划内毕业生"],
        "min_match": 3
    },
    {
        "question": "什么是就业协议书？",
        "expected_keywords": ["就业协议书", "三方协议", "毕业生", "用人单位", "学校", "户口迁移", "档案转递"],
        "min_match": 3
    },
    {
        "question": "签订就业协议书前应了解哪些事项？",
        "expected_keywords": ["就业协议书", "就业方案", "唯一一份", "档案转递", "信息核对"],
        "min_match": 2
    },
    {
        "question": "签订就业协议书后，毕业生和用人单位的权利、义务及责任包括什么？",
        "expected_keywords": ["就业协议书", "违约责任", "解约证明", "违约金", "就业方案编制"],
        "min_match": 3
    },
    {
        "question": "签订就业协议书时需要注意什么？",
        "expected_keywords": ["就业协议书", "用人单位了解", "违约金", "备注栏", "单位名称与印章一致"],
        "min_match": 3
    },
    {
        "question": "签订就业协议书后不想去该怎么办？",
        "expected_keywords": ["就业协议书违约", "解约手续", "违约金", "解约函", "重新择业"],
        "min_match": 3
    },
    {
        "question": "就业协议书与劳动合同的区别是什么？",
        "expected_keywords": ["就业协议书", "劳动合同", "法律依据", "主体", "内容", "有效期", "法律适用"],
        "min_match": 3
    },
    {
        "question": "毕业生就业过程中发生纠纷该怎么办？",
        "expected_keywords": ["就业纠纷", "上级主管部门申诉", "劳动仲裁", "人力资源社会保障部门举报"],
        "min_match": 2
    },
    {
        "question": "什么是毕业生档案？",
        "expected_keywords": ["档案", "个人身份", "学历", "资历", "工资待遇", "社会保险", "组织关系"],
        "min_match": 3
    },
    {
        "question": "毕业生档案一般包含哪些内容？",
        "expected_keywords": ["毕业生档案", "高中学籍材料", "高考招生材料", "大学学籍变动材料", "奖惩材料", "毕业生登记表"],
        "min_match": 3
    },
    {
        "question": "应届生毕业后档案有哪些去处？",
        "expected_keywords": ["应届生档案去向", "用人单位档案管理部门", "公共就业人才服务机构", "户籍地", "升学学校"],
        "min_match": 3
    },
    {
        "question": "什么是毕业生户口迁移？",
        "expected_keywords": ["户口迁移", "户口迁移证", "公安机关", "迁入地", "有效期"],
        "min_match": 2
    },
    {
        "question": "什么是户口迁移证？",
        "expected_keywords": ["户口迁移证", "户口迁出地公安机关", "迁入地申报入户", "有效期", "遗失处理"],
        "min_match": 3
    },
    {
        "question": "毕业生的户口和档案是如何转迁的？",
        "expected_keywords": ["户口转迁", "档案转迁", "就业方案", "公安机关", "档案管理部门", "人才机构"],
        "min_match": 3
    },
    {
        "question": "用人单位不能接收户口和档案的毕业生，如何办理就业手续？",
        "expected_keywords": ["不接收户口档案", "劳动合同复印件", "录用证明", "人力资源公共服务中心", "生源地"],
        "min_match": 2
    },
    {
        "question": "未就业毕业生如何办理户口和档案转迁手续？",
        "expected_keywords": ["未就业毕业生", "户口转迁", "档案转迁", "生源地", "人力资源公共服务中心"],
        "min_match": 2
    },
    {
        "question": "考研或保研的毕业生如何转迁档案？",
        "expected_keywords": ["考研", "保研", "档案转迁", "调档函", "档案管理部门", "对方院校"],
        "min_match": 3
    },
    {
        "question": "出国留学的毕业生如何办理户口和档案转迁手续？",
        "expected_keywords": ["出国留学", "户口转迁", "档案转迁", "生源地", "就业单位落实后重新办理"],
        "min_match": 2
    },
    {
        "question": "毕业生户口和档案转迁时可以分离吗？",
        "expected_keywords": ["户口档案分离", "升学学校", "生源地", "落户限制城市", "用人单位不解决户口"],
        "min_match": 2
    },
    {
        "question": "非京籍生源拿到北京三年落户指标后，如何办理户口和档案转迁手续？",
        "expected_keywords": ["非京籍生源", "北京三年落户指标", "档案转递", "用人单位", "户口迁回原籍"],
        "min_match": 3
    },
    {
        "question": "毕业生档案存放是否收取费用？",
        "expected_keywords": ["档案存放", "免费", "人事关系保管费", "档案转递费", "公共就业和人才服务机构"],
        "min_match": 2
    },
    {
        "question": "毕业生如何查询自己的档案存放在哪里？",
        "expected_keywords": ["档案查询", "全国人社政务服务平台", "户籍地公共就业人才服务机构", "存档情况", "注册查询"],
        "min_match": 2
    },
    {
        "question": "毕业生档案遗失该怎么办？",
        "expected_keywords": ["档案遗失", "毕业学校咨询", "生源地人社局", "档案遗失证明", "材料补办"],
        "min_match": 2
    },
    {
        "question": "地方人才引进政策对毕业生就业有什么影响？",
        "expected_keywords": ["人才引进政策", "先落户后就业", "人力资源和社会保障局", "接收函", "就业手续办理"],
        "min_match": 2
    },
    {
        "question": "什么是党员组织关系？",
        "expected_keywords": ["党员组织关系", "基层组织隶属关系", "支部", "固定工作单位党组织", "公共就业人才服务机构党组织"],
        "min_match": 3
    },
    {
        "question": "已落实工作单位的毕业生党员，组织关系应如何转移？",
        "expected_keywords": ["毕业生党员", "组织关系转移", "工作单位党组织", "街道乡镇党组织", "公共就业和人才服务机构党组织"],
        "min_match": 3
    },
    {
        "question": "毕业生离校时如何办理党组织关系转接？",
        "expected_keywords": ["党组织关系转接", "党员E先锋系统", "纸质介绍信", "党支部", "组织关系与户口档案分离"],
        "min_match": 2
    },
    {
        "question": "什么是团员档案和团组织关系？",
        "expected_keywords": ["团员档案", "入团志愿书", "团员证", "团组织关系", "基层组织转移", "团费交纳"],
        "min_match": 3
    },
    {
        "question": "已落实工作单位的毕业生团员，团组织关系应转至哪里？",
        "expected_keywords": ["毕业生团员", "团组织关系", "工作单位团组织", "乡镇街道团组织", "经常居住地团组织"],
        "min_match": 2
    },
    {
        "question": "为什么毕业生就业要签订劳动合同？",
        "expected_keywords": ["劳动合同", "劳动关系确立", "权利义务", "劳动争议证明", "工资标准", "工作时间"],
        "min_match": 3
    },
    {
        "question": "劳动合同应在什么时间签订？",
        "expected_keywords": ["劳动合同签订时间", "入职之日起1个月", "双倍工资", "无固定期限劳动合同", "用工之日"],
        "min_match": 2
    },
    {
        "question": "劳动合同主要有哪些类型？",
        "expected_keywords": ["劳动合同类型", "固定期限劳动合同", "无固定期限劳动合同", "以完成一定工作任务为期限的劳动合同"],
        "min_match": 2
    },
    {
        "question": "劳动合同何时生效？",
        "expected_keywords": ["劳动合同生效", "签字盖章", "约定生效时间", "约定生效条件", "劳动关系建立"],
        "min_match": 2
    },
    {
        "question": "劳动合同的必备条款有哪些？",
        "expected_keywords": ["劳动合同必备条款", "用人单位信息", "劳动者信息", "工作内容", "工作地点", "劳动报酬", "社会保险"],
        "min_match": 3
    },
    {
        "question": "什么是五险一金？",
        "expected_keywords": ["五险一金", "社会保险", "住房公积金", "养老保险", "医疗保险", "失业保险", "工伤保险", "生育保险"],
        "min_match": 3
    },
    {
        "question": "毕业生在试用期是否享有五险一金？",
        "expected_keywords": ["试用期", "五险一金", "入职30日内", "缴纳手续", "待遇不变"],
        "min_match": 2
    },
    {
        "question": "劳动者需要自己留存劳动合同吗？",
        "expected_keywords": ["劳动合同留存", "各执一份", "维权依据", "劳动保障监察部门投诉", "合同文本"],
        "min_match": 2
    },
    {
        "question": "毕业生可以签订电子劳动合同吗？",
        "expected_keywords": ["电子劳动合同", "电子签名法", "数据电文", "可靠电子签名", "法律效力"],
        "min_match": 3
    },
    {
        "question": "劳动合同丢失了该怎么办？",
        "expected_keywords": ["劳动合同丢失", "复印用人单位保存文本", "重新订立", "签字盖章"],
        "min_match": 2
    },
    {
        "question": "用人单位可以扣押劳动者的身份证等证件吗？",
        "expected_keywords": ["用人单位", "扣押证件", "身份证", "学历证书", "劳动合同法第九条"],
        "min_match": 2
    },
    {
        "question": "离职后，劳动者需要将劳动合同交还给用人单位吗？",
        "expected_keywords": ["离职", "劳动合同", "各执一份", "无需交还", "劳动合同法第十六条"],
        "min_match": 2
    },
    {
        "question": "劳动合同中关于试用期的规定有哪些？",
        "expected_keywords": ["试用期", "合同期限", "试用期时长", "三个月以下合同无试用期", "非全日制用工无试用期"],
        "min_match": 3
    },
    {
        "question": "试用期工资应该如何计算？",
        "expected_keywords": ["试用期工资", "本单位相同岗位最低档工资80%", "劳动合同约定工资80%", "用人单位所在地最低工资标准"],
        "min_match": 2
    },
    {
        "question": "毕业生进行职业选择时，可参考哪些关键标准？",
        "expected_keywords": ["职业选择", "兴趣要素", "发展前景", "收入潜力", "适配生活方式", "入职门槛"],
        "min_match": 3
    }
]


@dataclass
class EvalResult:
    """评估结果"""
    question: str
    retrieved_text: str
    matched_keywords: List[str]
    total_keywords: int
    precision: float  # 匹配的关键词数 / 检索文本中的关键词数
    recall: float     # 匹配的关键词数 / 预期关键词总数
    is_hit: bool      # 是否达到最小匹配数


@dataclass 
class ParamResult:
    """参数组合的测试结果"""
    chunk_size: int
    chunk_overlap: int
    top_k: int
    avg_precision: float
    avg_recall: float
    hit_rate: float  # 命中率 = 命中的问题数 / 总问题数
    f1_score: float
    total_time: float
    total_chunks: int


def evaluate_single_query(
    question: str,
    expected_keywords: List[str],
    min_match: int,
    retrieved_text: str
) -> EvalResult:
    """评估单个查询的检索结果"""
    
    # 统计匹配的关键词
    matched = []
    retrieved_lower = retrieved_text.lower()
    
    for kw in expected_keywords:
        if kw.lower() in retrieved_lower:
            matched.append(kw)
    
    # 计算指标
    num_matched = len(matched)
    num_expected = len(expected_keywords)
    
    # 召回率 = 匹配数 / 预期关键词数
    recall = num_matched / num_expected if num_expected > 0 else 0
    
    # 精准率 = 匹配数 / min(预期数, 实际检索到的内容相关性)
    # 这里简化为：匹配数 / 预期数（因为我们没有标注检索结果中的所有关键词）
    precision = recall  # 简化处理
    
    # 是否命中
    is_hit = num_matched >= min_match
    
    return EvalResult(
        question=question,
        retrieved_text=retrieved_text[:200] + "..." if len(retrieved_text) > 200 else retrieved_text,
        matched_keywords=matched,
        total_keywords=num_expected,
        precision=precision,
        recall=recall,
        is_hit=is_hit
    )


def run_test_with_params(
    test_file: str,
    chunk_size: int,
    chunk_overlap: int,
    top_k: int,
    db_path: str
) -> ParamResult:
    """使用指定参数运行测试"""
    
    # 清理旧数据库
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    # 创建配置
    config = RAGConfig(
        embedding=EmbeddingConfig(
            provider="huggingface",
            model_name="BAAI/bge-small-zh-v1.5",
            kwargs={"model_kwargs": {"device": "cpu"}}
        ),
        vector_store=VectorStoreConfig(
            provider="chroma",
            collection_name="test_eval",
            persist_path=db_path
        ),
        ingestion=IngestionConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
        search_top_k=top_k
    )
    
    # 初始化服务
    start_time = time.time()
    service = RAGService(config=config)
    
    # 添加测试文件
    service.add_file(test_file)
    indexing_time = time.time() - start_time
    
    # 获取 chunk 数量
    doc_meta = service.get_all_doc_meta().get(os.path.basename(test_file), {})
    total_chunks = doc_meta.get("chunk_count", 0)
    
    # 评估每个测试问题
    results = []
    query_start = time.time()
    
    for case in TEST_CASES:
        retrieved = service.search(case["question"])
        result = evaluate_single_query(
            question=case["question"],
            expected_keywords=case["expected_keywords"],
            min_match=case["min_match"],
            retrieved_text=retrieved
        )
        results.append(result)
    
    query_time = time.time() - query_start
    total_time = indexing_time + query_time
    
    # 计算汇总指标
    avg_precision = sum(r.precision for r in results) / len(results)
    avg_recall = sum(r.recall for r in results) / len(results)
    hit_count = sum(1 for r in results if r.is_hit)
    hit_rate = hit_count / len(results)
    
    # F1 分数
    if avg_precision + avg_recall > 0:
        f1_score = 2 * avg_precision * avg_recall / (avg_precision + avg_recall)
    else:
        f1_score = 0
    
    return ParamResult(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        avg_precision=avg_precision,
        avg_recall=avg_recall,
        hit_rate=hit_rate,
        f1_score=f1_score,
        total_time=total_time,
        total_chunks=total_chunks
    )


def print_result_table(results: List[ParamResult]):
    """打印结果表格"""
    print("\n" + "=" * 100)
    print("📊 RAG 参数调优测试结果")
    print("=" * 100)
    
    # 表头
    print(f"{'chunk_size':>12} | {'overlap':>8} | {'top_k':>6} | {'精准率':>8} | {'召回率':>8} | {'命中率':>8} | {'F1':>8} | {'耗时(s)':>8} | {'chunks':>8}")
    print("-" * 100)
    
    # 按 F1 分数排序
    sorted_results = sorted(results, key=lambda x: x.f1_score, reverse=True)
    
    for r in sorted_results:
        print(f"{r.chunk_size:>12} | {r.chunk_overlap:>8} | {r.top_k:>6} | {r.avg_precision:>8.2%} | {r.avg_recall:>8.2%} | {r.hit_rate:>8.2%} | {r.f1_score:>8.3f} | {r.total_time:>8.2f} | {r.total_chunks:>8}")
    
    print("=" * 100)
    
    # 最优参数
    best = sorted_results[0]
    print(f"\n🏆 最优参数组合:")
    print(f"   chunk_size={best.chunk_size}, chunk_overlap={best.chunk_overlap}, top_k={best.top_k}")
    print(f"   F1={best.f1_score:.3f}, 召回率={best.avg_recall:.2%}, 命中率={best.hit_rate:.2%}")


def main():
    """主函数"""
    print("=" * 60)
    print("🧪 RAG 参数调优测试")
    print("=" * 60)
    
    # 测试文件
    test_file = os.path.join(current_dir, "test.pdf")
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print(f"📄 测试文件: {test_file}")
    print(f"📝 测试问题数: {len(TEST_CASES)}")
    
    # 参数组合
    chunk_sizes = [300, 500, 800]
    chunk_overlaps = [50, 100, 150]
    top_ks = [3, 5, 10]
    
    # 生成所有参数组合
    param_combinations = list(product(chunk_sizes, chunk_overlaps, top_ks))
    print(f"🔧 参数组合数: {len(param_combinations)}")
    
    print("\n开始测试...\n")
    
    results = []
    db_base_path = os.path.join(current_dir, "test_eval_db")
    
    for i, (chunk_size, chunk_overlap, top_k) in enumerate(param_combinations):
        print(f"[{i+1}/{len(param_combinations)}] 测试: chunk_size={chunk_size}, overlap={chunk_overlap}, top_k={top_k}")
        
        db_path = f"{db_base_path}_{chunk_size}_{chunk_overlap}_{top_k}"
        
        try:
            result = run_test_with_params(
                test_file=test_file,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                top_k=top_k,
                db_path=db_path
            )
            results.append(result)
            print(f"   ✅ 完成 - F1={result.f1_score:.3f}, 召回率={result.avg_recall:.2%}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        # 清理临时数据库
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
    
    # 打印结果
    if results:
        print_result_table(results)
        
        # 保存结果到 JSON
        output_file = os.path.join(current_dir, "rag_test_results.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([{
                "chunk_size": r.chunk_size,
                "chunk_overlap": r.chunk_overlap,
                "top_k": r.top_k,
                "precision": r.avg_precision,
                "recall": r.avg_recall,
                "hit_rate": r.hit_rate,
                "f1_score": r.f1_score,
                "time": r.total_time
            } for r in results], f, indent=2, ensure_ascii=False)
        print(f"\n📁 结果已保存到: {output_file}")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    main()

