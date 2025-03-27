# 语义修复实验工具指南

本文档提供了语义修复(Semantic Restoration)项目中实验脚本的详细说明和使用方法。这些脚本主要用于评估、调优和分析系统性能。

## 实验脚本概览

### 代码分析与还原工具

#### 1. `experiments/experiment_runner.py`

**功能**：实验运行器，用于执行各种语义还原实验，支持依赖注入、AOP切面和完整代码还原等多种实验，并提供模型对比功能。

**输入**：
- 建模结果文件
- 源代码文件
- 要处理的类名
- 实验类型和参数

**输出**：
- 实验结果JSON文件
- 还原后的代码文件

**运行方式**：
```bash
# 依赖注入实验
python experiments/experiment_runner.py --modeling-file modeling.json --output-dir results di --class-name MyClass --source-file src/MyClass.java

# AOP切面实验
python experiments/experiment_runner.py --modeling-file modeling.json --output-dir results aop --class-name MyClass --source-file src/MyClass.java

# 完整代码还原
python experiments/experiment_runner.py --modeling-file modeling.json --output-dir results complete --class-name MyClass --source-file src/MyClass.java

# 模型对比实验
python experiments/experiment_runner.py --modeling-file modeling.json --output-dir results compare --class-name MyClass --source-file src/MyClass.java --models gpt-3.5-turbo gpt-4

# 批量实验
python experiments/experiment_runner.py --modeling-file modeling.json --output-dir results batch --experiment-type complete --config-file batch_config.json
```

**具体功能**：
- 运行依赖注入、AOP切面、完整代码还原等多种实验
- 对比不同LLM模型的代码还原效果
- 支持单个类实验和批量实验
- 记录实验时间、成功率和还原结果

### 权重优化与评估工具

#### 1. `experiments/weight_optimization.py`

**功能**：此脚本用于优化语义距离和代码距离的权重组合，以达到最佳的检测性能。它会生成多种可视化结果和分析报告。

**输入**：
- 语义和代码查询结果 (`experiments/query_result.json`)
- 带有真值标记的结果数据 (`experiments/restore_detailed_results.json`)

**输出**：
- F1分数热图 (`experiments/weight_heatmap.png`)
- PR曲线 (`experiments/pr_curve.png`)
- 阈值影响分析图 (`experiments/threshold_impact.png`)
- 权重比较CSV表格 (`experiments/weight_comparison.csv`)
- Markdown格式的比较表 (`experiments/weight_comparison_table.md`)
- 优化结果详情 (`experiments/weight_optimization_results.json`)

**运行方式**：
```bash
python experiments/weight_optimization.py
```

**具体功能**：
- 使用网格搜索寻找最佳权重组合
- 分析不同阈值对检测准确率和召回率的影响
- 计算最佳F1分数及其对应的权重组合和阈值
- 可视化不同权重组合的性能对比
- 详细分析分类错误的样本

#### 2. `experiments/false_positive_filter.py`

**功能**：基于优化后的权重和阈值，过滤掉检测结果中的误报，提高检测结果的精确率。

**输入**：
- 语义和代码查询结果 (`experiments/query_result.json`)
- 检测结果数据 (`experiments/restore_detailed_results.json`)
- 语义权重、代码权重和阈值参数

**输出**：
- 过滤后的检测结果 (`experiments/filtered_results.json`)

**运行方式**：
```bash
python experiments/false_positive_filter.py --semantic-weight 0.7 --code-weight 0.3 --threshold -15.0 --query-result experiments/query_result.json --detection-result experiments/restore_detailed_results.json --output experiments/filtered_results.json
```

**具体功能**：
- 根据优化的权重计算每个检测项的组合得分
- 基于阈值过滤可能的误报
- 保留真阳性结果，同时标记并过滤假阳性
- 生成详细的过滤统计信息

### 结果分析与可视化工具

#### 1. `experiments/analyze_results.py`

**功能**：分析语义还原实验结果，生成多种可视化报告和统计数据。

**输入**：
- 实验结果目录 (包含JSON格式的实验结果文件)

**输出**：
- 成功率图表 (`analysis/success_rate_chart.png`)
- 时间对比图表 (`analysis/time_comparison_chart.png`)
- 模型对比图表 (`analysis/model_comparison_chart.png`)
- HTML格式的分析报告 (`analysis/analysis_report.html`)

**运行方式**：
```bash
python experiments/analyze_results.py --results-dir ./results --output-dir ./analysis
```

**具体功能**：
- 加载并整理不同类型的实验结果
- 计算成功率、执行时间等关键指标
- 对比不同模型的性能
- 生成直观的图表和综合分析报告

## 具体使用指南

### 语义还原实验流程

1. **准备数据和环境**：
   - 确保建模结果文件已生成
   - 准备好源代码文件
   - 配置所需的LLM API密钥

2. **运行单个类实验**：
   ```bash
   # 例如，运行完整代码还原实验
   python experiments/experiment_runner.py --modeling-file modeling.json --output-dir results complete --class-name MyService --source-file src/MyService.java
   ```

3. **运行批量实验**：
   - 创建批量配置文件，如：
     ```json
     [
       {"class_name": "UserService", "source_file": "src/UserService.java"},
       {"class_name": "OrderService", "source_file": "src/OrderService.java"}
     ]
     ```
   - 运行批量实验：
     ```bash
     python experiments/experiment_runner.py --modeling-file modeling.json batch --experiment-type complete --config-file batch_config.json
     ```

4. **分析实验结果**：
   - 检查生成的JSON文件了解详细结果
   - 比较还原的代码与原始代码的差异
   - 使用`analyze_results.py`生成可视化报告

### 权重优化流程

1. **准备数据文件**：
   - 确保在`experiments`目录下有`query_result.json`和`restore_detailed_results.json`文件
   - `query_result.json`：包含每个代码片段的语义距离和代码距离
   - `restore_detailed_results.json`：包含每个检测结果的真值标记(TP/FP)

2. **运行优化**：
   ```bash
   python experiments/weight_optimization.py
   ```

3. **分析结果**：
   - 检查生成的热图，找到F1分数最高的权重组合区域
   - 查看PR曲线，了解最佳权重组合的精确率和召回率关系
   - 分析阈值影响图，选择适合应用场景的阈值
   - 通过Markdown表格比较不同权重组合的性能

4. **应用优化结果**：
   - 优化完成后，使用找到的最佳权重组合和阈值配置系统
   - 优化结果保存在`experiments/weight_optimization_results.json`中

### 误报过滤流程

1. **准备必要文件**：
   - 确保有`query_result.json`和检测结果文件
   - 从权重优化结果中获取最佳权重和阈值

2. **运行过滤器**：
   ```bash
   python experiments/false_positive_filter.py --semantic-weight 0.7 --code-weight 0.3 --threshold -15.0
   ```

3. **分析过滤结果**：
   - 查看控制台输出的过滤统计信息
   - 检查过滤后的结果文件，评估误报减少的效果
   - 根据需要调整阈值，平衡精确率和召回率

### 结果分析流程

1. **收集实验结果**：
   - 将所有实验结果JSON文件放在一个目录中
   - 确保文件命名符合脚本识别规则

2. **运行分析脚本**：
   ```bash
   python experiments/analyze_results.py --results-dir ./results --output-dir ./analysis
   ```

3. **查看分析报告**：
   - 打开生成的HTML报告，获取综合分析
   - 检查各种图表，了解系统性能和不同因素的影响
   - 根据分析结果调整系统参数或优化方法

## 数据文件格式

### 1. 实验配置文件 `batch_config.json` 格式

```json
[
  {
    "class_name": "UserService",
    "source_file": "src/UserService.java"
  },
  {
    "class_name": "OrderService",
    "source_file": "src/OrderService.java",
    "models": ["gpt-3.5-turbo", "gpt-4"]  // 仅用于模型对比实验
  }
]
```

### 2. 实验结果文件格式

```json
{
  "class_name": "UserService",
  "success": true,
  "original_code": "原始代码内容...",
  "restored_code": "还原后的代码内容...",
  "time_taken": 5.67,
  "model_used": "gpt-4",
  "timestamp": "2023-03-27 14:23:45"
}
```

### 3. `query_result.json` 格式

```json
[
  {
    "semantic": {
      "distance": 0.127,
      "document": "代码片段的语义描述..."
    },
    "code": {
      "distance": 0.257,
      "document": "实际代码内容..."
    },
    "file_path": "路径/到/文件.java"
  },
  ...
]
```

### 4. `restore_detailed_results.json` 格式

```json
{
  "78": [
    {
      "file_path": "路径/到/文件.java",
      "result_type": "TP",  // 或 "FP"
      "class_name": "类名",
      "method_name": "方法名"
    },
    ...
  ]
}
```

### 5. `filtered_results.json` 格式

```json
{
  "78": [
    {
      "file_path": "路径/到/文件.java",
      "result_type": "FP_FILTERED",  // 被过滤的假阳性
      "filter_score": -18.5,         // 组合得分
      "filter_threshold": -15.0      // 使用的阈值
    },
    ...
  ]
}
```

## 常见问题与解决方案

1. **问题**: LLM API请求失败或超时
   **解决方案**: 检查API密钥是否有效，增加超时时间，实现请求重试机制

2. **问题**: 代码还原结果质量不高
   **解决方案**: 尝试使用更高级的模型，优化建模结果，或调整提示词

3. **问题**: 数据集标记不均衡(TP或FP数量太少)
   **解决方案**: 增加数据样本或考虑使用加权F1分数

4. **问题**: 找不到明显的最佳权重
   **解决方案**: 使用更高分辨率的网格搜索，缩小权重范围，或尝试不同的评估指标

5. **问题**: 误报率仍然较高
   **解决方案**: 通过分析`detailed_analysis`中的误报样本，找出共同特征，优化匹配逻辑

6. **问题**: 过滤后误报减少太多，可能过滤了一些真阳性
   **解决方案**: 调整阈值，使其更保守，或使用不同权重组合

## 最佳实践

1. 对于重要的代码还原实验，推荐使用高级模型(如GPT-4)以获得更好的结果
2. 在批量实验前先进行单个类的测试，确保配置正确
3. 权重优化应在有代表性的数据集上进行，确保数据集覆盖各种代码风格和漏洞类型
4. 定期重新优化权重，以适应系统和数据变化
5. 在解释结果时，不仅关注F1分数，还要考虑精确率和召回率在特定应用场景中的重要性
6. 保存每次优化的结果，以便比较不同版本的性能变化
7. 使用误报过滤器时，选择略微保守的阈值，避免过滤掉真阳性结果
8. 定期分析系统性能，特别是关注误分类的案例，持续改进模型
9. 对于大型项目，可以分阶段运行实验并整合结果，避免单次实验时间过长 