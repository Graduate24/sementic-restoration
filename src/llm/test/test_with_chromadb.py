import unittest
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from chromadb.config import Settings
import re

class TestChromaDB(unittest.TestCase):
    def setUp(self):
        """初始化向量数据库客户端"""
        # 使用ChromaDB内置的SentenceTransformerEmbeddingFunction
        self.embedding_function = SentenceTransformerEmbeddingFunction(model_name="microsoft/codebert-base")
        
        self.client = chromadb.Client(Settings(
            persist_directory="./test_chroma_direct_db",
            anonymized_telemetry=False
        ))
        self.collection = self.client.create_collection(
            name="direct_code_snippets",
            metadata={"description": "使用ChromaDB内置函数存储代码片段的集合"},
            embedding_function=self.embedding_function
        )
        
        # 准备测试数据
        self.test_documents = [
            "def add(a, b):\n    return a + b",
            "def multiply(x, y):\n    return x * y",
            "class Calculator:\n    def __init__(self):\n        self.result = 0",
            "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
        ]
        self.test_ids = ["add_func", "multiply_func", "calculator_class", "fibonacci_func"]
        self.test_metadata = [
            {"type": "function", "language": "python", "description": "实现两个数相加的函数"},
            {"type": "function", "language": "python", "description": "实现两个数相乘的函数"},
            {"type": "class", "language": "python", "description": "计算器类，用于基本数学运算"},
            {"type": "function", "language": "python", "description": "计算斐波那契数列的函数"}
        ]

    def test_add_and_query(self):
        """测试添加文档和查询功能"""
        # 添加文档到向量数据库
        self.collection.add(
            documents=self.test_documents,
            ids=self.test_ids,
            metadatas=self.test_metadata
        )
        
        # 测试相似度查询
        query_result = self.collection.query(
            query_texts=["如何实现加法函数"],
            n_results=2
        )
        
        # 验证查询结果
        self.assertIsNotNone(query_result)
        self.assertTrue(len(query_result['ids'][0]) > 0)
        
        # 测试带元数据的过滤查询
        filtered_result = self.collection.query(
            query_texts=["计算器类"],
            where={"type": "class"},
            n_results=1
        )
        
        self.assertIsNotNone(filtered_result)
        self.assertTrue(len(filtered_result['ids'][0]) > 0)

    def tearDown(self):
        """清理测试数据"""
        # 删除集合
        self.client.delete_collection("direct_code_snippets")

if __name__ == '__main__':
    unittest.main() 