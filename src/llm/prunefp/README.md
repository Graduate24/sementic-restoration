# 大模型辅助的静态分析误报消除工具

本工具基于大语言模型(LLM)的推理能力，对静态污点分析结果进行误报过滤，帮助开发者和安全研究人员快速区分真实漏洞和误报。

## 核心特性

1. **大模型逐步推理** - 利用LLM的强大语义理解能力，逐步分析污点传播路径
2. **渐进式交互** - 允许模型主动请求额外信息，如方法源码、调用图等
3. **自动代码检索** - 自动查找分析中涉及的Java方法实现
4. **结构化输出** - 生成规范的JSON格式结果，便于集成到自动化工作流

## 运行环境要求

- Python 3.8+
- Java项目源代码
- 污点分析结果(JSON格式)
- OpenRouter API密钥(或替代LLM服务)

## 快速开始

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 设置环境变量：

```bash
export OPENROUTER_API_KEY="你的API密钥"
```

3. 运行工具：

```bash
python -m src.llm.prunefp.main --result path/to/detected_result_raw.json --project path/to/java_project
```

## 命令行参数

```
usage: main.py [-h] --result RESULT --project PROJECT [--output OUTPUT] [--model MODEL] [--max-findings MAX_FINDINGS]

大模型辅助的静态分析误报消除工具

required arguments:
  --result RESULT, -r RESULT
                        污点分析结果的JSON文件路径
  --project PROJECT, -p PROJECT
                        Java项目根目录路径

optional arguments:
  --output OUTPUT, -o OUTPUT
                        分析结果输出目录，默认为当前目录下的output_日期_时间
  --model MODEL, -m MODEL
                        使用的LLM模型，默认为gpt-4
  --max-findings MAX_FINDINGS
                        最大分析的漏洞数量，用于测试
```

## 输出结果

工具会在指定的输出目录中生成以下文件：

- `analysis_results_full.json` - 完整的分析结果
- `analysis_results_summary.json` - 简洁的统计汇总
- `false_positives.json` - 识别为误报的结果
- `true_positives.json` - 识别为真实漏洞的结果
- `analysis_report.md` - 可读性好的分析报告
- `prunefp.log` - 分析过程日志

## 工作原理

1. 工具首先加载污点分析结果和Java项目源码
2. 对每个污点传播路径，创建一个分析会话
3. 使用渐进式交互方式与LLM沟通：
   - 提供初始分析信息(漏洞类型、传播路径等)
   - 根据LLM请求提供额外代码上下文
   - 最多进行5轮交互，确保信息充分
4. 解析LLM的最终判断，确定是否为误报
5. 汇总所有结果，生成报告

## 定制化

- 修改`prompt.py`中的提示词模板以针对特定应用场景
- 在`repository.py`中添加实际的工具调用，获取更详细的代码分析信息
- 通过修改`session.py`中的`max_rounds`参数调整最大交互轮数

## 局限性

- 目前只支持Java项目的分析
- 对于极其复杂的污点传播路径，可能需要手动提供额外信息
- LLM的分析可能不如专业安全人员准确，建议作为辅助工具使用 