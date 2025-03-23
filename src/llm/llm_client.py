"""
LLM客户端模块，提供与OpenRouter API通信的功能
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Union, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import (
    OPENROUTER_API_KEY, 
    OPENROUTER_API_BASE, 
    DEFAULT_MODEL, 
    DEFAULT_PARAMS,
    AVAILABLE_MODELS
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm_client")

class LLMClient:
    """
    LLM客户端类，处理与OpenRouter API的通信
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        retry_attempts: int = 3,
        retry_delay: int = 5,
    ):
        """
        初始化LLM客户端
        
        参数:
            api_key: OpenRouter API密钥，默认使用配置文件中的密钥
            model: 要使用的模型ID，默认使用配置文件中的默认模型
            temperature: 温度参数，控制随机性
            max_tokens: 生成的最大token数
            top_p: top-p采样参数
            retry_attempts: 请求失败时的重试次数
            retry_delay: 重试之间的延迟（秒）
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("未提供API密钥。请在.env文件中设置OPENROUTER_API_KEY或直接传入api_key参数")
        
        # 使用完整的模型ID（如果提供的是短名称，则从可用模型中查找）
        if model in AVAILABLE_MODELS:
            self.model = AVAILABLE_MODELS[model]
        else:
            self.model = model or DEFAULT_MODEL
        
        # 设置模型参数
        self.params = DEFAULT_PARAMS.copy()
        if temperature is not None:
            self.params["temperature"] = temperature
        if max_tokens is not None:
            self.params["max_tokens"] = max_tokens
        if top_p is not None:
            self.params["top_p"] = top_p
            
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # API端点
        self.chat_endpoint = f"{OPENROUTER_API_BASE}/chat/completions"
        
        logger.info(f"LLM客户端初始化完成，使用模型: {self.model}")
    
    def _prepare_headers(self) -> Dict[str, str]:
        """
        准备API请求头
        
        返回:
            包含API密钥和其他必要头信息的字典
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def _prepare_messages(
        self, 
        system_prompt: Optional[str],
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        准备消息格式
        
        参数:
            system_prompt: 系统角色提示词
            user_prompt: 用户提示词
            conversation_history: 之前的对话历史
        
        返回:
            格式化的消息列表
        """
        messages = []
        
        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加对话历史
        if conversation_history:
            messages.extend(conversation_history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_prompt})
        
        return messages
    
    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成文本补全
        
        参数:
            prompt: 用户提示词
            system_prompt: 系统角色提示词
            conversation_history: 对话历史
            stream: 是否使用流式传输
            **kwargs: 其他参数，将覆盖默认参数
        
        返回:
            API响应的字典
        """
        messages = self._prepare_messages(system_prompt, prompt, conversation_history)
        
        # 合并默认参数和自定义参数
        params = self.params.copy()
        params.update(kwargs)
        
        # 准备请求体
        request_body = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            **params
        }
        
        # 记录请求信息（仅用于调试）
        logger.debug(f"API请求: {json.dumps(request_body, ensure_ascii=False, indent=2)}")
        
        # 发送请求并处理重试
        response = None
        attempt = 0
        
        while attempt < self.retry_attempts:
            try:
                response = requests.post(
                    self.chat_endpoint,
                    headers=self._prepare_headers(),
                    json=request_body,
                    timeout=60  # 设置超时时间
                )
                
                response.raise_for_status()  # 如果请求失败，抛出异常
                
                if stream:
                    # 返回响应对象以便调用者处理流式传输
                    return response
                else:
                    # 解析并返回JSON响应
                    result = response.json()
                    logger.debug(f"API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    return result
            
            except requests.exceptions.RequestException as e:
                attempt += 1
                logger.warning(f"请求失败 (尝试 {attempt}/{self.retry_attempts}): {str(e)}")
                
                if attempt < self.retry_attempts:
                    logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"达到最大重试次数。最后错误: {str(e)}")
                    raise
    
    def extract_content(self, response: Dict[str, Any]) -> str:
        """
        从API响应中提取文本内容
        
        参数:
            response: API响应字典
        
        返回:
            提取的文本内容
        """
        try:
            return response['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            logger.error(f"从响应中提取内容失败: {str(e)}")
            return ""
    
    def process_streaming_response(self, response) -> str:
        """
        处理流式响应并返回完整的生成内容
        
        参数:
            response: 流式响应对象
        
        返回:
            拼接的完整文本内容
        """
        content = ""
        
        try:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    
                    # 跳过保持连接的空行
                    if line_text.strip() == '':
                        continue
                    
                    # 检查数据行格式
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]  # 去掉'data: '前缀
                        
                        # 处理心跳消息
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            delta_content = data['choices'][0]['delta'].get('content', '')
                            if delta_content:
                                content += delta_content
                                # 可以在这里添加实时输出，如print(delta_content, end='', flush=True)
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON解析错误: {str(e)}, 行: {line_text}")
                        except (KeyError, IndexError) as e:
                            logger.warning(f"响应格式错误: {str(e)}, 数据: {data_str}")
        
        except Exception as e:
            logger.error(f"处理流式响应时出错: {str(e)}")
        
        return content
    
    def simple_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """
        简化的补全API，直接返回生成的文本内容
        
        参数:
            prompt: 用户提示词
            system_prompt: 系统角色提示词
            stream: 是否使用流式传输
        
        返回:
            生成的文本内容
        """
        try:
            if stream:
                response = self.generate_completion(prompt, system_prompt, stream=True)
                return self.process_streaming_response(response)
            else:
                response = self.generate_completion(prompt, system_prompt)
                return self.extract_content(response)
        except Exception as e:
            logger.error(f"生成补全时出错: {str(e)}")
            return f"错误: 无法获取生成结果 - {str(e)}"


# 简单测试函数
def test_llm_client():
    """
    测试LLM客户端是否正常工作
    """
    client = LLMClient()
    prompt = "将下面的Java代码转换为不使用Spring注解的形式: \n\n```java\n@Service\npublic class UserService {\n    @Autowired\n    private UserRepository userRepository;\n    \n    public User findById(Long id) {\n        return userRepository.findById(id).orElse(null);\n    }\n}\n```"
    
    system_prompt = "你是一个专门将Spring框架代码转换为纯Java代码的专家。"
    
    print("发送请求...")
    response = client.simple_completion(prompt, system_prompt)
    print("\n生成结果:\n")
    print(response)


if __name__ == "__main__":
    test_llm_client() 