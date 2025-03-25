"""
提示模板工具，用于生成语义还原的提示词
"""

import os
import json
from typing import Dict, List, Any, Optional

class PromptTemplate:
    """
    生成语义还原所需的提示词
    """
    
    @staticmethod
    def generate_user_prompt(source_code: str, modeling_data: Dict[str, str]) -> str:
        """
        生成用户提示词，包含源代码和建模数据
        
        参数:
            source_code: 源代码内容
            modeling_data: 建模数据字典，包含各种建模信息
        
        返回:
            格式化的用户提示词
        """
        # 创建用户提示模板
        prompt = f"""请对以下Java代码进行语义还原，将带有注解的代码转换为没有注解的等效纯Java代码。

## 源代码：
```java
{source_code}
```

## 建模数据：

### AOP建模数据：
注意：AOP数据是一个列表，每个项目包含：
1. invocations - 方法调用信息，包含调用者、被调用方法和行号
2. aspect_type - 切面类型（beforeAspects、afterAspects、aroundAspects等）
3. definitions - 切面方法的定义信息

```json
{modeling_data.get('aop_data', '{}')}
```

### IoC建模数据：
```json
{modeling_data.get('ioc_data', '{}')}
```

### MyBatis映射数据：
```json
{modeling_data.get('mybatis_data', '{}')}
```

### 字段定义数据：
```json
{modeling_data.get('field_def_data', '{}')}
```

### 字段引用数据：
```json
{modeling_data.get('field_ref_data', '{}')}
```

### 方法定义数据：
```json
{modeling_data.get('method_def_data', '{}')}
```

### 方法调用数据：
```json
{modeling_data.get('method_call_data', '{}')}
```

### 调用图数据：
```json
{modeling_data.get('call_graph_data', '{}')}
```


请遵循系统提示中的所有规则和指导，生成可以编译运行的纯Java代码。请确保生成的代码尽量不包含任何框架特定的注解，同时保持功能等价性。

注意处理AOP数据时：
1. 对于每个AOP条目，查看invocations部分了解被拦截的方法调用
2. 根据aspect_type（前置、后置、环绕、异常通知）在适当位置添加切面方法调用
3. 利用definitions了解切面方法的具体实现细节
4. 在原方法调用前后插入适当的切面方法调用，保持功能等价性

请保持代码结构清晰，并添加适当的注释标识添加的AOP相关代码。
"""
        return prompt
    
    @staticmethod
    def generate_batch_user_prompt(file_list: List[Dict[str, Any]]) -> str:
        """
        生成批处理用户提示词，包含多个文件的源代码和建模数据
        
        参数:
            file_list: 文件列表，每个文件包含源代码和建模数据
        
        返回:
            格式化的批处理用户提示词
        """
        prompt = """请对以下多个Java文件进行语义还原，将带有注解的代码转换为没有注解的等效纯Java代码。\n\n"""
        
        for i, file_data in enumerate(file_list):
            prompt += f"""## 文件 {i+1}: {file_data.get('file_path', '')}
### 源代码：
```java
{file_data.get('source_code', '')}
```

### 建模数据：
注意：如果存在AOP数据，它是一个列表，每个项目包含：
1. invocations - 方法调用信息，包含调用者、被调用方法和行号
2. aspect_type - 切面类型（beforeAspects、afterAspects、aroundAspects等）
3. definitions - 切面方法的定义信息

```json
{json.dumps(file_data.get('modeling_data', {}), indent=2)}
```

"""
        
        prompt += """请遵循系统提示中的所有规则和指导，为每个文件生成可以编译运行的纯Java代码。请确保生成的代码不包含任何Spring、MyBatis或其他框架特定的注解，同时保持功能等价性。

注意处理AOP数据时：
1. 对于每个AOP条目，查看invocations部分了解被拦截的方法调用
2. 根据aspect_type（前置、后置、环绕、异常通知）在适当位置添加切面方法调用
3. 利用definitions了解切面方法的具体实现细节
4. 在原方法调用前后插入适当的切面方法调用，保持功能等价性

请按以下格式返回每个文件的语义还原结果：

## 文件 1 还原结果:
```java
// 还原后的Java代码
```

## 文件 2 还原结果:
```java
// 还原后的Java代码
```

以此类推...
"""
        return prompt
    
    @staticmethod
    def format_restoration_result(restored_code: str, original_file_path: str, debug_info: Optional[Dict] = None) -> Dict:
        """
        格式化还原结果，生成包含原始文件路径、还原后代码和调试信息的字典
        
        参数:
            restored_code: 还原后的代码
            original_file_path: 原始文件路径
            debug_info: 可选的调试信息
        
        返回:
            格式化的还原结果字典
        """
        result = {
            "original_file_path": original_file_path,
            "restored_code": restored_code,
        }
        
        if debug_info:
            result["debug_info"] = debug_info
        
        return result
    
    @staticmethod
    def parse_batch_result(batch_result: str, file_paths: List[str]) -> List[Dict]:
        """
        解析批处理结果，提取每个文件的还原代码
        
        参数:
            batch_result: 批处理结果文本
            file_paths: 原始文件路径列表
        
        返回:
            包含每个文件还原结果的字典列表
        """
        results = []
        
        # 查找所有文件结果
        import re
        pattern = r"## 文件 (\d+) 还原结果:\s*```java\s*(.*?)\s*```"
        file_matches = re.findall(pattern, batch_result, re.DOTALL)
        
        for match in file_matches:
            file_index = int(match[0]) - 1  # 文件索引（从0开始）
            restored_code = match[1].strip()
            
            if 0 <= file_index < len(file_paths):
                result = {
                    "original_file_path": file_paths[file_index],
                    "restored_code": restored_code
                }
                results.append(result)
        
        return results
    
    @staticmethod
    def generate_user_prompt_with_context(
        target_file_data: Dict[str, Any],
        related_files: List[Dict[str, Any]],
        max_context_files: int = 2
    ) -> str:
        """
        生成带有上下文的用户提示词，包含目标文件和相关文件的源代码和建模数据
        
        参数:
            target_file_data: 目标文件数据，包含源代码和建模数据
            related_files: 相关文件列表，每个文件包含源代码和建模数据
            max_context_files: 最大上下文文件数量
        
        返回:
            格式化的用户提示词
        """
        # 限制上下文文件数量
        if len(related_files) > max_context_files:
            related_files = related_files[:max_context_files]
        
        prompt = f"""请对以下目标Java文件进行语义还原，将带有注解的代码转换为没有注解的等效纯Java代码。

## 目标文件: {target_file_data.get('file_path', '')}
### 源代码：
```java
{target_file_data.get('source_code', '')}
```

### 建模数据：
#### AOP建模数据：
注意：AOP数据是一个列表，每个项目包含：
1. invocations - 方法调用信息，包含调用者、被调用方法和行号
2. aspect_type - 切面类型（beforeAspects、afterAspects、aroundAspects等）
3. definitions - 切面方法的定义信息

```json
{json.dumps(target_file_data.get('modeling_data', {}).get('aop_data', {}), indent=2)}
```

#### IoC建模数据：
```json
{json.dumps(target_file_data.get('modeling_data', {}).get('ioc_data', {}), indent=2)}
```

#### MyBatis映射数据：
```json
{json.dumps(target_file_data.get('modeling_data', {}).get('mybatis_data', {}), indent=2)}
```

#### 字段定义数据：
```json
{json.dumps(target_file_data.get('modeling_data', {}).get('field_def_data', {}), indent=2)}
```

#### 方法定义数据：
```json
{json.dumps(target_file_data.get('modeling_data', {}).get('method_def_data', {}), indent=2)}
```

#### 方法调用数据：
```json
{json.dumps(target_file_data.get('modeling_data', {}).get('method_call_data', {}), indent=2)}
```

#### 调用图数据：
```json
{json.dumps(target_file_data.get('modeling_data', {}).get('call_graph_data', {}), indent=2)}
```
"""
        
        # 添加上下文文件信息
        if related_files:
            prompt += "\n## 相关上下文文件：\n"
            
            for i, file_data in enumerate(related_files):
                prompt += f"""### 文件 {i+1}: {file_data.get('file_path', '')}
#### 源代码：
```java
{file_data.get('source_code', '')}
```

"""
        
        prompt += """请遵循系统提示中的所有规则和指导，仅对目标文件生成可以编译运行的纯Java代码。请确保生成的代码不包含任何Spring、MyBatis或其他框架特定的注解，同时保持功能等价性。上下文文件仅供参考，帮助你理解代码之间的联系，不需要对它们进行还原。

注意处理AOP数据时：
1. 对于每个AOP条目，查看invocations部分了解被拦截的方法调用
2. 根据aspect_type（前置、后置、环绕、异常通知）在适当位置添加切面方法调用
3. 利用definitions了解切面方法的具体实现细节
4. 在原方法调用前后插入适当的切面方法调用，保持功能等价性

请保持代码结构清晰，并添加适当的注释标识添加的AOP相关代码。

请返回目标文件的语义还原结果：
```java
// 还原后的Java代码
```
"""
        return prompt


def test_prompt_template():
    """
    测试提示模板生成
    """
    # 示例源代码
    source_code = """
package com.example.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;
import com.example.repository.UserRepository;
import com.example.model.User;

@Service
public class UserService {
    
    @Autowired
    private UserRepository userRepository;
    
    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }
}
"""
    
    # 示例建模数据
    modeling_data = {
        "aop_data": "{}",
        "ioc_data": """
{
  "com.example.service.UserService.userRepository": {
    "fieldName": "userRepository",
    "fieldType": "com.example.repository.UserRepository",
    "declaringType": "com.example.service.UserService",
    "injectType": "FIELD",
    "qualifier": null
  }
}
""",
        "mybatis_data": "{}",
        "field_def_data": "{}",
        "method_def_data": "{}"
    }
    
    # 生成用户提示词
    user_prompt = PromptTemplate.generate_user_prompt(source_code, modeling_data)
    print(user_prompt)
    
    # 生成批处理提示词
    file_list = [
        {
            "file_path": "src/main/java/com/example/service/UserService.java",
            "source_code": source_code,
            "modeling_data": json.loads("""
{
  "aop_data": {},
  "ioc_data": {
    "com.example.service.UserService.userRepository": {
      "fieldName": "userRepository",
      "fieldType": "com.example.repository.UserRepository",
      "declaringType": "com.example.service.UserService",
      "injectType": "FIELD",
      "qualifier": null
    }
  },
  "mybatis_data": {}
}
""")
        }
    ]
    
    batch_prompt = PromptTemplate.generate_batch_user_prompt(file_list)
    print("\n批处理提示词:")
    print(batch_prompt)
    
    # 解析批处理结果
    batch_result = """
## 文件 1 还原结果:
```java
package com.example.service;

import com.example.repository.UserRepository;
import com.example.model.User;

public class UserService {
    
    private UserRepository userRepository;
    
    public UserService() {
        // 构造函数
    }
    
    public void setUserRepository(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
    
    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }
}
```
"""
    
    parsed_results = PromptTemplate.parse_batch_result(batch_result, ["src/main/java/com/example/service/UserService.java"])
    print("\n解析的批处理结果:")
    for result in parsed_results:
        print(f"文件: {result['original_file_path']}")
        print(f"还原代码:\n{result['restored_code']}")


if __name__ == "__main__":
    test_prompt_template() 