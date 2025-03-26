import unittest
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from java_code_analyzer import JavaCodeAnalyzer
import numpy as np
from embedding_function import SentenceTransformerEmbeddings

class TestJavaAnalyzer(unittest.TestCase):
    def setUp(self):
        """初始化向量数据库客户端"""
        # 使用CodeBERT作为embeddings模型
        self.embedding_function = SentenceTransformerEmbeddings(model_name="microsoft/codebert-base")
        
        self.client = chromadb.Client(Settings(
            persist_directory="./test_java_db",
            anonymized_telemetry=False
        ))
        self.collection = self.client.create_collection(
            name="java_code_snippets",
            metadata={"description": "存储Java代码片段的集合"},
            embedding_function=self.embedding_function
        )
        
        # 准备Java测试数据
        self.java_code = """
package com.example.service;

import java.util.List;
import java.util.Optional;
import java.time.LocalDateTime;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * 用户服务类，处理用户相关业务逻辑
 */
@Service
public class UserService {
    private final UserRepository userRepository;
    private final EmailService emailService;
    private final PasswordEncoder passwordEncoder;
    
    @Autowired
    public UserService(UserRepository userRepository, 
                      EmailService emailService,
                      PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.emailService = emailService;
        this.passwordEncoder = passwordEncoder;
    }
    
    /**
     * 创建新用户
     * @param userDTO 用户数据传输对象
     * @return 创建的用户
     * @throws IllegalArgumentException 如果用户数据无效
     */
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
    
    /**
     * 获取所有用户
     * @return 用户列表
     */
    public List<User> getAllUsers() {
        return userRepository.findAll();
    }
    
    /**
     * 根据ID获取用户
     * @param id 用户ID
     * @return 用户对象
     * @throws UserNotFoundException 如果用户不存在
     */
    public User getUserById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException("User not found with id: " + id));
    }
    
    /**
     * 更新用户信息
     * @param id 用户ID
     * @param userDTO 用户数据
     * @return 更新后的用户
     * @throws UserNotFoundException 如果用户不存在
     */
    public User updateUser(Long id, UserDTO userDTO) {
        User existingUser = getUserById(id);
        
        if (userDTO.getEmail() != null && !userDTO.getEmail().isEmpty()) {
            existingUser.setEmail(userDTO.getEmail());
        }
        
        if (userDTO.getPassword() != null && !userDTO.getPassword().isEmpty()) {
            validatePassword(userDTO.getPassword());
            existingUser.setPassword(passwordEncoder.encode(userDTO.getPassword()));
        }
        
        return userRepository.save(existingUser);
    }
    
    private void validatePassword(String password) {
        if (password.length() < 8) {
            throw new IllegalArgumentException("Password must be at least 8 characters");
        }
    }
    
    /**
     * 删除用户
     * @param id 用户ID
     * @throws UserNotFoundException 如果用户不存在
     */
    public void deleteUser(Long id) {
        if (!userRepository.existsById(id)) {
            throw new UserNotFoundException("User not found with id: " + id);
        }
        userRepository.deleteById(id);
    }
}
"""

    def test_java_analyzer(self):
        """测试Java代码分析器"""
        # 分析并分割Java代码
        code_chunks = JavaCodeAnalyzer.parse_and_split(self.java_code, max_tokens=400, include_imports=True)
        
        # 验证分割结果
        self.assertTrue(len(code_chunks) > 0)
        
        # 增强元数据
        enhanced_chunks = JavaCodeAnalyzer.enhance_metadata(code_chunks)
        
        # 准备加入向量数据库的数据
        documents = [chunk["code"] for chunk in enhanced_chunks]
        ids = [f"userservice_{i}" for i in range(len(enhanced_chunks))]
        metadatas = [chunk["metadata"] for chunk in enhanced_chunks]
        
        # 添加到向量数据库
        self.collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        
        # 测试中文查询
        query_result = self.collection.query(
            query_texts=["如何创建新用户"],
            n_results=2
        )
        
        self.assertIsNotNone(query_result)
        self.assertTrue(len(query_result['ids'][0]) > 0)
        
        # 测试元数据过滤查询
        filtered_result = self.collection.query(
            query_texts=["创建用户"],
            where={"section": "method", "method_name": "createUser"},
            n_results=1
        )
        
        self.assertIsNotNone(filtered_result)
        self.assertTrue(len(filtered_result['ids'][0]) > 0)

    def test_method_extraction(self):
        """测试方法信息提取"""
        # 提取方法信息
        method_info = JavaCodeAnalyzer.extract_method_info(self.java_code)
        
        # 验证提取结果
        self.assertTrue(len(method_info) > 0)
        
        # 检查特定方法
        create_user_method = None
        for method in method_info:
            if method["name"] == "createUser":
                create_user_method = method
                break
        
        self.assertIsNotNone(create_user_method)
        self.assertEqual(create_user_method["return_type"], "User")
        self.assertTrue("public" in create_user_method["modifiers"])
        self.assertTrue(len(create_user_method["parameters"]) > 0)

    def tearDown(self):
        """清理测试数据"""
        # 删除集合
        self.client.delete_collection("java_code_snippets")

if __name__ == '__main__':
    unittest.main() 