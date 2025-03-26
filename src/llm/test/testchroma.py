from sentence_transformers import SentenceTransformer
import chromadb

# 显式创建 Chroma 客户端
client = chromadb.Client()

# 初始化 SentenceTransformer 模型
model = SentenceTransformer("/home/ran/Documents/work/graduate/llm-agent/models/codebert")

# 自定义 embedding 函数，接收文本列表，返回对应的向量列表
def custom_embedding_function(texts):
    # texts 是一个字符串列表，使用模型编码后转换为 Python 列表
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()

# 创建集合时指定自定义 embedding 函数
collection = client.create_collection(
    name="示例集合",
    embedding_function=custom_embedding_function
)

# 准备待插入的数据
documents = [
    "这是第一条文本",
    "这是第二条文本",
    "这是第三条文本"
]
ids = ["doc1", "doc2", "doc3"]
metadatas = [
    {"类别": "测试"},
    {"类别": "测试"},
    {"类别": "测试"}
]

# 添加数据到集合中
collection.add(
    ids=ids,
    documents=documents,
    metadatas=metadatas
)

# 执行查询：例如查找与 "第一条" 相关的文本
query_text = "第一条"
results = collection.query(
    query_texts=[query_text],
    n_results=2  # 返回最相似的两个结果
)

# 输出查询结果
print("查询结果:", results)
