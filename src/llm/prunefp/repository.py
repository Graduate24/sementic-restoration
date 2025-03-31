"""
代码检索工具，负责从Java项目中获取方法源码、调用图和Jimple IR
"""

import os
import re
import json
import logging
import subprocess
from typing import Dict, List, Any, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prunefp_repository")


class SourceCodeRepository:
    """
    代码检索工具类，用于获取Java代码的相关信息
    """

    def __init__(self, project_path: str, code_index: str, code_index_jar: Optional[str] = None):
        """
        初始化代码检索工具
        
        参数:
            project_path: Java项目根目录
            code_index: 代码索引目录路径，包含call_graph.json和jimple目录
            code_index_jar: code-index工具的jar包路径（可选）
        """
        self.project_path = os.path.abspath(project_path)
        self.code_index = os.path.abspath(code_index)
        self.code_index_jar = code_index_jar or "/home/ran/Documents/work/graduate/code-index/target/code-index-1.0-SNAPSHOT.jar"

        # 加载调用图
        self.call_graph_path = os.path.join(self.code_index, "call_graph.json")
        self.jimple_dir = os.path.join(self.code_index, "jimple")

        # 缓存
        self.method_cache = {}
        self.jimple_cache = {}
        self.call_graph_cache = {}

        logger.info(f"初始化代码检索工具: 项目路径={project_path}, 代码索引={code_index}")
        self._cache_all_call_graph()

    def _cache_all_call_graph(self):
        if not os.path.exists(self.call_graph_path):
            logger.warning(f"未找到调用图文件: {self.call_graph_path}")
            return None

        with open(self.call_graph_path, 'r', encoding='utf-8') as f:
            call_graph_data = json.load(f)

        self.call_graph_cache = call_graph_data

    def get_method_source(self, class_name: str, method_name: str, signature: Optional[str] = None) -> Optional[str]:
        """
        获取方法的源代码实现
        
        参数:
            class_name: 完整的类名（包含包名）
            method_name: 方法名
            signature: 方法签名
            
        返回:
            方法源代码，如果未找到则返回None
        """
        # 生成缓存键
        cache_key = f"<{class_name}: {method_name}>"
        if signature:
            cache_key = signature

        # 检查缓存
        if cache_key in self.method_cache:
            logger.debug(f"使用缓存的方法源码: {cache_key}")
            return self.method_cache[cache_key]

        logger.info(f"查找方法源码: {cache_key}")

        try:
            # 使用code-index工具提取方法源码
            command = f"java -jar {self.code_index_jar} -s {self.project_path} -extract -m \"{cache_key}\""
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                # 提取源码（在BEGIN和END标记之间）
                source_code = self._extract_between_markers(result.stdout)
                if source_code:
                    self.method_cache[cache_key] = source_code
                    return source_code

            logger.warning(f"未能提取到方法源码: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"提取方法源码时出错: {str(e)}")
            return None

    def get_method_jimple(self, class_name: str, method_name: str, signature: Optional[str] = None) -> Optional[str]:
        """
        获取方法的Jimple中间表示
        
        参数:
            class_name: 完整的类名（包含包名）
            method_name: 方法名
            signature: 方法签名
            
        返回:
            Jimple IR，如果未找到则返回None
        """
        # 生成缓存键
        cache_key = signature or f"{class_name}.{method_name}"

        # 检查缓存
        if cache_key in self.jimple_cache:
            logger.debug(f"使用缓存的Jimple IR: {cache_key}")
            return self.jimple_cache[cache_key]

        logger.info(f"查找方法Jimple IR: {cache_key}")

        try:
            # 从jimple目录中读取对应的文件
            class_path = class_name.replace('.', '/')
            jimple_file = os.path.join(self.jimple_dir, f"{class_path}.jimple")

            if not os.path.exists(jimple_file):
                logger.warning(f"未找到Jimple文件: {jimple_file}")
                return None

            with open(jimple_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取特定方法的Jimple IR
            method_jimple = self._extract_method_jimple(content, method_name, signature)

            if method_jimple:
                self.jimple_cache[cache_key] = method_jimple
                return method_jimple

            logger.warning(f"未找到方法的Jimple IR: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"获取Jimple IR时出错: {str(e)}")
            return None

    def get_call_graph(self, class_name: str, method_name: str, signature: Optional[str] = None) -> Optional[str]:
        """
        获取方法的调用图
        
        参数:
            class_name: 完整的类名（包含包名）
            method_name: 方法名
            signature: 方法签名
            
        返回:
            调用图文本表示，如果未找到则返回None
        """
        # 生成缓存键
        cache_key = signature or f"<{class_name}: {method_name}>"

        # 检查缓存
        if cache_key in self.call_graph_cache:
            logger.debug(f"使用缓存的调用图: {cache_key}")
            return self.call_graph_cache[cache_key]

        logger.warning(f"未找到方法的调用图: {cache_key}")
        return None

    def _extract_between_markers(self, text, start_marker="++++++++++++++++++++++++++++++++",
                                end_marker="-----------------------------"):
        """提取两个标记之间的内容"""
        try:
            # 查找开始标记的位置
            start_index = text.find(start_marker)
            if start_index == -1:
                return None  # 没找到开始标记

            # 计算内容开始的位置（开始标记之后）
            content_start = start_index + len(start_marker)

            # 从内容开始处查找结束标记
            end_index = text.find(end_marker, content_start)
            if end_index == -1:
                return None  # 没找到结束标记

            # 提取两个标记之间的内容
            extracted_content = text[content_start:end_index].strip()
            return extracted_content

        except Exception as e:
            print(f"提取内容时出错: {e}")
            return None


    def _extract_method_jimple(self, content: str, method_name: str, signature: Optional[str] = None) -> Optional[str]:
        """
        从Jimple文件内容中提取特定方法的IR
        """
        if signature:
            # 使用完整签名匹配
            pattern = fr'(.*{signature}.*?}})'
        else:
            # 使用方法名匹配
            pattern = fr'(\s*(?:public|protected|private|static|final|abstract|synchronized|native)*\s+.*?\s+{method_name}\s*\([^)]*\).*?}})'

        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _find_method_call_graph(self, call_graph_data: Dict, class_name: str, method_name: str,
                                signature: Optional[str] = None) -> Optional[Dict]:
        """
        在调用图数据中查找特定方法的调用关系
        """
        method_key = signature or f"<{class_name}: {method_name}>"

        # 在调用图中查找方法
        for node in call_graph_data.get("nodes", []):
            if node.get("signature") == method_key or node.get("method") == method_key:
                # 构建该方法的调用图
                return {
                    "method": node.get("method", method_key),
                    "callers": node.get("callers", []),
                    "callees": node.get("callees", [])
                }

        return None
