"""
语义还原客户端，用于处理源码文件并调用LLM进行语义还原
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

# 导入项目内部模块
# 注意：这里假设以下模块已存在，根据实际情况调整导入路径
from src.llm.llm_client import LLMClient
from src.llm.util.data_processor import ModelingDataProcessor
from src.llm.util.prompt_template import PromptTemplate

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("semantic_restoration_client")

class SemanticRestorationClient:
    """
    语义还原客户端，处理源码文件并调用LLM进行语义还原
    """
    
    def __init__(
        self, 
        project_dir: str,
        modeling_dir: str,
        output_dir: str,
        llm_client: Optional[LLMClient] = None,
        batch_size: int = 1,
        max_retries: int = 3,
        retry_delay: int = 5,
        use_context: bool = True,
        max_context_files: int = 2
    ):
        """
        初始化语义还原客户端
        
        参数:
            project_dir: Java项目目录路径
            modeling_dir: 建模数据目录路径
            output_dir: 输出目录路径
            llm_client: LLM客户端实例，如果为None则创建新实例
            batch_size: 批处理大小
            max_retries: 最大重试次数
            retry_delay: 重试延迟秒数
            use_context: 是否使用上下文文件
            max_context_files: 最大上下文文件数量
        """
        self.project_dir = os.path.abspath(project_dir)
        self.modeling_dir = os.path.abspath(modeling_dir)
        self.output_dir = os.path.abspath(output_dir)
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置LLM客户端
        self.llm_client = llm_client if llm_client else LLMClient()
        
        # 设置数据处理器
        self.data_processor = ModelingDataProcessor(
            project_dir=self.project_dir,
            modeling_dir=self.modeling_dir,
            batch_size=batch_size
        )
        
        # 设置其他参数
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.use_context = use_context
        self.max_context_files = max_context_files
        
        # 存储处理结果
        self.restoration_results = {}
        self.failed_files = []
        
        logger.info(f"初始化语义还原客户端: 项目目录={project_dir}, 建模目录={modeling_dir}, 输出目录={output_dir}")
    
    def load_data(self) -> None:
        """
        加载所有必要的数据
        """
        logger.info("开始加载数据...")
        
        # 加载建模数据
        self.data_processor.load_modeling_data()
        
        # 扫描Java文件
        self.data_processor.scan_java_files()
        
        # 如果需要使用上下文，构建依赖关系
        if self.use_context:
            self.data_processor._build_dependencies()
        
        logger.info("数据加载完成")
    
    def _find_related_files(self, file_path: str, max_files: int = 2) -> List[str]:
        """
        查找与目标文件相关的文件
        
        参数:
            file_path: 目标文件路径
            max_files: 最大相关文件数量
        
        返回:
            相关文件路径列表
        """
        related_files = []
        
        # 获取依赖该文件的文件（被依赖关系）
        dependent_files = []
        for other_file, deps in self.data_processor.file_dependencies.items():
            if file_path in deps:
                dependent_files.append(other_file)
        
        # 获取该文件依赖的文件（依赖关系）
        dependency_files = list(self.data_processor.file_dependencies.get(file_path, []))
        
        # 合并并限制数量
        # 优先添加依赖关系，因为通常依赖的文件对理解当前文件更重要
        for f in dependency_files + dependent_files:
            if f not in related_files and len(related_files) < max_files:
                related_files.append(f)
        
        return related_files
    
    def restore_file(self, file_path: str) -> Dict:
        """
        还原单个文件
        
        参数:
            file_path: 文件相对路径
        
        返回:
            还原结果字典
        """
        logger.info(f"开始还原文件: {file_path}")
        
        # 获取文件数据
        file_data = self.data_processor.gather_file_modeling_data(file_path)
        
        if not file_data:
            logger.warning(f"无法获取文件 {file_path} 的数据")
            self.failed_files.append(file_path)
            return {"error": "无法获取文件数据"}
        
        # 格式化为提示词数据
        prompt_data = self.data_processor.generate_prompt_data(file_path)
        
        # 如果使用上下文，查找相关文件
        related_files_data = []
        if self.use_context:
            related_files = self._find_related_files(file_path, self.max_context_files)
            for rel_file in related_files:
                rel_file_data = self.data_processor.gather_file_modeling_data(rel_file)
                if rel_file_data:
                    related_files_data.append(rel_file_data)
        
        # 构造用户提示词
        if self.use_context and related_files_data:
            user_prompt = PromptTemplate.generate_user_prompt_with_context(
                target_file_data=file_data,
                related_files=related_files_data,
                max_context_files=self.max_context_files
            )
        else:
            user_prompt = PromptTemplate.generate_user_prompt(
                source_code=prompt_data["source_code"],
                modeling_data=prompt_data
            )
        
        # 调用LLM进行还原
        retries = 0
        result = None
        
        while retries <= self.max_retries:
            try:
                # 调用LLM
                llm_response = self.llm_client.generate_completion(user_prompt)
                
                # 提取还原后的代码
                import re
                code_pattern = r"```java\s*(.*?)\s*```"
                code_match = re.search(code_pattern, llm_response, re.DOTALL)
                
                if code_match:
                    restored_code = code_match.group(1).strip()
                    result = PromptTemplate.format_restoration_result(
                        restored_code=restored_code,
                        original_file_path=file_path,
                        debug_info={"llm_response": llm_response}
                    )
                    break
                else:
                    logger.warning(f"无法从LLM响应中提取代码: {file_path}")
                    retries += 1
                    time.sleep(self.retry_delay)
            
            except Exception as e:
                logger.error(f"调用LLM时出错: {str(e)}")
                retries += 1
                time.sleep(self.retry_delay)
        
        if result:
            # 存储结果
            self.restoration_results[file_path] = result
            
            # 保存到输出目录
            self._save_restored_file(result)
            
            logger.info(f"成功还原文件: {file_path}")
            return result
        else:
            logger.error(f"还原文件失败: {file_path}")
            self.failed_files.append(file_path)
            return {"error": "LLM还原失败"}
    
    def restore_batch(self, file_paths: List[str]) -> List[Dict]:
        """
        批量还原多个文件
        
        参数:
            file_paths: 文件路径列表
        
        返回:
            还原结果字典列表
        """
        if len(file_paths) > self.batch_size:
            logger.warning(f"文件数量 {len(file_paths)} 超过批处理大小 {self.batch_size}，将仅处理前 {self.batch_size} 个文件")
            file_paths = file_paths[:self.batch_size]
        
        logger.info(f"开始批量还原 {len(file_paths)} 个文件")
        
        # 收集文件数据
        file_data_list = []
        for file_path in file_paths:
            file_data = self.data_processor.gather_file_modeling_data(file_path)
            if file_data:
                file_data_list.append(file_data)
            else:
                logger.warning(f"无法获取文件 {file_path} 的数据")
                self.failed_files.append(file_path)
        
        if not file_data_list:
            logger.warning("没有有效的文件数据可以处理")
            return []
        
        # 构造批处理提示词
        user_prompt = PromptTemplate.generate_batch_user_prompt(file_data_list)
        
        # 调用LLM进行还原
        retries = 0
        results = []
        
        while retries <= self.max_retries:
            try:
                # 调用LLM
                llm_response = self.llm_client.generate_completion(user_prompt)
                
                # 解析响应
                valid_paths = [data["file_path"] for data in file_data_list]
                parsed_results = PromptTemplate.parse_batch_result(llm_response, valid_paths)
                
                if parsed_results:
                    results = parsed_results
                    break
                else:
                    logger.warning("无法从LLM响应中解析结果")
                    retries += 1
                    time.sleep(self.retry_delay)
            
            except Exception as e:
                logger.error(f"调用LLM时出错: {str(e)}")
                retries += 1
                time.sleep(self.retry_delay)
        
        if results:
            # 存储结果并保存到输出目录
            for result in results:
                file_path = result["original_file_path"]
                self.restoration_results[file_path] = result
                self._save_restored_file(result)
            
            logger.info(f"成功批量还原 {len(results)} 个文件")
            return results
        else:
            logger.error(f"批量还原失败")
            for file_path in file_paths:
                if file_path not in self.failed_files:
                    self.failed_files.append(file_path)
            return []
    
    def _save_restored_file(self, result: Dict) -> None:
        """
        保存还原后的文件
        
        参数:
            result: 还原结果字典
        """
        original_path = result["original_file_path"]
        restored_code = result["restored_code"]
        
        # 构造输出路径
        output_path = os.path.join(self.output_dir, original_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(restored_code)
        
        logger.info(f"已保存还原文件: {output_path}")
    
    def restore_all_files(self) -> Dict:
        """
        还原所有Java文件
        
        返回:
            包含还原统计信息的字典
        """
        logger.info("开始还原所有文件")
        
        # 确保数据已加载
        if not self.data_processor.java_files:
            self.load_data()
        
        total_files = len(self.data_processor.java_files)
        successfully_restored = 0
        failed_to_restore = 0
        
        # 如果使用上下文，首先进行文件排序
        if self.use_context:
            file_list = self.data_processor.prioritize_files()
        else:
            file_list = self.data_processor.java_files
        
        # 如果批处理大小大于1，按批次处理
        if self.batch_size > 1:
            batches = [file_list[i:i+self.batch_size] for i in range(0, len(file_list), self.batch_size)]
            
            for i, batch in enumerate(batches):
                logger.info(f"处理批次 {i+1}/{len(batches)}")
                results = self.restore_batch(batch)
                successfully_restored += len(results)
                failed_to_restore += len(batch) - len(results)
                
                # 处理完一个批次后暂停一下，避免API速率限制
                if i < len(batches) - 1:
                    time.sleep(2)
        else:
            # 逐个处理文件
            for i, file_path in enumerate(file_list):
                logger.info(f"处理文件 {i+1}/{total_files}: {file_path}")
                result = self.restore_file(file_path)
                
                if "error" not in result:
                    successfully_restored += 1
                else:
                    failed_to_restore += 1
                
                # 每处理10个文件暂停一下，避免API速率限制
                if i % 10 == 9 and i < total_files - 1:
                    time.sleep(2)
        
        # 保存处理统计信息
        stats = {
            "total_files": total_files,
            "successfully_restored": successfully_restored,
            "failed_to_restore": failed_to_restore,
            "failed_files": self.failed_files
        }
        
        # 将统计信息保存到文件
        stats_path = os.path.join(self.output_dir, "restoration_stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"所有文件处理完成: 成功={successfully_restored}, 失败={failed_to_restore}")
        return stats
    
    def restore_specific_files(self, file_paths: List[str]) -> Dict:
        """
        还原指定的Java文件
        
        参数:
            file_paths: 要还原的文件路径列表
        
        返回:
            包含还原统计信息的字典
        """
        logger.info(f"开始还原指定的 {len(file_paths)} 个文件")
        
        # 确保数据已加载
        if not self.data_processor.java_files:
            self.load_data()
        
        # 验证文件路径是否存在于项目中
        valid_paths = []
        for path in file_paths:
            if path in self.data_processor.java_files:
                valid_paths.append(path)
            else:
                logger.warning(f"文件 {path} 不存在于项目中，将被跳过")
                self.failed_files.append(path)
        
        total_files = len(valid_paths)
        successfully_restored = 0
        failed_to_restore = 0
        
        # 按批次处理
        if self.batch_size > 1:
            batches = [valid_paths[i:i+self.batch_size] for i in range(0, len(valid_paths), self.batch_size)]
            
            for i, batch in enumerate(batches):
                logger.info(f"处理批次 {i+1}/{len(batches)}")
                results = self.restore_batch(batch)
                successfully_restored += len(results)
                failed_to_restore += len(batch) - len(results)
                
                # 处理完一个批次后暂停一下，避免API速率限制
                if i < len(batches) - 1:
                    time.sleep(2)
        else:
            # 逐个处理文件
            for i, file_path in enumerate(valid_paths):
                logger.info(f"处理文件 {i+1}/{total_files}: {file_path}")
                result = self.restore_file(file_path)
                
                if "error" not in result:
                    successfully_restored += 1
                else:
                    failed_to_restore += 1
                
                # 每处理10个文件暂停一下，避免API速率限制
                if i % 10 == 9 and i < total_files - 1:
                    time.sleep(2)
        
        # 保存处理统计信息
        stats = {
            "total_files": total_files,
            "successfully_restored": successfully_restored,
            "failed_to_restore": failed_to_restore,
            "failed_files": self.failed_files
        }
        
        # 将统计信息保存到文件
        stats_path = os.path.join(self.output_dir, "restoration_stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"指定文件处理完成: 成功={successfully_restored}, 失败={failed_to_restore}")
        return stats


def test_semantic_restoration_client():
    """
    测试语义还原客户端
    """
    # 示例路径
    project_dir = "/path/to/java/project"
    modeling_dir = "/path/to/modeling/data"
    output_dir = "/path/to/output"
    
    # 创建客户端
    client = SemanticRestorationClient(
        project_dir=project_dir,
        modeling_dir=modeling_dir,
        output_dir=output_dir,
        batch_size=1,
        use_context=True
    )
    
    # 加载数据
    client.load_data()
    
    # 还原特定文件（示例）
    file_path = "src/main/java/com/example/service/UserService.java"
    if file_path in client.data_processor.java_files:
        result = client.restore_file(file_path)
        print(f"还原结果: {result}")
    else:
        print(f"文件 {file_path} 不存在")
    
    # 还原所有文件（通常不在测试中运行，这里仅作示例）
    # stats = client.restore_all_files()
    # print(f"还原统计: {stats}")


if __name__ == "__main__":
    test_semantic_restoration_client() 