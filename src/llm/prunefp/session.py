"""
分析会话模块，负责管理单个污点分析路径的LLM交互
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from src.llm.llm_client import LLMClient
from src.llm.prunefp.repository import SourceCodeRepository
from src.llm.prunefp.prompt import PromptGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prunefp_session")


class AnalysisSession:
    """
    分析会话类，负责管理与LLM的交互以分析单个污点传播路径
    """

    def __init__(
            self,
            finding: Dict[str, Any],
            source_repo: SourceCodeRepository,
            llm_client: LLMClient,
            max_rounds: int = 5
    ):
        """
        初始化分析会话
        
        参数:
            finding: 单个污点分析结果
            source_repo: 源代码仓库实例
            llm_client: LLM客户端实例
            max_rounds: 最大交互轮数，默认为5
        """
        self.finding = finding
        self.source_repo = source_repo
        self.llm_client = llm_client
        self.max_rounds = max_rounds
        self.conversation_history = []
        self.requested_info = set()  # 记录已请求的信息
        self.result = None
        self.prompt_generator = PromptGenerator()

        logger.info(f"创建分析会话: {finding.get('class_name')}:{finding.get('method_name')}")

    def run_analysis(self) -> Dict[str, Any]:
        """
        运行分析流程
        
        返回:
            分析结果字典
        """
        # 准备初始提示词
        initial_prompt = self._prepare_initial_prompt()
        system_prompt = self._get_system_prompt()

        # 第一轮分析
        logger.info(f"开始第一轮分析...")
        response = self.llm_client.generate_completion(
            prompt=initial_prompt,
            system_prompt=system_prompt
        )
        response_content = self.llm_client.extract_content(response)
        self._add_to_conversation({"role": "user", "content": initial_prompt})
        self._add_to_conversation({"role": "assistant", "content": response_content})

        current_round = 1

        # 进行渐进式分析
        while self._needs_more_info(response_content) and current_round < self.max_rounds:
            current_round += 1
            logger.info(f"开始第{current_round}轮分析...")

            # 提取需要的信息类型
            requested_info = self._extract_requested_info(response_content)

            # 获取请求的信息
            additional_info = self._fetch_additional_info(requested_info)

            # 继续对话
            follow_up_prompt = self._prepare_follow_up_prompt(additional_info)
            response = self.llm_client.generate_completion(
                prompt=follow_up_prompt,
                conversation_history=self.conversation_history
            )
            response_content = self.llm_client.extract_content(response)

            self._add_to_conversation({"role": "user", "content": follow_up_prompt})
            self._add_to_conversation({"role": "assistant", "content": response_content})

        # 如果达到最大轮数但仍需要更多信息，记录警告
        if current_round >= self.max_rounds and self._needs_more_info(response_content):
            logger.warning(f"达到最大对话轮数 ({self.max_rounds})，但LLM仍需要更多信息")

        # 最终判断
        final_prompt = self._prepare_final_prompt()
        final_response = self.llm_client.generate_completion(
            prompt=final_prompt,
            conversation_history=self.conversation_history
        )
        final_content = self.llm_client.extract_content(final_response)

        self._add_to_conversation({"role": "user", "content": final_prompt})
        self._add_to_conversation({"role": "assistant", "content": final_content})

        # 解析结果
        analysis_result = self._parse_result(final_content)
        self.result = analysis_result

        return analysis_result

    def _prepare_initial_prompt(self) -> str:
        """
        准备初始分析提示词
        
        返回:
            格式化的提示词字符串
        """
        return self.prompt_generator.generate_initial_prompt(self.finding)

    def _prepare_final_prompt(self) -> str:
        """
        准备最终分析提示词

        返回:
            格式化的提示词字符串
        """
        return self.prompt_generator.generate_final_prompt(self.finding)

    def _prepare_follow_up_prompt(self, additional_info: Dict[str, Any]) -> str:
        """
        准备后续提示词
        
        参数:
            additional_info: 额外信息字典
            
        返回:
            格式化的提示词字符串
        """
        return self.prompt_generator.generate_follow_up_prompt(additional_info)

    def _get_system_prompt(self) -> str:
        """
        获取系统提示词
        
        返回:
            系统提示词字符串
        """
        return self.prompt_generator.generate_system_prompt()

    def _add_to_conversation(self, message: Dict[str, str]) -> None:
        """
        添加消息到对话历史
        
        参数:
            message: 消息字典，包含role和content
        """
        self.conversation_history.append(message)

    def _needs_more_info(self, response: str) -> bool:
        """
        检查LLM是否需要更多信息
        
        参数:
            response: LLM响应文本
            
        返回:
            如果需要更多信息则为True，否则为False
        """
        # 检查是否包含表示需要更多信息的JSON结构
        needs_more_pattern = r'"需要更多信息"\s*:\s*true'
        return bool(re.search(needs_more_pattern, response, re.IGNORECASE))

    def _extract_requested_info(self, response: str) -> Dict[str, Any]:
        """
        从LLM响应中提取请求的信息
        
        参数:
            response: LLM响应文本
            
        返回:
            请求信息的字典
        """
        # 尝试从JSON或文本中提取请求的信息
        json_pattern = r'{.*?"需要更多信息"\s*:\s*true.*?}'
        json_match = re.search(json_pattern, response, re.DOTALL)

        if json_match:
            try:
                json_str = json_match.group(0)
                info_request = json.loads(json_str)
                return info_request
            except json.JSONDecodeError:
                logger.warning(f"无法解析请求的JSON: {json_match.group(0)}")

        # 备用方案：文本解析
        info_types = []
        if "方法源码" in response or "源代码" in response:
            info_types.append("方法源码")
        if "调用图" in response:
            info_types.append("调用图")
        if "Jimple" in response or "IR" in response:
            info_types.append("Jimple IR")

        # 尝试提取类名和方法名
        class_pattern = r'类名[：:]\s*["\']?([\w\.]+)["\']?'
        method_pattern = r'方法名[：:]\s*["\']?([\w]+)["\']?'

        class_match = re.search(class_pattern, response)
        method_match = re.search(method_pattern, response)

        class_name = class_match.group(1) if class_match else None
        method_name = method_match.group(1) if method_match else None

        return {
            "需要更多信息": True,
            "信息类型": info_types,
            "类名": class_name,
            "方法名": method_name
        }

    def _fetch_additional_info(self, info_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取请求的额外信息
        
        参数:
            info_request: 信息请求字典
            
        返回:
            获取的信息字典
        """
        result = {}

        class_name = info_request.get("类名")
        method_name = info_request.get("方法名")
        info_types = info_request.get("信息类型", [])
        method_signature = info_request.get("签名", "")

        if not class_name or not method_name:
            # 如果未提供类名或方法名，尝试从污点分析路径中获取一个
            path = self.finding.get("path", [])
            if path:
                first_path_node = path[0]
                class_name = first_path_node.get("javaClass")
                method_signature = first_path_node.get("function", "")
                if ":" in method_signature:
                    method_name = method_signature.split(":")[1].strip()

        # 检查请求的每种信息类型
        for info_type in info_types:
            if "方法源码" in info_type or "源代码" in info_type:
                source_code = self.source_repo.get_method_source(class_name, method_name,
                                                                 method_signature)
                if source_code:
                    result["方法源码"] = {
                        "类名": class_name,
                        "方法名": method_name,
                        "源码": source_code
                    }

            if "调用图" in info_type:
                call_graph = self.source_repo.get_call_graph(class_name, method_name,
                                                             method_signature)
                if call_graph:
                    result["调用图"] = {
                        "类名": class_name,
                        "方法名": method_name,
                        "调用图": call_graph
                    }

            if "Jimple" in info_type or "IR" in info_type:
                jimple = self.source_repo.get_method_jimple(class_name, method_name,
                                                            method_signature)
                if jimple:
                    result["Jimple IR"] = {
                        "类名": class_name,
                        "方法名": method_name,
                        "Jimple": jimple
                    }

                # 记录已请求的信息
                key = f"{class_name}_{method_name}"
                self.requested_info.add(key)

        return result

    def _parse_result(self, response: str) -> Dict[str, Any]:
        """
        解析LLM的最终响应
        
        参数:
            response: LLM响应文本
            
        返回:
            解析后的结果字典
        """
        # 尝试提取JSON结果
        json_pattern = r'{.*?"是否误报".*?}'
        json_match = re.search(json_pattern, response, re.DOTALL)

        if json_match:
            try:
                result = json.loads(response)

                # 添加原始查询信息
                result["原始数据"] = {
                    "类名": self.finding.get("class_name"),
                    "方法名": self.finding.get("method_name"),
                    "行号": self.finding.get("line_number"),
                    "源点": self.finding.get("source"),
                    "汇点": self.finding.get("sink"),
                    "函数": self.finding.get("function"),
                }
                result["是否误报"] = False if "不是误报" == result["是否误报"] else True
                """
                "是否误报": is_false_positive,
                "置信度": confidence,
                "理由": response[:500],  # 截取前500个字符作为理由
                """
                return result
            except json.JSONDecodeError:
                logger.warning(f"无法解析结果JSON: {json_match.group(0)}")

        # 备用方案：文本解析
        is_false_positive = "误报" in response and "不是误报" not in response
        confidence = 70  # 默认置信度

        # 尝试提取置信度
        confidence_pattern = r'置信度[：:]\s*(\d+)'
        confidence_match = re.search(confidence_pattern, response)
        if confidence_match:
            try:
                confidence = int(confidence_match.group(1))
            except ValueError:
                pass

        # 构建结果字典
        result = {
            "是否误报": is_false_positive,
            "置信度": confidence,
            "理由": response[:500],  # 截取前500个字符作为理由
            "原始数据": {
                "类名": self.finding.get("class_name"),
                "方法名": self.finding.get("method_name"),
                "行号": self.finding.get("line_number"),
                "源点": self.finding.get("source"),
                "汇点": self.finding.get("sink"),
                "函数": self.finding.get("function"),
            }
        }

        return result
