import re
import javalang
from typing import List, Dict, Any, Union, Tuple

class JavaCodeAnalyzer:
    """用于分析和分割Java代码的工具类"""
    
    @staticmethod
    def parse_and_split(java_code: str, max_tokens: int = 400, 
                         include_imports: bool = True) -> List[Dict[str, Any]]:
        """
        解析Java代码并智能分割成语义上连贯的块
        
        Args:
            java_code: Java源代码
            max_tokens: 每个块的最大token数
            include_imports: 是否在每个块中包含导入语句
            
        Returns:
            包含代码块和元数据的列表
        """
        try:
            # 尝试使用javalang解析
            tree = javalang.parse.parse(java_code)
            return JavaCodeAnalyzer._process_tree(tree, java_code, max_tokens, include_imports)
        except:
            # 如果解析失败，回退到正则表达式方法
            return JavaCodeAnalyzer._split_with_regex(java_code, max_tokens, include_imports)
    
    @staticmethod
    def _process_tree(tree, java_code: str, max_tokens: int, include_imports: bool) -> List[Dict[str, Any]]:
        """使用语法树处理Java代码"""
        result = []
        package_name = ""
        imports = []
        
        # 提取包名和导入
        for path, node in tree.filter(javalang.tree.PackageDeclaration):
            package_name = ".".join(node.name.values)
        
        for path, node in tree.filter(javalang.tree.Import):
            imports.append("import " + ".".join(node.path.values) + ";")
        
        imports_text = "\n".join(imports) if imports else ""
        
        # 处理类、接口和枚举
        for path, node in tree.filter(javalang.tree.TypeDeclaration):
            if isinstance(node, (javalang.tree.ClassDeclaration, 
                                javalang.tree.InterfaceDeclaration, 
                                javalang.tree.EnumDeclaration)):
                
                # 获取类定义
                class_name = node.name
                modifiers = " ".join(node.modifiers) if hasattr(node, "modifiers") else ""
                declaration_type = node.__class__.__name__.replace("Declaration", "").lower()
                
                # 类级别元数据
                class_metadata = {
                    "type": declaration_type,
                    "name": class_name,
                    "package": package_name,
                    "modifiers": modifiers,
                    "language": "java"
                }
                
                # 添加类定义块
                class_definition = JavaCodeAnalyzer._extract_node_code(node, java_code)
                
                # 处理类太大的情况
                if len(class_definition.split()) > max_tokens:
                    # 添加类声明头部
                    class_header = JavaCodeAnalyzer._extract_class_header(node, java_code)
                    if include_imports:
                        class_header = imports_text + "\n\n" + class_header
                    
                    result.append({
                        "code": class_header,
                        "metadata": {**class_metadata, "section": "header"}
                    })
                    
                    # 处理方法
                    if hasattr(node, "methods"):
                        for method in node.methods:
                            method_code = JavaCodeAnalyzer._extract_node_code(method, java_code)
                            method_metadata = {
                                **class_metadata,
                                "section": "method",
                                "method_name": method.name,
                                "method_modifiers": " ".join(method.modifiers) if hasattr(method, "modifiers") else "",
                                "return_type": method.return_type.name if method.return_type else "void"
                            }
                            
                            if include_imports:
                                method_code = imports_text + "\n\n" + class_header.split("{")[0] + "{\n" + method_code + "\n}"
                            
                            result.append({
                                "code": method_code,
                                "metadata": method_metadata
                            })
                else:
                    # 整个类作为一个块
                    if include_imports:
                        class_definition = imports_text + "\n\n" + class_definition
                    
                    result.append({
                        "code": class_definition,
                        "metadata": class_metadata
                    })
        
        return result
    
    @staticmethod
    def _extract_node_code(node, full_code: str) -> str:
        """从完整代码中提取节点的代码"""
        if hasattr(node, "position") and node.position:
            start_line = node.position.line - 1
            lines = full_code.split("\n")
            
            # 找到结束行（通过括号匹配）
            end_line = start_line
            brace_count = 0
            in_code = False
            
            for i in range(start_line, len(lines)):
                if "{" in lines[i]:
                    in_code = True
                
                if in_code:
                    brace_count += lines[i].count("{") - lines[i].count("}")
                    if brace_count == 0:
                        end_line = i
                        break
            
            return "\n".join(lines[start_line:end_line+1])
        return ""
    
    @staticmethod
    def _extract_class_header(node, full_code: str) -> str:
        """提取类的头部声明"""
        if hasattr(node, "position") and node.position:
            start_line = node.position.line - 1
            lines = full_code.split("\n")
            
            # 找到类声明的大括号
            for i in range(start_line, len(lines)):
                if "{" in lines[i]:
                    return "\n".join(lines[start_line:i+1])
            
            return lines[start_line]
        return ""
    
    @staticmethod
    def _split_with_regex(java_code: str, max_tokens: int, include_imports: bool) -> List[Dict[str, Any]]:
        """使用正则表达式分割Java代码"""
        result = []
        
        # 提取包名和导入
        package_pattern = r'package\s+([^;]+);'
        package_match = re.search(package_pattern, java_code)
        package_name = package_match.group(1) if package_match else ""
        
        import_pattern = r'import\s+[^;]+;'
        imports = re.findall(import_pattern, java_code)
        imports_text = "\n".join(imports) if imports else ""
        
        # 提取类、接口和枚举
        type_pattern = r'(public|private|protected)?\s*(class|interface|enum)\s+(\w+)([^{]*\{)'
        type_matches = re.finditer(type_pattern, java_code)
        
        for match in type_matches:
            # 类信息
            modifiers = match.group(1) if match.group(1) else ""
            type_kind = match.group(2)
            type_name = match.group(3)
            type_start = match.start()
            
            # 找到类的结束大括号
            brace_count = 1
            type_end = type_start + len(match.group(0))
            
            for i in range(type_end, len(java_code)):
                if java_code[i] == '{':
                    brace_count += 1
                elif java_code[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        type_end = i + 1
                        break
            
            class_code = java_code[type_start:type_end]
            class_metadata = {
                "type": type_kind,
                "name": type_name,
                "package": package_name,
                "modifiers": modifiers,
                "language": "java"
            }
            
            # 检查类大小
            if len(class_code.split()) > max_tokens:
                # 添加类声明头部
                class_header_end = class_code.find('{') + 1
                class_header = class_code[:class_header_end]
                
                if include_imports:
                    class_header = imports_text + "\n\n" + class_header
                
                result.append({
                    "code": class_header,
                    "metadata": {**class_metadata, "section": "header"}
                })
                
                # 提取方法
                method_pattern = r'(public|private|protected)?\s*(static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*(\{[^}]*\})'
                method_matches = re.finditer(method_pattern, class_code)
                
                for m_match in method_matches:
                    method_code = m_match.group(0)
                    method_name = m_match.group(3)
                    method_modifiers = (m_match.group(1) or "") + " " + (m_match.group(2) or "")
                    method_modifiers = method_modifiers.strip()
                    
                    method_metadata = {
                        **class_metadata,
                        "section": "method",
                        "method_name": method_name,
                        "method_modifiers": method_modifiers
                    }
                    
                    if include_imports:
                        method_code = imports_text + "\n\n" + class_header + "\n" + method_code + "\n}"
                    
                    result.append({
                        "code": method_code,
                        "metadata": method_metadata
                    })
            else:
                # 整个类作为一个块
                if include_imports:
                    class_code = imports_text + "\n\n" + class_code
                
                result.append({
                    "code": class_code,
                    "metadata": class_metadata
                })
        
        return result

    @staticmethod
    def extract_method_info(java_code: str) -> List[Dict[str, str]]:
        """
        提取Java代码中的方法信息
        
        Args:
            java_code: Java源代码
            
        Returns:
            方法信息列表
        """
        method_info = []
        
        try:
            # 尝试使用javalang解析
            tree = javalang.parse.parse(java_code)
            
            for path, node in tree.filter(javalang.tree.MethodDeclaration):
                info = {
                    "name": node.name,
                    "return_type": node.return_type.name if node.return_type else "void",
                    "modifiers": " ".join(node.modifiers) if hasattr(node, "modifiers") else "",
                    "parameters": [],
                    "throws": [],
                }
                
                # 提取参数
                if hasattr(node, "parameters") and node.parameters:
                    for param in node.parameters:
                        param_info = {
                            "name": param.name,
                            "type": param.type.name if hasattr(param.type, "name") else str(param.type)
                        }
                        info["parameters"].append(param_info)
                
                # 提取异常
                if hasattr(node, "throws") and node.throws:
                    info["throws"] = [t.name for t in node.throws]
                
                method_info.append(info)
        except:
            # 如果解析失败，回退到正则表达式
            method_pattern = r'(public|private|protected)?\s*(static)?\s*(\w+)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+([^{]+))?\s*\{'
            method_matches = re.finditer(method_pattern, java_code)
            
            for match in method_matches:
                modifiers = []
                if match.group(1):
                    modifiers.append(match.group(1))
                if match.group(2):
                    modifiers.append(match.group(2))
                
                return_type = match.group(3)
                method_name = match.group(4)
                param_str = match.group(5)
                throws_str = match.group(6)
                
                # 处理参数
                params = []
                if param_str and param_str.strip():
                    param_parts = param_str.split(',')
                    for part in param_parts:
                        part = part.strip()
                        if part:
                            # 简单分割，假设最后一个单词是参数名
                            parts = part.split()
                            if len(parts) > 1:
                                param_type = ' '.join(parts[:-1])
                                param_name = parts[-1]
                                params.append({"type": param_type, "name": param_name})
                
                # 处理异常
                throws = []
                if throws_str:
                    throws = [t.strip() for t in throws_str.split(',')]
                
                method_info.append({
                    "name": method_name,
                    "return_type": return_type,
                    "modifiers": ' '.join(modifiers),
                    "parameters": params,
                    "throws": throws
                })
        
        return method_info

    @staticmethod
    def enhance_metadata(code_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        增强代码块的元数据
        
        Args:
            code_chunks: 代码块列表
            
        Returns:
            增强后的代码块列表
        """
        for chunk in code_chunks:
            code = chunk["code"]
            metadata = chunk["metadata"]
            
            # 提取类的完整特征
            if metadata.get("type") in ["class", "interface", "enum"]:
                # 提取父类
                extends_pattern = r'extends\s+(\w+)'
                extends_match = re.search(extends_pattern, code)
                if extends_match:
                    metadata["extends"] = extends_match.group(1)
                
                # 提取实现的接口
                implements_pattern = r'implements\s+([^{]+)'
                implements_match = re.search(implements_pattern, code)
                if implements_match:
                    interfaces = [i.strip() for i in implements_match.group(1).split(',')]
                    metadata["implements"] = interfaces
                
                # 提取注解
                annotation_pattern = r'@(\w+)(?:\([^)]*\))?'
                annotations = re.findall(annotation_pattern, code)
                if annotations:
                    metadata["annotations"] = annotations
            
            # 提取方法的完整特征
            if metadata.get("section") == "method":
                # 提取方法的注释
                javadoc_pattern = r'/\*\*([\s\S]*?)\*/'
                javadoc_match = re.search(javadoc_pattern, code)
                if javadoc_match:
                    metadata["javadoc"] = javadoc_match.group(1).strip()
                
                # 提取方法的注解
                annotation_pattern = r'@(\w+)(?:\([^)]*\))?'
                annotations = re.findall(annotation_pattern, code)
                if annotations:
                    metadata["annotations"] = annotations
        
        return code_chunks 