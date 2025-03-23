# 语义还原实验模块

本模块提供了一套工具，用于设计和执行基于大语言模型的Java代码语义还原实验。

## 介绍

语义还原是指将使用各种框架特性（如Spring的依赖注入、AOP等）的Java代码转换为不依赖这些框架的纯Java代码的过程。本实验模块通过LLM（大语言模型）技术实现自动化的语义还原，帮助提高静态分析工具的分析能力。

## 功能特性

- **依赖注入还原**：将Spring的依赖注入自动转换为显式的对象创建和赋值
- **AOP切面还原**：将AOP切面转换为直接的方法调用
- **完整代码还原**：综合还原所有框架特性
- **多模型对比**：支持比较不同LLM模型在代码还原任务上的表现
- **批量实验**：支持批量执行多个类的还原实验
- **结果分析**：自动生成实验结果分析报告，包括成功率、时间性能等指标

## 目录结构

```
experiments/
├── experiment_runner.py       # 实验运行器主模块
├── experiment_config.json     # 实验配置文件
├── model_comparison_config.json # 模型对比实验配置
├── run_experiments.sh         # 实验执行脚本
├── analyze_results.py         # 结果分析工具
└── README.md                  # 使用说明文档
```

## 环境要求

- Python 3.8+
- matplotlib, numpy 等依赖库
- 设置好的LLM API密钥（通过环境变量或配置文件）

## 使用方法

### 基本用法

1. **单个类的依赖注入还原实验**：
```bash
python experiment_runner.py --modeling-file ../annotated-benchmark.report di --class-name CommandInjectionController --source-file ../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/CommandInjectionController.java
```

2. **单个类的AOP切面还原实验**：
```bash
python experiment_runner.py --modeling-file ../annotated-benchmark.report aop --class-name LoggingAspect --source-file ../benchmark/src/main/java/edu/thu/benchmark/annotated/aspect/LoggingAspect.java
```

3. **单个类的完整代码还原实验**：
```bash
python experiment_runner.py --modeling-file ../annotated-benchmark.report complete --class-name CommandInjectionController --source-file ../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/CommandInjectionController.java
```

4. **模型对比实验**：
```bash
python experiment_runner.py --modeling-file ../annotated-benchmark.report compare --class-name CommandInjectionController --source-file ../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/CommandInjectionController.java --models gpt-4-turbo claude-3-opus
```

### 使用Shell脚本

为了简化实验执行，我们提供了一个Shell脚本：

```bash
# 运行依赖注入实验
./run_experiments.sh -c CommandInjectionController di

# 运行AOP切面实验
./run_experiments.sh -c LoggingAspect aop

# 运行完整代码还原实验
./run_experiments.sh -c SqlInjectionTestController complete

# 运行模型对比实验
./run_experiments.sh -c PathTraversalController compare

# 批量运行依赖注入实验
./run_experiments.sh batch di

# 批量运行所有实验
./run_experiments.sh all
```

### 批量实验配置

批量实验需要一个JSON格式的配置文件，如`experiment_config.json`：

```json
[
  {
    "class_name": "CommandInjectionController",
    "source_file": "../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/CommandInjectionController.java"
  },
  {
    "class_name": "SqlInjectionTestController",
    "source_file": "../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/SqlInjectionTestController.java"
  }
]
```

对于模型对比实验，配置文件格式为：

```json
[
  {
    "class_name": "CommandInjectionController",
    "source_file": "../benchmark/src/main/java/edu/thu/benchmark/annotated/controller/CommandInjectionController.java",
    "models": ["gpt-4-turbo", "claude-3-opus"]
  }
]
```

### 结果分析

实验完成后，使用结果分析工具生成报告：

```bash
python analyze_results.py --results-dir ./results --output-dir ./analysis
```

这将生成包含图表和HTML报告的分析结果，详细展示各种实验的成功率、时间性能以及不同模型的对比结果。

## 实验结果解释

实验结果保存在JSON文件中，包含以下信息：

- **class_name**：被实验的类名
- **success**：是否成功还原
- **original_code**：原始代码
- **restored_code**：还原后的代码
- **time_taken**：耗时（秒）
- **model_used**：使用的LLM模型
- **timestamp**：实验时间戳

对于模型对比实验，结果还包含每个模型的单独结果。

## 注意事项

1. 确保在运行实验前已正确设置API密钥
2. 对于大型类，语义还原可能需要较长时间
3. 不同模型的性能和成功率可能存在显著差异
4. 批量实验会消耗大量API调用次数，请注意控制成本

## 常见问题

1. **LLM返回错误**：检查API密钥是否正确，以及是否超出了API调用限制
2. **代码还原不完整**：尝试使用更先进的模型，或调整提示工程
3. **分析报告中图表不显示中文**：确保matplotlib配置了正确的中文字体

## 示例输出

成功还原的示例输出可能如下所示：

```
INFO - 开始完整代码还原实验，类: CommandInjectionController
INFO - 读取源文件并获取建模信息
INFO - 开始使用GPT-4执行代码还原
INFO - 代码还原成功，耗时: 5.23秒
INFO - 结果已保存到: ./results/CommandInjectionController_complete_experiment.json
```

还原的代码将替换Spring的注解和依赖注入，使用显式的对象创建和方法调用。

## 贡献指南

如果您想为本项目贡献代码或提出建议，请：

1. Fork本仓库
2. 创建您的特性分支
3. 提交您的更改
4. 推送到分支
5. 创建新的Pull Request 