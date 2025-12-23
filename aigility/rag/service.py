# [服务层] 对外暴露的统一入口 (RAGManager)
import shutil
# 第一步：添加这几行代码（解决相对导入问题）
import sys
import os
# 获取当前文件的父目录（aigility/rag）
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录（aigility-master）
root_dir = os.path.dirname(os.path.dirname(current_dir))
# 将根目录添加到Python路径
sys.path.insert(0, root_dir)

# 第二步：修改相对导入为绝对导入（或保留相对导入，此时已识别父包）
from aigility.rag.config import RAGConfig
from aigility.rag.embeddings.factory import EmbeddingFactory
from aigility.rag.vector_stores.factory import VectorStoreFactory
from aigility.rag.ingestion import IngestionManager




class RAGService:
    def __init__(self, config: RAGConfig = None):
        # 如果用户没传配置，使用默认配置
        self.config = config or RAGConfig()
        
        print(f"🔧 Initializing RAG with: Embedding={self.config.embedding.provider}, Store={self.config.vector_store.provider}")

        # 1. 工厂生产 Embedding
        self.embedding_model = EmbeddingFactory.get_embedding_model(self.config.embedding)
        
        # 2. 工厂生产 Vector Store (注入 embedding)
        self.vector_store = VectorStoreFactory.get_vector_store(
            self.config.vector_store, 
            self.embedding_model
        )
        
        # 3. 初始化数据处理模块
        self.ingestion = IngestionManager(self.config.ingestion)

    def add_file(self, file_path: str):
        """加载文件 -> 切分 -> 存入向量库"""
        if not isinstance(file_path, str):
            raise TypeError(f"file_path must be str, got {type(file_path)}")
        if not os.path.isabs(file_path):
            file_path = os.path.join(current_dir, file_path)
        
        print(f"📄 Processing file: {file_path}")
        try:
            # 1. 加载文件（返回原始Document列表）
            raw_docs = self.ingestion.load_file(file_path)
            # 2. 处理已加载的文档（核心修复：调用process_raw_docs而非process_documents）
            chunks = self.ingestion.process_raw_docs(raw_docs, file_path)
            # 3. 存入向量库
            if chunks:
                self.vector_store.add_documents(chunks)
                print(f"✅ Successfully added {len(chunks)} chunks to {self.config.vector_store.provider}.")
            else:
                print("⚠️ No content found in file.")
        except Exception as e:
            print(f"❌ Error adding file {file_path}: {str(e)}")
            raise e

    def search(self, query: str) -> str:
        """检索逻辑"""
        try:
            docs = self.vector_store.similarity_search(query, k=self.config.search_top_k)
            
            if not docs:
                return ""

            # 格式化上下文
            results = []
            for doc in docs:
                source = doc.metadata.get("source", "Unknown")
                content = doc.page_content.replace("\n", " ")
                results.append(f"Source: {source}\nContent: {content}")
            
            return "\n\n".join(results)
        except Exception as e:
            print(f"❌ Search failed: {str(e)}")
            return ""
    def clear_knowledge_base(self):
        """(危险操作) 清空知识库"""
        try:
            if self.config.vector_store.provider == "chroma":
                # Chroma：删除持久化目录
                if os.path.exists(self.config.vector_store.persist_path):
                    shutil.rmtree(self.config.vector_store.persist_path)
                    os.makedirs(self.config.vector_store.persist_path, exist_ok=True)
                    print(f"✅ Chroma知识库 {self.config.vector_store.persist_path} 已清空")
            elif self.config.vector_store.provider == "milvus":
                # Milvus：删除集合
                from pymilvus import utility
                if utility.has_collection(self.config.vector_store.collection_name):
                    utility.drop_collection(self.config.vector_store.collection_name)
                    print(f"✅ Milvus集合 {self.config.vector_store.collection_name} 已删除")
            elif self.config.vector_store.provider == "faiss":  # 新增FAISS清空逻辑
                # FAISS：删除索引文件
                faiss_index_path = os.path.join(
                    self.config.vector_store.persist_path,
                    f"{self.config.vector_store.collection_name}.index"
                )
                if os.path.exists(faiss_index_path):
                    os.remove(faiss_index_path)
                    # 可选：删除整个FAISS目录
                    if os.path.exists(self.config.vector_store.persist_path):
                        shutil.rmtree(self.config.vector_store.persist_path)
                        os.makedirs(self.config.vector_store.persist_path, exist_ok=True)
                    print(f"✅ FAISS索引 {faiss_index_path} 已清空")
            else:
                print(f"⚠️ 不支持清空 {self.config.vector_store.provider} 知识库")
        except Exception as e:
            print(f"❌ 清空知识库失败: {str(e)}")

# ====================== 测试代码（直接运行） ======================
if __name__ == "__main__":

    # 示例1：使用默认配置（DashScope + Chroma）
    # ------------------------------
    '''
    service = RAGService()
    service.add_file("./test.txt")
    print(service.search("公司最新的休假政策是什么？"))
    
    输出：
        🔧 Initializing RAG with: Embedding=huggingface, Store=chroma
        🔍 检测到Embedding维度：512
        📄 Processing file: /Users/qyd/Downloads/Edge/aigility-master/aigility/rag/./test.txt
        ✅ Successfully added 7 chunks to chroma.
        Source: /Users/qyd/Downloads/Edge/aigility-master/aigility/rag/./test.txt
        Content: 【TXT-PAGE0-CHUNK7】【标题：4. 休假流程：所有休假均需通过企业微信】 4. 休假流程：所有休假均需通过企业微信提交书面申请，附相关证明材料（病假需医疗证明、婚假需结婚证等），按审批权限报批：试用期员工及普通员工由直属领导、部门负责人审批；主管及以上人员需额外经人力资源部、 总经理审批，审批通过后方可休假，未审批擅自休假视为旷工。 5. 其他说明：休假期间员工需保持通讯畅通，紧急工作需配合处理；休假结束后1个工作日内到人力资源部办理销假手续，未按时销假按旷工处理。                                                                                           

        Source: /Users/qyd/Downloads/Edge/aigility-master/aigility/rag/./test.txt
        Content: 【TXT-PAGE0-CHUNK6】 - 病假：员工凭县级及以上医院出具的诊断证明、病历等材料申请，病假期间工资按公司薪酬制度执行（连续病假不满3天按正常工资80%发放，3天及以上按当地最低工资标准的80%发放），月累计病假超过10天取消当月全勤奖。 - 事假：员工因个人事务需请假的，事假期间无工资 ，月累计事假不超过3天，年累计事假不超过15天，超期按旷工处理。 - 婚假：员工结婚可享受婚假3天，符合晚婚条件（男满25周岁、女满23周岁）的额外增加婚假7天，婚假期间按正常工资发放，需一次性休完，提前15天提交申请。 - 产假：女职工生育享受产假98天，其中产前可休假15天；难产的增加产假15天 ；生育多胞胎的，每多生育1个婴儿增加产假15天，产假期间按当地生育保险相关规定发放生育津贴。 - 丧假：员工直系亲属（父母、配偶、子女）去世，可 享受丧假3天；祖父母、外祖父母、岳父母、公婆去世，可享受丧假1天，丧假期间按正常工资发放。                                                   

        Source: /Users/qyd/Downloads/Edge/aigility-master/aigility/rag/./test.txt
        Content: 【TXT-PAGE0-CHUNK5】【标题：5. 使用要求：员工需合理使用办公用品，】 5. 使用要求：员工需合理使用办公用品，杜绝浪费，损坏或丢失办公用品需按成本价赔偿；离职时需交回未使用完的办公用品及借用的办公设备（如电脑、打印机等），经人力资源部验收合格后办理离职手续。 五、员工休假管理制度（最新） 1. 目的：保障员工休息休假权利，规范休假管理，平衡工作与生活，提升员工幸福感。 2. 适用范围：公司全体在职员工（含试用期员工、 劳务派遣员工，试用期员工不享受年假，其他休假按规定执行）。 3. 核心休假类型及标准： - 带薪年休假：员工连续工作满1年不满10年的，年休假5天；满10年不满20年的，年休假10天；满20年的，年休假15天。年休假可分段申请，原则上当年休完，未休完部分不结转至次年，特殊情况经总经理审批可结转不超 过5天至次年第一季度。 - 法定节假日：按《中华人民共和国劳动法》规定执行，包括元旦1天、春节3天、劳动节1天、国庆节3天等，具体放假安排以公司年 度通知为准，法定节假日加班按3倍日工资支付报酬。                                                                                            
    '''

    # ------------------------------
    # 示例2：切换为 DashScope + FAISS
    # ------------------------------
    from aigility.rag.config import VectorStoreConfig
    from aigility.rag.config import EmbeddingConfig
    embedding_config = EmbeddingConfig(
        provider="dashscope",
        model_name="text-embedding-v4",
        api_key=os.getenv("DASHSCOPE_API_KEY")
    )
    vector_store_config = VectorStoreConfig(
        provider="faiss",
        path="./faiss_db"
    )
    config = RAGConfig(embedding=embedding_config, vector_store=vector_store_config)
    service = RAGService(config=config)
    service.add_file("./test.txt")
    print(service.search("公司最新的休假政策是什么？"))

    # ------------------------------
    # 示例3：切换为 DashScope + Milvus
    # ------------------------------
    '''
    from aigility.rag.config import VectorStoreConfig
    from aigility.rag.config import EmbeddingConfig
    embedding_config = EmbeddingConfig(
        provider="dashscope",
        model_name="text-embedding-v4",
        api_key=os.getenv("DASHSCOPE_API_KEY")
    )
    vector_store_config = VectorStoreConfig(
        provider="milvus",  # 切换向量库
        url="http://localhost:19530"
    )
    config = RAGConfig(embedding=embedding_config, vector_store=vector_store_config)
    service = RAGService(config=config)
    service.add_file("./test.txt")
    print(service.search("公司最新的休假政策是什么？"))
    '''
    