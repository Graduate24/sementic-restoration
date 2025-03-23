"""
代码语义还原模块，提供将注解、依赖注入等Spring特性还原为纯Java代码的功能
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Union, Any, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import SYSTEM_PROMPTS
from src.llm.llm_client import LLMClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("code_restoration")

class CodeRestorer:
    """
    代码语义还原类，负责将带有框架特性的Java代码还原为纯Java代码
    """
    
    def __init__(
        self, 
        llm_client: Optional[LLMClient] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        初始化代码还原器
        
        参数:
            llm_client: LLM客户端实例，如果为None则创建新实例
            model: 要使用的模型，仅在llm_client为None时使用
            api_key: API密钥，仅在llm_client为None时使用
        """
        self.llm_client = llm_client or LLMClient(model=model, api_key=api_key)
        logger.info("代码还原器初始化完成")
    
    def _prepare_restoration_prompt(
        self, 
        code: str, 
        modeling_info: Optional[Dict[str, Any]] = None,
        task_type: str = "code_restoration"
    ) -> Tuple[str, str]:
        """
        准备用于代码还原的提示词
        
        参数:
            code: 原始Java代码
            modeling_info: 建模信息（依赖注入映射、AOP信息等）
            task_type: 任务类型，可以是"code_restoration"、"dependency_injection"或"aop_restoration"
        
        返回:
            元组(system_prompt, user_prompt)
        """
        # 获取系统提示词
        system_prompt = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["code_restoration"])
        
        # 构建用户提示词
        user_prompt = "请将下面的Java代码转换为不使用框架特性的纯Java代码，保持相同的功能：\n\n"
        user_prompt += f"```java\n{code}\n```\n\n"
        
        # 如果有建模信息，添加到提示中
        if modeling_info:
            user_prompt += "以下是相关的依赖和配置信息，请在转换时考虑这些信息：\n\n"
            
            # 添加Bean定义信息
            if "beans" in modeling_info:
                user_prompt += "【Bean定义】\n"
                for bean in modeling_info["beans"]:
                    user_prompt += f"- {bean['name']} ({bean['type']})\n"
                user_prompt += "\n"
            
            # 添加依赖注入信息
            if "injections" in modeling_info:
                user_prompt += "【依赖注入关系】\n"
                for injection in modeling_info["injections"]:
                    user_prompt += f"- {injection['target']} 依赖 {injection['dependency']}\n"
                user_prompt += "\n"
            
            # 添加AOP信息
            if "aop" in modeling_info:
                user_prompt += "【AOP切面信息】\n"
                for aspect in modeling_info["aop"]:
                    user_prompt += f"- {aspect['type']} 切面: {aspect['aspect']} 作用于 {aspect['target']}\n"
                user_prompt += "\n"
        
        user_prompt += "请确保：\n"
        user_prompt += "1. 去除所有框架相关注解（如@Service, @Autowired等）\n"
        user_prompt += "2. 将依赖注入转换为显式构造函数或setter方法注入\n"
        user_prompt += "3. 将AOP切面逻辑内联到相关方法中\n"
        user_prompt += "4. 代码能够正常编译和运行\n"
        user_prompt += "5. 保持原始代码的功能语义不变\n\n"
        user_prompt += "请只返回转换后的代码，不需要解释。"
        
        return system_prompt, user_prompt
    
    def restore_code(
        self, 
        code: str, 
        modeling_info: Optional[Dict[str, Any]] = None,
        task_type: str = "code_restoration",
        stream: bool = False
    ) -> str:
        """
        将带有框架特性的Java代码还原为纯Java代码
        
        参数:
            code: 原始Java代码
            modeling_info: 建模信息（依赖注入映射、AOP信息等）
            task_type: 任务类型，可以是"code_restoration"、"dependency_injection"或"aop_restoration"
            stream: 是否使用流式输出
        
        返回:
            还原后的Java代码
        """
        logger.info(f"开始代码还原，代码长度: {len(code)} 字符，任务类型: {task_type}")
        
        # 准备提示词
        system_prompt, user_prompt = self._prepare_restoration_prompt(code, modeling_info, task_type)
        
        try:
            # 使用LLM进行代码转换
            restored_code = self.llm_client.simple_completion(user_prompt, system_prompt, stream)
            
            # 提取代码块（如果模型返回了markdown格式）
            if "```java" in restored_code and "```" in restored_code.split("```java", 1)[1]:
                restored_code = restored_code.split("```java", 1)[1].split("```", 1)[0].strip()
            elif "```" in restored_code:
                # 尝试获取任何代码块
                restored_code = restored_code.split("```", 1)[1].split("```", 1)[0].strip()
            
            logger.info(f"代码还原完成，还原后代码长度: {len(restored_code)} 字符")
            return restored_code
            
        except Exception as e:
            logger.error(f"代码还原过程中出错: {str(e)}")
            return f"错误: 代码还原失败 - {str(e)}"
    
    def restore_dependency_injection(
        self, 
        code: str, 
        bean_definitions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> str:
        """
        专门处理依赖注入还原
        
        参数:
            code: 原始Java代码
            bean_definitions: Bean定义列表
            stream: 是否使用流式输出
        
        返回:
            还原后的Java代码
        """
        modeling_info = {"beans": bean_definitions} if bean_definitions else None
        return self.restore_code(code, modeling_info, "dependency_injection", stream)
    
    def restore_aop(
        self, 
        code: str, 
        aop_info: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> str:
        """
        专门处理AOP切面还原
        
        参数:
            code: 原始Java代码
            aop_info: AOP切面信息列表
            stream: 是否使用流式输出
        
        返回:
            还原后的Java代码
        """
        modeling_info = {"aop": aop_info} if aop_info else None
        return self.restore_code(code, modeling_info, "aop_restoration", stream)


# 简单测试函数
def test_code_restorer():
    """
    测试代码还原功能
    """
    # 创建LLM客户端
    llm_client = LLMClient()
    
    # 创建代码还原器
    restorer = CodeRestorer(llm_client)
    
    # 示例代码
    code = """
@Service
public class UserService {
    @Autowired
    private UserRepository userRepository;
    
    @Autowired
    private EmailService emailService;
    
    @Value("${app.user.default-role}")
    private String defaultRole;
    
    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }
    
    public User createUser(String username, String email) {
        User user = new User();
        user.setUsername(username);
        user.setEmail(email);
        user.setRole(defaultRole);
        User savedUser = userRepository.save(user);
        emailService.sendWelcomeEmail(savedUser);
        return savedUser;
    }
}
"""
    
    # 示例建模信息
    modeling_info = {
        "beans": [
            {"name": "userRepository", "type": "com.example.repository.UserRepository"},
            {"name": "emailService", "type": "com.example.service.EmailService"},
            {"name": "userService", "type": "com.example.service.UserService"}
        ],
        "injections": [
            {"target": "userService", "dependency": "userRepository"},
            {"target": "userService", "dependency": "emailService"}
        ]
    }
    
    # 进行代码还原
    print("开始代码还原...")
    restored_code = restorer.restore_code(code, modeling_info)
    
    print("\n还原后的代码:\n")
    print(restored_code)


if __name__ == "__main__":
    test_code_restorer() 