# 基于相似度的静态分析误报消除工具

本项目实现了一个基于语义相似度和代码相似度的静态分析工具误报过滤方案。通过对误报模式库的匹配，可以有效识别并过滤掉常见的误报情况，提高静态分析工具的精确率。

## 方案概述

本方案的核心思想是：
1. 建立误报模式库，包含代码片段及其语义描述
2. 使用大模型对检测出的漏洞生成语义描述
3. 计算检测结果与误报模式库的相似度（包括语义相似度和代码相似度）
4. 根据综合相似度判断是否为误报

## 目录结构

```
experiments/
├── weight_optimization.py    # 权重优化脚本
├── false_positive_filter.py  # 误报过滤应用脚本
├── query_result.json         # 相似度查询结果
├── restore_detailed_results.json  # 标记了TP/FP的检测结果
├── weight_heatmap.png        # 权重热图（运行后生成）
├── pr_curve.png              # 精确率-召回率曲线（运行后生成）
├── threshold_impact.png      # 阈值影响分析图（运行后生成）
└── README.md                 # 本文档
```

## 使用方法

### 1. 确定最佳权重和阈值

运行权重优化脚本，通过网格搜索找到最佳的语义相似度权重、代码相似度权重和阈值：

```bash
python weight_optimization.py
```

该脚本会：
- 进行网格搜索，尝试不同的权重组合
- 生成权重组合热图 `weight_heatmap.png`
- 生成最佳权重的PR曲线 `pr_curve.png`
- 分析阈值对性能的影响 `threshold_impact.png`
- 保存详细分析结果到 `weight_optimization_results.json`

### 2. 应用误报过滤

使用找到的最佳权重和阈值，运行误报过滤器：

```bash
python false_positive_filter.py --semantic-weight 0.6 --code-weight 0.4 --threshold -15.5
```

参数说明：
- `--semantic-weight`：语义相似度权重（根据优化结果填写）
- `--code-weight`：代码相似度权重（根据优化结果填写）
- `--threshold`：分类阈值（根据优化结果填写）
- `--query-result`：查询结果文件路径（可选，默认为 `experiments/query_result.json`）
- `--detection-result`：检测结果文件路径（可选，默认为 `experiments/restore_detailed_results.json`）
- `--output`：输出文件路径（可选，默认为 `experiments/filtered_results.json`）

该脚本会：
- 根据指定的权重和阈值，计算每个检测结果的组合分数
- 过滤掉被判定为误报的结果
- 保存过滤后的结果到指定输出文件
- 输出误报过滤统计信息

## 调优建议

为了获得最佳的误报过滤效果，可以考虑以下几点：

1. **权重平衡**：语义相似度和代码相似度的权重应当根据具体场景调整。一般来说，语义相似度对于识别误报模式更有效，可以给予更高的权重。

2. **阈值选择**：阈值过高会导致大量误报被保留，阈值过低则可能错误地过滤掉真正的漏洞。建议根据PR曲线和阈值影响分析图选择合适的阈值，通常在F1分数最高的点附近。

3. **误报模式库扩充**：随着使用过程中积累更多误报样例，应当不断扩充误报模式库，提高覆盖率。

4. **特定领域适应**：对于特定领域的代码，可能需要调整权重和阈值，以适应该领域的特点。

## 性能指标

使用本方案进行误报过滤，可以通过以下指标评估效果：

- **误报消除率**：成功过滤的误报数量 / 总误报数量
- **误杀率**：错误过滤的真实漏洞数量 / 总真实漏洞数量
- **F1分数**：综合考虑精确率和召回率的调和平均值

理想情况下，我们希望在保持高召回率（不误杀真实漏洞）的同时，提高精确率（减少误报）。

## 限制和注意事项

1. 本方案需要预先标记部分数据以训练最佳权重和阈值。
2. 对于全新类型的误报模式，可能无法有效识别，需要不断更新误报模式库。
3. 在实际应用中，应根据具体场景对 `match_result` 函数进行修改，以正确匹配检测结果和查询结果。
4. 建议定期重新优化权重和阈值，以适应不断变化的代码库和误报模式。 