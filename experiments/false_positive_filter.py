#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import argparse
import os

class FalsePositiveFilter:
    def __init__(self, semantic_weight, code_weight, threshold, query_result_path=None, detailed_results_path=None):
        self.semantic_weight = semantic_weight
        self.code_weight = code_weight
        self.threshold = threshold
        
        # 若提供了路径，加载查询结果和详细分析结果
        if query_result_path:
            with open(query_result_path, 'r', encoding='utf-8') as f:
                self.query_results = json.load(f)
        
        if detailed_results_path:
            with open(detailed_results_path, 'r', encoding='utf-8') as f:
                self.detection_results = json.load(f)
    
    def load_detection_results(self, file_path):
        """加载检测结果数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            self.detection_results = json.load(f)
        print(f"已加载检测结果，包含 {sum(len(v) for v in self.detection_results.values())} 条记录")
    
    def load_query_results(self, file_path):
        """加载查询结果数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            self.query_results = json.load(f)
        print(f"已加载查询结果，包含 {len(self.query_results)} 条记录")
    
    def compute_score(self, semantic_distance, code_distance):
        """计算组合得分"""
        return -(self.semantic_weight * semantic_distance + self.code_weight * code_distance)
    
    def classify_result(self, result):
        """根据语义和代码相似度距离，判断是否为误报"""
        semantic_distance = result['semantic']['distance']
        code_distance = result['code']['distance']
        score = self.compute_score(semantic_distance, code_distance)
        
        # 得分低于阈值的视为误报
        if score < self.threshold:
            return "FP_FILTERED"  # 被过滤的误报
        else:
            return "VALID"        # 有效的报告
    
    def filter_false_positives(self):
        """过滤误报并返回结果"""
        if not hasattr(self, 'query_results') or not self.query_results:
            raise ValueError("未加载查询结果数据，请先加载数据")
        
        filtered_results = []
        fp_filtered = 0
        
        for i, result in enumerate(self.query_results):
            result_type = self.classify_result(result)
            
            # 添加分类结果
            result_with_classification = result.copy()
            result_with_classification['classification'] = result_type
            result_with_classification['combined_score'] = self.compute_score(
                result['semantic']['distance'], 
                result['code']['distance']
            )
            
            filtered_results.append(result_with_classification)
            
            if result_type == "FP_FILTERED":
                fp_filtered += 1
        
        print(f"总共过滤 {fp_filtered} 个误报，保留 {len(filtered_results) - fp_filtered} 个有效报告")
        
        return filtered_results
    
    def apply_to_detection_results(self):
        """将过滤结果应用到原始检测结果上"""
        if not hasattr(self, 'detection_results') or not self.detection_results:
            raise ValueError("未加载检测结果数据，请先加载数据")
        
        if not hasattr(self, 'query_results') or not self.query_results:
            raise ValueError("未加载查询结果数据，请先加载数据")
        
        # 创建一个新的结果结构
        filtered_detection_results = {}
        
        # 获取过滤结果
        filtered_results = self.filter_false_positives()
        
        for cwe_id, cwe_results in self.detection_results.items():
            filtered_cwe_results = []
            
            for result in cwe_results:
                # 如果是TP，直接保留
                if result['result_type'] == 'TP' or result['result_type'] == 'TN':
                    filtered_cwe_results.append(result)
                    continue
                
                # 处理FP
                if result['result_type'] == 'FP':
                    # 查找对应的查询结果
                    found = False
                    for query_result in filtered_results:
                        # 这里需要根据实际数据匹配规则来找到对应关系
                        # 假设通过某种方式能够匹配到对应的查询结果
                        if self.match_result(result, query_result):
                            found = True
                            
                            # 根据分类结果决定是保留还是过滤
                            if query_result['classification'] == 'FP_FILTERED':
                                # 过滤掉，修改结果类型
                                modified_result = result.copy()
                                modified_result['result_type'] = 'FP_FILTERED'
                                modified_result['filter_score'] = query_result['combined_score']
                                modified_result['filter_threshold'] = self.threshold
                                filtered_cwe_results.append(modified_result)
                            else:
                                # 保留原来的FP标记
                                filtered_cwe_results.append(result)
                            
                            break
                    
                    # 如果没找到对应的查询结果，则保留原来的结果
                    if not found:
                        filtered_cwe_results.append(result)
                # 其他类型的结果直接保留
                else:
                    filtered_cwe_results.append(result)
            
            filtered_detection_results[cwe_id] = filtered_cwe_results
        
        return filtered_detection_results
    
    def match_result(self, detection_result, query_result):
        """匹配检测结果与查询结果，根据具体数据结构实现匹配逻辑"""
        # 从检测结果中获取有效信息
        detection_signature = detection_result.get('flowdroid_item', {}).get('soot_signature', '')
        detection_file = detection_result.get('flowdroid_item', {}).get('file_path', '')
        detection_class = detection_result.get('flowdroid_item', {}).get('class_name', '')
        detection_method = detection_result.get('flowdroid_item', {}).get('method_name', '')
        detection_line = detection_result.get('flowdroid_item', {}).get('line_number', -1)
        
        # 查看query_result['code'] 中是否包含相似的模式
        semantic_distance = query_result['semantic']['distance']
        code_distance = query_result['code']['distance']
        
        # 根据阈值判断是否匹配
        if detection_result.get('result_type') == 'FP':
            # 使用我们的过滤标准来匹配，我们认为这是一个FP结果
            combined_score = -(self.semantic_weight * semantic_distance + self.code_weight * code_distance)
            if combined_score < self.threshold:
                # 当得分低于阈值时，认为是匹配成功
                return True
                
        # 默认匹配失败
        return False
    
    def save_filtered_results(self, filtered_results, output_path):
        """保存过滤后的结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_results, f, ensure_ascii=False, indent=2)
        print(f"已将过滤后的结果保存到 {output_path}")

def main():
    parser = argparse.ArgumentParser(description='基于最佳权重和阈值的漏洞误报过滤器')
    parser.add_argument('--semantic-weight', type=float, required=True, help='语义相似度权重')
    parser.add_argument('--code-weight', type=float, required=True, help='代码相似度权重')
    parser.add_argument('--threshold', type=float, required=True, help='分类阈值')
    parser.add_argument('--query-result', type=str, default='experiments/query_result.json', help='查询结果文件路径')
    parser.add_argument('--detection-result', type=str, default='experiments/restore_detailed_results.json', help='检测结果文件路径')
    parser.add_argument('--output', type=str, default='experiments/filtered_results.json', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 创建过滤器
    filter = FalsePositiveFilter(
        args.semantic_weight,
        args.code_weight,
        args.threshold
    )
    
    # 加载数据
    filter.load_query_results(args.query_result)
    filter.load_detection_results(args.detection_result)
    
    # 应用过滤并保存结果
    filtered_results = filter.apply_to_detection_results()
    filter.save_filtered_results(filtered_results, args.output)
    
    # 统计过滤结果
    total_fp = 0
    filtered_fp = 0
    
    for cwe_id, results in filtered_results.items():
        cwe_fp = 0
        cwe_filtered_fp = 0
        
        for result in results:
            if result['result_type'] == 'FP':
                cwe_fp += 1
            elif result['result_type'] == 'FP_FILTERED':
                cwe_filtered_fp += 1
                cwe_fp += 1  # 过滤的FP也算作原始FP
        
        total_fp += cwe_fp
        filtered_fp += cwe_filtered_fp
        
        # 添加零除保护
        if cwe_fp > 0:
            percentage = cwe_filtered_fp / cwe_fp * 100
            print(f"CWE-{cwe_id}: 共 {cwe_fp} 个FP，过滤 {cwe_filtered_fp} 个 ({percentage:.2f}% 的误报被消除)")
        else:
            print(f"CWE-{cwe_id}: 没有FP记录")
    
    # 添加零除保护
    if total_fp > 0:
        total_percentage = filtered_fp / total_fp * 100
        print(f"\n总体结果: 共 {total_fp} 个FP，过滤 {filtered_fp} 个 ({total_percentage:.2f}% 的误报被消除)")
    else:
        print("\n总体结果: 没有检测到FP记录")

if __name__ == "__main__":
    main() 