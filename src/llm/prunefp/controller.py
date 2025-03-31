"""
分析控制器模块，负责管理误报分析流程
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional

from src.llm.llm_client import LLMClient
from src.llm.prunefp.repository import SourceCodeRepository
from src.llm.prunefp.session import AnalysisSession
from src.llm.prunefp.processor import ResultProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prunefp_controller")

class FalsePositiveAnalysisController:
    """
    误报分析控制器，负责管理分析流程和会话
    """
    
    def __init__(
        self, 
        raw_result_path: str, 
        project_path: str,
        output_path: str,
        llm_client: Optional[LLMClient] = None,
        llm_model: Optional[str] = None,
        code_index: Optional[str] = None
    ):
        """
        初始化分析控制器
        
        参数:
            raw_result_path: 原始污点分析结果的JSON文件路径
            project_path: Java项目根目录
            output_path: 分析结果输出目录
            llm_client: LLM客户端实例，如果未提供则创建新实例
            llm_model: 使用的LLM模型名称，仅在未提供llm_client时使用
            code_index: 代码索引目录路径，包含call_graph.json和jimple目录
        """
        self.raw_result_path = raw_result_path
        self.project_path = project_path
        self.output_path = output_path
        self.llm_client = llm_client or LLMClient(model=llm_model)
        self.code_index = code_index
        self.source_repo = SourceCodeRepository(project_path, code_index) if code_index else None
        self.result_processor = ResultProcessor(output_path)
        
        # 加载原始污点分析结果
        self.raw_results = self._load_results(raw_result_path)
        
        # 会话字典，用于跟踪每个分析路径的会话
        self.sessions = {}
        
        logger.info(f"初始化误报分析控制器: 分析结果={raw_result_path}, 项目路径={project_path}")
        
    def _load_results(self, result_path: str) -> Dict:
        """
        加载污点分析结果文件
        
        参数:
            result_path: 结果文件路径
            
        返回:
            解析后的结果字典
        """
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            logger.info(f"成功加载污点分析结果: {len(results)} 个结果集")
            return results
        except Exception as e:
            logger.error(f"加载污点分析结果失败: {str(e)}")
            raise
    
    def _create_session_id(self, finding: Dict) -> str:
        """
        为分析结果创建唯一的会话ID
        
        参数:
            finding: 单个污点分析结果
            
        返回:
            会话ID字符串
        """
        return finding.get('function')

    def analyze_all_paths(self) -> Dict:
        """
        分析所有污点传播路径
        
        返回:
            分析结果的汇总字典
        """
        total_findings = 0
        processed_findings = 0
        
        all_results = []
        
        logger.info("开始分析所有污点传播路径...")
        
        # 遍历所有结果集
        for result_id, findings in self.raw_results.items():
            total_findings += len(findings)
            
            for finding in findings:
                try:
                    # 分析单个污点传播路径
                    analysis_result = self.analyze_single_finding(finding)
                    all_results.append(analysis_result)
                    processed_findings += 1
                    
                    logger.info(f"已处理: {processed_findings}/{total_findings} "
                               f"- {finding.get('class_name')}:{finding.get('method_name')}")
                    
                except Exception as e:
                    logger.error(f"分析路径失败: {str(e)}")
        
        # 处理并保存汇总结果
        summary = self.result_processor.process_results(all_results)
        
        logger.info(f"污点路径分析完成: 总计={total_findings}, 处理={processed_findings}, "
                   f"误报={summary.get('false_positives', 0)}, 真实漏洞={summary.get('true_positives', 0)}")
        self.result_processor.generate_report(summary)
        return summary
    
    def analyze_single_finding(self, finding: Dict) -> Dict:
        """
        分析单个污点传播路径
        
        参数:
            finding: 单个污点分析结果
            
        返回:
            分析结果字典
        """
        # 创建会话ID并检查是否已经分析过
        session_id = self._create_session_id(finding)
        
        if session_id in self.sessions:
            logger.info(f"使用缓存的分析结果: {session_id}")
            return self.sessions[session_id].result
        
        # 创建新的分析会话
        logger.info(f"创建新的分析会话: {session_id}")
        session = AnalysisSession(finding, self.source_repo, self.llm_client)
        self.sessions[session_id] = session
        
        # 执行分析
        analysis_result = session.run_analysis()
        
        return analysis_result 