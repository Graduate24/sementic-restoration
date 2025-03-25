#!/usr/bin/env python3
"""
命令行工具，用于执行语义还原操作
"""

import os
import sys
import argparse
import logging
import json
from typing import List, Dict, Any, Optional

# 配置根日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("semantic_restoration_cli")

# 导入项目内部模块
# 使用相对导入可能会更好，这里为了简单使用绝对导入
try:
    from src.llm.llm_client import LLMClient
    from src.llm.util.data_processor import ModelingDataProcessor
    from src.llm.util.prompt_template import PromptTemplate
    from src.llm.util.semantic_restoration_client import SemanticRestorationClient
except ImportError:
    # 尝试添加项目根目录到Python路径
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from src.llm.llm_client import LLMClient
    from src.llm.util.data_processor import ModelingDataProcessor
    from src.llm.util.prompt_template import PromptTemplate
    from src.llm.util.semantic_restoration_client import SemanticRestorationClient


def parse_arguments():
    """
    解析命令行参数
    
    返回:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description="语义还原工具 - 将带注解的Java代码转换为纯Java代码")
    
    # 必须参数
    parser.add_argument("--project_dir", type=str, required=True,
                        help="要处理的Java项目目录路径")
    parser.add_argument("--modeling_dir", type=str, required=True,
                        help="包含建模数据的目录路径")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="还原结果的输出目录路径")
    
    # 操作模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--restore_all", action="store_true",
                           help="还原项目中的所有Java文件")
    mode_group.add_argument("--restore_files", type=str, nargs="+",
                           help="还原指定的Java文件（提供相对于project_dir的文件路径）")
    mode_group.add_argument("--restore_file_list", type=str,
                           help="还原从文件中读取的Java文件列表（每行一个文件路径）")
    
    # 可选参数
    parser.add_argument("--batch_size", type=int, default=1,
                        help="批处理大小，同时处理多少个文件（默认：1）")
    parser.add_argument("--no_context", action="store_true",
                        help="不使用上下文文件进行还原")
    parser.add_argument("--max_context_files", type=int, default=2,
                        help="最大上下文文件数量（默认：2）")
    parser.add_argument("--max_retries", type=int, default=3,
                        help="调用LLM失败时最大重试次数（默认：3）")
    parser.add_argument("--retry_delay", type=int, default=5,
                        help="重试间隔秒数（默认：5）")
    parser.add_argument("--api_key", type=str,
                        help="LLM API密钥（默认使用环境变量）")
    parser.add_argument("--log_level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                        help="日志级别（默认：INFO）")
    
    return parser.parse_args()


def setup_logging(log_level: str):
    """
    设置日志级别
    
    参数:
        log_level: 日志级别字符串
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"无效的日志级别: {log_level}")
    
    logging.getLogger().setLevel(numeric_level)
    

def read_file_list(file_path: str) -> List[str]:
    """
    从文件中读取文件路径列表
    
    参数:
        file_path: 包含文件路径的文件
    
    返回:
        文件路径列表
    """
    file_list = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    file_list.append(line)
    except Exception as e:
        logger.error(f"读取文件列表失败: {str(e)}")
    
    return file_list


def setup_llm_client(api_key: Optional[str] = None) -> LLMClient:
    """
    设置LLM客户端
    
    参数:
        api_key: 可选的API密钥
    
    返回:
        配置好的LLM客户端
    """
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key
    
    return LLMClient()


def main():
    """
    主函数
    """
    args = parse_arguments()
    
    # 设置日志级别
    setup_logging(args.log_level)
    
    # 打印参数信息
    logger.info("语义还原工具启动")
    logger.info(f"项目目录: {args.project_dir}")
    logger.info(f"建模数据目录: {args.modeling_dir}")
    logger.info(f"输出目录: {args.output_dir}")
    
    # 设置LLM客户端
    llm_client = setup_llm_client(args.api_key)
    
    # 创建语义还原客户端
    client = SemanticRestorationClient(
        project_dir=args.project_dir,
        modeling_dir=args.modeling_dir,
        output_dir=args.output_dir,
        llm_client=llm_client,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        use_context=not args.no_context,
        max_context_files=args.max_context_files
    )
    
    # 加载数据
    client.load_data()
    
    # 执行还原操作
    if args.restore_all:
        logger.info("开始还原所有文件")
        stats = client.restore_all_files()
    elif args.restore_files:
        logger.info(f"开始还原指定的 {len(args.restore_files)} 个文件")
        stats = client.restore_specific_files(args.restore_files)
    elif args.restore_file_list:
        file_list = read_file_list(args.restore_file_list)
        logger.info(f"从文件 {args.restore_file_list} 中读取到 {len(file_list)} 个文件路径")
        stats = client.restore_specific_files(file_list)
    else:
        logger.error("未指定操作模式")
        sys.exit(1)
    
    # 打印统计信息
    logger.info("语义还原完成")
    logger.info(f"总文件数: {stats['total_files']}")
    logger.info(f"成功还原: {stats['successfully_restored']}")
    logger.info(f"失败文件数: {stats['failed_to_restore']}")
    
    if stats['failed_to_restore'] > 0:
        logger.warning("以下文件还原失败:")
        for file_path in stats['failed_files']:
            logger.warning(f"  - {file_path}")
    
    # 输出统计信息路径
    stats_path = os.path.join(args.output_dir, "restoration_stats.json")
    logger.info(f"详细统计信息已保存至: {stats_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}", exc_info=True)
        sys.exit(1) 