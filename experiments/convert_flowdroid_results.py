#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
import csv
from collections import defaultdict

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
    """从函数签名字符串中提取完整的类路径和方法名"""
    if not function_str:
        return None, None, None, None
    
    try:
        # 处理形如 "<edu.thu.benchmark.annotated.controller.CommandInjectionController: void executeCommand01(...)>" 的字符串
        if '<' in function_str and ':' in function_str:
            # 提取类的完整路径
            class_part = function_str.split('<')[1].split(':')[0].strip()
            class_name = class_part.split('.')[-1]  # 取最后一部分作为类名
            
            # 提取方法名和返回类型
            method_part = function_str.split(':')[1].strip()
            
            # 尝试提取返回类型和方法名
            if ' ' in method_part:
                return_type = method_part.split(' ')[0]
                method_name = method_part.split(' ')[1].split('(')[0]
            else:
                return_type = "void"  # 默认返回类型
                method_name = method_part.split('(')[0]
            
            return class_part, class_name, method_name, return_type
    except Exception as e:
        print(f"解析完整函数签名失败: {e} - {function_str}")
    
    return None, None, None, None

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

def generate_soot_signature(full_class_path, method_name, return_type="java.lang.Object"):
    """生成Soot格式的方法签名
    
    格式：<package.ClassName: ReturnType methodName(ParamType1,ParamType2)>
    由于参数类型信息缺失，这里只生成基本结构
    """
    return f"<{full_class_path}: {return_type} {method_name}>"

def extract_package_and_class(java_file_path, class_name):
    """从Java文件路径和类名推断包名和完整类路径"""
    try:
        # 从文件路径中找到src/main/java/后的部分作为包路径
        if 'src/main/java/' in java_file_path:
            package_path = java_file_path.split('src/main/java/')[1]
            # 去掉文件名部分
            package_path = os.path.dirname(package_path)
            # 将路径分隔符替换为点
            package_name = package_path.replace('/', '.')
            # 构建完整类名
            full_class_path = f"{package_name}.{class_name}" if package_name else class_name
            return package_name, full_class_path
    except Exception as e:
        print(f"从文件路径提取包名失败: {e} - {java_file_path}")
    
    # 无法提取时，尝试从文件名猜测包名
    try:
        file_name = os.path.basename(java_file_path)
        if file_name.endswith('.java'):
            base_name = file_name[:-5]  # 去掉.java后缀
            if base_name == class_name:
                # 从目录结构猜测包名
                dir_path = os.path.dirname(java_file_path)
                if 'controller' in dir_path.lower():
                    return "edu.thu.benchmark.annotated.controller", f"edu.thu.benchmark.annotated.controller.{class_name}"
                elif 'util' in dir_path.lower():
                    return "edu.thu.benchmark.annotated.util", f"edu.thu.benchmark.annotated.util.{class_name}"
                elif 'service' in dir_path.lower():
                    return "edu.thu.benchmark.annotated.service", f"edu.thu.benchmark.annotated.service.{class_name}"
    except Exception:
        pass
    
    # 如果无法提取，返回空包名和类名本身
    return "", class_name

def load_truth_data(truth_files):
    """加载真值表数据"""
    if not truth_files:
        return {}
    
    truth_data = {}
    
    for truth_file in truth_files:
        if not os.path.exists(truth_file):
            print(f"警告：未找到真值表文件 {truth_file}")
            continue
        
        try:
            with open(truth_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 构建唯一标识，使用类名和方法名的组合
                    key = f"{row.get('class_name', '')}.{row.get('method_name', '')}"
                    
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
                    truth_data[key] = item
            
            print(f"已加载 {len(truth_data)} 条真值表数据")
        except Exception as e:
            print(f"错误：加载真值表文件 {truth_file} 时发生异常：{e}")
    
    return truth_data

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

def is_point_matching(item, truth_item):
    """检查检测结果与真值表项是否匹配"""
    # 文件路径匹配
    if not check_path_match(item.get('file_path', ''), truth_item['file_path']):
        return False
    
    # 类名匹配
    item_class = item.get('class_name', '')
    truth_class = truth_item['class_name']
    
    if item_class and truth_class and not item_class.endswith(truth_class) and not truth_class.endswith(item_class):
        return False
    
    # 方法名匹配
    item_method = item.get('method_name', '')
    truth_method = truth_item['method_name']
    
    if item_method and truth_method and item_method != truth_method:
        return False
    
    # 检查行号是否在范围内
    line_number = int(item.get('line_number', 0))
    if line_number > 0:
        if line_number < truth_item['start_line'] or line_number > truth_item['end_line']:
            return False
    
    return True

def classify_detection(item, truth_data):
    """根据真值表对检测结果进行分类（TP或FP）"""
    if not truth_data:
        return "未知" # 没有真值表无法分类
    
    # 尝试精确匹配
    key = f"{item.get('class_name', '')}.{item.get('method_name', '')}"
    if key in truth_data:
        truth_item = truth_data[key]
        # 确保文件路径和行号也匹配
        if is_point_matching(item, truth_item):
            return "TP" if truth_item['is_vulnerability'] else "FP"
    
    # 如果没有精确匹配，尝试全面检查
    for truth_key, truth_item in truth_data.items():
        if is_point_matching(item, truth_item):
            return "TP" if truth_item['is_vulnerability'] else "FP"
    
    # 如果没有找到匹配项，标记为"未知"
    return "未知"

def convert_flowdroid_results(input_file_path, output_file_path=None, filter_cwes=None, truth_files=None):
    """将FlowDroid的原始结果转换为简化的列表格式
    
    参数:
        input_file_path: 输入文件路径
        output_file_path: 输出文件路径（可选）
        filter_cwes: 要过滤的CWE编号列表（可选）
        truth_files: 真值表文件路径列表（可选）
    """
    if not os.path.exists(input_file_path):
        print(f"错误：未找到输入文件 {input_file_path}")
        return False
    
    # 如果未指定输出文件路径，则基于输入文件生成
    if not output_file_path:
        base_name = os.path.splitext(input_file_path)[0]
        output_file_path = f"{base_name}_simplified.json"
    
    # 加载真值表数据
    truth_data = load_truth_data(truth_files)
    
    # 存储简化后的结果
    simplified_results = []
    
    try:
        # 读取原始结果
        with open(input_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 用于跟踪已处理的路径签名，防止重复
        processed_signatures = set()
        
        # 处理每个规则的结果
        for rule_data in data:
            cwe = rule_data.get('ruleCwe', 'unknown')
            
            # 如果指定了CWE过滤列表，检查当前CWE是否在列表中
            if filter_cwes and cwe not in filter_cwes:
                continue
            
            rule_id = rule_data.get('ruleId', 'unknown')
            
            results = rule_data.get('result', [])
            for result in results:
                path = result.get('path', [])
                if not path:
                    continue
                
                # 生成路径签名，用于去重
                path_signature = extract_path_signature(path)
                if path_signature in processed_signatures:
                    print(f"跳过重复路径: {path_signature}")
                    continue
                
                # 标记为已处理
                processed_signatures.add(path_signature)
                
                # 获取汇点（最后一个点）作为主要定位信息
                sink_point = path[-1]
                
                # 从函数签名中提取类名和方法名
                sink_function = sink_point.get('function', '')
                
                # 提取完整的类路径和方法信息
                full_class_path, class_name, method_name, return_type = extract_full_class_and_method(sink_function)
                
                # 如果无法从函数签名中提取，则尝试从文件路径和类名推断
                if not full_class_path or not class_name:
                    class_name = sink_point.get('javaClass', '').split('.')[-1]
                    method_name = method_name or "unknown"
                    file_path = sink_point.get('file', '')
                    _, full_class_path = extract_package_and_class(file_path, class_name)
                
                # 生成Soot格式的方法签名
                return_type = return_type or "java.lang.Object"  # 如果无法提取返回类型，使用默认值
                soot_signature = generate_soot_signature(full_class_path, method_name, return_type)
                
                # 构建简化的结果项
                simplified_item = {
                    'cwe': cwe,
                    'rule_id': rule_id,
                    'file_path': sink_point.get('file', ''),
                    'class_name': class_name,
                    'method_name': method_name,
                    'full_class_path': full_class_path,
                    'line_number': sink_point.get('line', 0),
                    'path_signature': path_signature,
                    'soot_signature': soot_signature,
                    'source_sig': result.get('sourceSig', ''),
                    'sink_sig': result.get('sinkSig', '')
                }
                
                # 如果有真值表数据，添加结果类型分类
                if truth_data:
                    result_type = classify_detection(simplified_item, truth_data)
                    simplified_item['result_type'] = result_type
                
                simplified_results.append(simplified_item)
        
        # 计算各类型结果的数量
        if truth_data:
            tp_count = len([item for item in simplified_results if item.get('result_type') == 'TP'])
            fp_count = len([item for item in simplified_results if item.get('result_type') == 'FP'])
            unknown_count = len([item for item in simplified_results if item.get('result_type') == '未知'])
            
            print(f"结果分类统计:")
            print(f"  - 真阳性 (TP): {tp_count}")
            print(f"  - 假阳性 (FP): {fp_count}")
            print(f"  - 未知: {unknown_count}")
        
        # 写入简化结果到输出文件
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(simplified_results, f, indent=2, ensure_ascii=False)
        
        filtered_msg = f"(已过滤CWE: {', '.join(filter_cwes)})" if filter_cwes else ""
        print(f"已成功转换 {len(simplified_results)} 个结果项 {filtered_msg}")
        print(f"简化结果已保存到: {output_file_path}")
        return True
    
    except Exception as e:
        print(f"转换过程中出错: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='将FlowDroid结果转换为简化列表格式')
    parser.add_argument('--input', '-i', required=True, help='FlowDroid原始结果JSON文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径（可选，默认为input_simplified.json）')
    parser.add_argument('--cwe', '-c', nargs='+', help='需要过滤的CWE编号列表（如：22 78 89）')
    parser.add_argument('--truth', '-t', nargs='+', help='真值表CSV文件路径（可选，用于标记TP/FP）')
    args = parser.parse_args()
    
    convert_flowdroid_results(args.input, args.output, args.cwe, args.truth)

if __name__ == "__main__":
    main() 