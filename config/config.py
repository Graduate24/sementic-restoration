"""
配置文件，存储项目所需的API密钥、模型配置等信息
"""

import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量（如果存在）
load_dotenv()

# OpenRouter API配置
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # 请在.env文件中设置此变量
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

# 默认模型配置
DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"  # Claude 3 Opus
AVAILABLE_MODELS = {
    "claude-3-sonnet": "anthropic/claude-3.7-sonnet",
    "gpt-4o": "openai/gpt-4o",
    "o1": "openai/o1",
    "deepseek": "deepseek/deepseek-r1",
    "gemini-flash": "google/gemini-2.0-flash-001",
}

# 模型参数配置
DEFAULT_PARAMS = {
    "temperature": 0.1,     # 较低的温度以确保代码生成的确定性
    "max_tokens": None,     # 最大输出长度
    "top_p": 0.95,          # 概率阈值
    "frequency_penalty": 0, # 频率惩罚
    "presence_penalty": 0,  # 存在惩罚
}

# 系统角色提示词 - 可针对不同任务定制
SYSTEM_PROMPTS = {
    "code_restoration": """你是一个专门负责Java代码语义还原的AI助手。
你的任务是将带有Spring等框架特性（如注解、AOP、依赖注入）的Java代码，
转换为不依赖这些框架特性的纯Java代码，保留原始代码的功能和语义。
你生成的代码应该能够被传统静态分析工具正确理解和分析。
请确保你的代码：
1. 保持功能等价性
2. 消除框架特性的隐式行为
3. 显式化所有依赖关系和控制流
4. 可以编译和执行
5. 代码风格保持一致且可读性良好
""",
    
    "dependency_injection": """你是一个专门处理Java依赖注入还原的AI助手。
你的任务是将使用@Autowired、@Value等注解实现的依赖注入，
转换为显式构造函数注入或setter方法注入的形式。
你需要理解Bean之间的依赖关系，并在新代码中显式构建这些关系。
""",
    
    "aop_restoration": """你是一个专门处理Java AOP切面还原的AI助手。
你的任务是将使用@Aspect、@Before、@After等注解实现的切面逻辑，
内联到目标方法中，使切面逻辑显式化。
你需要理解切点表达式，识别受影响的方法，并在这些方法中适当位置插入切面代码。
"""
}

# 项目路径配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 