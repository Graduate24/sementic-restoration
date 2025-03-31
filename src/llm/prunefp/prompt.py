"""
提示词生成器模块，负责生成各类提示词
"""

import json
from typing import Dict, List, Any, Optional

class PromptGenerator:
    """
    提示词生成器，用于生成各种分析提示词
    """
    
    def generate_system_prompt(self) -> str:
        """
        生成系统提示词
        
        返回:
            系统提示词字符串
        """
        return """你是一个专业的Java安全漏洞分析专家，负责分析静态污点分析工具的结果，并判断其是否为误报。

请遵循以下分析步骤：
1. 仔细分析污点传播路径，了解数据如何从源头流向漏洞点
2. 考虑所有可能的验证、过滤或转义操作
3. 逐步推理每个函数如何处理输入数据
4. 判断是否存在足够的安全措施防止漏洞利用

如果你需要更多信息来做出判断，请明确指出你需要什么信息，并使用以下JSON格式请求：
{
  "需要更多信息": true,
  "信息类型": ["方法源码", "调用图", "Jimple IR"],
  "类名": "example.package.ClassName",
  "方法名": "methodName",
  "签名": "methodSignature",
}
示例:
{
  "需要更多信息": true,
  "信息类型": ["方法源码"],
  "类名": "edu.thu.benchmark.annotated.controller.CommandInjectionController",
  "方法名": "executeWithFullValidation07",
  "签名": "<edu.thu.benchmark.annotated.controller.CommandInjectionController: java.lang.String executeWithFullValidation07(java.lang.String)>",
}

最终结论请使用以下JSON格式输出：
{
  "是否误报": true/false,
  "置信度": 0-100,
  "理由": "详细解释为什么是误报或真实漏洞的理由",
  "建议修复方案": "如果是真实漏洞，提供修复建议"
}"""
    
    def generate_initial_prompt(self, finding: Dict[str, Any]) -> str:
        """
        生成初始分析提示词
        
        参数:
            finding: 污点分析结果
            
        返回:
            格式化的提示词字符串
        """
        # 提取信息
        vulnerability_type = self._determine_vulnerability_type(finding)
        source = finding.get('source', '未知')
        sink = finding.get('sink', '未知')
        file_path = finding.get('file_path', '未知')
        class_name = finding.get('class_name', '未知')
        method_name = finding.get('method_name', '未知')
        line_number = finding.get('line_number', '未知')
        
        # 格式化污点传播路径
        path = finding.get('path', [])
        formatted_path = self._format_path(path)
        
        prompt = f"""我正在分析一个可能的{vulnerability_type}漏洞。请帮我评估这是真实漏洞还是误报。

## 漏洞信息
- 类型: {vulnerability_type}
- 源点: {source}
- 汇点: {sink}
- 文件路径: {file_path}
- 类名: {class_name}
- 方法名: {method_name}
- 行号: {line_number}

## 污点传播路径
{formatted_path}

请分析这个污点传播路径，特别关注：
1. 数据如何从源点流向汇点
2. 是否存在任何数据验证、过滤或转义
3. 在到达汇点之前是否对数据进行了充分的安全处理

请逐步分析，如果你需要任何方法的具体实现代码或其他信息，请告诉我。
"""
        return prompt
    
    def generate_follow_up_prompt(self, additional_info: Dict[str, Any]) -> str:
        """
        生成后续信息提示词
        
        参数:
            additional_info: 额外信息字典
            
        返回:
            格式化的提示词字符串
        """
        prompt = "以下是你请求的额外信息：\n\n"
        
        # 添加方法源码
        if "方法源码" in additional_info:
            method_info = additional_info["方法源码"]
            prompt += f"## 方法源码: {method_info['类名']}.{method_info['方法名']}\n"
            prompt += "```java\n"
            prompt += method_info["源码"]
            prompt += "\n```\n\n"
        
        # 添加调用图
        if "调用图" in additional_info:
            call_graph_info = additional_info["调用图"]
            prompt += f"## 调用图: {call_graph_info['类名']}.{call_graph_info['方法名']}\n"
            prompt += "```\n"
            prompt += call_graph_info["调用图"]
            prompt += "\n```\n\n"
        
        # 添加Jimple IR
        if "Jimple IR" in additional_info:
            jimple_info = additional_info["Jimple IR"]
            prompt += f"## Jimple中间表示: {jimple_info['类名']}.{jimple_info['方法名']}\n"
            prompt += "```\n"
            prompt += jimple_info["Jimple"]
            prompt += "\n```\n\n"
        
        prompt += "请继续你的分析，判断这是否是一个真实的安全漏洞或误报。"
        
        return prompt
    
    def _determine_vulnerability_type(self, finding: Dict[str, Any]) -> str:
        """
        根据sink确定漏洞类型
        
        参数:
            finding: 污点分析结果
            
        返回:
            漏洞类型字符串
        """
        sink = finding.get('sink', '').lower()
        
        if 'sql' in sink:
            return "SQL注入"
        elif 'process' in sink or 'exec' in sink or 'command' in sink:
            return "命令注入"
        elif 'xss' in sink or 'html' in sink:
            return "跨站脚本(XSS)"
        elif 'file' in sink or 'path' in sink:
            return "路径操作/文件注入"
        elif 'ldap' in sink:
            return "LDAP注入" 
        elif 'xpath' in sink:
            return "XPath注入"
        elif 'deserial' in sink:
            return "不安全的反序列化"
        else:
            return "安全漏洞"
    
    def _format_path(self, path: List[Dict[str, Any]]) -> str:
        """
        格式化污点传播路径
        
        参数:
            path: 污点传播路径列表
            
        返回:
            格式化的路径字符串
        """
        if not path:
            return "未提供污点传播路径"
        
        formatted_path = ""
        for i, node in enumerate(path):
            java_class = node.get('javaClass', '未知')
            function = node.get('function', '未知')
            jimple_stmt = node.get('jimpleStmt', '未知')
            line = node.get('line', -1)
            
            formatted_path += f"{i+1}. 类: {java_class}\n"
            formatted_path += f"   函数: {function}\n"
            formatted_path += f"   Jimple语句: {jimple_stmt}\n"
            
            if line > 0:
                formatted_path += f"   行号: {line}\n"
            
            # 添加箭头，除了最后一个节点
            if i < len(path) - 1:
                formatted_path += "   ↓\n"
        
        return formatted_path 