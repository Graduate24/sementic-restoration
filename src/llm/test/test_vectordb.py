import re
import unittest

import torch
from transformers import AutoTokenizer, AutoModel

import chromadb


class CustomEmbeddingFunction:
    def __init__(self, model_path):
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



class TestVectorDB(unittest.TestCase):
    def setUp(self):
        """初始化向量数据库客户端"""
        # 使用CodeBERT作为embeddings模型
        # /home/ran/Documents/work/graduate/graphcodebert
        self.embedding_function = CustomEmbeddingFunction('/home/ran/Documents/work/graduate/llm-agent/models/codebert')

        self.client = chromadb.PersistentClient('./chromadb')

        self.collection = self.client.add.create_collection(
            name="code_snippets",
            metadata={"description": "存储代码片段的集合"},
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

    def split_code_into_chunks(self, code, max_tokens=400):
        """将代码分割成较小的块"""
        # 按函数或类分割代码
        chunks = []
        current_chunk = []
        current_length = 0
        
        # 使用正则表达式匹配函数和类定义
        code_lines = code.split('\n')
        for line in code_lines:
            # 估算token数量（简单估算，实际应该使用tokenizer）
            line_tokens = len(line.split()) + 1
            
            if current_length + line_tokens > max_tokens and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_tokens
            else:
                current_chunk.append(line)
                current_length += line_tokens
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

    def split_java_code(self, code, max_tokens=400):
        """将Java代码分割成较小的块，保持代码的语义完整性"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        # 定义Java代码的关键结构
        class_pattern = r'class\s+\w+'
        method_pattern = r'(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\([^)]*\)'
        interface_pattern = r'interface\s+\w+'
        enum_pattern = r'enum\s+\w+'
        
        # 分割代码行
        lines = code.split('\n')
        current_block = []
        in_block = False
        brace_count = 0
        
        for line in lines:
            # 计算当前行的token数量（简单估算）
            line_tokens = len(line.split()) + 1
            
            # 检查是否是新的结构开始
            if re.match(class_pattern, line.strip()) or \
               re.match(interface_pattern, line.strip()) or \
               re.match(enum_pattern, line.strip()):
                if current_block:
                    chunks.append('\n'.join(current_block))
                current_block = [line]
                in_block = True
                brace_count = 0
                continue
            
            # 检查是否是方法开始
            if re.match(method_pattern, line.strip()):
                if current_block and brace_count == 0:
                    chunks.append('\n'.join(current_block))
                current_block = [line]
                in_block = True
                brace_count = 0
                continue
            
            # 处理代码块
            if in_block:
                current_block.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    chunks.append('\n'.join(current_block))
                    current_block = []
                    in_block = False
            else:
                current_block.append(line)
            
            # 检查token限制
            if len('\n'.join(current_block).split()) > max_tokens and current_block:
                chunks.append('\n'.join(current_block))
                current_block = []
                in_block = False
        
        # 处理剩余的代码
        if current_block:
            chunks.append('\n'.join(current_block))
        
        return chunks

    def test_add_and_query_documents(self):
        """测试添加文档和查询功能"""
        # 添加文档到向量数据库
        self.collection.add(
            documents=self.test_documents,
            ids=self.test_ids,
            metadatas=self.test_metadata
        )
        
        # 测试相似度查询
        query_result = self.collection.query(
            query_texts=["Add two numbers together"],
            n_results=2
        )
        
        # 验证查询结果
        self.assertIsNotNone(query_result)
        self.assertIn("add_func", query_result['ids'][0])
        
        # 测试带元数据的过滤查询
        filtered_result = self.collection.query(
            query_texts=["计算器类"],
            where={"type": "class"},
            n_results=1
        )
        
        self.assertIsNotNone(filtered_result)
        self.assertIn("calculator_class", filtered_result['ids'][0])

    def test_update_and_delete(self):
        """测试更新和删除文档"""
        # 添加文档
        self.collection.add(
            documents=self.test_documents,
            ids=self.test_ids,
            metadatas=self.test_metadata
        )
        
        # 更新文档
        self.collection.update(
            ids=["add_func"],
            documents=["def add(a, b):\n    return a + b + 1"],
            metadatas=[{"type": "function", "language": "python", "updated": True}]
        )
        
        # 验证更新
        query_result = self.collection.query(
            query_texts=["加法函数"],
            n_results=1
        )
        self.assertIn("add_func", query_result['ids'][0])
        
        # 删除文档
        self.collection.delete(ids=["add_func"])
        
        # 验证删除
        query_result = self.collection.query(
            query_texts=["加法函数"],
            n_results=1
        )
        self.assertNotIn("add_func", query_result['ids'][0])

    def test_long_code_handling(self):
        """测试处理长代码的情况"""
        # 创建一个较长的代码文件
        long_code = """
class ComplexCalculator:
    def __init__(self):
        self.result = 0
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"add: {a} + {b} = {result}")
        return result
    
    def subtract(self, a, b):
        result = a - b
        self.history.append(f"subtract: {a} - {b} = {result}")
        return result
    
    def multiply(self, a, b):
        result = a * b
        self.history.append(f"multiply: {a} * {b} = {result}")
        return result
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("除数不能为零")
        result = a / b
        self.history.append(f"divide: {a} / {b} = {result}")
        return result
    
    def get_history(self):
        return self.history
"""
        # 分割代码
        chunks = self.split_code_into_chunks(long_code)
        
        # 添加分割后的代码块
        chunk_ids = [f"complex_calc_chunk_{i}" for i in range(len(chunks))]
        chunk_metadata = [
            {"type": "class", "language": "python", "description": "复杂计算器类的第{}部分".format(i+1)}
            for i in range(len(chunks))
        ]
        
        self.collection.add(
            documents=chunks,
            ids=chunk_ids,
            metadatas=chunk_metadata
        )
        
        # 测试查询
        query_result = self.collection.query(
            query_texts=["如何实现一个带有历史记录的计算器"],
            n_results=2
        )
        
        self.assertIsNotNone(query_result)
        self.assertTrue(any("complex_calc_chunk" in id for id in query_result['ids'][0]))

    def test_multilingual_query(self):
        """测试多语言查询效果"""
        # 添加文档
        self.collection.add(
            documents=self.test_documents,
            ids=self.test_ids,
            metadatas=self.test_metadata
        )
        
        # 测试中文查询
        chinese_result = self.collection.query(
            query_texts=["如何实现加法函数"],
            n_results=1
        )
        
        # 测试英文查询
        english_result = self.collection.query(
            query_texts=["how to implement addition function"],
            n_results=1
        )
        
        # 验证两种语言的查询结果是否一致
        self.assertEqual(chinese_result['ids'][0], english_result['ids'][0])

    def test_java_code_splitting(self):
        """测试Java代码分割功能"""
        # 创建一个Java代码示例
        java_code = """
public class UserService {
    private final UserRepository userRepository;
    private final EmailService emailService;
    
    public UserService(UserRepository userRepository, EmailService emailService) {
        this.userRepository = userRepository;
        this.emailService = emailService;
    }
    
    public User createUser(UserDTO userDTO) {
        validateUserDTO(userDTO);
        User user = convertToUser(userDTO);
        user = userRepository.save(user);
        emailService.sendWelcomeEmail(user.getEmail());
        return user;
    }
    
    private void validateUserDTO(UserDTO userDTO) {
        if (userDTO.getEmail() == null || userDTO.getEmail().isEmpty()) {
            throw new IllegalArgumentException("Email cannot be empty");
        }
        if (userDTO.getPassword() == null || userDTO.getPassword().length() < 8) {
            throw new IllegalArgumentException("Password must be at least 8 characters");
        }
    }
    
    private User convertToUser(UserDTO userDTO) {
        User user = new User();
        user.setEmail(userDTO.getEmail());
        user.setPassword(passwordEncoder.encode(userDTO.getPassword()));
        user.setCreatedAt(LocalDateTime.now());
        return user;
    }
    
    public List<User> getAllUsers() {
        return userRepository.findAll();
    }
    
    public User getUserById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException("User not found with id: " + id));
    }
}
"""
        # 分割代码
        chunks = self.split_java_code(java_code)
        
        # 验证分割结果
        self.assertTrue(len(chunks) > 0)
        
        # 添加分割后的代码块到向量数据库
        chunk_ids = [f"user_service_chunk_{i}" for i in range(len(chunks))]
        chunk_metadata = [
            {
                "type": "class",
                "language": "java",
                "description": f"UserService类的第{i+1}部分",
                "framework": "spring",
                "component": "service"
            }
            for i in range(len(chunks))
        ]
        
        self.collection.add(
            documents=chunks,
            ids=chunk_ids,
            metadatas=chunk_metadata
        )
        
        # 测试查询
        query_result = self.collection.query(
            query_texts=["如何实现用户创建功能"],
            n_results=2
        )
        
        self.assertIsNotNone(query_result)
        self.assertTrue(any("user_service_chunk" in id for id in query_result['ids'][0]))

    def tearDown(self):
        """清理测试数据"""
        # 删除集合
        self.client.delete_collection("code_snippets")

if __name__ == '__main__':
    unittest.main() 