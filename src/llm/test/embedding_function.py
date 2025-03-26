from typing import List, Union, Optional, Any, Callable
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingFunction:
    """ChromaDB的基础嵌入函数接口"""
    def __call__(self, input: List[str]) -> List[List[float]]:
        """将输入文本列表转换为嵌入向量列表"""
        raise NotImplementedError("子类必须实现此方法")

class SentenceTransformerEmbeddings(EmbeddingFunction):
    """使用SentenceTransformer模型的嵌入函数实现"""
    
    def __init__(self, model_name: str = "microsoft/codebert-base", **kwargs):
        """
        初始化SentenceTransformer嵌入函数
        
        Args:
            model_name: SentenceTransformer模型名称或路径
            **kwargs: 传递给SentenceTransformer.encode的其他参数
        """
        self.model = SentenceTransformer(model_name)
        self.kwargs = kwargs
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        将输入文本列表转换为嵌入向量列表
        
        Args:
            input: 要嵌入的文本列表
            
        Returns:
            文本嵌入的列表，每个嵌入都是浮点数列表
        """
        # 确保输入是字符串列表
        if not isinstance(input, list):
            raise ValueError(f"输入必须是字符串列表，而不是 {type(input)}")
        
        if len(input) == 0:
            return []
        
        # 使用模型进行嵌入
        embeddings = self.model.encode(
            input, 
            convert_to_numpy=True,
            **self.kwargs
        )
        
        # 确保输出是二维列表
        if len(embeddings.shape) == 1:
            # 单个嵌入，添加批处理维度
            return [embeddings.tolist()]
        
        return embeddings.tolist() 