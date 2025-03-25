"""
实验运行器模块，设计和执行各种语义还原实验
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.llm.llm_client import LLMClient
from src.llm.code_restoration import CodeRestorer
from utils.modeling_parser import ModelingParser
from src.config.config import AVAILABLE_MODELS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("experiments.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("experiment_runner")

class ExperimentRunner:
    """
    实验运行器类，负责设计和执行语义还原实验
    """
    
    def __init__(
        self, 
        modeling_file: str,
        output_dir: str = "results",
        model: str = None,
        api_key: str = None
    ):
        """
        初始化实验运行器
        
        参数:
            modeling_file: 建模结果文件路径
            output_dir: 实验结果输出目录
            model: 使用的LLM模型
            api_key: API密钥
        """
        self.modeling_file = modeling_file
        self.output_dir = output_dir
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建LLM客户端
        self.llm_client = LLMClient(model=model, api_key=api_key)
        
        # 创建代码还原器
        self.code_restorer = CodeRestorer(self.llm_client)
        
        # 解析建模结果
        self.parser = ModelingParser(modeling_file)
        self.modeling_data = self.parser.parse()
        
        logger.info(f"实验运行器初始化完成，使用模型: {self.llm_client.model}")
    
    def read_java_file(self, file_path: str) -> str:
        """
        读取Java源代码文件
        
        参数:
            file_path: 文件路径
        
        返回:
            文件内容字符串
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件 {file_path} 失败: {str(e)}")
            return ""
    
    def write_java_file(self, file_path: str, content: str) -> bool:
        """
        写入Java源代码文件
        
        参数:
            file_path: 文件路径
            content: 文件内容
        
        返回:
            是否成功写入
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"写入文件 {file_path} 失败: {str(e)}")
            return False
    
    def run_dependency_injection_experiment(self, 
                                           class_name: str, 
                                           source_file: str,
                                           save_result: bool = True) -> Dict[str, Any]:
        """
        运行依赖注入还原实验
        
        参数:
            class_name: 类名
            source_file: 源代码文件路径
            save_result: 是否保存结果
        
        返回:
            实验结果字典
        """
        logger.info(f"开始依赖注入还原实验，类: {class_name}")
        
        # 读取源代码
        original_code = self.read_java_file(source_file)
        if not original_code:
            logger.error(f"读取源文件 {source_file} 失败")
            return {"success": False, "error": f"读取源文件失败"}
        
        # 获取类的依赖信息
        modeling_info = self.parser.format_for_code_restoration(class_name)
        
        # 开始计时
        start_time = time.time()
        
        # 执行代码还原
        restored_code = self.code_restorer.restore_dependency_injection(original_code, modeling_info.get("beans", []))
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        result = {
            "class_name": class_name,
            "success": bool(restored_code and not restored_code.startswith("错误")),
            "original_code": original_code,
            "restored_code": restored_code,
            "time_taken": elapsed_time,
            "model_used": self.llm_client.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存结果
        if save_result:
            output_file = os.path.join(self.output_dir, f"{class_name}_di_experiment.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # 保存还原的代码
            if result["success"]:
                output_code_file = os.path.join(self.output_dir, f"{class_name}_restored.java")
                self.write_java_file(output_code_file, restored_code)
            
            logger.info(f"依赖注入还原实验结果已保存到 {output_file}")
        
        return result
    
    def run_aop_experiment(self, 
                           class_name: str, 
                           source_file: str,
                           save_result: bool = True) -> Dict[str, Any]:
        """
        运行AOP切面还原实验
        
        参数:
            class_name: 类名
            source_file: 源代码文件路径
            save_result: 是否保存结果
        
        返回:
            实验结果字典
        """
        logger.info(f"开始AOP切面还原实验，类: {class_name}")
        
        # 读取源代码
        original_code = self.read_java_file(source_file)
        if not original_code:
            logger.error(f"读取源文件 {source_file} 失败")
            return {"success": False, "error": f"读取源文件失败"}
        
        # 获取类的依赖信息
        modeling_info = self.parser.format_for_code_restoration(class_name)
        
        # 开始计时
        start_time = time.time()
        
        # 执行代码还原
        restored_code = self.code_restorer.restore_aop(original_code, modeling_info.get("aop", []))
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        result = {
            "class_name": class_name,
            "success": bool(restored_code and not restored_code.startswith("错误")),
            "original_code": original_code,
            "restored_code": restored_code,
            "time_taken": elapsed_time,
            "model_used": self.llm_client.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存结果
        if save_result:
            output_file = os.path.join(self.output_dir, f"{class_name}_aop_experiment.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # 保存还原的代码
            if result["success"]:
                output_code_file = os.path.join(self.output_dir, f"{class_name}_aop_restored.java")
                self.write_java_file(output_code_file, restored_code)
            
            logger.info(f"AOP切面还原实验结果已保存到 {output_file}")
        
        return result
    
    def run_complete_restoration_experiment(self, 
                                           class_name: str, 
                                           source_file: str,
                                           save_result: bool = True) -> Dict[str, Any]:
        """
        运行完整的代码还原实验，包括依赖注入和AOP切面
        
        参数:
            class_name: 类名
            source_file: 源代码文件路径
            save_result: 是否保存结果
        
        返回:
            实验结果字典
        """
        logger.info(f"开始完整代码还原实验，类: {class_name}")
        
        # 读取源代码
        original_code = self.read_java_file(source_file)
        if not original_code:
            logger.error(f"读取源文件 {source_file} 失败")
            return {"success": False, "error": f"读取源文件失败"}
        
        # 获取类的依赖信息
        modeling_info = self.parser.format_for_code_restoration(class_name)
        
        # 开始计时
        start_time = time.time()
        
        # 执行代码还原
        restored_code = self.code_restorer.restore_code(original_code, modeling_info)
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        result = {
            "class_name": class_name,
            "success": bool(restored_code and not restored_code.startswith("错误")),
            "original_code": original_code,
            "restored_code": restored_code,
            "time_taken": elapsed_time,
            "model_used": self.llm_client.model,
            "modeling_info": modeling_info,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存结果
        if save_result:
            output_file = os.path.join(self.output_dir, f"{class_name}_complete_experiment.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # 保存还原的代码
            if result["success"]:
                output_code_file = os.path.join(self.output_dir, f"{class_name}_complete_restored.java")
                self.write_java_file(output_code_file, restored_code)
            
            logger.info(f"完整代码还原实验结果已保存到 {output_file}")
        
        return result
    
    def run_model_comparison_experiment(self, 
                                        class_name: str, 
                                        source_file: str,
                                        models: List[str] = None,
                                        save_result: bool = True) -> Dict[str, Any]:
        """
        运行不同模型的对比实验
        
        参数:
            class_name: 类名
            source_file: 源代码文件路径
            models: 要比较的模型列表
            save_result: 是否保存结果
        
        返回:
            实验结果字典
        """
        logger.info(f"开始模型对比实验，类: {class_name}")
        
        # 读取源代码
        original_code = self.read_java_file(source_file)
        if not original_code:
            logger.error(f"读取源文件 {source_file} 失败")
            return {"success": False, "error": f"读取源文件失败"}
        
        # 获取类的依赖信息
        modeling_info = self.parser.format_for_code_restoration(class_name)
        
        # 如果没有指定模型，使用配置中的可用模型
        if not models:
            models = list(AVAILABLE_MODELS.keys())
        
        results = {}
        
        # 对每个模型进行实验
        for model_name in models:
            logger.info(f"模型 {model_name} 的还原实验开始")
            
            # 创建模型特定的LLM客户端
            model_client = LLMClient(model=model_name)
            
            # 创建代码还原器
            model_restorer = CodeRestorer(model_client)
            
            # 开始计时
            start_time = time.time()
            
            # 执行代码还原
            restored_code = model_restorer.restore_code(original_code, modeling_info)
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            # 记录结果
            results[model_name] = {
                "success": bool(restored_code and not restored_code.startswith("错误")),
                "restored_code": restored_code,
                "time_taken": elapsed_time,
                "model": model_client.model
            }
            
            # 保存该模型的还原代码
            if save_result and results[model_name]["success"]:
                output_code_file = os.path.join(self.output_dir, f"{class_name}_{model_name}_restored.java")
                self.write_java_file(output_code_file, restored_code)
        
        # 汇总结果
        comparison_result = {
            "class_name": class_name,
            "original_code": original_code,
            "model_results": results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存结果
        if save_result:
            output_file = os.path.join(self.output_dir, f"{class_name}_model_comparison.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(comparison_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"模型对比实验结果已保存到 {output_file}")
        
        return comparison_result
    
    def run_batch_experiment(self, 
                            experiment_type: str,
                            class_config: List[Dict[str, str]],
                            save_result: bool = True) -> Dict[str, Any]:
        """
        批量运行实验
        
        参数:
            experiment_type: 实验类型，可选值："di"（依赖注入）、"aop"、"complete"（完整还原）、"model_comparison"
            class_config: 类配置列表，每个元素包含"class_name"和"source_file"
            save_result: 是否保存结果
        
        返回:
            实验结果字典
        """
        logger.info(f"开始批量 {experiment_type} 实验，共 {len(class_config)} 个类")
        
        results = {}
        
        for config in class_config:
            class_name = config["class_name"]
            source_file = config["source_file"]
            
            logger.info(f"处理类 {class_name}, 源文件: {source_file}")
            
            if experiment_type == "di":
                result = self.run_dependency_injection_experiment(class_name, source_file, save_result)
            elif experiment_type == "aop":
                result = self.run_aop_experiment(class_name, source_file, save_result)
            elif experiment_type == "complete":
                result = self.run_complete_restoration_experiment(class_name, source_file, save_result)
            elif experiment_type == "model_comparison":
                models = config.get("models", None)
                result = self.run_model_comparison_experiment(class_name, source_file, models, save_result)
            else:
                logger.error(f"未知的实验类型: {experiment_type}")
                continue
            
            results[class_name] = result
        
        # 汇总结果
        batch_result = {
            "experiment_type": experiment_type,
            "total_classes": len(class_config),
            "successful_restorations": sum(1 for r in results.values() if r.get("success", False)),
            "class_results": results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存结果
        if save_result:
            output_file = os.path.join(self.output_dir, f"batch_{experiment_type}_experiment.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"批量实验结果已保存到 {output_file}")
        
        return batch_result


def main():
    """
    主函数，处理命令行参数并运行实验
    """
    parser = argparse.ArgumentParser(description="语义还原实验运行器")
    
    parser.add_argument("--modeling-file", "-m", required=True, help="建模结果文件路径")
    parser.add_argument("--output-dir", "-o", default="results", help="输出目录")
    parser.add_argument("--model", default=None, help="使用的LLM模型")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 依赖注入实验
    di_parser = subparsers.add_parser("di", help="运行依赖注入还原实验")
    di_parser.add_argument("--class-name", "-c", required=True, help="类名")
    di_parser.add_argument("--source-file", "-s", required=True, help="源代码文件路径")
    
    # AOP实验
    aop_parser = subparsers.add_parser("aop", help="运行AOP切面还原实验")
    aop_parser.add_argument("--class-name", "-c", required=True, help="类名")
    aop_parser.add_argument("--source-file", "-s", required=True, help="源代码文件路径")
    
    # 完整还原实验
    complete_parser = subparsers.add_parser("complete", help="运行完整代码还原实验")
    complete_parser.add_argument("--class-name", "-c", required=True, help="类名")
    complete_parser.add_argument("--source-file", "-s", required=True, help="源代码文件路径")
    
    # 模型对比实验
    compare_parser = subparsers.add_parser("compare", help="运行模型对比实验")
    compare_parser.add_argument("--class-name", "-c", required=True, help="类名")
    compare_parser.add_argument("--source-file", "-s", required=True, help="源代码文件路径")
    compare_parser.add_argument("--models", "-m", nargs="+", help="要比较的模型列表")
    
    # 批量实验
    batch_parser = subparsers.add_parser("batch", help="批量运行实验")
    batch_parser.add_argument("--experiment-type", "-t", required=True, choices=["di", "aop", "complete", "model_comparison"], help="实验类型")
    batch_parser.add_argument("--config-file", "-f", required=True, help="配置文件路径，JSON格式，包含类配置列表")
    
    args = parser.parse_args()
    
    # 创建实验运行器
    runner = ExperimentRunner(
        modeling_file=args.modeling_file,
        output_dir=args.output_dir,
        model=args.model
    )
    
    # 根据命令执行相应的实验
    if args.command == "di":
        runner.run_dependency_injection_experiment(args.class_name, args.source_file)
    elif args.command == "aop":
        runner.run_aop_experiment(args.class_name, args.source_file)
    elif args.command == "complete":
        runner.run_complete_restoration_experiment(args.class_name, args.source_file)
    elif args.command == "compare":
        runner.run_model_comparison_experiment(args.class_name, args.source_file, args.models)
    elif args.command == "batch":
        # 读取配置文件
        try:
            with open(args.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if not isinstance(config, list):
                logger.error("配置文件格式错误，应为类配置列表")
                return
            
            runner.run_batch_experiment(args.experiment_type, config)
        except Exception as e:
            logger.error(f"读取配置文件失败: {str(e)}")
    else:
        logger.error("未指定有效的命令")


if __name__ == "__main__":
    main() 