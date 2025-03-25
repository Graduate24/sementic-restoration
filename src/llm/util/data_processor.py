"""
数据处理工具，用于组织源码文件和对应的建模信息
"""

import os
import json
import re
import logging
from typing import Dict, List, Set, Any, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("data_processor")


class ModelingDataProcessor:
    """
    处理源码和建模数据，为语义还原准备输入
    """

    def __init__(
            self,
            project_dir: str,
            modeling_dir: str,
            batch_size: int = 1,
            java_ext: str = ".java"
    ):
        """
        初始化数据处理器
        
        参数:
            project_dir: Java项目目录路径
            modeling_dir: 建模数据目录路径
            batch_size: 每批处理的文件数，默认为1
            java_ext: Java文件扩展名，默认为.java
        """
        self.project_dir = os.path.abspath(project_dir)
        self.modeling_dir = os.path.abspath(modeling_dir)
        self.batch_size = batch_size
        self.java_ext = java_ext

        # 索引和建模数据
        self.aop_data = {}
        self.ioc_data = {}
        self.field_definitions = {}
        self.field_references = {}
        self.method_definitions = {}
        self.method_invocations = {}
        self.call_graph = {}
        # 暂时不支持MyBatis
        self.mybatis_mapping = {}
        self.grouped_method_invocations = {}
        self.grouped_method_definitions = {}
        self.grouped_field_definitions = {}

        # 文件列表和依赖关系
        self.java_files = []
        self.file_dependencies = {}

        logger.info(f"初始化数据处理器: 项目目录={project_dir}, 建模目录={modeling_dir}")

    def load_modeling_data(self) -> None:
        """
        加载所有建模数据和索引信息
        """
        logger.info("开始加载建模数据...")

        model_dir = os.path.join(self.modeling_dir, "model")
        # 加载AOP数据
        aop_file = os.path.join(model_dir, "aop.json")
        if os.path.exists(aop_file):
            with open(aop_file, 'r', encoding='utf-8') as f:
                self.aop_data = json.load(f)
            logger.info(f"已加载AOP数据: {len(self.aop_data)} 条记录")

        # 加载IoC数据
        ioc_file = os.path.join(model_dir, "ioc.json")
        if os.path.exists(ioc_file):
            with open(ioc_file, 'r', encoding='utf-8') as f:
                self.ioc_data = json.load(f)
            logger.info(f"已加载IoC数据: {len(self.ioc_data)} 条记录")

        # 加载索引数据
        index_dir = os.path.join(self.modeling_dir, "index")

        # 字段定义
        field_def_file = os.path.join(index_dir, "field_definitions.json")
        if os.path.exists(field_def_file):
            with open(field_def_file, 'r', encoding='utf-8') as f:
                self.field_definitions = json.load(f)
            logger.info(f"已加载字段定义: {len(self.field_definitions)} 条记录")

        # 字段引用
        field_ref_file = os.path.join(index_dir, "field_references.json")
        if os.path.exists(field_ref_file):
            with open(field_ref_file, 'r', encoding='utf-8') as f:
                self.field_references = json.load(f)
            logger.info(f"已加载字段引用: {len(self.field_references)} 条记录")

        # 方法定义
        method_def_file = os.path.join(index_dir, "method_definitions.json")
        if os.path.exists(method_def_file):
            with open(method_def_file, 'r', encoding='utf-8') as f:
                self.method_definitions = json.load(f)
            logger.info(f"已加载方法定义: {len(self.method_definitions)} 条记录")

        # 方法调用
        method_invoc_file = os.path.join(index_dir, "method_invocations.json")
        if os.path.exists(method_invoc_file):
            with open(method_invoc_file, 'r', encoding='utf-8') as f:
                self.method_invocations = json.load(f)
            logger.info(f"已加载方法调用: {len(self.method_invocations)} 条记录")

        # 调用图
        call_graph_file = os.path.join(index_dir, "call_graph.json")
        if os.path.exists(call_graph_file):
            with open(call_graph_file, 'r', encoding='utf-8') as f:
                self.call_graph = json.load(f)
            logger.info(f"已加载调用图: {len(self.call_graph)} 条记录")

        # 对method invocation groupby
        self.grouped_method_invocations = self._groupby_class(self.method_invocations)
        self.grouped_method_definitions = self._groupby_class(self.method_definitions)
        self.grouped_field_definitions = self._groupby_class(self.field_definitions)

    def _groupby_class(self, methods):
        method_invoke_group = {}
        for k, v in methods.items():
            for i in v:
                if i['className'] not in method_invoke_group:
                    method_invoke_group[i['className']] = [i]
                else:
                    method_invoke_group[i['className']].append(i)
        return method_invoke_group

    def scan_java_files(self) -> List[str]:
        """
        扫描项目目录中的所有Java文件
        
        返回:
            Java文件路径列表
        """
        logger.info(f"开始扫描Java文件...")
        java_files = []

        for root, _, files in os.walk(self.project_dir):
            for file in files:
                if file.endswith(self.java_ext):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_dir)
                    java_files.append(rel_path)

        self.java_files = sorted(java_files)
        logger.info(f"共扫描到 {len(self.java_files)} 个Java文件")
        return self.java_files

    def _extract_package_class(self, file_path: str) -> Optional[str]:
        """
        从文件路径提取包名和类名
        
        参数:
            file_path: Java文件相对路径
        
        返回:
            完整的包名.类名字符串
        """
        try:
            with open(os.path.join(self.project_dir, file_path), 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取包名
            package_match = re.search(r'package\s+([\w.]+);', content)
            if not package_match:
                return None
            package_name = package_match.group(1)

            # 提取类名 - 修改正则表达式以匹配更多的类声明形式
            # 旧的正则表达式: r'(?:public|private|protected)?\s+(?:abstract|final)?\s+class\s+(\w+)'
            class_match = re.search(
                r'(?:@\w+(?:\([^)]*\))?(?:\s*|\s+))*(?:public|private|protected|)?\s*(?:abstract|final|static)?\s*(?:class|interface|enum)\s+(\w+)',
                content)
            if not class_match:
                # 尝试备用的简化正则表达式
                class_match = re.search(r'\bclass\s+(\w+)', content)
                if not class_match:
                    return None
            class_name = class_match.group(1)

            return f"{package_name}.{class_name}"
        except Exception as e:
            logger.error(f"提取包名和类名时出错: {str(e)}")
            return None

    def _find_related_aop(self, full_class_name: str) -> List:
        """
        查找与给定类相关的AOP切面，同时考虑类中的方法以及方法调用点
        
        参数:
            full_class_name: 完整的类名（包含包名）
        
        返回:
            包含方法级别和调用点级别AOP数据的字典
        """
        # 初始化结果容器
        result = []
        # 如果没有AOP数据则返回空结果
        if not self.aop_data:
            return result



        # 1. 获取类中的方法调用点
        """
         {
          "className": "edu.thu.benchmark.annotated.mapper.UserSqlInjectionMapper",
          "memberName": "findUsersSortedUnsafe",
          "signature": "<edu.thu.benchmark.annotated.mapper.UserSqlInjectionMapper: java.util.List findUsersSortedUnsafe(java.lang.String)>",
          "sourceFile": "edu.thu.benchmark.annotated.service.SqlInjectionTestService.java",
          "lineNumber": 47
        },
        """
        class_invocations = self.grouped_method_invocations.get(full_class_name, [])
        logger.debug(f"类 {full_class_name} 中找到 {len(class_invocations)} 个方法调用点")

        aspect_list = []
        # 2. 获取切面方法
        for aspect_type in ["beforeAspects", "afterAspects", "aroundAspects", "afterThrowingAspects"]:
            if aspect_type not in self.aop_data:
                continue
            """ aop.json
                 {
                  "targetMethods": [
                    {
                      "signature": "findUsersByAspectSafe(java.lang.String)",
                      "name": "findUsersByAspectSafe",
                      "declaringType": "edu.thu.benchmark.annotated.service.SqlInjectionTestService",
                      "returnType": "java.util.List"
                    }
                  ],
                  "adviceMethod": {
                    "signature": "beforeUnsafeSqlExecution()",
                    "name": "beforeUnsafeSqlExecution",
                    "type": "before",
                    "declaringType": "edu.thu.benchmark.annotated.aspect.SqlInjectionAspect",
                    "returnType": "void"
                  }
                },
                """
            for aop in self.aop_data[aspect_type]:
                for m in aop.get("targetMethods", []):
                    """ method_invocations.json
                        {
                      "findUsersSortedUnsafe": [
                        {
                          "className": "edu.thu.benchmark.annotated.mapper.UserSqlInjectionMapper",
                          "memberName": "findUsersSortedUnsafe",
                          "signature": "<edu.thu.benchmark.annotated.mapper.UserSqlInjectionMapper: java.util.List findUsersSortedUnsafe(java.lang.String)>",
                          "sourceFile": "edu.thu.benchmark.annotated.service.SqlInjectionTestService.java",
                          "lineNumber": 47
                        },
                        {
                          "className": "edu.thu.benchmark.annotated.service.SqlInjectionTestService",
                          "memberName": "findUsersSortedUnsafe",
                          "signature": "<edu.thu.benchmark.annotated.service.SqlInjectionTestService: java.util.List findUsersSortedUnsafe(java.lang.String)>",
                          "sourceFile": "edu.thu.benchmark.annotated.controller.SqlInjectionTestController.java",
                          "lineNumber": 65
                        }
                      ],
                    """
                    for invocations in class_invocations:
                        if invocations['signature'] != f"<{m['declaringType']}: {m['returnType']} {m['signature']}>":
                            continue

                        r = {'invocations': invocations, 'aspect_type': aspect_type}
                        """ method_definitions.json
                             "testCase27": [
                                {
                                  "className": "edu.thu.benchmark.annotated.controller.SqlInjectionTestController",
                                  "memberName": "testCase27",
                                  "signature": "<edu.thu.benchmark.annotated.controller.SqlInjectionTestController: int testCase27(java.lang.Integer)>",
                                  "sourceFile": "edu.thu.benchmark.annotated.controller.SqlInjectionTestController.java",
                                  "lineNumber": -1
                                }
                              ],
                        """
                        if aop['adviceMethod']['name'] in self.method_definitions:
                            for definitions in self.method_definitions[aop['adviceMethod']['name']]:
                                if definitions['signature'] == f"<{aop['adviceMethod']['declaringType']}: {aop['adviceMethod']['returnType']} {aop['adviceMethod']['signature']}>":
                                    r['definitions'] = definitions
                                    break

                        result.append(r)

        return result

    def _find_related_ioc(self, full_class_name: str) -> Dict:
        """
        查找与给定类相关的IoC连接

        参数:
            full_class_name: 完整的类名（包含包名）

        返回:
            相关的IoC连接数据
        """
        related_ioc = {}

        # 如果没有IoC数据则返回空结果
        if not self.ioc_data:
            return related_ioc

        # 遍历IoC数据查找与这个类相关的条目
        for key, value in self.ioc_data.items():
            if key.startswith(full_class_name + ".") or value.get("declaringType") == full_class_name:
                related_ioc[key] = value

        return related_ioc

    def _find_related_field_definitions(self, full_class_name: str) -> Dict:
        """
        查找与给定类相关的字段定义

        参数:
            full_class_name: 完整的类名（包含包名）

        返回:
            相关的字段定义数据
        """
        related_fields = {}

        # 遍历字段定义查找与这个类相关的条目
        for field_name, definitions in self.field_definitions.items():
            related_defs = []
            for definition in definitions:
                if definition.get("className") == full_class_name:
                    related_defs.append(definition)

            if related_defs:
                related_fields[field_name] = related_defs

        return related_fields

    def _find_related_field_references(self, full_class_name: str) -> Dict:
        """
        查找与给定类相关的字段引用

        参数:
            full_class_name: 完整的类名（包含包名）

        返回:
            相关的字段引用数据
        """
        related_refs = {}

        # 遍历字段引用查找与这个类相关的条目
        for field_name, references in self.field_references.items():
            related_field_refs = []
            for reference in references:
                if reference.get("className") == full_class_name:
                    related_field_refs.append(reference)

            if related_field_refs:
                related_refs[field_name] = related_field_refs

        return related_refs

    def _find_related_method_definitions(self, full_class_name: str) -> Dict:
        """
        查找与给定类相关的方法定义

        参数:
            full_class_name: 完整的类名（包含包名）

        返回:
            相关的方法定义数据
        """
        related_methods = {}

        # 遍历方法定义查找与这个类相关的条目
        for method_name, definitions in self.method_definitions.items():
            related_defs = []
            for definition in definitions:
                if definition.get("className") == full_class_name:
                    related_defs.append(definition)

            if related_defs:
                related_methods[method_name] = related_defs

        return related_methods

    def _find_related_method_invocations(self, full_class_name: str) -> Dict:
        """
        查找与给定类相关的方法调用

        参数:
            full_class_name: 完整的类名（包含包名）

        返回:
            相关的方法调用数据
        """
        related_invocations = {}

        # 遍历方法调用查找与这个类相关的条目
        for method_name, invocations in self.method_invocations.items():
            related_invocs = []
            for invocation in invocations:
                if invocation.get("className") == full_class_name:
                    related_invocs.append(invocation)

            if related_invocs:
                related_invocations[method_name] = related_invocs

        return related_invocations

    def _find_related_call_graph(self, full_class_name: str) -> Dict:
        """
        查找与给定类相关的调用图

        参数:
            full_class_name: 完整的类名（包含包名）

        返回:
            相关的调用图数据
        """
        related_call_graph = {}

        # 遍历调用图查找与这个类相关的条目
        for method_sig, called_methods in self.call_graph.items():
            # 检查方法签名是否属于这个类
            if f"<{full_class_name}:" in method_sig:
                related_call_graph[method_sig] = called_methods

        return related_call_graph

    def _find_related_mybatis(self, full_class_name: str) -> Dict:
        """
        查找与给定类相关的MyBatis映射

        参数:
            full_class_name: 完整的类名（包含包名）

        返回:
            相关的MyBatis映射数据
        """
        related_mybatis = {}

        # 如果没有MyBatis数据则返回空结果
        if not self.mybatis_mapping:
            return related_mybatis

        # 遍历MyBatis映射查找与这个类相关的条目
        for key, value in self.mybatis_mapping.items():
            if key.startswith(full_class_name + "."):
                related_mybatis[key] = value

        return related_mybatis

    def gather_file_modeling_data(self, file_path: str) -> Dict:
        """
        收集单个文件相关的所有建模数据

        参数:
            file_path: Java文件相对路径

        返回:
            包含相关建模数据的字典
        """
        full_class_name = self._extract_package_class(file_path)

        if not full_class_name:
            logger.warning(f"无法从文件 {file_path} 提取包名和类名")
            return {}

        # 读取源代码
        try:
            with open(os.path.join(self.project_dir, file_path), 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"读取源代码失败: {str(e)}")
            source_code = ""

        # 收集相关的建模数据
        aop_data = self._find_related_aop(full_class_name)
        ioc_data = self._find_related_ioc(full_class_name)
        field_def_data = self._find_related_field_definitions(full_class_name)
        field_ref_data = self._find_related_field_references(full_class_name)
        method_def_data = self._find_related_method_definitions(full_class_name)
        method_call_data = self._find_related_method_invocations(full_class_name)
        call_graph_data = self._find_related_call_graph(full_class_name)
        mybatis_data = self._find_related_mybatis(full_class_name)

        # 组装结果
        result = {
            "file_path": file_path,
            "full_class_name": full_class_name,
            "source_code": source_code,
            "modeling_data": {
                "aop_data": aop_data,
                "ioc_data": ioc_data,
                "field_def_data": field_def_data,
                "field_ref_data": field_ref_data,
                "method_def_data": method_def_data,
                "method_call_data": method_call_data,
                "call_graph_data": call_graph_data,
                # "mybatis_data": mybatis_data
            }
        }

        return result

    def generate_prompt_data(self, file_path: str) -> Dict:
        """
        为单个文件生成提示词所需的数据

        参数:
            file_path: Java文件相对路径

        返回:
            格式化的提示词数据
        """
        file_data = self.gather_file_modeling_data(file_path)
        if not file_data:
            return {}

        # 读取源代码
        try:
            with open(os.path.join(self.project_dir, file_path), 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"读取源代码失败: {str(e)}")
            source_code = ""

        # 格式化数据用于提示词
        prompt_data = {
            "source_code": source_code,
            "aop_data": json.dumps(file_data["modeling_data"]["aop_data"], indent=2) if file_data["modeling_data"][
                "aop_data"] else "{}",
            "ioc_data": json.dumps(file_data["modeling_data"]["ioc_data"], indent=2) if file_data["modeling_data"][
                "ioc_data"] else "{}",
            "mybatis_data": json.dumps(file_data["modeling_data"]["mybatis_data"], indent=2) if
            file_data["modeling_data"]["mybatis_data"] else "{}",
            "field_def_data": json.dumps(file_data["modeling_data"].get("field_def_data", {}), indent=2) if file_data[
                "modeling_data"].get("field_def_data") else "{}",
            "field_ref_data": json.dumps(file_data["modeling_data"].get("field_ref_data", {}), indent=2) if file_data[
                "modeling_data"].get("field_ref_data") else "{}",
            "method_def_data": json.dumps(file_data["modeling_data"].get("method_def_data", {}), indent=2) if file_data[
                "modeling_data"].get("method_def_data") else "{}",
            "method_call_data": json.dumps(file_data["modeling_data"].get("method_call_data", {}), indent=2) if
            file_data["modeling_data"].get("method_call_data") else "{}",
            "call_graph_data": json.dumps(file_data["modeling_data"].get("call_graph_data", {}), indent=2) if file_data[
                "modeling_data"].get("call_graph_data") else "{}",
        }

        return prompt_data

    def generate_batches(self) -> List[List[str]]:
        """
        将Java文件按批次划分

        返回:
            批次列表，每个批次包含多个文件路径
        """
        if not self.java_files:
            self.scan_java_files()

        batches = []
        for i in range(0, len(self.java_files), self.batch_size):
            batch = self.java_files[i:i + self.batch_size]
            batches.append(batch)

        logger.info(f"已将 {len(self.java_files)} 个文件划分为 {len(batches)} 个批次")
        return batches

    def prioritize_files(self) -> List[str]:
        """
        对Java文件进行优先级排序，以便有序处理

        返回:
            排序后的文件路径列表
        """
        if not self.java_files:
            self.scan_java_files()

        # 构建依赖关系
        self._build_dependencies()

        # 基于依赖关系进行排序
        sorted_files = self._topological_sort()

        logger.info(f"已完成文件优先级排序")
        return sorted_files

    def _build_dependencies(self) -> None:
        """
        构建文件之间的依赖关系
        """
        self.file_dependencies = {file: set() for file in self.java_files}
        file_to_class = {}

        # 先建立文件到类名的映射
        for file in self.java_files:
            full_class_name = self._extract_package_class(file)
            if full_class_name:
                file_to_class[file] = full_class_name

        # 根据导入关系建立依赖
        class_to_file = {v: k for k, v in file_to_class.items()}

        for file in self.java_files:
            try:
                with open(os.path.join(self.project_dir, file), 'r', encoding='utf-8') as f:
                    content = f.read()

                # 查找import语句
                imports = re.findall(r'import\s+([\w.]+)(?:\.\*)?;', content)

                for imp in imports:
                    # 检查是否导入了项目中的其他类
                    for cls_name, cls_file in class_to_file.items():
                        if cls_name.startswith(imp) and cls_file != file:
                            self.file_dependencies[file].add(cls_file)
                            break
            except Exception as e:
                logger.error(f"分析文件 {file} 依赖时出错: {str(e)}")

    def _topological_sort(self) -> List[str]:
        """
        对文件进行拓扑排序，以便先处理被依赖的文件

        返回:
            排序后的文件列表
        """
        result = []
        visited = set()
        temp_visited = set()

        def visit(file):
            if file in temp_visited:
                # 检测到循环依赖，简单处理
                return
            if file in visited:
                return

            temp_visited.add(file)

            for dep in self.file_dependencies[file]:
                visit(dep)

            temp_visited.remove(file)
            visited.add(file)
            result.append(file)

        for file in self.java_files:
            if file not in visited:
                visit(file)

        # 结果是拓扑排序的逆序，需要反转
        return result[::-1]


def test_data_processor():
    """
    测试数据处理器
    """
    # 示例项目和建模目录
    project_dir = "/path/to/your/java/project"
    modeling_dir = "/path/to/your/modeling/data"

    # 创建处理器
    processor = ModelingDataProcessor(project_dir, modeling_dir)

    # 模拟一些测试数据
    # 注意：在实际测试中应该使用真实数据
    processor.method_definitions = {
        "findById": [
            {
                "className": "com.example.service.UserService",
                "signature": "com.example.service.UserService.findById(Long)",
                "parameterTypes": ["java.lang.Long"]
            }
        ],
        "save": [
            {
                "className": "com.example.service.UserService",
                "signature": "com.example.service.UserService.save(User)",
                "parameterTypes": ["com.example.model.User"]
            }
        ],
        "findAll": [
            {
                "className": "com.example.repository.UserRepository",
                "signature": "com.example.repository.UserRepository.findAll()",
                "parameterTypes": []
            }
        ],
        "logBefore": [
            {
                "className": "com.example.aspect.LoggingAspect",
                "signature": "com.example.aspect.LoggingAspect.logBefore(JoinPoint)",
                "parameterTypes": ["org.aspectj.lang.JoinPoint"],
                "body": "System.out.println(\"Before method: \" + joinPoint.getSignature());"
            }
        ],
        "logAfter": [
            {
                "className": "com.example.aspect.LoggingAspect",
                "signature": "com.example.aspect.LoggingAspect.logAfter(JoinPoint)",
                "parameterTypes": ["org.aspectj.lang.JoinPoint"],
                "body": "System.out.println(\"After method: \" + joinPoint.getSignature());"
            }
        ]
    }

    # 添加方法调用信息
    processor.method_invocations = {
        "findAll": [
            {
                "className": "com.example.service.UserService",
                "methodName": "getAllUsers",
                "signature": "com.example.repository.UserRepository.findAll()",
                "targetClassName": "com.example.repository.UserRepository",
                "lineNumber": 25
            }
        ]
    }

    processor.aop_data = {
        "beforeAspects": [
            {
                "id": "logBefore",
                "pointcut": "execution(* com.example.service.*.*(..))",
                "adviceMethod": {
                    "declaringType": "com.example.aspect.LoggingAspect",
                    "name": "logBefore",
                    "signature": "com.example.aspect.LoggingAspect.logBefore(JoinPoint)"
                },
                "targetMethods": [
                    {
                        "declaringType": "com.example.service.UserService",
                        "name": "findById",
                        "signature": "com.example.service.UserService.findById(Long)"
                    }
                ],
                "order": 1
            }
        ],
        "afterAspects": [
            {
                "id": "logAfter",
                "pointcut": "execution(* com.example.service.*.*(..))",
                "adviceMethod": {
                    "declaringType": "com.example.aspect.LoggingAspect",
                    "name": "logAfter",
                    "signature": "com.example.aspect.LoggingAspect.logAfter(JoinPoint)"
                },
                "targetMethods": [
                    {
                        "declaringType": "com.example.service.UserService",
                        "name": "save",
                        "signature": "com.example.service.UserService.save(User)"
                    },
                    {
                        "declaringType": "com.example.repository.UserRepository",
                        "name": "findAll",
                        "signature": "com.example.repository.UserRepository.findAll()"
                    }
                ],
                "order": 2
            }
        ],
        "aroundAspects": [],
        "afterThrowingAspects": []
    }

    # 测试改进后的AOP查找方法
    aop_data = processor._find_related_aop("com.example.service.UserService")

    # 打印AOP数据结构
    print("\n改进后的AOP数据结构:")
    print(f"按方法组织的AOP数据: {json.dumps(aop_data['byMethod'], indent=2)}")
    print(f"按调用点组织的AOP数据: {json.dumps(aop_data['byInvocation'], indent=2)}")
    print(f"按类型组织的AOP数据: {json.dumps(aop_data['byType'], indent=2)}")

    # 验证是否正确找到了方法级别的切面
    if "findById" in aop_data["byMethod"]:
        print("\n在findById方法上找到的切面:")
        for aspect_type, aspects in aop_data["byMethod"]["findById"].items():
            if aspects:
                print(f"- {aspect_type}: {len(aspects)}个切面")
                for aspect in aspects:
                    print(f"  - 切面ID: {aspect.get('aspectId')}")
                    print(f"    通知方法: {aspect.get('adviceMethod', {}).get('name')}")
                    print(f"    通知方法定义: {aspect.get('adviceMethod', {}).get('definition')}")

    # 验证是否正确找到了调用点级别的切面
    if aop_data["byInvocation"]:
        print("\n在方法调用点上找到的切面:")
        for invocation_key, invocation_data in aop_data["byInvocation"].items():
            print(f"- 调用点: {invocation_key}")
            print(f"  源方法: {invocation_data.get('sourceMethod')}")
            print(f"  调用方法: {invocation_data.get('invokedMethod')}")

            for aspect_type, aspects in invocation_data.get('aspects', {}).items():
                if aspects:
                    print(f"  - {aspect_type}: {len(aspects)}个切面")
                    for aspect in aspects:
                        print(f"    - 切面ID: {aspect.get('aspectId')}")
                        print(f"      通知方法: {aspect.get('adviceMethod', {}).get('name')}")

    # 测试整体数据收集
    java_files = processor.scan_java_files()

    # 查看前3个文件（如果有的话）
    for file in java_files[:3]:
        print(f"\n处理文件: {file}")
        prompt_data = processor.generate_prompt_data(file)

        # 打印源代码的前100个字符和相关建模数据的统计
        print(f"源代码 (前100个字符): {prompt_data.get('source_code', '')[:100]}...")
        print(f"AOP数据大小: {len(prompt_data.get('aop_data', '{}'))}")
        print(f"IoC数据大小: {len(prompt_data.get('ioc_data', '{}'))}")
        print(f"字段定义数据大小: {len(prompt_data.get('field_def_data', '{}'))}")
        print(f"方法定义数据大小: {len(prompt_data.get('method_def_data', '{}'))}")
        print(f"调用图数据大小: {len(prompt_data.get('call_graph_data', '{}'))}")


if __name__ == "__main__":
    test_data_processor()
