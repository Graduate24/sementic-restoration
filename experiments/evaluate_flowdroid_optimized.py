#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import json
from collections import defaultdict

# 要评估的CWE类型
CWES_TO_EVALUATE = ['22', '78', '89']  # 对应路径遍历、命令注入和SQL注入

# 真值表文件路径
TRUTH_DATA_PATHS = {
    '22': 'truth_tables/path_traversal_cwe22.csv',
    '78': 'truth_tables/command_injection_cwe78.csv',
    '89': 'truth_tables/sql_injection_cwe89.csv'
}

# FlowDroid结果文件路径
FLOWDROID_RESULTS_PATH = 'test_result_restore.json'

def load_truth_data():
    """加载真值表数据"""
    truth_data = defaultdict(list)
    
    for cwe, path in TRUTH_DATA_PATHS.items():
        if not os.path.exists(path):
            print(f"警告：未找到真值表文件 {path}")
            continue
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 将行数据转换为正确的类型
                    item = {
                        'file_path': row.get('file_path', ''),
                        'class_name': row.get('class_name', ''),
                        'method_name': row.get('method_name', ''),
                        'start_line': int(row.get('start_line', 0)),
                        'end_line': int(row.get('end_line', 0)),
                        'is_vulnerability': row.get('is_vulnerability', '').lower() == 'true',
                        'description': row.get('description', ''),
                        'remediation': row.get('remediation', '')
                    }
                    truth_data[cwe].append(item)
            print(f"已加载 {len(truth_data[cwe])} 条 CWE-{cwe} 的真值表数据")
        except Exception as e:
            print(f"错误：加载真值表文件 {path} 时发生异常：{e}")
    
    return dict(truth_data)

def extract_path_signature(path):
    """提取路径的签名（源点和汇点的组合）
    
    格式：source_class:source_method -> sink_class:sink_method
    """
    if not path or len(path) < 2:  # 至少需要源点和汇点
        return None
    
    # 获取源点（第一个点）
    source_point = path[0]
    source_function = source_point.get('function', '')
    source_class, source_method = extract_class_and_method(source_function)
    if not source_class or not source_method:
        source_class = source_point.get('javaClass', '').split('.')[-1]
    
    # 获取汇点（最后一个点）
    sink_point = path[-1]
    sink_function = sink_point.get('function', '')
    sink_class, sink_method = extract_class_and_method(sink_function)
    if not sink_class or not sink_method:
        sink_class = sink_point.get('javaClass', '').split('.')[-1]
    
    # 创建路径签名
    return f"{source_class}:{source_method} -> {sink_class}:{sink_method}"

def load_flowdroid_results():
    """加载FlowDroid的分析结果，并去重处理调用链信息"""
    if not os.path.exists(FLOWDROID_RESULTS_PATH):
        print(f"错误：未找到FlowDroid结果文件 {FLOWDROID_RESULTS_PATH}")
        return {}
    
    flowdroid_data = defaultdict(list)
    
    try:
        with open(FLOWDROID_RESULTS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 用于追踪已处理的路径签名
            processed_signatures = defaultdict(set)
            
            for rule_data in data:
                cwe = rule_data.get('ruleCwe')
                if not cwe or cwe not in CWES_TO_EVALUATE:
                    continue
                
                results = rule_data.get('result', [])
                for result in results:
                    path = result.get('path', [])
                    if not path:
                        continue
                    
                    # 生成路径签名，用于去重
                    path_signature = extract_path_signature(path)
                    if path_signature in processed_signatures[cwe]:
                        print(f"跳过重复路径: {path_signature}")
                        continue
                    
                    # 标记为已处理
                    processed_signatures[cwe].add(path_signature)
                    
                    # 获取汇点（最后一个点）作为主要定位信息
                    sink_point = path[-1]
                    
                    # 从函数签名中提取类名和方法名
                    sink_function = sink_point.get('function', '')
                    class_name, method_name = extract_class_and_method(sink_function)
                    
                    # 构建FlowDroid结果项
                    flowdroid_item = {
                        'file_path': sink_point.get('file', ''),
                        'function': sink_function,
                        'class_name': class_name or sink_point.get('javaClass', '').split('.')[-1],
                        'method_name': method_name,
                        'line_number': sink_point.get('line', 0),
                        'source': result.get('sourceSig', ''),
                        'sink': result.get('sinkSig', ''),
                        'path': path,  # 保存整个调用链
                        'path_signature': path_signature  # 存储路径签名，用于调试
                    }
                    
                    flowdroid_data[cwe].append(flowdroid_item)
            
            print(f"已加载并去重 FlowDroid 结果数据")
            for cwe in CWES_TO_EVALUATE:
                print(f"  CWE-{cwe}: {len(flowdroid_data.get(cwe, []))} 个不重复漏洞")
    except Exception as e:
        print(f"错误：加载FlowDroid结果文件时发生异常：{e}")
    
    return dict(flowdroid_data)

def extract_class_and_method(function_str):
    """从函数签名字符串中提取类名和方法名"""
    if not function_str:
        return None, None
    
    try:
        # 处理形如 "<edu.thu.benchmark.annotated.controller.CommandInjectionController: void executeCommand01(...)>" 的字符串
        if '<' in function_str and ':' in function_str:
            # 提取类的完整路径
            class_part = function_str.split('<')[1].split(':')[0].strip()
            class_name = class_part.split('.')[-1]  # 取最后一部分作为类名
            
            # 提取方法名
            method_part = function_str.split(':')[1].strip()
            method_name = method_part.split(' ')[1].split('(')[0] if ' ' in method_part else method_part.split('(')[0]
            
            return class_name, method_name
    except Exception as e:
        print(f"解析函数签名失败: {e} - {function_str}")
    
    return None, None

def extract_full_class_and_method(function_str):
    """从函数签名字符串中提取完整的类名（带包名）和方法名"""
    if not function_str:
        return None, None
    
    try:
        # 处理形如 "<edu.thu.benchmark.annotated.controller.CommandInjectionController: void executeCommand01(...)>" 的字符串
        if '<' in function_str and ':' in function_str:
            # 提取类的完整路径
            class_part = function_str.split('<')[1].split(':')[0].strip()
            
            # 提取方法名
            method_part = function_str.split(':')[1].strip()
            method_name = method_part.split(' ')[1].split('(')[0] if ' ' in method_part else method_part.split('(')[0]
            
            return class_part, method_name
    except Exception as e:
        print(f"解析函数签名失败: {e} - {function_str}")
    
    return None, None

def normalize_path(path):
    """标准化文件路径以便比较"""
    if not path:
        return ""
    
    # 统一处理路径分隔符
    normalized = path.replace('\\', '/').strip()
    
    # 如果是相对路径，转换为绝对路径
    if not normalized.startswith('/'):
        normalized = '/' + normalized
    
    return normalized

def check_path_match(flowdroid_path, truth_path):
    """检查文件路径是否匹配"""
    fd_path = normalize_path(flowdroid_path)
    t_path = normalize_path(truth_path)
    
    # 完全匹配
    if fd_path == t_path:
        return True
    
    # 文件名匹配
    fd_filename = os.path.basename(fd_path)
    t_filename = os.path.basename(t_path)
    if fd_filename == t_filename:
        return True
    
    # 路径结尾匹配
    if fd_path.endswith(t_path) or t_path.endswith(fd_path):
        return True
    
    return False

def is_matching_in_call_chain(flowdroid_item, truth_item):
    """检查真值表中的漏洞是否在调用链中的某一点匹配"""
    # 首先检查汇点是否匹配
    if is_point_matching(flowdroid_item, truth_item):
        return True
    
    # 如果汇点不匹配，检查调用链中的每个点
    for point in flowdroid_item.get('path', []):
        # 构建点信息
        function = point.get('function', '')
        class_name, method_name = extract_class_and_method(function)
        
        point_info = {
            'file_path': point.get('file', ''),
            'function': function,
            'class_name': class_name or point.get('javaClass', '').split('.')[-1],
            'method_name': method_name,
            'line_number': point.get('line', 0)
        }
        
        if is_point_matching(point_info, truth_item):
            return True
    
    return False

def is_point_matching(point_info, truth_item):
    """检查单个点是否与真值表项匹配"""
    # 文件路径匹配
    if not check_path_match(point_info.get('file_path', ''), truth_item['file_path']):
        return False
    
    # 类名匹配
    point_class = point_info.get('class_name', '')
    truth_class = truth_item['class_name']
    
    if point_class and truth_class and not point_class.endswith(truth_class) and not truth_class.endswith(point_class):
        return False
    
    # 方法名匹配
    point_method = point_info.get('method_name', '')
    truth_method = truth_item['method_name']
    
    if point_method and truth_method and point_method != truth_method:
        return False
    
    # 检查行号是否在范围内
    line_number = int(point_info.get('line_number', 0))
    if line_number > 0:
        if line_number < truth_item['start_line'] or line_number > truth_item['end_line']:
            return False
    
    return True

def calculate_metrics(truth_data, flowdroid_data):
    """计算评估指标，考虑调用链信息"""
    metrics = {}
    total_tp = total_fp = total_tn = total_fn = 0
    
    # 详细结果记录
    detailed_results = defaultdict(list)
    
    for cwe in CWES_TO_EVALUATE:
        tp = fp = tn = fn = 0
        
        truth_items = truth_data.get(cwe, [])
        flowdroid_items = flowdroid_data.get(cwe, [])
        
        # 跟踪已匹配的FlowDroid项
        matched_flowdroid_indices = set()
        
        # 为每个真值表项查找匹配的FlowDroid结果
        for i, truth_item in enumerate(truth_items):
            match_found = False
            
            for j, fd_item in enumerate(flowdroid_items):
                # 考虑调用链中的任意点匹配
                if is_matching_in_call_chain(fd_item, truth_item):
                    if truth_item['is_vulnerability']:  # 真实漏洞
                        tp += 1  # 真阳性
                        detailed_results[cwe].append({
                            'result_type': 'TP',
                            'truth_item': truth_item,
                            'flowdroid_item': fd_item
                        })
                    else:  # 非漏洞（安全实现）
                        fp += 1  # 假阳性
                        detailed_results[cwe].append({
                            'result_type': 'FP',
                            'truth_item': truth_item,
                            'flowdroid_item': fd_item
                        })
                    
                    matched_flowdroid_indices.add(j)
                    match_found = True
                    break
            
            if not match_found:
                if truth_item['is_vulnerability']:
                    fn += 1  # 假阴性
                    detailed_results[cwe].append({
                        'result_type': 'FN',
                        'truth_item': truth_item,
                        'flowdroid_item': None
                    })
                else:
                    tn += 1  # 真阴性
                    detailed_results[cwe].append({
                        'result_type': 'TN',
                        'truth_item': truth_item,
                        'flowdroid_item': None
                    })
        
        # 处理FlowDroid找到但不在真值表中的项（假设都是假阳性）
        for j, fd_item in enumerate(flowdroid_items):
            if j not in matched_flowdroid_indices:
                fp += 1
                detailed_results[cwe].append({
                    'result_type': 'FP (未匹配)',
                    'truth_item': None,
                    'flowdroid_item': fd_item
                })
        
        # 计算指标
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
        
        metrics[cwe] = {
            'TP': tp,
            'FP': fp,
            'TN': tn,
            'FN': fn,
            'Precision': precision,
            'Recall': recall,
            'F1': f1,
            'Accuracy': accuracy
        }
        
        total_tp += tp
        total_fp += fp
        total_tn += tn
        total_fn += fn
    
    # 计算总体指标
    total_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    total_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    total_f1 = 2 * total_precision * total_recall / (total_precision + total_recall) if (total_precision + total_recall) > 0 else 0
    total_accuracy = (total_tp + total_tn) / (total_tp + total_tn + total_fp + total_fn) if (total_tp + total_tn + total_fp + total_fn) > 0 else 0
    
    metrics['总体'] = {
        'TP': total_tp,
        'FP': total_fp,
        'TN': total_tn,
        'FN': total_fn,
        'Precision': total_precision,
        'Recall': total_recall,
        'F1': total_f1,
        'Accuracy': total_accuracy
    }
    
    # 保存详细结果
    save_detailed_results(detailed_results)
    
    return metrics

def save_detailed_results(detailed_results):
    """保存详细的评估结果"""
    # 简化详细结果中的数据，只保留必要信息
    simplified_results = {}
    
    for cwe, results in detailed_results.items():
        simplified_results[cwe] = []
        
        for result in results:
            simplified_item = {
                'result_type': result['result_type'],
            }
            
            if result['truth_item']:
                simplified_item['truth_item'] = {
                    'file_path': result['truth_item']['file_path'],
                    'class_name': result['truth_item']['class_name'],
                    'method_name': result['truth_item']['method_name'],
                    'start_line': result['truth_item']['start_line'],
                    'end_line': result['truth_item']['end_line'],
                    'is_vulnerability': result['truth_item']['is_vulnerability']
                }
            
            if result['flowdroid_item']:
                simplified_item['flowdroid_item'] = {
                    'file_path': result['flowdroid_item'].get('file_path', ''),
                    'class_name': result['flowdroid_item'].get('class_name', ''),
                    'method_name': result['flowdroid_item'].get('method_name', ''),
                    'line_number': result['flowdroid_item'].get('line_number', 0),
                    'path_signature': result['flowdroid_item'].get('path_signature', '')  # 添加路径签名用于调试
                }
            
            simplified_results[cwe].append(simplified_item)
    
    try:
        with open('flowdroid_detailed_results_optimized.json', 'w', encoding='utf-8') as f:
            json.dump(simplified_results, f, indent=2, ensure_ascii=False)
        print(f"详细评估结果已保存到 flowdroid_detailed_results_optimized.json")
    except Exception as e:
        print(f"保存详细评估结果时出错: {e}")

def print_metrics(metrics):
    """打印评估指标"""
    cwe_names = {
        '22': '路径遍历 (CWE-22)',
        '78': '命令注入 (CWE-78)',
        '89': 'SQL注入 (CWE-89)',
        '总体': '总体评估'
    }
    
    print("\n===== FlowDroid漏洞检测评估结果（优化版） =====\n")
    
    for cwe, metric in metrics.items():
        cwe_name = cwe_names.get(cwe, f'CWE-{cwe}')
        print(f"## {cwe_name} ##")
        print(f"真阳性 (TP): {metric['TP']}")
        print(f"假阳性 (FP): {metric['FP']}")
        print(f"真阴性 (TN): {metric['TN']}")
        print(f"假阴性 (FN): {metric['FN']}")
        print(f"精确率 (Precision): {metric['Precision']:.4f}")
        print(f"召回率 (Recall): {metric['Recall']:.4f}")
        print(f"F1分数: {metric['F1']:.4f}")
        print(f"准确率 (Accuracy): {metric['Accuracy']:.4f}")
        print("")

def save_evaluation_results(metrics):
    """保存评估结果到JSON文件"""
    try:
        with open('flowdroid_evaluation_results_optimized.json', 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"评估结果已保存到 flowdroid_evaluation_results_optimized.json")
    except Exception as e:
        print(f"保存评估结果时出错: {e}")

def main():
    # 加载数据
    truth_data = load_truth_data()
    flowdroid_data = load_flowdroid_results()
    
    # 检查数据是否加载成功
    if not truth_data or not flowdroid_data:
        print("错误：无法加载真值表或FlowDroid结果数据。请检查文件路径和格式。")
        return
    
    # 计算指标
    metrics = calculate_metrics(truth_data, flowdroid_data)
    
    # 打印结果
    print_metrics(metrics)
    
    # 保存评估结果
    save_evaluation_results(metrics)

if __name__ == "__main__":
    main() 