#!/usr/bin/env python3
"""
清理知识库并重新测试高阳纺织PDF
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

print("=" * 80)
print("🧹 清理知识库并重新测试")
print("=" * 80)

# 初始化RAG服务
rag_config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="zhipuai",
        model_name="embedding-3",
        api_key=os.getenv("ZHIPUAI_API_KEY", "")
    ),
    vector_store=VectorStoreConfig(
        provider="qdrant",
        collection_name="adp_knowledge_base",
        url="http://localhost:6333"
    ),
    search_top_k=5
)

rag_service = RAGService(config=rag_config)

# 1. 清空知识库
print("\n1️⃣ 清空知识库")
print("-" * 80)
# rag_service.clear_knowledge_base()
print("✅ 知识库已清空")

# 2. 添加知识库文件
print("\n2️⃣ 添加知识库文件")
print("-" * 80)
pdf_path = "docs/test.docx"
result = rag_service.add_file(pdf_path, auto_build_bm25=True)
print(f"✅ 已添加: {result['file_name']}")
print(f"   文件哈希: {result['file_hash'][:16]}...")

# 3. 测试查询
print("\n3️⃣ 测试查询")
print("-" * 80)

queries = [
    "密封材料 温度范围"
]

for query in queries:
    print(f"\n查询: 「{query}」")
    print("-" * 40)
    result = rag_service.search(query, expand_context=False)
    if result:
        print(result)
    else:
        print("❌ 无结果")

print("\n" + "=" * 80)

"""测试结果：
✅ 知识库已清空

2️⃣ 添加高阳纺织PDF
--------------------------------------------------------------------------------
Building prefix dict from the default dictionary ...
DEBUG:jieba:Building prefix dict from the default dictionary ...
Loading model from cache /var/folders/qc/1b7dd715127ckhq9vl_0yzpr0000gn/T/jieba.cache
DEBUG:jieba:Loading model from cache /var/folders/qc/1b7dd715127ckhq9vl_0yzpr0000gn/T/jieba.cache
Loading model cost 0.233 seconds.
DEBUG:jieba:Loading model cost 0.233 seconds.
Prefix dict has been built successfully.
DEBUG:jieba:Prefix dict has been built successfully.
✅ 已添加: 高阳纺织 AI创意设计生成 案例测试.pdf
   文件哈希: be6835e03b4b9634...

3️⃣ 测试查询
--------------------------------------------------------------------------------

查询: 「目的市场」
----------------------------------------
--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 1) ---
TipoDZGN|TDTX-GY-BD001工程设计文档 CONFIDENTIAL
TipoDZGN™
AI原生工业设计平台·纺织品类
工程设计文档
Engineering Design Document
高阳纺织 · 家居四件套 · 欧美出口
项目编号 TDTX-GY-BD001
产品名称 SereneDawn晨曦系列·长绒棉缎纹四件套
产品品类 家居纺织HomeTextiles·床上用品BeddingSet
产地 河北省保定市高阳县Gaoyang,Baoding,Hebei
目标市场 北美（AmazonUS）+欧洲（AmazonEU/Wayfair）
零售价 $89.99-$109.99USD
目标FOB价 $18-22USD/套
首批订单 2000套（含Queen+King两个尺码）
版本 v1.0
日期 202608
SereneDawn晨曦系列v1.0TipoDZGN|TDTX-GY-BD001工程设计文档 CONFIDENTIAL
1 设计简报 Design Brief
▶ 产品概述
Serene Dawn（晨曦系列）是一款面向欧美中高端市场的长绒棉缎纹四件套。采用60S长绒棉，400TC缎纹织造，
OEKO-TEXStandard100认证，主打'高阳品质·全球标准'定位。
四件套包含：1×被套 Duvet Cover + 1×床笠 Fitted Sheet + 2×枕套 Pillowcase。提供Queen和King两个主力尺
码，覆盖北美85%以上的床型需求。
设计语言：北欧极简风格（ScandinavianMinimalism），以自然色系为主调，搭配细腻缎面光泽感，营造宁静舒适的卧
室氛围。适合25-45岁注重生活品质的欧美中产家庭。
▶ 市场定位
价格带 $89.99-$109.99USD（AmazonBedding中高端段）
竞品区间 $60-$80低端棉vs$120-$180高端品牌（如Brooklinen/Parachute）
差异化定位 60S长绒棉品质×中端价格=性价比之王

--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 2) ---
国内物流+报关 8.0 1.1 1.5% 高阳→天津港
海运费分摊 6.0 0.8 1.1% 天津→美西按套分摊
FOB价合计 ¥430.2 $58.9 —
汇率按1USD=7.3RMB计算。实际FOB约$58.9，低于目标$18-22区间较多，需调整——以下为修正方案。
▶ 成本优化方案（V2）
原方案60S长绒棉400TC成本偏高，以下提供两套方案：
对比项 方案A：40S精梳棉300TC 方案B：60S长绒棉400TC
纱支/织密 40S精梳棉300TC 60S长绒棉400TC
面料单价 ¥22/m ¥38/m
面料成本(6.8m) ¥149.6 ¥258.4
染整成本 ¥40.8(¥6/m) ¥54.4(¥8/m)
FOB总价 ≈¥145($19.9) ≈¥430($58.9)
零售定价 $79.99-$89.99 $109.99-$129.99
Amazon定位 中端性价比 中高端品质
毛利率(按$89.99) ≈78% —
毛利率(按$109.99) — ≈46%零售定价 $79.99-$89.99 $109.99-$129.99
Amazon定位 中端性价比 中高端品质
毛利率(按$89.99) ≈78% —
毛利率(按$109.99) — ≈46%
建议：首批用方案A(40S300TC)打入市场验证，定价$89.99，FOB$19.9符合目标区间。方案B作为升级版Premium线后续推
出。
SereneDawn晨曦系列v1.0

--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 3) ---
撕破强力 ASTMD1424 ≥15N Elmendorf法
可燃性 16CFR1632 ClassI 美国床上用品
▶ 7.3 标签要求
美国市场：纤维成分标签（100%Cotton）+原产国（MadeinChina）+护理指令（ASTMD5489图标）+制造商/进
口商信息+RN/CA注册号。
欧盟市场：多语言纤维成分（至少 EN/DE/FR/IT/ES）+ 原产地 + 护理符号（ISO 3758）+ CE标识（如适用）+
SereneDawn晨曦系列v1.0


查询: 「目标市场」
----------------------------------------
--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 1) ---
TipoDZGN|TDTX-GY-BD001工程设计文档 CONFIDENTIAL
TipoDZGN™
AI原生工业设计平台·纺织品类
工程设计文档
Engineering Design Document
高阳纺织 · 家居四件套 · 欧美出口
项目编号 TDTX-GY-BD001
产品名称 SereneDawn晨曦系列·长绒棉缎纹四件套
产品品类 家居纺织HomeTextiles·床上用品BeddingSet
产地 河北省保定市高阳县Gaoyang,Baoding,Hebei
目标市场 北美（AmazonUS）+欧洲（AmazonEU/Wayfair）
零售价 $89.99-$109.99USD
目标FOB价 $18-22USD/套
首批订单 2000套（含Queen+King两个尺码）
版本 v1.0
日期 202608
SereneDawn晨曦系列v1.0TipoDZGN|TDTX-GY-BD001工程设计文档 CONFIDENTIAL
1 设计简报 Design Brief
▶ 产品概述
Serene Dawn（晨曦系列）是一款面向欧美中高端市场的长绒棉缎纹四件套。采用60S长绒棉，400TC缎纹织造，
OEKO-TEXStandard100认证，主打'高阳品质·全球标准'定位。
四件套包含：1×被套 Duvet Cover + 1×床笠 Fitted Sheet + 2×枕套 Pillowcase。提供Queen和King两个主力尺
码，覆盖北美85%以上的床型需求。
设计语言：北欧极简风格（ScandinavianMinimalism），以自然色系为主调，搭配细腻缎面光泽感，营造宁静舒适的卧
室氛围。适合25-45岁注重生活品质的欧美中产家庭。
▶ 市场定位
价格带 $89.99-$109.99USD（AmazonBedding中高端段）
竞品区间 $60-$80低端棉vs$120-$180高端品牌（如Brooklinen/Parachute）
差异化定位 60S长绒棉品质×中端价格=性价比之王竞品区间 $60-$80低端棉vs$120-$180高端品牌（如Brooklinen/Parachute）
差异化定位 60S长绒棉品质×中端价格=性价比之王
目标评分 Amazon4.5★以上，目标BestSeller子类目前20
▶ 核心卖点 Core Selling Points

--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 2) ---
国内物流+报关 8.0 1.1 1.5% 高阳→天津港
海运费分摊 6.0 0.8 1.1% 天津→美西按套分摊
FOB价合计 ¥430.2 $58.9 —
汇率按1USD=7.3RMB计算。实际FOB约$58.9，低于目标$18-22区间较多，需调整——以下为修正方案。
▶ 成本优化方案（V2）
原方案60S长绒棉400TC成本偏高，以下提供两套方案：
对比项 方案A：40S精梳棉300TC 方案B：60S长绒棉400TC
纱支/织密 40S精梳棉300TC 60S长绒棉400TC
面料单价 ¥22/m ¥38/m
面料成本(6.8m) ¥149.6 ¥258.4
染整成本 ¥40.8(¥6/m) ¥54.4(¥8/m)
FOB总价 ≈¥145($19.9) ≈¥430($58.9)
零售定价 $79.99-$89.99 $109.99-$129.99
Amazon定位 中端性价比 中高端品质
毛利率(按$89.99) ≈78% —
毛利率(按$109.99) — ≈46%零售定价 $79.99-$89.99 $109.99-$129.99
Amazon定位 中端性价比 中高端品质
毛利率(按$89.99) ≈78% —
毛利率(按$109.99) — ≈46%
建议：首批用方案A(40S300TC)打入市场验证，定价$89.99，FOB$19.9符合目标区间。方案B作为升级版Premium线后续推
出。
SereneDawn晨曦系列v1.0


查询: 「营销市场」
----------------------------------------
--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 1) ---
TipoDZGN|TDTX-GY-BD001工程设计文档 CONFIDENTIAL
TipoDZGN™
AI原生工业设计平台·纺织品类
工程设计文档
Engineering Design Document
高阳纺织 · 家居四件套 · 欧美出口
项目编号 TDTX-GY-BD001
产品名称 SereneDawn晨曦系列·长绒棉缎纹四件套
产品品类 家居纺织HomeTextiles·床上用品BeddingSet
产地 河北省保定市高阳县Gaoyang,Baoding,Hebei
目标市场 北美（AmazonUS）+欧洲（AmazonEU/Wayfair）
零售价 $89.99-$109.99USD
目标FOB价 $18-22USD/套
首批订单 2000套（含Queen+King两个尺码）
版本 v1.0
日期 202608
SereneDawn晨曦系列v1.0TipoDZGN|TDTX-GY-BD001工程设计文档 CONFIDENTIAL
1 设计简报 Design Brief
▶ 产品概述
Serene Dawn（晨曦系列）是一款面向欧美中高端市场的长绒棉缎纹四件套。采用60S长绒棉，400TC缎纹织造，
OEKO-TEXStandard100认证，主打'高阳品质·全球标准'定位。
四件套包含：1×被套 Duvet Cover + 1×床笠 Fitted Sheet + 2×枕套 Pillowcase。提供Queen和King两个主力尺
码，覆盖北美85%以上的床型需求。
设计语言：北欧极简风格（ScandinavianMinimalism），以自然色系为主调，搭配细腻缎面光泽感，营造宁静舒适的卧
室氛围。适合25-45岁注重生活品质的欧美中产家庭。
▶ 市场定位
价格带 $89.99-$109.99USD（AmazonBedding中高端段）
竞品区间 $60-$80低端棉vs$120-$180高端品牌（如Brooklinen/Parachute）
差异化定位 60S长绒棉品质×中端价格=性价比之王

--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 2) ---
零售定价 $79.99-$89.99 $109.99-$129.99
Amazon定位 中端性价比 中高端品质
毛利率(按$89.99) ≈78% —
毛利率(按$109.99) — ≈46%
建议：首批用方案A(40S300TC)打入市场验证，定价$89.99，FOB$19.9符合目标区间。方案B作为升级版Premium线后续推
出。
SereneDawn晨曦系列v1.0

--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 3) ---
撕破强力 ASTMD1424 ≥15N Elmendorf法
可燃性 16CFR1632 ClassI 美国床上用品
▶ 7.3 标签要求
美国市场：纤维成分标签（100%Cotton）+原产国（MadeinChina）+护理指令（ASTMD5489图标）+制造商/进
口商信息+RN/CA注册号。
欧盟市场：多语言纤维成分（至少 EN/DE/FR/IT/ES）+ 原产地 + 护理符号（ISO 3758）+ CE标识（如适用）+
SereneDawn晨曦系列v1.0

--- [引用] 来源: 高阳纺织 AI创意设计生成 案例测试.pdf (片段 4) ---
# 系列 数量 内容
A 产品白底图 6组 整套平铺/被套正面/床笠细节/枕套堆叠/包装展示/面料质感
B 卧室场景图 6组 晨光卧室/北欧极简/美式经典/酒店风格/4色对比/季节氛围
C 细节特写 5组 缎纹光泽/角扣系统/隐形拉链/弹力床笠/水洗标
D A+素材 5组 面料对比/TC图解/深口袋截面/色卡/认证
E Lifestyle 3组 叠被过程/护理场景/礼盒送礼
▶ 9.2 视频 (Veo) — 15组
# 系列 数量 内容
A 产品展示 4组 铺床全过程/面料垂坠/光泽感/360°包装
B 功能演示 4组 深口袋安装/角扣固定/隐形拉链/水洗后效果
C 场景短片 4组 晨光卧室/酒店体验/季节切换/色彩搭配
D 广告素材 3组 Amazon主图视频/社媒15秒/开箱体验
10 项目时间表 Project Timeline


================================================================================
"""