#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, average_precision_score, f1_score, precision_score, recall_score
import os
import pandas as pd
import csv

class WeightOptimizer:
    def __init__(self, query_result_path, ground_truth_path):
        # 加载查询结果数据
        with open(query_result_path, 'r', encoding='utf-8') as f:
            self.query_results = json.load(f)
        
        # 加载标记好的真值数据（TP/FP标记）
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            self.ground_truth = json.load(f)
        
        # 提取CWE-78的结果
        self.cwe78_results = self.ground_truth.get('78', [])
        
        # 创建索引映射，便于后续匹配
        self.true_positive_indices = []
        self.false_positive_indices = []
        
        # 统计TP和FP在ground truth中的数量
        self.num_true_positives = 0
        self.num_false_positives = 0
        
        # 根据ground truth标记初始化
        for i, item in enumerate(self.cwe78_results):
            if item['result_type'] == 'TP':
                self.num_true_positives += 1
                self.true_positive_indices.append(i)
            elif item['result_type'] == 'FP':
                self.num_false_positives += 1
                self.false_positive_indices.append(i)
        
        print(f"数据集包含 {self.num_true_positives} 个真正例(TP)和 {self.num_false_positives} 个假正例(FP)")
        
        # 确保query_results与cwe78_results的顺序一致
        if len(self.query_results) != (self.num_true_positives + self.num_false_positives):
            print(f"警告: 查询结果数量({len(self.query_results)})与ground truth中的TP+FP数量({self.num_true_positives + self.num_false_positives})不一致")
    
    def compute_combined_score(self, semantic_weight, code_weight):
        """计算组合分数并返回标签和分数"""
        y_true = []  # 实际标签(1表示TP, 0表示FP)
        scores = []  # 组合得分
        
        for i, result in enumerate(self.query_results):
            semantic_distance = result['semantic']['distance']
            code_distance = result['code']['distance']
            
            # 计算加权组合得分 (负值是为了让较小的距离得到较高的得分)
            combined_score = -(semantic_weight * semantic_distance + code_weight * code_distance)
            scores.append(combined_score)
            
            # 确定实际标签
            is_tp = i < self.num_true_positives  # 假设query_results的排序与ground truth中的顺序一致
            y_true.append(1 if is_tp else 0)
        
        return np.array(y_true), np.array(scores)
    
    def evaluate_weights(self, semantic_weight, code_weight, threshold=None):
        """评估特定权重组合的性能"""
        y_true, scores = self.compute_combined_score(semantic_weight, code_weight)
        
        if threshold is None:
            # 如果没有指定阈值，计算PR曲线并返回最佳F1分数
            precision, recall, thresholds = precision_recall_curve(y_true, scores)
            f1_scores = 2 * precision * recall / (precision + recall + 1e-10)
            best_idx = np.argmax(f1_scores)
            best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else thresholds[-1]
            best_precision = precision[best_idx]
            best_recall = recall[best_idx]
            best_f1 = f1_scores[best_idx]
            return {
                'semantic_weight': semantic_weight,
                'code_weight': code_weight,
                'best_threshold': best_threshold,
                'best_f1': best_f1,
                'best_precision': best_precision,
                'best_recall': best_recall,
                'avg_precision': average_precision_score(y_true, scores)
            }
        else:
            # 使用给定阈值计算指标
            y_pred = (scores >= threshold).astype(int)
            return {
                'semantic_weight': semantic_weight,
                'code_weight': code_weight,
                'threshold': threshold,
                'precision': precision_score(y_true, y_pred, zero_division=0),
                'recall': recall_score(y_true, y_pred, zero_division=0),
                'f1': f1_score(y_true, y_pred, zero_division=0)
            }
    
    def grid_search(self, verbose=True):
        """进行网格搜索以找到最佳权重组合"""
        # 设置权重值范围
        semantic_weights = np.linspace(0.1, 0.9, 9)
        code_weights = np.linspace(0.1, 0.9, 9)
        
        results = []
        best_result = {'best_f1': 0}
        
        for sw in semantic_weights:
            for cw in code_weights:
                # 标准化权重
                total = sw + cw
                semantic_norm = sw / total
                code_norm = cw / total
                
                result = self.evaluate_weights(semantic_norm, code_norm)
                results.append(result)
                
                if result['best_f1'] > best_result['best_f1']:
                    best_result = result
                
                if verbose:
                    print(f"语义权重={semantic_norm:.2f}, 代码权重={code_norm:.2f}, "
                          f"最佳F1={result['best_f1']:.4f}, 精确率={result['best_precision']:.4f}, "
                          f"召回率={result['best_recall']:.4f}, 阈值={result['best_threshold']:.4f}")
        
        print("\n最佳权重组合:")
        print(f"语义权重={best_result['semantic_weight']:.2f}, 代码权重={best_result['code_weight']:.2f}")
        print(f"最佳F1={best_result['best_f1']:.4f}, 精确率={best_result['best_precision']:.4f}, 召回率={best_result['best_recall']:.4f}")
        print(f"最佳阈值={best_result['best_threshold']:.4f}")
        
        return results, best_result
    
    def plot_heatmap(self, results):
        """绘制F1分数热图"""
        semantic_weights = sorted(list(set([round(r['semantic_weight'], 2) for r in results])))
        code_weights = sorted(list(set([round(r['code_weight'], 2) for r in results])))
        
        f1_matrix = np.zeros((len(semantic_weights), len(code_weights)))
        
        for r in results:
            sw_idx = semantic_weights.index(round(r['semantic_weight'], 2))
            cw_idx = code_weights.index(round(r['code_weight'], 2))
            f1_matrix[sw_idx, cw_idx] = r['best_f1']
        
        plt.figure(figsize=(10, 8))
        plt.imshow(f1_matrix, cmap='viridis', interpolation='nearest')
        plt.colorbar(label='F1 Score')
        plt.xticks(np.arange(len(code_weights)), [f"{w:.2f}" for w in code_weights], rotation=45)
        plt.yticks(np.arange(len(semantic_weights)), [f"{w:.2f}" for w in semantic_weights])
        plt.xlabel('Code Similarity Weight')
        plt.ylabel('Semantic Similarity Weight')
        plt.title('F1 Scores for Different Weight Combinations')
        
        # 在热图上标注具体值
        for i in range(len(semantic_weights)):
            for j in range(len(code_weights)):
                plt.text(j, i, f"{f1_matrix[i, j]:.3f}", 
                         ha="center", va="center", 
                         color="white" if f1_matrix[i, j] < 0.7 else "black")
        
        plt.tight_layout()
        plt.savefig('experiments/weight_heatmap.png')
        plt.close()
    
    def plot_pr_curve(self, best_weights):
        """为最佳权重组合绘制PR曲线"""
        semantic_weight = best_weights['semantic_weight']
        code_weight = best_weights['code_weight']
        
        y_true, scores = self.compute_combined_score(semantic_weight, code_weight)
        precision, recall, thresholds = precision_recall_curve(y_true, scores)
        
        plt.figure(figsize=(10, 6))
        plt.plot(recall, precision, marker='.', label=f'PR Curve (AP={average_precision_score(y_true, scores):.3f})')
        
        # 标记最佳F1点
        f1_scores = 2 * precision * recall / (precision + recall + 1e-10)
        best_idx = np.argmax(f1_scores)
        plt.plot(recall[best_idx], precision[best_idx], 'ro', 
                 label=f'Best F1={f1_scores[best_idx]:.3f} (Threshold={thresholds[best_idx] if best_idx < len(thresholds) else thresholds[-1]:.3f})')
        
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title(f'PR Curve (Semantic Weight={semantic_weight:.2f}, Code Weight={code_weight:.2f})')
        plt.legend(loc='lower left')
        plt.grid(True)
        plt.savefig('experiments/pr_curve.png')
        plt.close()
    
    def analysis_threshold_impact(self, best_weights):
        """分析阈值对消除误报的影响"""
        semantic_weight = best_weights['semantic_weight']
        code_weight = best_weights['code_weight']
        
        thresholds = np.linspace(-50, 0, 100)  # 使用更大范围的阈值
        results = []
        
        for threshold in thresholds:
            result = self.evaluate_weights(semantic_weight, code_weight, threshold)
            results.append(result)
        
        # 绘制阈值对精确率、召回率和F1的影响
        plt.figure(figsize=(12, 6))
        
        precisions = [r['precision'] for r in results]
        recalls = [r['recall'] for r in results]
        f1s = [r['f1'] for r in results]
        
        plt.plot(thresholds, precisions, label='Precision', marker='.')
        plt.plot(thresholds, recalls, label='Recall', marker='.')
        plt.plot(thresholds, f1s, label='F1 Score', marker='.')
        
        plt.axvline(x=best_weights['best_threshold'], color='r', linestyle='--', 
                    label=f'Best Threshold={best_weights["best_threshold"]:.3f}')
        
        plt.xlabel('Threshold')
        plt.ylabel('Metric Value')
        plt.title(f'Threshold Impact on Performance (Semantic Weight={semantic_weight:.2f}, Code Weight={code_weight:.2f})')
        plt.legend()
        plt.grid(True)
        plt.savefig('experiments/threshold_impact.png')
        plt.close()
    
    def detailed_analysis(self, best_weights):
        """详细分析最佳权重和阈值下的分类结果"""
        semantic_weight = best_weights['semantic_weight']
        code_weight = best_weights['code_weight']
        threshold = best_weights['best_threshold']
        
        y_true, scores = self.compute_combined_score(semantic_weight, code_weight)
        y_pred = (scores >= threshold).astype(int)
        
        # 分析各类结果
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        
        print("\nDetailed Analysis Results:")
        print(f"True Positives (TP): {tp}")
        print(f"False Positives (FP): {fp}")
        print(f"True Negatives (TN): {tn}")
        print(f"False Negatives (FN): {fn}")
        
        print(f"\nPrecision: {tp/(tp+fp) if tp+fp > 0 else 0:.4f}")
        print(f"Recall: {tp/(tp+fn) if tp+fn > 0 else 0:.4f}")
        print(f"F1 Score: {2*tp/(2*tp+fp+fn) if 2*tp+fp+fn > 0 else 0:.4f}")
        
        # 记录分类错误的样本
        misclassified = []
        for i, (true, pred, score) in enumerate(zip(y_true, y_pred, scores)):
            if true != pred:
                result = self.query_results[i]
                misclassified.append({
                    'index': i,
                    'true_label': 'TP' if true == 1 else 'FP',
                    'predicted': 'TP' if pred == 1 else 'FP',
                    'score': score,
                    'semantic_distance': result['semantic']['distance'],
                    'code_distance': result['code']['distance']
                })
        
        print(f"\nMisclassified Sample Count: {len(misclassified)}")
        for i, sample in enumerate(misclassified):
            print(f"\nMisclassified Sample {i+1}:")
            print(f"   True Label: {sample['true_label']}")
            print(f"   Predicted Label: {sample['predicted']}")
            print(f"   Combined Score: {sample['score']:.4f} (Threshold: {threshold:.4f})")
            print(f"   Semantic Distance: {sample['semantic_distance']:.4f}")
            print(f"   Code Distance: {sample['code_distance']:.4f}")
        
        return {
            'confusion_matrix': {
                'tp': int(tp), 'fp': int(fp), 'tn': int(tn), 'fn': int(fn)
            },
            'metrics': {
                'precision': tp/(tp+fp) if tp+fp > 0 else 0,
                'recall': tp/(tp+fn) if tp+fn > 0 else 0,
                'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn > 0 else 0
            },
            'misclassified': misclassified
        }
    
    def save_results(self, best_weights, detailed_results):
        """保存最佳权重和详细分析结果"""
        results = {
            'best_weights': best_weights,
            'detailed_results': detailed_results
        }
        
        with open('experiments/weight_optimization_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print("\nResults saved to experiments/weight_optimization_results.json")
    
    def generate_comparison_table(self):
        """生成不同权重组合的性能比较表格，并保存为CSV文件"""
        # 测试不同权重组合
        weights = [
            (0.5, 0.5),
            (0.6, 0.4),
            (0.7, 0.3),
            (0.8, 0.2),
            (0.4, 0.6),
            (0.3, 0.7)
        ]
        
        # 对于每个权重组合，测试不同阈值
        thresholds = [-30.0, -25.0, -20.0, -15.0, -10.0]
        
        results = []
        best_results = []
        
        for semantic_weight, code_weight in weights:
            print(f"Testing weight combination: 语义权重={semantic_weight}, 代码权重={code_weight}")
            
            # 准备评估数据
            true_labels = []  # 真实标签
            scores = []       # 组合分数
            
            for item in self.cwe78_results:
                result_type = item.get("result_type", "unknown")
                if result_type in ["TP", "FP"]:  # 只关注真阳性和假阳性
                    # 添加到标签列表(TP=1, FP=0)
                    true_labels.append(1 if result_type == "TP" else 0)
                    
                    # 基于权重计算综合得分
                    best_match = None
                    best_score = float("-inf")
                    
                    for query_item in self.query_results:
                        # 检查文件路径和类名是否匹配
                        if (item.get("file_path", "") in query_item.get("file_path", "") or 
                            query_item.get("file_path", "") in item.get("file_path", "")):
                            
                            semantic_distance = query_item.get("semantic_distance", 1.0)
                            code_distance = query_item.get("code_distance", 1.0)
                            
                            # 计算加权分数 (距离越小，分数越高)
                            score = -(semantic_weight * semantic_distance + code_weight * code_distance)
                            
                            if score > best_score:
                                best_score = score
                                best_match = query_item
                    
                    # 如果找到匹配项，添加分数到列表
                    if best_match:
                        scores.append(best_score)
                    else:
                        # 如果没有找到匹配项，给予最低分数
                        scores.append(float("-inf"))
            
            # 计算PR曲线和最佳阈值
            if len(true_labels) > 0 and len(scores) > 0:
                # 对每个阈值，计算precision、recall和F1
                for threshold in thresholds:
                    predicted = [1 if s >= threshold else 0 for s in scores]
                    
                    # 计算性能指标
                    tp = sum(1 for i in range(len(true_labels)) if true_labels[i] == 1 and predicted[i] == 1)
                    fp = sum(1 for i in range(len(true_labels)) if true_labels[i] == 0 and predicted[i] == 1)
                    fn = sum(1 for i in range(len(true_labels)) if true_labels[i] == 1 and predicted[i] == 0)
                    
                    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                    
                    # 保存结果
                    result = {
                        "semantic_weight": semantic_weight,
                        "code_weight": code_weight,
                        "best_threshold": threshold,
                        "best_f1": f1,
                        "best_precision": precision,
                        "best_recall": recall,
                        "ap": average_precision_score(true_labels, scores)
                    }
                    results.append(result)
                    best_results.append(result)
                    
                    print(f"  最佳阈值: {threshold:.2f}, F1: {f1:.4f}, 精确率: {precision:.4f}, 召回率: {recall:.4f}, AP: {average_precision_score(true_labels, scores):.4f}")
        
        # 创建基本的比较表
        comparison_df = pd.DataFrame(results)
        comparison_df.to_csv('experiments/weight_comparison.csv', index=False)
        
        # 创建Markdown格式的表格
        with open('experiments/weight_comparison_table.md', 'w') as f:
            f.write("# 权重组合比较表\n\n")
            
            # 基本比较表
            f.write("## 权重组合性能总览\n\n")
            f.write("| 语义权重 | 代码权重 | 最佳阈值 | 最佳F1 | 最佳精确率 | 最佳召回率 | AP值 |\n")
            f.write("|---------|---------|----------|--------|-----------|-----------|------|\n")
            
            for result in best_results:
                f.write(f"| {result['semantic_weight']:.2f} | {result['code_weight']:.2f} | {result['best_threshold']:.2f} ")
                f.write(f"| {result['best_f1']:.4f} | {result['best_precision']:.4f} | {result['best_recall']:.4f} ")
                f.write(f"| {result['ap']:.4f} |\n")
            
            # 不同阈值下的比较
            f.write("\n## 不同阈值下的性能比较\n\n")
            
            for threshold in thresholds:
                f.write(f"\n### 阈值 = {threshold}\n\n")
                f.write("| 权重组合 | 精确率 | 召回率 | F1分数 |\n")
                f.write("|----------|--------|--------|-------|\n")
                
                for semantic_weight, code_weight in weights:
                    metrics = {
                        'precision': precision_score(true_labels, [1 if s >= threshold else 0 for s in scores], zero_division=0),
                        'recall': recall_score(true_labels, [1 if s >= threshold else 0 for s in scores], zero_division=0),
                        'f1': f1_score(true_labels, [1 if s >= threshold else 0 for s in scores], zero_division=0)
                    }
                    f.write(f"| {semantic_weight:.1f}:{code_weight:.1f} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['f1']:.4f} |\n")
        
        print(f"比较表已保存至: experiments/weight_comparison.csv")
        print(f"Markdown格式表格已保存至: experiments/weight_comparison_table.md")
        print(f"PR曲线已保存至experiments目录")
        
        return best_results

def main():
    # 创建目录
    os.makedirs('experiments', exist_ok=True)
    
    # 初始化优化器
    optimizer = WeightOptimizer(
        query_result_path='experiments/query_result.json', 
        ground_truth_path='experiments/restore_detailed_results.json'
    )
    
    # 执行网格搜索
    results, best_result = optimizer.grid_search()
    
    # 绘制热图
    optimizer.plot_heatmap(results)
    
    # 绘制PR曲线
    optimizer.plot_pr_curve(best_result)
    
    # 分析阈值影响
    optimizer.analysis_threshold_impact(best_result)
    
    # 详细分析最佳结果
    detailed_results = optimizer.detailed_analysis(best_result)
    
    # 生成比较表格
    best_results = optimizer.generate_comparison_table()
    
    # 保存结果
    optimizer.save_results(best_result, detailed_results)
    
    print("\nAnalysis completed. Visualizations generated.")
    print("1. Weight Combination Heatmap: experiments/weight_heatmap.png")
    print("2. Best Weight PR Curve: experiments/pr_curve.png")
    print("3. Threshold Impact Analysis: experiments/threshold_impact.png")
    print("4. Weight Comparison Table: experiments/weight_comparison.csv")
    print("5. Markdown Tables: experiments/weight_comparison_table.md")
    print("6. Additional PR Curves for different weights saved in experiments/")

if __name__ == "__main__":
    main() 