# ROC曲线分析结果

## 不同权重组合的ROC AUC值

| 语义权重 | 代码权重 | ROC AUC |
|---------|---------|----------|
| 0.50 | 0.50 | 0.5000 |
| 0.60 | 0.40 | 0.5000 |
| 0.70 | 0.30 | 0.5000 |
| 0.80 | 0.20 | 0.5000 |
| 0.40 | 0.60 | 0.5000 |
| 0.30 | 0.70 | 0.5000 |

## ROC曲线解释

ROC曲线(接收者操作特征曲线)是一种评估二分类模型性能的图形工具。它通过绘制不同阈值下的真阳性率(TPR)和假阳性率(FPR)的关系来展示模型的表现。

* **横轴**：假阳性率(FPR) = 假阳性/(假阳性+真阴性)
* **纵轴**：真阳性率(TPR) = 真阳性/(真阳性+假阴性)
* **AUC值**：曲线下面积，取值范围为[0,1]。AUC值越大，说明模型的分类性能越好。

### AUC值解释

* **AUC=1.0**：完美分类，模型能够100%正确区分真阳性和假阳性
* **AUC=0.5**：相当于随机猜测，模型没有区分能力
* **0.7≤AUC<0.8**：可接受的区分能力
* **0.8≤AUC<0.9**：良好的区分能力
* **AUC≥0.9**：极佳的区分能力

### 与PR曲线的比较

* ROC曲线在类别不平衡问题上比PR曲线更稳定
* 当我们更关注查全率(召回率)和真阳性时，ROC曲线更有参考价值
* ROC曲线能更好地反映模型在不同阈值下的整体表现

### ROC曲线与阈值选择

* ROC曲线上的每一点对应一个特定的阈值
* 左上角的点表示高TPR(高召回率)和低FPR(高特异度)，通常是理想的阈值选择区域
* 右上角的点表示高TPR但也有高FPR，适用于更关注不遗漏真阳性的场景
* 在安全分析中，我们通常更倾向于高召回率，以确保不遗漏真实漏洞
