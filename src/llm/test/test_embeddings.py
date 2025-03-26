import unittest

from langchain_community.embeddings import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer

class TestEmbeddings(unittest.TestCase):

    def __init__(self, method_name: str = "runTest"):
        super().__init__(method_name)
        self.model = None
        self.local_model_path = "/home/ran/Documents/work/graduate/llm-agent/models/codebert"
        self.code_snippet = """
                public List<User> testCase18(
                    @RequestParam(required = false) String username,
                    @RequestParam(required = false) String email,
                    @RequestParam(required = false) String sortBy) {
                    StringBuilder whereClause = new StringBuilder();
                    if (username != null) {
                        whereClause.append("username LIKE '%").append(username).append("%'");
                    }
                    if (email != null) {
                        if (whereClause.length() > 0) {
                            whereClause.append(" AND ");
                        }
                        whereClause.append("email LIKE '%").append(email).append("%'");
                    }
                    if (sortBy != null) {
                        whereClause.append(" ORDER BY ").append(sortBy);
                    }
                    return sqlInjectionTestService.findUsersByMultipleConditionsUnsafe(whereClause.toString());
                }
                """

    def setUp(self):
        if not self.model:
            self.model = SentenceTransformer(self.local_model_path)


    def test_embeddings1(self):
        try:
            embedding = self.model.encode([self.code_snippet])
            print(f"SentenceTransformer方法 - 嵌入向量维度: {embedding.shape}")
        except Exception as e:
            print(f"使用SentenceTransformer创建嵌入时出错: {str(e)}")

    def test_embeddings2(self):
        model_kwargs = {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': True}

        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=self.local_model_path,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
            embedding = embeddings.embed_documents([self.code_snippet])
            print(f"LangChain方法 - 嵌入向量维度: {len(embedding[0])}")
        except Exception as e:
            print(f"使用LangChain创建嵌入时出错: {str(e)}")

    

if __name__ == '__main__':
    unittest.main() 