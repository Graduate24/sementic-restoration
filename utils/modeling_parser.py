"""
建模结果解析模块，用于解析注解建模工具的输出结果并转换为语义还原所需的格式
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Set

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("modeling_parser")

class ModelingParser:
    """
    建模结果解析类，负责解析注解建模工具的输出
    """
    
    def __init__(self, modeling_file: str):
        """
        初始化解析器
        
        参数:
            modeling_file: 建模结果文件路径
        """
        self.modeling_file = modeling_file
        self.raw_content = self._read_file(modeling_file)
        self.beans = []
        self.autowired_fields = {}
        self.value_fields = {}
        self.aop_aspects = []
        self.entry_points = []
        self.sources = []
        self.sinks = []
        
        logger.info(f"建模解析器初始化完成，解析文件: {modeling_file}")
    
    def _read_file(self, file_path: str) -> str:
        """
        读取文件内容
        
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
    
    def _extract_bean_definitions(self) -> List[Dict[str, Any]]:
        """
        提取Bean定义信息
        
        返回:
            Bean定义列表
        """
        beans = []
        
        # 匹配BeanDefinitionModel的正则表达式
        pattern = r"BeanDefinitionModel\{\s*name=([^,]+),\s*type=([^,]+),\s*scope=([^,]+),\s*fromSource=([^,]+),\s*constructorArguments=([^,]+),\s*initializeMethod=([^,]+),\s*constructor=([^,]+),\s*properties=\[([^\]]*)\],\s*propertiesValue=([^,]+),\s*lazyInit=([^\s]+)\s*\}"
        
        matches = re.finditer(pattern, self.raw_content)
        for match in matches:
            bean = {
                "name": match.group(1).strip(),
                "type": match.group(2).strip(),
                "scope": match.group(3).strip(),
                "source": match.group(4).strip(),
                "constructor": match.group(7).strip(),
                "properties": [prop.strip() for prop in match.group(8).split(",")] if match.group(8).strip() else []
            }
            beans.append(bean)
        
        return beans
    
    def _extract_autowired_fields(self) -> Dict[str, List[Dict[str, str]]]:
        """
        提取@Autowired注解字段信息
        
        返回:
            类到注入字段映射的字典
        """
        autowired_fields = {}
        
        # 提取@Autowired部分
        autowired_section = ""
        if "---------@Autowired-----------" in self.raw_content:
            autowired_section = self.raw_content.split("---------@Autowired-----------")[1].split("---------@Value-----------")[0]
        
        # 匹配每个注入的字段
        pattern = r"([\w\.]+)#(\w+)\s*-->\s*(\d+)\|\s*\[(.*?)\]"
        matches = re.finditer(pattern, autowired_section, re.DOTALL)
        
        for match in matches:
            class_name = match.group(1)
            field_name = match.group(2)
            count = int(match.group(3))
            bean_info = match.group(4).strip()
            
            if class_name not in autowired_fields:
                autowired_fields[class_name] = []
            
            field_info = {
                "field": field_name,
                "count": count,
                "bean_info": bean_info
            }
            
            autowired_fields[class_name].append(field_info)
        
        return autowired_fields
    
    def _extract_value_fields(self) -> Dict[str, List[Dict[str, str]]]:
        """
        提取@Value注解字段信息
        
        返回:
            类到值字段映射的字典
        """
        value_fields = {}
        
        # 提取@Value部分
        value_section = ""
        if "---------@Value-----------" in self.raw_content:
            parts = self.raw_content.split("---------@Value-----------")
            if len(parts) > 1:
                if " --- AOP ---" in parts[1]:
                    value_section = parts[1].split(" --- AOP ---")[0]
                else:
                    value_section = parts[1]
        
        # 匹配每个@Value字段
        pattern = r"([\w\.]+)#(\w+)\s*-->\s*(\d+)\|\s*\[(.*?)\]"
        matches = re.finditer(pattern, value_section, re.DOTALL)
        
        for match in matches:
            class_name = match.group(1)
            field_name = match.group(2)
            count = int(match.group(3))
            value_info = match.group(4).strip()
            
            if class_name not in value_fields:
                value_fields[class_name] = []
            
            field_info = {
                "field": field_name,
                "count": count,
                "value_info": value_info
            }
            
            value_fields[class_name].append(field_info)
        
        return value_fields
    
    def _extract_aop_aspects(self) -> List[Dict[str, Any]]:
        """
        提取AOP切面信息
        
        返回:
            AOP切面信息列表
        """
        aspects = []
        
        # 提取AOP部分
        aop_section = ""
        if " --- AOP ---" in self.raw_content:
            aop_section = self.raw_content.split(" --- AOP ---")[1].split(" --- Entry point ---")[0]
        
        # 提取不同类型的切面
        aspect_types = ["before", "after", "afterreturning", "afterthrowing", "around"]
        
        for aspect_type in aspect_types:
            # 查找该类型的部分
            if aspect_type in aop_section.lower():
                type_section = aop_section.lower().split(aspect_type)[1]
                if aspect_type != aspect_types[-1]:  # 如果不是最后一个类型
                    for next_type in aspect_types[aspect_types.index(aspect_type) + 1:]:
                        if next_type in type_section:
                            type_section = type_section.split(next_type)[0]
                            break
                
                # 匹配切面方法和目标
                pattern = r"(public|private|protected)?\s*([\w\.<>\[\]]+)\s+([\w\.]+)\((.*?)\)\s*;\s*aspect targets:\s*((?:.*?->.*?$)*)"
                matches = re.finditer(pattern, type_section, re.MULTILINE)
                
                for match in matches:
                    return_type = match.group(2)
                    aspect_method = match.group(3)
                    params = match.group(4)
                    targets_text = match.group(5)
                    
                    # 解析目标方法
                    targets = []
                    if targets_text:
                        target_pattern = r"->([^-].*?)$"
                        target_matches = re.finditer(target_pattern, targets_text, re.MULTILINE)
                        for target_match in target_matches:
                            targets.append(target_match.group(1).strip())
                    
                    aspect = {
                        "type": aspect_type,
                        "aspect": aspect_method,
                        "return_type": return_type,
                        "params": params,
                        "targets": targets
                    }
                    
                    aspects.append(aspect)
        
        return aspects
    
    def _extract_entry_points(self) -> List[str]:
        """
        提取入口点信息
        
        返回:
            入口点方法签名列表
        """
        entry_points = []
        
        # 提取入口点部分
        entry_section = ""
        if " --- Entry point ---" in self.raw_content:
            parts = self.raw_content.split(" --- Entry point ---")
            if len(parts) > 1:
                if " --- Source sink ---" in parts[1]:
                    entry_section = parts[1].split(" --- Source sink ---")[0]
                else:
                    entry_section = parts[1]
        
        # 匹配每个入口点
        pattern = r"(public|private|protected)?\s*([\w\.<>\[\]]+)\s+([\w\.]+)\((.*?)\)"
        matches = re.finditer(pattern, entry_section)
        
        for match in matches:
            return_type = match.group(2)
            method = match.group(3)
            params = match.group(4)
            
            entry_point = f"{return_type} {method}({params})"
            entry_points.append(entry_point)
        
        return entry_points
    
    def _extract_sources_and_sinks(self) -> Tuple[List[str], List[str]]:
        """
        提取源点和汇点信息
        
        返回:
            (源点列表, 汇点列表)
        """
        sources = []
        sinks = []
        
        # 提取源汇点部分
        source_sink_section = ""
        if " --- Source sink ---" in self.raw_content:
            source_sink_section = self.raw_content.split(" --- Source sink ---")[1]
        
        # 提取源点
        source_section = ""
        if "source---" in source_sink_section:
            parts = source_sink_section.split("source---")
            if len(parts) > 1:
                if "sink---" in parts[1]:
                    source_section = parts[1].split("sink---")[0]
                else:
                    source_section = parts[1]
        
        # 匹配每个源点
        pattern = r"(public|private|protected)?\s*([\w\.<>\[\]]+)\s+([\w\.]+)\((.*?)\)"
        source_matches = re.finditer(pattern, source_section)
        
        for match in source_matches:
            return_type = match.group(2)
            method = match.group(3)
            params = match.group(4)
            
            source = f"{return_type} {method}({params})"
            sources.append(source)
        
        # 提取汇点
        sink_section = ""
        if "sink---" in source_sink_section:
            sink_section = source_sink_section.split("sink---")[1]
        
        # 匹配每个汇点
        sink_matches = re.finditer(pattern, sink_section)
        
        for match in sink_matches:
            return_type = match.group(2)
            method = match.group(3)
            params = match.group(4)
            
            sink = f"{return_type} {method}({params})"
            sinks.append(sink)
        
        return sources, sinks
    
    def parse(self) -> Dict[str, Any]:
        """
        解析建模结果文件并提取所有相关信息
        
        返回:
            包含解析结果的字典
        """
        logger.info("开始解析建模结果文件")
        
        try:
            # 提取各类信息
            self.beans = self._extract_bean_definitions()
            self.autowired_fields = self._extract_autowired_fields()
            self.value_fields = self._extract_value_fields()
            self.aop_aspects = self._extract_aop_aspects()
            self.entry_points = self._extract_entry_points()
            self.sources, self.sinks = self._extract_sources_and_sinks()
            
            # 构建结果字典
            result = {
                "beans": self.beans,
                "autowired_fields": self.autowired_fields,
                "value_fields": self.value_fields,
                "aop_aspects": self.aop_aspects,
                "entry_points": self.entry_points,
                "sources": self.sources,
                "sinks": self.sinks
            }
            
            logger.info("解析完成，提取了以下信息:")
            logger.info(f"- Bean定义: {len(self.beans)}个")
            logger.info(f"- Autowired字段: {sum(len(fields) for fields in self.autowired_fields.values())}个")
            logger.info(f"- Value字段: {sum(len(fields) for fields in self.value_fields.values())}个")
            logger.info(f"- AOP切面: {len(self.aop_aspects)}个")
            logger.info(f"- 入口点: {len(self.entry_points)}个")
            logger.info(f"- 源点: {len(self.sources)}个")
            logger.info(f"- 汇点: {len(self.sinks)}个")
            
            return result
            
        except Exception as e:
            logger.error(f"解析建模结果文件时出错: {str(e)}")
            return {}
    
    def get_class_dependencies(self, class_name: str) -> Dict[str, Any]:
        """
        获取指定类的依赖信息
        
        参数:
            class_name: 类名（可以是简单类名或完全限定名）
        
        返回:
            包含类依赖信息的字典
        """
        # 处理类名（支持简单类名和完全限定名）
        simple_class_name = class_name.split('.')[-1]
        
        # 查找匹配的类（完全匹配或简单名称匹配）
        matching_classes = []
        for full_class in self.autowired_fields.keys():
            if full_class == class_name or full_class.endswith('.' + simple_class_name):
                matching_classes.append(full_class)
        
        if not matching_classes:
            logger.warning(f"未找到类 {class_name} 的依赖信息")
            return {}
        
        # 如果有多个匹配，选择第一个
        if len(matching_classes) > 1:
            logger.warning(f"类名 {class_name} 匹配多个类: {matching_classes}，将使用第一个")
        
        target_class = matching_classes[0]
        
        # 获取类的依赖（Autowired字段）
        autowired_deps = []
        if target_class in self.autowired_fields:
            autowired_deps = self.autowired_fields[target_class]
        
        # 获取类的配置值（Value字段）
        value_configs = []
        if target_class in self.value_fields:
            value_configs = self.value_fields[target_class]
        
        # 获取影响该类的AOP切面
        related_aspects = []
        for aspect in self.aop_aspects:
            for target in aspect.get('targets', []):
                if target_class in target or simple_class_name in target:
                    related_aspects.append(aspect)
                    break
        
        return {
            "class_name": target_class,
            "autowired_fields": autowired_deps,
            "value_fields": value_configs,
            "related_aspects": related_aspects
        }
    
    def format_for_code_restoration(self, class_name: str = None) -> Dict[str, Any]:
        """
        将解析结果格式化为代码还原所需的格式
        
        参数:
            class_name: 如果指定，则只返回该类相关的信息
        
        返回:
            格式化的字典
        """
        if class_name:
            class_info = self.get_class_dependencies(class_name)
            if not class_info:
                return {}
            
            # 提取依赖的Bean信息
            bean_deps = []
            for field in class_info.get("autowired_fields", []):
                if field.get("count", 0) > 0:
                    # 查找对应的Bean定义
                    for bean in self.beans:
                        if field.get("field") in bean.get("name", ""):
                            bean_deps.append(bean)
                            break
            
            # 提取相关的AOP信息
            aop_info = []
            for aspect in class_info.get("related_aspects", []):
                aop_info.append({
                    "type": aspect.get("type"),
                    "aspect": aspect.get("aspect"),
                    "targets": aspect.get("targets", [])
                })
            
            return {
                "beans": bean_deps,
                "injections": [
                    {"target": class_name, "dependency": field.get("field")}
                    for field in class_info.get("autowired_fields", [])
                    if field.get("count", 0) > 0
                ],
                "configs": [
                    {"field": field.get("field"), "value": field.get("value_info", "")}
                    for field in class_info.get("value_fields", [])
                    if field.get("count", 0) > 0
                ],
                "aop": aop_info
            }
        else:
            # 全局信息格式化
            return {
                "beans": self.beans,
                "injections": [
                    {"target": class_name, "dependency": field.get("field")}
                    for class_name, fields in self.autowired_fields.items()
                    for field in fields if field.get("count", 0) > 0
                ],
                "configs": [
                    {"target": class_name, "field": field.get("field"), "value": field.get("value_info", "")}
                    for class_name, fields in self.value_fields.items()
                    for field in fields if field.get("count", 0) > 0
                ],
                "aop": [
                    {
                        "type": aspect.get("type"),
                        "aspect": aspect.get("aspect"),
                        "targets": aspect.get("targets", [])
                    }
                    for aspect in self.aop_aspects
                ],
                "entry_points": self.entry_points,
                "sources": self.sources,
                "sinks": self.sinks
            }


# 简单测试函数
def test_modeling_parser():
    """
    测试建模解析器功能
    """
    # 指定建模文件路径
    modeling_file = "../annotated-benchmark.report"
    
    # 检查文件是否存在
    if not os.path.exists(modeling_file):
        print(f"错误：找不到建模文件 {modeling_file}")
        return
    
    # 创建解析器
    parser = ModelingParser(modeling_file)
    
    # 解析建模结果
    print("开始解析建模结果...")
    result = parser.parse()
    
    # 显示结果摘要
    print("\n解析结果摘要:")
    print(f"- Bean定义: {len(result['beans'])}个")
    print(f"- Autowired字段: {len(result['autowired_fields'])}个类, "
          f"{sum(len(fields) for fields in result['autowired_fields'].values())}个字段")
    print(f"- Value字段: {len(result['value_fields'])}个类, "
          f"{sum(len(fields) for fields in result['value_fields'].values())}个字段")
    print(f"- AOP切面: {len(result['aop_aspects'])}个")
    print(f"- 入口点: {len(result['entry_points'])}个")
    print(f"- 源点: {len(result['sources'])}个")
    print(f"- 汇点: {len(result['sinks'])}个")
    
    # 获取示例类的依赖信息
    example_class = "CommandInjectionController"
    print(f"\n获取类 {example_class} 的依赖信息:")
    class_deps = parser.get_class_dependencies(example_class)
    print(json.dumps(class_deps, indent=2, ensure_ascii=False))
    
    # 格式化用于代码还原
    print(f"\n格式化用于 {example_class} 的代码还原:")
    restoration_format = parser.format_for_code_restoration(example_class)
    print(json.dumps(restoration_format, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_modeling_parser() 