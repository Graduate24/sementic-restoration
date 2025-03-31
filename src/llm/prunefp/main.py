"""
误报消除工具的主程序入口
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from src.llm.llm_client import LLMClient
from src.llm.prunefp.controller import FalsePositiveAnalysisController

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prunefp_main")

def parse_arguments():
    """
    解析命令行参数
    
    返回:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(description='大模型辅助的静态分析误报消除工具')
    
    parser.add_argument('--result', '-r', required=True,
                        help='污点分析结果的JSON文件路径')
    
    parser.add_argument('--project', '-p', required=True,
                        help='Java项目根目录路径')
    
    parser.add_argument('--output', '-o', required=False,
                        help='分析结果输出目录，默认为当前目录下的output_日期_时间')
    
    parser.add_argument('--model', '-m', required=False, default='gpt-4',
                        help='使用的LLM模型，默认为gpt-4')
    
    parser.add_argument('--max-findings', type=int, required=False,
                        help='最大分析的漏洞数量，用于测试')
    
    args = parser.parse_args()
    
    # 设置默认输出目录
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = os.path.join(os.getcwd(), f"output_{timestamp}")
    
    # 确保输出目录存在
    os.makedirs(args.output, exist_ok=True)
    
    return args

def setup_logging(output_dir):
    """
    设置日志记录
    
    参数:
        output_dir: 输出目录
    """
    log_file = os.path.join(output_dir, 'prunefp.log')
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # 添加文件处理器到根日志记录器
    logging.getLogger().addHandler(file_handler)
    
    logger.info(f"日志将被保存到: {log_file}")

def main():
    """
    主程序入口
    """
    start_time = time.time()
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 配置日志
    setup_logging(args.output)
    
    logger.info(f"开始运行误报消除工具")
    logger.info(f"污点分析结果: {args.result}")
    logger.info(f"Java项目路径: {args.project}")
    logger.info(f"输出目录: {args.output}")
    logger.info(f"使用模型: {args.model}")
    
    try:
        # 创建分析控制器
        controller = FalsePositiveAnalysisController(
            raw_result_path=args.result,
            project_path=args.project,
            output_path=args.output,
            llm_model=args.model
        )
        
        # 执行分析
        results = controller.analyze_all_paths()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        logger.info(f"分析完成! 耗时: {elapsed_time:.2f} 秒")
        logger.info(f"结果已保存到: {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"运行时发生错误: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main()) 