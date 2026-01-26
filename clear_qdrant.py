#!/usr/bin/env python3
"""
快速清空 Qdrant 集合中的所有数据
"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FilterSelector

load_dotenv()

# 配置
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "adp_knowledge_base"

print(f"⚠️  即将清空 Qdrant 集合: {COLLECTION_NAME}")
print(f"   服务地址: {QDRANT_URL}")
confirm = input("确认删除？(yes/no): ")

if confirm.lower() != "yes":
    print("❌ 操作已取消")
    exit(0)

try:
    client = QdrantClient(url=QDRANT_URL)

    # 检查集合是否存在
    collections = client.get_collections().collections
    collection_names = [col.name for col in collections]

    if COLLECTION_NAME not in collection_names:
        print(f"⚠️  集合 '{COLLECTION_NAME}' 不存在")
        exit(0)

    # 获取删除前的点数量
    info_before = client.get_collection(COLLECTION_NAME)
    count_before = info_before.points_count
    print(f"📊 删除前: {count_before} 个向量")

    # 删除所有数据 - 使用空的 Filter 来匹配所有点
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=FilterSelector(
            filter=Filter(must=[])  # 空条件匹配所有点
        )
    )

    # 获取删除后的点数量
    info_after = client.get_collection(COLLECTION_NAME)
    count_after = info_after.points_count

    print(f"📊 删除后: {count_after} 个向量")
    print("✅ 清空完成！")

except Exception as e:
    print(f"❌ 清空失败: {e}")
    exit(1)
