#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import json
import argparse
from collections import defaultdict

# 要评估的CWE类型
CWES_TO_EVALUATE = ['22', '78', '89']  # 对应路径遍历、命令注入和SQL注入

# 真值表文件路径
TRUTH_DATA_PATHS = {
    '22': 'truth_tables/path_traversal_cwe22.csv',
    '78': 'truth_tables/command_injection_cwe78.csv',
    '89': 'truth_tables/sql_injection_cwe89.csv'
}

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

def load_flowdroid_results(results_file_path):
    """加载FlowDroid的分析结果，并去重处理调用链信息"""
    if not os.path.exists(results_file_path):
        print(f"错误：未找到FlowDroid结果文件 {results_file_path}")
        return {}
    
    flowdroid_data = defaultdict(list)
    
    try:
        with open(results_file_path, 'r', encoding='utf-8') as f:
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
    """从函数签名字符串中提取完整的类名（带包名）、方法名、返回类型和参数列表"""
    if not function_str:
        return None, None, None, None
    
    try:
        # 处理形如 "<edu.thu.benchmark.annotated.controller.CommandInjectionController: void executeCommand01(...)>" 的字符串
        if '<' in function_str and ':' in function_str:
            # 提取类的完整路径
            class_part = function_str.split('<')[1].split(':')[0].strip()
            
            # 提取方法完整部分（包含返回类型、方法名和参数）
            method_part = function_str.split(':')[1].strip()
            
            # 提取方法完整签名，包括返回类型、方法名和参数
            if '>' in method_part:
                method_part = method_part[:-1]  # 去除结尾的'>'
            
            # 查找返回类型和方法名（包括参数）的分隔位置
            space_pos = method_part.find(' ')
            if space_pos != -1:
                return_type = method_part[:space_pos].strip()
                method_with_params = method_part[space_pos+1:].strip()
                
                # 提取方法名（不带参数）
                if '(' in method_with_params:
                    method_name = method_with_params.split('(')[0].strip()
                else:
                    method_name = method_with_params
                
                return class_part, method_name, return_type, method_with_params
            else:
                # 如果没有空格分隔符，可能是非标准格式
                return class_part, method_part, "void", method_part
            
    except Exception as e:
        print(f"解析函数签名失败: {e} - {function_str}")
    
    return None, None, None, None

def generate_soot_signature(full_class_path, method_with_params=None, return_type="java.lang.Object", method_name=None):
    """生成Soot格式的方法签名
    
    格式：<package.ClassName: ReturnType methodName(ParamType1,ParamType2)>
    保留完整的参数类型列表
    """
    # 如果提供了完整的方法签名（含参数），优先使用
    if method_with_params and '(' in method_with_params:
        return f"<{full_class_path}: {return_type} {method_with_params}>"
    
    # 否则使用方法名构建基本签名（带空括号）
    method_to_use = method_name if method_name else "unknown"
    return f"<{full_class_path}: {return_type} {method_to_use}()>"

def extract_package_and_class(file_path, class_name):
    """从文件路径和类名尝试推断包名和完整类路径"""
    if not file_path or not class_name:
        return "", class_name
    
    try:
        # 尝试从文件路径推断包名
        if 'src/main/java/' in file_path:
            package_path = file_path.split('src/main/java/')[1]
            # 去掉文件名部分
            package_path = '/'.join(package_path.split('/')[:-1])
            # 将路径分隔符替换为点
            package_name = package_path.replace('/', '.')
            # 构建完整类名
            full_class_path = f"{package_name}.{class_name}" if package_name else class_name
            return package_name, full_class_path
    except Exception as e:
        print(f"从文件路径提取包名失败: {e} - {file_path}")
    
    # 无法提取时，尝试从文件路径猜测包名
    try:
        file_name = file_path.split('/')[-1]
        if file_name.endswith('.java'):
            base_name = file_name[:-5]  # 去掉.java后缀
            if base_name == class_name:
                # 从目录结构猜测包名
                if 'controller' in file_path.lower():
                    return "edu.thu.benchmark.annotated.controller", f"edu.thu.benchmark.annotated.controller.{class_name}"
                elif 'service' in file_path.lower():
                    return "edu.thu.benchmark.annotated.service", f"edu.thu.benchmark.annotated.service.{class_name}"
                elif 'util' in file_path.lower():
                    return "edu.thu.benchmark.annotated.util", f"edu.thu.benchmark.annotated.util.{class_name}"
                elif 'aspect' in file_path.lower():
                    return "edu.thu.benchmark.annotated.aspect", f"edu.thu.benchmark.annotated.aspect.{class_name}"
    except Exception:
        pass
    
    # 如果无法提取，返回默认包名和类名
    return "edu.thu.benchmark.annotated", f"edu.thu.benchmark.annotated.{class_name}"

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

def calculate_metrics(truth_data, flowdroid_data, base_output_name):
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
    save_detailed_results(detailed_results, base_output_name)
    
    return metrics

def save_detailed_results(detailed_results, base_output_name):
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
                # 获取类名、方法名和文件路径
                class_name = result['flowdroid_item'].get('class_name', '')
                method_name = result['flowdroid_item'].get('method_name', '')
                file_path = result['flowdroid_item'].get('file_path', '')
                
                # 直接使用原始的函数签名（如果存在且格式正确）
                sink_function = result['flowdroid_item'].get('function', '')
                if sink_function and sink_function.startswith('<') and sink_function.endswith('>') and ':' in sink_function:
                    # 已经是标准Soot格式，直接使用
                    soot_signature = sink_function
                else:
                    # 从函数签名中提取信息
                    full_class_path = None
                    return_type = "java.lang.Object"
                    method_with_params = None
                    
                    # 查看调用链中是否有更完整的函数签名信息
                    path = result['flowdroid_item'].get('path', [])
                    best_signature = None
                    
                    for point in path:
                        point_function = point.get('function', '')
                        if point_function and '(' in point_function and ')' in point_function:
                            best_signature = point_function
                            break
                    
                    # 使用找到的最佳签名
                    if best_signature:
                        full_class_path, method_name, return_type, method_with_params = extract_full_class_and_method(best_signature)
                    elif sink_function:
                        full_class_path, method_name, return_type, method_with_params = extract_full_class_and_method(sink_function)
                    
                    # 如果仍然无法提取，尝试从文件路径推断
                    if not full_class_path:
                        _, full_class_path = extract_package_and_class(file_path, class_name)
                    
                    # 生成Soot签名
                    soot_signature = generate_soot_signature(full_class_path, method_with_params, return_type, method_name)
                
                simplified_item['flowdroid_item'] = {
                    'file_path': file_path,
                    'class_name': class_name,
                    'method_name': method_name,
                    'line_number': result['flowdroid_item'].get('line_number', 0),
                    'path_signature': result['flowdroid_item'].get('path_signature', ''),
                    'soot_signature': soot_signature
                }
            
            simplified_results[cwe].append(simplified_item)
    
    detailed_results_file = f"{base_output_name}_detailed_results.json"
    try:
        with open(detailed_results_file, 'w', encoding='utf-8') as f:
            json.dump(simplified_results, f, indent=2, ensure_ascii=False)
        print(f"详细评估结果已保存到 {detailed_results_file}")
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
    
    # 打印评估指标计算公式说明
    print("评估指标计算公式说明:")
    print("- 精确率 (Precision) = TP / (TP + FP) - 所有报告的漏洞中真实漏洞的比例")
    print("- 召回率 (Recall) = TP / (TP + FN) - 所有真实漏洞中被成功检测到的比例")
    print("- F1分数 = 2 * (Precision * Recall) / (Precision + Recall) - 精确率和召回率的调和平均值")
    print("- 准确率 (Accuracy) = (TP + TN) / (TP + TN + FP + FN) - 所有预测中正确预测的比例")
    print("其中: TP=真阳性, FP=假阳性, TN=真阴性, FN=假阴性\n")
    
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

def save_evaluation_results(metrics, base_output_name):
    """保存评估结果到JSON文件"""
    evaluation_results_file = f"{base_output_name}_evaluation_results.json"
    try:
        with open(evaluation_results_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"评估结果已保存到 {evaluation_results_file}")
    except Exception as e:
        print(f"保存评估结果时出错: {e}")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='评估FlowDroid检测结果')
    parser.add_argument('--input', '-i', required=True, help='FlowDroid结果JSON文件路径')
    parser.add_argument('--output', '-o', help='输出文件名前缀，默认基于输入文件名')
    args = parser.parse_args()
    
    # 设置输出文件名前缀
    if args.output:
        base_output_name = args.output
    else:
        # 从输入文件名生成输出文件名前缀
        base_name = os.path.basename(args.input)
        base_output_name = os.path.splitext(base_name)[0]
    
    # 加载数据
    truth_data = load_truth_data()
    flowdroid_data = load_flowdroid_results(args.input)
    
    # 检查数据是否加载成功
    if not truth_data or not flowdroid_data:
        print("错误：无法加载真值表或FlowDroid结果数据。请检查文件路径和格式。")
        return
    
    # 计算指标
    metrics = calculate_metrics(truth_data, flowdroid_data, base_output_name)
    
    # 打印结果
    print_metrics(metrics)
    
    # 保存评估结果
    save_evaluation_results(metrics, base_output_name)

if __name__ == "__main__":
    main() 