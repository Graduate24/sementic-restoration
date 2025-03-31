"""
误报消除评价脚本，用于评估误报消除的准确性
"""

import os
import json
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prunefp_evaluate")

@dataclass
class EvaluationMetrics:
    """评估指标数据类"""
    total: int = 0
    true_positives: int = 0
    false_positives: int = 0
    uncertain: int = 0
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0
    correct_true_positives: int = 0
    correct_false_positives: int = 0
    incorrect_true_positives: int = 0
    incorrect_false_positives: int = 0
    correct_uncertain: int = 0
    incorrect_uncertain: int = 0

class FalsePositiveEvaluator:
    """误报消除评价器"""
    
    def __init__(self, tool_result_path: str, ground_truth_path: str):
        """
        初始化评价器
        
        参数:
            tool_result_path: 误报消除工具的结果文件路径
            ground_truth_path: 人工标注的真实结果文件路径
        """
        self.tool_result_path = tool_result_path
        self.ground_truth_path = ground_truth_path
        self.metrics = EvaluationMetrics()
        
        # 加载结果
        self.tool_results = self._load_results(tool_result_path)
        self.ground_truth = self._load_results(ground_truth_path)
        
        # 创建方法签名到结果的映射
        self.tool_result_map = {}
        self.ground_truth_map = {}
        
        # 创建结果映射
        self.tool_result_map = self._create_result_map(self.tool_results)
        self.ground_truth_map = self._create_result_map(self.ground_truth)
        
        logger.info(f"初始化评价器: 工具结果={tool_result_path}, 真实结果={ground_truth_path}")
    
    def _load_results(self, result_path: str) -> Dict:
        """
        加载结果文件
        
        参数:
            result_path: 结果文件路径
            
        返回:
            解析后的结果字典
        """
        if not os.path.exists(result_path):
            error_msg = f"结果文件不存在: {result_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            logger.info(f"成功加载结果文件: {result_path}, 键名: {list(results.keys())}")
            
            # 检查文件内容格式
            if "details" in results:
                logger.info(f"检测到工具结果格式，包含 {len(results.get('details', []))} 条详细记录")
                if len(results.get("details", [])) == 0:
                    logger.warning("警告：工具结果中没有详细记录！")
                else:
                    sample = results["details"][0]
                    logger.info(f"示例记录: 键名={list(sample.keys())}")
                    if "原始数据" in sample:
                        logger.info(f"原始数据示例: 键名={list(sample['原始数据'].keys())}")
            else:
                total_items = sum(len(vuln_list) if isinstance(vuln_list, list) else 0 for vuln_list in results.values())
                logger.info(f"检测到真值结果格式，包含 {len(results)} 个漏洞类型，共 {total_items} 条记录")
                
                # 如果没有内容，输出更多信息
                if total_items == 0:
                    logger.error(f"错误：真值结果中没有记录！完整内容：{json.dumps(results, ensure_ascii=False)[:1000]}")
                else:
                    # 找到第一个非空列表
                    for vuln_id, vuln_list in results.items():
                        if isinstance(vuln_list, list) and len(vuln_list) > 0:
                            sample = vuln_list[0]
                            logger.info(f"示例记录({vuln_id}): 键名={list(sample.keys())}")
                            if "result_type" in sample:
                                logger.info(f"结果类型: {sample['result_type']}")
                            if "flowdroid_item" in sample:
                                logger.info(f"flowdroid_item示例: 键名={list(sample['flowdroid_item'].keys())}")
                            if "truth_item" in sample:
                                logger.info(f"truth_item示例: 键名={list(sample['truth_item'].keys())}")
                            break
            
            return results
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析错误: {str(e)}"
            logger.error(error_msg)
            
            # 尝试读取文件的前1000个字符，看看内容是什么
            try:
                with open(result_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)
                logger.error(f"文件内容前1000个字符: {content}")
            except Exception:
                pass
                
            raise
        except Exception as e:
            error_msg = f"加载结果文件失败: {str(e)}"
            logger.error(error_msg)
            raise
    
    def _create_tool_result_map(self, results: Dict) -> Dict:
        """
        从误报消除工具结果创建方法签名到结果的映射
        
        参数:
            results: 工具结果字典
            
        返回:
            方法签名到结果的映射字典
        """
        result_map = {}
        
        # 提取details字段，可能是直接在results中，也可能在results['results']中
        details = results.get("details", [])
        if not details and "results" in results and isinstance(results["results"], dict):
            details = results["results"].get("details", [])
        
        if not isinstance(details, list):
            logger.warning(f"工具结果中details不是列表类型: {type(details)}")
            return result_map
            
        if len(details) == 0:
            logger.warning("工具结果中details列表为空")
            return result_map
            
        logger.info(f"处理误报消除工具结果，找到 {len(details)} 条记录")
        
        for i, result in enumerate(details):
            if not isinstance(result, dict):
                logger.warning(f"跳过非字典类型的结果记录 [{i+1}/{len(details)}]: {result}")
                continue
            
            original_data = result.get("原始数据", {})
            if not isinstance(original_data, dict):
                logger.warning(f"跳过原始数据非字典类型的记录 [{i+1}/{len(details)}]: {original_data}")
                continue
            
            # 提取类名和方法名
            class_name = original_data.get("类名", "")
            method_name = original_data.get("方法名", "")
            
            if not class_name or not method_name:
                logger.warning(f"跳过缺少类名或方法名的记录 [{i+1}/{len(details)}]: 类名={class_name}, 方法名={method_name}")
                continue
            
            method_signature = f"{class_name}.{method_name}"
            result_map[method_signature] = {
                "是否误报": result.get("是否误报", False),
                "置信度": result.get("置信度", 0),
                "理由": result.get("理由", ""),
                "类型": "工具结果"
            }
            logger.info(f"添加工具结果 [{i+1}/{len(details)}]: {method_signature}, 是否误报: {result.get('是否误报', False)}")
        
        logger.info(f"从工具结果中创建了 {len(result_map)} 个方法签名到结果的映射")
        return result_map
    
    def _create_result_map(self, results: Dict) -> Dict:
        """
        创建方法签名到结果的映射
        
        参数:
            results: 结果字典
            
        返回:
            方法签名到结果的映射字典
        """
        # 处理误报消除结果 (prunefp_statistics.json)
        if "details" in results or "results" in results:
            return self._create_tool_result_map(results)
        
        # 处理真值结果 (restored_detailed_results.json)
        result_map = {}
        total_records = 0
        for vuln_id, vuln_list in results.items():
            if not isinstance(vuln_list, list):
                continue
            
            for vuln in vuln_list:
                if not isinstance(vuln, dict):
                    continue
                
                total_records += 1
                
                # 获取result_type，确定是TP、FP、TN还是FN
                result_type = vuln.get("result_type", "")
                
                # 跳过无效结果类型
                if not result_type:
                    logger.warning(f"跳过没有result_type的记录: {vuln}")
                    continue
                
                # 确定使用哪个项目获取方法签名
                method_signature = ""
                is_false_positive = False
                
                # 处理各种不同类型的结果
                if result_type == "TP":
                    # TP: 真阳性，静态分析工具正确检测到了真实漏洞
                    is_false_positive = False
                    # 使用flowdroid_item，因为这与工具结果更匹配
                    flowdroid_item = vuln.get("flowdroid_item", {})
                    if flowdroid_item and isinstance(flowdroid_item, dict):
                        class_name = flowdroid_item.get("class_name", "")
                        method_name = flowdroid_item.get("method_name", "")
                        if class_name and method_name:
                            method_signature = f"{class_name}.{method_name}"
                
                elif result_type.startswith("FP"):
                    # FP: 假阳性，静态分析工具的误报
                    is_false_positive = True
                    # 对于未匹配的FP，使用flowdroid_item
                    if "未匹配" in result_type:
                        flowdroid_item = vuln.get("flowdroid_item", {})
                        if flowdroid_item and isinstance(flowdroid_item, dict):
                            class_name = flowdroid_item.get("class_name", "")
                            method_name = flowdroid_item.get("method_name", "")
                            if class_name and method_name:
                                method_signature = f"{class_name}.{method_name}"
                    else:
                        # 对于匹配的FP，使用flowdroid_item和truth_item
                        flowdroid_item = vuln.get("flowdroid_item", {})
                        if flowdroid_item and isinstance(flowdroid_item, dict):
                            class_name = flowdroid_item.get("class_name", "")
                            method_name = flowdroid_item.get("method_name", "")
                            if class_name and method_name:
                                method_signature = f"{class_name}.{method_name}"
                        
                        # 如果无法从flowdroid_item获取，尝试从truth_item获取
                        if not method_signature:
                            truth_item = vuln.get("truth_item", {})
                            if truth_item and isinstance(truth_item, dict):
                                class_name = truth_item.get("class_name", "")
                                method_name = truth_item.get("method_name", "")
                                if class_name and method_name:
                                    method_signature = f"{class_name}.{method_name}"
                
                # 如果仍然无法获取方法签名，跳过这个结果
                if not method_signature:
                    logger.warning(f"无法创建方法签名: {vuln}")
                    continue
                
                result_map[method_signature] = {
                    "是否误报": is_false_positive,
                    "置信度": 100,  # 真值结果置信度为100%
                    "理由": f"静态分析结果: {result_type}",
                    "类型": "真值结果",
                    "原始记录": vuln
                }
                logger.info(f"添加真值结果: {method_signature}, 是否误报: {is_false_positive}, 类型: {result_type}")
        
        logger.info(f"处理真值结果，找到并处理了 {total_records} 条记录，生成了 {len(result_map)} 个有效方法签名")
        
        logger.info(f"创建结果映射: 结果数量={len(result_map)}")
        return result_map
    
    def _create_method_signature(self, data: Dict) -> str:
        """
        创建方法签名
        
        参数:
            data: 包含类名、方法名等信息的字典
            
        返回:
            方法签名字符串
        """
        if not data or not isinstance(data, dict):
            logger.warning(f"无效的数据类型: {type(data)}")
            return ""
            
        class_name = data.get("class_name", "") or data.get("类名", "")
        method_name = data.get("method_name", "") or data.get("方法名", "")
        
        if not class_name:
            logger.warning(f"未找到类名: {data}")
        if not method_name:
            logger.warning(f"未找到方法名: {data}")
            
        if class_name and method_name:
            signature = f"{class_name}.{method_name}"
            logger.debug(f"创建方法签名: {signature}")
            return signature
        return ""
    
    def _print_signatures_debug(self):
        """打印方法签名的调试信息"""
        tool_signatures = set(self.tool_result_map.keys())
        ground_truth_signatures = set(self.ground_truth_map.keys())
        
        logger.info(f"工具结果方法签名 ({len(tool_signatures)}): {sorted(tool_signatures)}")
        logger.info(f"真值结果方法签名 ({len(ground_truth_signatures)}): {sorted(ground_truth_signatures)}")
        
        common = tool_signatures.intersection(ground_truth_signatures)
        logger.info(f"共同方法签名 ({len(common)}): {sorted(common)}")
        
        only_in_tool = tool_signatures - ground_truth_signatures
        only_in_truth = ground_truth_signatures - tool_signatures
        
        if only_in_tool:
            logger.info(f"仅在工具结果中 ({len(only_in_tool)}): {sorted(only_in_tool)}")
        if only_in_truth:
            logger.info(f"仅在真值结果中 ({len(only_in_truth)}): {sorted(only_in_truth)}")
    
    def evaluate(self) -> Dict:
        """
        执行评估
        
        返回:
            评估结果字典
        """
        logger.info("开始评估误报消除结果...")
        
        # 统计工具结果
        self._count_tool_results()
        
        # 打印方法签名调试信息
        self._print_signatures_debug()
        
        # 评估准确性
        self._evaluate_accuracy()
        
        # 计算评估指标
        metrics = self._calculate_metrics()
        
        # 生成详细报告
        report = self._generate_report(metrics)
        
        logger.info("评估完成")
        return report
    
    def _count_tool_results(self):
        """统计工具结果的数量"""
        # 从工具结果中获取details数量和统计信息
        details = self.tool_results.get("details", [])
        if not details and "results" in self.tool_results and isinstance(self.tool_results["results"], dict):
            details = self.tool_results["results"].get("details", [])
        
        if isinstance(details, list):
            self.metrics.total = len(details)
            logger.info(f"从details列表中获取到结果数量: {self.metrics.total}")
        else:
            self.metrics.total = 0
            logger.warning(f"工具结果中details不是列表类型: {type(details)}")
        
        # 从results字段获取统计数据
        results = self.tool_results.get("results", {})
        if results and isinstance(results, dict):
            self.metrics.true_positives = results.get("true_positives", 0)
            self.metrics.false_positives = results.get("false_positives", 0)
            self.metrics.uncertain = results.get("uncertain", 0)
            self.metrics.high_confidence = results.get("high_confidence", 0)
            self.metrics.medium_confidence = results.get("medium_confidence", 0)
            self.metrics.low_confidence = results.get("low_confidence", 0)
            logger.info(f"从results字段获取统计数据: TP={self.metrics.true_positives}, FP={self.metrics.false_positives}")
        else:
            logger.warning("工具结果中没有results字段或results不是字典类型")
        
        logger.info(f"统计结果: 总数={self.metrics.total}, "
                   f"真实漏洞={self.metrics.true_positives}, "
                   f"误报={self.metrics.false_positives}, "
                   f"不确定={self.metrics.uncertain}")
        logger.info(f"置信度分布: 高={self.metrics.high_confidence}, "
                   f"中={self.metrics.medium_confidence}, "
                   f"低={self.metrics.low_confidence}")
        
        # 如果没有details但有统计数据，使用统计数据作为总数
        if self.metrics.total == 0 and (self.metrics.true_positives + self.metrics.false_positives + self.metrics.uncertain > 0):
            self.metrics.total = self.metrics.true_positives + self.metrics.false_positives + self.metrics.uncertain
            logger.info(f"从统计数据计算总数: {self.metrics.total}")
    
    def _evaluate_accuracy(self):
        """评估准确性"""
        matched_count = 0
        tool_result_signatures = set(self.tool_result_map.keys())
        ground_truth_signatures = set(self.ground_truth_map.keys())
        
        common_signatures = tool_result_signatures.intersection(ground_truth_signatures)
        logger.info(f"工具结果数量: {len(tool_result_signatures)}, 真值结果数量: {len(ground_truth_signatures)}, 共同方法数量: {len(common_signatures)}")
        
        for method_signature in common_signatures:
            tool_result = self.tool_result_map[method_signature]
            ground_truth_result = self.ground_truth_map[method_signature]
            
            matched_count += 1
            tool_is_fp = tool_result.get("是否误报")
            ground_truth_is_fp = ground_truth_result.get("是否误报")
            
            logger.info(f"方法: {method_signature}, 工具判断为误报: {tool_is_fp}, 真值为误报: {ground_truth_is_fp}")
            
            # 评估准确性的核心逻辑
            if tool_is_fp == ground_truth_is_fp:
                # 工具判断与真值结果一致
                if tool_is_fp:
                    # 正确地识别了误报 (FP)
                    self.metrics.correct_false_positives += 1
                    logger.info(f"正确识别误报: {method_signature}")
                else:
                    # 正确地识别了真实漏洞 (TP)
                    self.metrics.correct_true_positives += 1
                    logger.info(f"正确识别真实漏洞: {method_signature}")
            else:
                # 工具判断与真值结果不一致
                if tool_is_fp:
                    # 将真实漏洞(TP)错误地标记为误报，导致漏报
                    self.metrics.incorrect_false_positives += 1
                    logger.info(f"错误将真实漏洞标记为误报(漏报): {method_signature}")
                else:
                    # 将误报(FP)错误地标记为真实漏洞，导致误报
                    self.metrics.incorrect_true_positives += 1
                    logger.info(f"错误将误报标记为真实漏洞(误报): {method_signature}")
        
        logger.info(f"匹配到 {matched_count} 个方法的结果")
        logger.info(f"正确识别真实漏洞: {self.metrics.correct_true_positives}")
        logger.info(f"正确识别误报: {self.metrics.correct_false_positives}")
        logger.info(f"错误将真实漏洞标记为误报(漏报): {self.metrics.incorrect_false_positives}")
        logger.info(f"错误将误报标记为真实漏洞(误报): {self.metrics.incorrect_true_positives}")
    
    def _calculate_metrics(self) -> Dict:
        """
        计算评估指标
        
        返回:
            评估指标字典
        """
        total_matches = (self.metrics.correct_true_positives + 
                       self.metrics.correct_false_positives + 
                       self.metrics.incorrect_true_positives + 
                       self.metrics.incorrect_false_positives)
        
        if total_matches == 0:
            return {
                "total_matches": 0,
                "tool_results_total": self.metrics.total,
                "true_positives": {
                    "total_actual": 0,
                    "tool_reported": self.metrics.true_positives,
                    "correct": 0,
                    "incorrect": 0,
                    "accuracy": 0
                },
                "false_positives": {
                    "total_actual": 0,
                    "tool_reported": self.metrics.false_positives,
                    "correct": 0,
                    "incorrect": 0,
                    "accuracy": 0
                },
                "confidence_levels": {
                    "high": self.metrics.high_confidence,
                    "medium": self.metrics.medium_confidence,
                    "low": self.metrics.low_confidence
                },
                "overall_accuracy": 0
            }
        
        # 计算真实检测到的TP和FP数量
        total_actual_tp = self.metrics.correct_true_positives + self.metrics.incorrect_false_positives
        total_actual_fp = self.metrics.correct_false_positives + self.metrics.incorrect_true_positives
            
        # 计算准确率
        true_positive_accuracy = (self.metrics.correct_true_positives / 
                                total_actual_tp
                                if total_actual_tp > 0 
                                else 0)
        
        false_positive_accuracy = (self.metrics.correct_false_positives / 
                                 total_actual_fp 
                                 if total_actual_fp > 0 
                                 else 0)
        
        # 计算总体准确率
        total_correct = self.metrics.correct_true_positives + self.metrics.correct_false_positives
        total_accuracy = total_correct / total_matches if total_matches > 0 else 0
        
        return {
            "total_matches": total_matches,
            "tool_results_total": self.metrics.total,
            "true_positives": {
                "total_actual": total_actual_tp,
                "tool_reported": self.metrics.true_positives,
                "correct": self.metrics.correct_true_positives,
                "incorrect": self.metrics.incorrect_false_positives,
                "accuracy": true_positive_accuracy
            },
            "false_positives": {
                "total_actual": total_actual_fp,
                "tool_reported": self.metrics.false_positives,
                "correct": self.metrics.correct_false_positives,
                "incorrect": self.metrics.incorrect_true_positives,
                "accuracy": false_positive_accuracy
            },
            "confidence_levels": {
                "high": self.metrics.high_confidence,
                "medium": self.metrics.medium_confidence,
                "low": self.metrics.low_confidence
            },
            "overall_accuracy": total_accuracy
        }
    
    def _generate_report(self, metrics: Dict) -> Dict:
        """
        生成评估报告
        
        参数:
            metrics: 评估指标字典
            
        返回:
            评估报告字典
        """
        total_matches = metrics.get("total_matches", 0)
        tool_results_total = metrics.get("tool_results_total", 0)
        
        # 计算准确率百分比，避免除以零
        overall_accuracy = f"{metrics['overall_accuracy']*100:.2f}%" if total_matches > 0 else "0.00%"
        tp_accuracy = f"{metrics['true_positives']['accuracy']*100:.2f}%" if metrics['true_positives']['total_actual'] > 0 else "0.00%"
        fp_accuracy = f"{metrics['false_positives']['accuracy']*100:.2f}%" if metrics['false_positives']['total_actual'] > 0 else "0.00%"
        
        # 计算置信度分布百分比
        high_conf = f"{metrics['confidence_levels']['high']/tool_results_total*100:.2f}%" if tool_results_total > 0 else "0.00%"
        medium_conf = f"{metrics['confidence_levels']['medium']/tool_results_total*100:.2f}%" if tool_results_total > 0 else "0.00%"
        low_conf = f"{metrics['confidence_levels']['low']/tool_results_total*100:.2f}%" if tool_results_total > 0 else "0.00%"
        
        # 误报消除效果
        fp_elimination_rate = f"{metrics['false_positives']['correct']/metrics['false_positives']['total_actual']*100:.2f}%" if metrics['false_positives']['total_actual'] > 0 else "0.00%"
        
        # 漏报率（将真实漏洞误判为误报的比例）
        false_negative_rate = f"{metrics['true_positives']['incorrect']/metrics['true_positives']['total_actual']*100:.2f}%" if metrics['true_positives']['total_actual'] > 0 else "0.00%"
        
        report = {
            "evaluation_metrics": metrics,
            "summary": {
                "total_matches": total_matches,
                "tool_results_total": tool_results_total,
                "overall_accuracy": overall_accuracy,
                "true_positive_accuracy": tp_accuracy,
                "false_positive_accuracy": fp_accuracy,
                "false_positive_elimination_rate": fp_elimination_rate,
                "false_negative_rate": false_negative_rate
            },
            "confidence_distribution": {
                "high": high_conf,
                "medium": medium_conf,
                "low": low_conf
            },
            "detailed_counts": {
                "correct_true_positives": metrics["true_positives"]["correct"],
                "incorrect_true_positives": metrics["false_positives"]["incorrect"],
                "correct_false_positives": metrics["false_positives"]["correct"],
                "incorrect_false_positives": metrics["true_positives"]["incorrect"]
            }
        }
        
        # 添加错误分析
        fp_errors = self._analyze_errors(metrics["true_positives"]["incorrect"])
        tp_errors = self._analyze_errors(metrics["false_positives"]["incorrect"])
        
        report["error_analysis"] = {
            "false_positive_errors": fp_errors,  # 应该识别为FP但没有识别出来的
            "true_positive_errors": tp_errors    # 应该识别为TP但没有识别出来的
        }
        
        return report
    
    def _analyze_errors(self, error_count: int) -> List[Dict]:
        """
        分析错误案例
        
        参数:
            error_count: 错误数量
            
        返回:
            错误分析列表
        """
        if error_count == 0:
            return []
            
        errors = []
        count = 0
        
        # 遍历共同方法签名
        common_signatures = set(self.tool_result_map.keys()).intersection(set(self.ground_truth_map.keys()))
        
        for method_signature in common_signatures:
            tool_result = self.tool_result_map.get(method_signature, {})
            ground_truth_result = self.ground_truth_map.get(method_signature, {})
                
            if tool_result.get("是否误报") != ground_truth_result.get("是否误报"):
                errors.append({
                    "method": method_signature,
                    "tool_result": "误报" if tool_result.get("是否误报") else "真实漏洞",
                    "ground_truth": "误报" if ground_truth_result.get("是否误报") else "真实漏洞",
                    "confidence": tool_result.get("置信度", 0),
                    "reason": tool_result.get("理由", "")[:500]  # 截取前500个字符，避免太长
                })
                
                count += 1
                if count >= 10:  # 最多分析10个错误案例
                    break
        
        return errors

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="评估误报消除工具的准确性")
    parser.add_argument("--tool-result", required=True, help="误报消除工具的结果文件路径")
    parser.add_argument("--ground-truth", required=True, help="人工标注的真实结果文件路径")
    parser.add_argument("--output", required=True, help="评估报告输出路径")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    parser.add_argument("--print-raw", action="store_true", help="打印原始结果内容")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("已启用调试日志")
    
    # 检查文件是否存在
    for path_arg, path_name in [
        (args.tool_result, "工具结果文件"),
        (args.ground_truth, "真值结果文件")
    ]:
        if not os.path.exists(path_arg):
            logger.error(f"{path_name}不存在: {path_arg}")
            alternate_path = path_arg.replace("restore_", "restored_")
            if os.path.exists(alternate_path):
                logger.info(f"找到备选文件路径: {alternate_path}，使用该路径")
                if path_name == "工具结果文件":
                    args.tool_result = alternate_path
                else:
                    args.ground_truth = alternate_path
            else:
                alternate_path = path_arg.replace("restored_", "restore_")
                if os.path.exists(alternate_path):
                    logger.info(f"找到备选文件路径: {alternate_path}，使用该路径")
                    if path_name == "工具结果文件":
                        args.tool_result = alternate_path
                    else:
                        args.ground_truth = alternate_path
                else:
                    logger.error(f"未找到备选文件路径，程序退出")
                    return None
    
    # 打印参数
    logger.info(f"工具结果文件: {args.tool_result}")
    logger.info(f"真值结果文件: {args.ground_truth}")
    logger.info(f"输出文件路径: {args.output}")
    
    # 如果需要打印原始结果内容
    if args.print_raw:
        for path_arg, path_name in [
            (args.tool_result, "工具结果文件"),
            (args.ground_truth, "真值结果文件")
        ]:
            try:
                with open(path_arg, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # 只读取前1000个字符
                logger.info(f"{path_name}内容前1000个字符: {content}")
            except Exception as e:
                logger.error(f"读取{path_name}失败: {str(e)}")
    
    try:
        # 创建评价器
        evaluator = FalsePositiveEvaluator(args.tool_result, args.ground_truth)
        
        # 执行评估
        report = evaluator.evaluate()
        
        # 保存评估报告
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"评估报告已保存到: {args.output}")
        
        # 输出关键指标
        logger.info(f"评估结果摘要:")
        logger.info(f"总体准确率: {report['summary']['overall_accuracy']}")
        logger.info(f"真实漏洞识别准确率: {report['summary']['true_positive_accuracy']}")
        logger.info(f"误报消除率: {report['summary']['false_positive_elimination_rate']}")
        logger.info(f"漏报率: {report['summary']['false_negative_rate']}")
        
        return report
    except Exception as e:
        logger.error(f"评估过程中发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    main() 