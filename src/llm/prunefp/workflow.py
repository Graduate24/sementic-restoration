"""
误报消除工作流模块，负责管理整个误报分析流程
"""

import os
import json
import logging
import time
from typing import Optional, Tuple

from src.llm.llm_client import LLMClient
from src.llm.prunefp.controller import FalsePositiveAnalysisController

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prunefp_workflow")

def execute_command(command: str, cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """
    执行命令行命令
    
    参数:
        command: 要执行的命令
        cwd: 命令执行的工作目录，默认为None表示当前目录
        
    返回:
        Tuple[int, str, str]: (返回码, 标准输出, 标准错误)
    """
    try:
        import subprocess
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

class PruneFalsePositivesWorkflow:
    """
    误报消除工作流类，管理整个误报分析流程
    """
    
    def __init__(
        self, 
        raw_result_path: str, 
        project_path: str, 
        output_path: str, 
        llm_model: str,
        code_index: str,
        tool_path: Optional[str] = None
    ):
        """
        初始化误报消除工作流
        
        参数:
            raw_result_path: 污点分析结果JSON文件路径
            project_path: Java项目根目录
            output_path: 输出目录路径
            llm_model: 使用的LLM模型
            code_index: 代码索引目录路径，包含call_graph.json和jimple目录
            tool_path: 外部工具目录路径（可选）
        """
        self.raw_result_path = raw_result_path
        self.project_path = project_path
        self.output_path = output_path
        self.llm_model = llm_model
        self.code_index = code_index
        self.tool_path = tool_path
        
        # 创建LLM客户端
        self.llm_client = LLMClient(model=self.llm_model)
        
        # 记录时间统计
        self.times = {
            "total": 0.0,
            "analysis": 0.0
        }
        
        # 创建输出目录
        os.makedirs(self.output_path, exist_ok=True)
        
        logger.info(f"初始化误报消除工作流: 结果={raw_result_path}, 项目={project_path}, 输出={output_path}")
    
    def run(self):
        """
        运行完整的误报消除工作流
        """
        start_time = time.time()
        logger.info("开始运行误报消除工作流")
        
        try:
            # 第1步：运行分析控制器
            analysis_results = self._run_analysis()
            
            # 第2步：生成统计报告
            self._generate_statistics(analysis_results)
            
            end_time = time.time()
            self.times["total"] = end_time - start_time
            
            logger.info(f"误报消除工作流完成! 总耗时: {self.times['total']:.2f} 秒")
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}", exc_info=True)
            raise
    
    def _run_analysis(self):
        """
        运行分析控制器
        
        返回:
            分析结果字典
        """
        logger.info("开始运行误报分析...")
        
        start_time = time.time()
        
        # 创建分析控制器
        controller = FalsePositiveAnalysisController(
            raw_result_path=self.raw_result_path,
            project_path=self.project_path,
            output_path=self.output_path,
            llm_client=self.llm_client,
            code_index=self.code_index
        )
        
        # 执行分析
        results = controller.analyze_all_paths()
        
        end_time = time.time()
        self.times["analysis"] = end_time - start_time
        
        logger.info(f"误报分析完成，耗时: {self.times['analysis']:.2f} 秒")
        
        return results
    
    def _generate_statistics(self, analysis_results):
        """
        生成统计数据
        
        参数:
            analysis_results: 分析结果字典
        """
        logger.info("生成统计报告...")
        
        # 创建统计信息
        statistics = {
            "times": self.times,
            "model": self.llm_model,
            "results": analysis_results
        }
        
        # 保存统计信息
        statistics_path = os.path.join(self.output_path, "workflow_statistics.json")
        with open(statistics_path, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, indent=2, ensure_ascii=False)
        
        logger.info(f"统计报告已保存到: {statistics_path}") 