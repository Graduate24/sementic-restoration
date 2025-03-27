import uuid

import chromadb
import torch
from chromadb.utils.embedding_functions.sentence_transformer_embedding_function import \
    SentenceTransformerEmbeddingFunction
from transformers import AutoModel, AutoTokenizer


class CustomEmbeddingFunction:
    def __init__(self, model_path='microsoft/codebert-base'):
        # 加载本地模型和 tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path)

    def __call__(self, input):
        # input 应该是一个字符串列表
        inputs = self.tokenizer(input, padding=True, truncation=True, return_tensors="pt")
        outputs = self.model(**inputs)
        embeddings = outputs.last_hidden_state
        attention_mask = inputs["attention_mask"].unsqueeze(-1).expand(embeddings.size()).float()
        masked_embeddings = embeddings * attention_mask
        summed = torch.sum(masked_embeddings, dim=1)
        counts = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
        mean_pooled = summed / counts
        # 返回一个 list，每个元素是对应文本的向量（list 格式）
        return mean_pooled.detach().numpy().tolist()

    def get_model(self):
        return self.model

    def get_tokenizer(self):
        return self.tokenizer


def sliding_window(text, tokenizer, max_length=512, stride=256):
    encoded = tokenizer.encode(text)
    result = []
    for i in range(0, len(encoded), stride):
        chunk = encoded[i:i + max_length]
        result.append(chunk)
    return result


def restore_text_from_tokens(tokens, tokenizer):
    """
    根据token列表还原原始文本

    参数:
        tokens: token列表或token列表的列表(2维)
        tokenizer: 用于解码的tokenizer对象

    返回:
        还原的原始文本或文本列表
    """
    # 检查是否是2维列表
    if isinstance(tokens, list):
        if len(tokens) > 0 and isinstance(tokens[0], list):
            # 处理2维列表情况
            results = []
            for token_seq in tokens:
                text = tokenizer.decode(token_seq, skip_special_tokens=True)
                results.append([text])
            return results
        else:
            # 处理1维列表情况
            return [tokenizer.decode(tokens, skip_special_tokens=True)]
    else:
        raise TypeError("输入的tokens必须是列表类型")


class VectorDB:
    def __init__(self, model_path='microsoft/codebert-base', path='./chromadb'):
        # embedding function for codes
        self.embedding_function = CustomEmbeddingFunction(model_path)
        # embedding function for other
        self.default_embedding_function = SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.default_tokenizer = AutoTokenizer.from_pretrained(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.model = AutoModel.from_pretrained(model_path)
        self.path = path
        self.client = chromadb.PersistentClient(self.path)

        self.semantic_collection = None
        self.code_collection = None
        self.context_collection = None

        self._init_db()

    def _init_db(self):
        # create 3 collections
        # 1. semantic collection
        self.semantic_collection = self.client.get_or_create_collection('semantic',
                                                                        metadata={"description": "语义信息数据库","hnsw:space": "cosine"},
                                                                        embedding_function=self.default_embedding_function)
        # 2. code collection
        self.code_collection = self.client.get_or_create_collection('code',
                                                                    metadata={"description": "代码特征数据库","hnsw:space": "cosine"},
                                                                    embedding_function=self.embedding_function)

        # 3. context collection
        self.context_collection = self.client.get_or_create_collection('context',
                                                                       metadata={"description": "上下文信息数据库","hnsw:space": "cosine"},
                                                                       embedding_function=self.embedding_function)

    def build_code_input(self, code):
        chunks = sliding_window(code, self.tokenizer)
        return restore_text_from_tokens(chunks, self.tokenizer)

    def build_text_input(self, text):
        chunks = sliding_window(text, self.default_tokenizer)
        return restore_text_from_tokens(chunks, self.default_tokenizer)

    def save_code(self, docs: list[str], metadata: list[dict[str:str | int | float]]):
        self._save(docs, metadata, self.build_code_input, self.code_collection)

    def save_semantic(self, docs: list[str], metadata: list[dict[str:str | int | float]]) -> None:
        self._save(docs, metadata, self.build_text_input, self.semantic_collection)

    def save_context(self, docs: list[str], metadata: list[dict[str:str | int | float]]):
        self._save(docs, metadata, self.build_code_input, self.context_collection)

    def _save(self, docs: list[str], metadata: list[dict[str:str | int | float]], input_builder, collection) -> None:
        for doc, m in zip(docs, metadata):
            chunks = input_builder(doc)
            if len(chunks) == 1:
                m['chunk'] = -1
                unique_id = str(uuid.uuid4())
                collection.add(ids=[unique_id], metadatas=[m], documents=chunks[0])
                continue
            for index, chunk in enumerate(chunks):
                m['chunk'] = index
                unique_id = str(uuid.uuid4())
                collection.add(ids=[unique_id], metadatas=[m], documents=chunk)
