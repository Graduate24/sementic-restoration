import re
from typing import Optional, Tuple

class JavaMethodExtractor:
    def __init__(self):
        # 匹配Java方法的基本模式
        self.method_pattern = re.compile(
            r'(?:public|private|protected|static|\s) +[\w\<\>\[\],\s]+\s+(\w+) *\([^\)]*\) *\{?',
            re.MULTILINE
        )
        
        # 匹配大括号
        self.brace_pattern = re.compile(r'\{|\}')
        
    def _find_method_start(self, content: str, method_name: str) -> Optional[int]:
        """查找方法开始的位置"""
        for match in self.method_pattern.finditer(content):
            if match.group(1) == method_name:
                return match.start()
        return None
    
    def _find_method_end(self, content: str, start_pos: int) -> Optional[int]:
        """查找方法结束的位置"""
        brace_count = 0
        pos = start_pos
        
        while pos < len(content):
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return pos + 1
            pos += 1
        return None
    
    def extract_method(self, file_content: str, method_name: str) -> Optional[str]:
        """
        从Java源代码中提取指定方法的源代码
        
        Args:
            file_content: Java源代码文件的内容
            method_name: 要提取的方法名
            
        Returns:
            方法的源代码字符串，如果未找到则返回None
        """
        # 查找方法开始位置
        start_pos = self._find_method_start(file_content, method_name)
        if start_pos is None:
            return None
            
        # 查找方法结束位置
        end_pos = self._find_method_end(file_content, start_pos)
        if end_pos is None:
            return None
            
        # 提取方法源代码
        method_code = file_content[start_pos:end_pos].strip()
        return method_code
    
    def extract_method_with_context(self, file_content: str, method_name: str, 
                                  context_lines: int = 5) -> Optional[Tuple[str, str, str]]:
        """
        从Java源代码中提取指定方法的源代码，包括方法前后的上下文
        
        Args:
            file_content: Java源代码文件的内容
            method_name: 要提取的方法名
            context_lines: 要包含的上下文行数
            
        Returns:
            包含前文、方法代码和后文的元组，如果未找到则返回None
        """
        # 查找方法开始位置
        start_pos = self._find_method_start(file_content, method_name)
        if start_pos is None:
            return None
            
        # 查找方法结束位置
        end_pos = self._find_method_end(file_content, start_pos)
        if end_pos is None:
            return None
            
        # 提取方法源代码
        method_code = file_content[start_pos:end_pos].strip()
        
        # 提取前文
        before_lines = file_content[:start_pos].split('\n')
        before_context = '\n'.join(before_lines[-context_lines:])
        
        # 提取后文
        after_lines = file_content[end_pos:].split('\n')
        after_context = '\n'.join(after_lines[:context_lines])
        
        return before_context, method_code, after_context

def extract_method_from_file(file_path: str, method_name: str, 
                           include_context: bool = False) -> Optional[str]:
    """
    从Java源代码文件中提取指定方法的源代码
    
    Args:
        file_path: Java源代码文件的路径
        method_name: 要提取的方法名
        include_context: 是否包含方法前后的上下文
        
    Returns:
        方法的源代码字符串，如果未找到则返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        extractor = JavaMethodExtractor()
        if include_context:
            result = extractor.extract_method_with_context(content, method_name)
            if result:
                before, method, after = result
                return f"{before}\n{method}\n{after}"
        else:
            return extractor.extract_method(content, method_name)
            
    except Exception as e:
        print(f"Error extracting method: {e}")
        return None 