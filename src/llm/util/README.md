# 语义还原工具

该工具用于将带有注解的Java代码（如Spring、MyBatis等框架）转换为不包含注解的纯Java代码，同时保持功能等价性。

## 功能概述

- 将带有Spring、MyBatis等框架注解的Java代码转换为纯Java代码
- 基于大型语言模型(LLM)进行语义理解和代码转换
- 利用预先生成的建模信息进行更准确的语义还原
- 支持批量处理多个文件
- 支持使用上下文文件进行更准确的还原
- 提供命令行接口，方便集成到工作流程中

## 目录结构

```
src/llm/util/
├── cli.py                      # 命令行工具
├── data_processor.py           # 数据处理工具
├── prompt_template.py          # 提示词模板
├── semantic_restoration_client.py  # 语义还原客户端
└── README.md                   # 本文档
```

## 依赖项

- Python 3.6+
- 大型语言模型API（OpenRouter或其他兼容的API）
- 项目其他部分的代码和建模工具

## 安装

1. 确保已安装Python 3.6+
2. 设置API密钥：
   ```bash
   export OPENROUTER_API_KEY="your_api_key_here"
   ```
   或在运行时使用`--api_key`参数

## 使用方法

### 命令行工具

```bash
python -m src.llm.util.cli --project_dir /path/to/java/project \
                           --modeling_dir /path/to/modeling/data \
                           --output_dir /path/to/output \
                           --restore_all
```

### 参数说明

#### 必选参数

- `--project_dir`: Java项目目录路径
- `--modeling_dir`: 包含建模数据的目录路径
- `--output_dir`: 还原结果的输出目录路径

#### 操作模式（三选一）

- `--restore_all`: 还原项目中的所有Java文件
- `--restore_files file1.java file2.java`: 还原指定的Java文件
- `--restore_file_list files.txt`: 从文件中读取要还原的Java文件列表

#### 可选参数

- `--batch_size N`: 批处理大小，同时处理多少个文件（默认：1）
- `--no_context`: 不使用上下文文件进行还原
- `--max_context_files N`: 最大上下文文件数量（默认：2）
- `--max_retries N`: 调用LLM失败时最大重试次数（默认：3）
- `--retry_delay N`: 重试间隔秒数（默认：5）
- `--api_key KEY`: LLM API密钥（默认使用环境变量）
- `--log_level {DEBUG,INFO,WARNING,ERROR}`: 日志级别（默认：INFO）

### 示例

#### 还原所有文件

```bash
python -m src.llm.util.cli --project_dir ./my-java-project \
                           --modeling_dir ./modeling-data \
                           --output_dir ./restored-code \
                           --restore_all
```

#### 还原特定文件

```bash
python -m src.llm.util.cli --project_dir ./my-java-project \
                           --modeling_dir ./modeling-data \
                           --output_dir ./restored-code \
                           --restore_files src/main/java/com/example/Controller.java src/main/java/com/example/Service.java
```

#### 从文件列表还原

```bash
python -m src.llm.util.cli --project_dir ./my-java-project \
                           --modeling_dir ./modeling-data \
                           --output_dir ./restored-code \
                           --restore_file_list file_list.txt
```

其中`file_list.txt`格式为每行一个文件路径，相对于项目目录：

```
src/main/java/com/example/Controller.java
src/main/java/com/example/Service.java
# 这是注释行，会被忽略
src/main/java/com/example/Dao.java
```

#### 使用批处理

```bash
python -m src.llm.util.cli --project_dir ./my-java-project \
                           --modeling_dir ./modeling-data \
                           --output_dir ./restored-code \
                           --restore_all \
                           --batch_size 5
```

## 输出结果

语义还原工具会在指定的输出目录中创建与原始项目相同的目录结构，并将还原后的Java文件保存在对应位置。同时，会生成一个`restoration_stats.json`文件，包含还原过程的统计信息。

## 故障排查

1. API调用失败：检查API密钥是否正确设置
2. 文件解析错误：确保项目目录结构正确，文件可读
3. 建模数据缺失：确保提供了正确的建模数据目录

## 高级用法

### 集成到持续集成流程

可以将语义还原工具集成到CI/CD流程中，自动对每次提交的代码进行语义还原测试：

```yaml
# .gitlab-ci.yml 示例
semantic-restoration:
  stage: test
  script:
    - python -m src.llm.util.cli --project_dir . --modeling_dir ./modeling --output_dir ./restored --restore_all
    - ./verify_restoration.sh # 验证还原结果的脚本
```

### 自定义处理流程

如果需要在代码中直接使用语义还原功能，可以导入相关类并创建自定义流程：

```python
from src.llm.util.semantic_restoration_client import SemanticRestorationClient

# 创建客户端
client = SemanticRestorationClient(
    project_dir="./my-java-project",
    modeling_dir="./modeling-data",
    output_dir="./restored-code",
    batch_size=2,
    use_context=True
)

# 加载数据
client.load_data()

# 还原特定文件
result = client.restore_file("src/main/java/com/example/Service.java")
print(f"还原结果: {result}")
```

## 贡献

欢迎提交问题报告和功能建议。如需贡献代码，请先与维护者讨论。 