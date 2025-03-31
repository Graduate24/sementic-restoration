"""
结果处理器模块，负责处理和汇总分析结果
"""

import os
import json
import logging
from typing import Dict, List, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prunefp_processor")

class ResultProcessor:
    """
    结果处理器类，用于处理和汇总分析结果
    """
    
    def __init__(self, output_path: str):
        """
        初始化结果处理器
        
        参数:
            output_path: 结果输出目录
        """
        self.output_path = os.path.abspath(output_path)
        os.makedirs(self.output_path, exist_ok=True)
        
        logger.info(f"初始化结果处理器: 输出路径={output_path}")
    
    def process_results(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理和汇总分析结果
        
        参数:
            analysis_results: 分析结果列表
            
        返回:
            汇总结果字典
        """
        # 汇总结果
        summary = {
            "total": len(analysis_results),
            "true_positives": 0,
            "false_positives": 0,
            "uncertain": 0,
            "high_confidence": 0,  # 高置信度结果数量
            "medium_confidence": 0,  # 中等置信度结果数量
            "low_confidence": 0,  # 低置信度结果数量
            "details": []
        }
        
        # 分类和汇总结果
        for result in analysis_results:
            is_false_positive = result.get("是否误报")
            confidence = result.get("置信度", 0)
            
            # 统计真假阳性
            if is_false_positive == True:
                summary["false_positives"] += 1
            elif is_false_positive == False:
                summary["true_positives"] += 1
            else:
                summary["uncertain"] += 1
            
            # 统计置信度
            if confidence >= 80:
                summary["high_confidence"] += 1
            elif confidence >= 50:
                summary["medium_confidence"] += 1
            else:
                summary["low_confidence"] += 1
            
            # 添加到详细结果列表
            summary["details"].append(result)
        
        # 计算比例
        total = summary["total"]
        if total > 0:
            summary["false_positive_rate"] = round(summary["false_positives"] / total * 100, 2)
            summary["true_positive_rate"] = round(summary["true_positives"] / total * 100, 2)
            summary["uncertain_rate"] = round(summary["uncertain"] / total * 100, 2)
        
        # 保存结果
        self._save_results(summary)
        
        logger.info(f"完成结果处理: 总计={total}, "
                   f"误报={summary['false_positives']}({summary.get('false_positive_rate', 0)}%), "
                   f"真实漏洞={summary['true_positives']}({summary.get('true_positive_rate', 0)}%)")
        
        return summary
    
    def _save_results(self, summary: Dict[str, Any]) -> None:
        """
        保存汇总结果
        
        参数:
            summary: 汇总结果字典
        """
        # 保存完整汇总结果
        full_output_path = os.path.join(self.output_path, "analysis_results_full.json")
        with open(full_output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # 保存简洁汇总结果（不包含详细信息）
        summary_only = summary.copy()
        summary_only.pop("details", None)
        
        summary_output_path = os.path.join(self.output_path, "analysis_results_summary.json")
        with open(summary_output_path, 'w', encoding='utf-8') as f:
            json.dump(summary_only, f, indent=2, ensure_ascii=False)
        
        # 保存仅误报结果
        false_positives = [r for r in summary.get("details", []) if r.get("是否误报") == True]
        fp_output_path = os.path.join(self.output_path, "false_positives.json")
        with open(fp_output_path, 'w', encoding='utf-8') as f:
            json.dump(false_positives, f, indent=2, ensure_ascii=False)
        
        # 保存仅真实漏洞结果
        true_positives = [r for r in summary.get("details", []) if r.get("是否误报") == False]
        tp_output_path = os.path.join(self.output_path, "true_positives.json")
        with open(tp_output_path, 'w', encoding='utf-8') as f:
            json.dump(true_positives, f, indent=2, ensure_ascii=False)
        
        logger.info(f"结果已保存到: {self.output_path}")
    
    def generate_report(self, summary: Dict[str, Any]) -> str:
        """
        生成可读的分析报告
        
        参数:
            summary: 汇总结果字典
            
        返回:
            报告文本
        """
        report = []
        report.append("# 污点分析误报消除报告")
        report.append("")
        
        # 汇总数据
        report.append("## 汇总数据")
        report.append(f"- 总分析路径数量: {summary['total']}")
        report.append(f"- 真实漏洞数量: {summary['true_positives']} ({summary.get('true_positive_rate', 0)}%)")
        report.append(f"- 误报数量: {summary['false_positives']} ({summary.get('false_positive_rate', 0)}%)")
        report.append(f"- 无法确定数量: {summary['uncertain']} ({summary.get('uncertain_rate', 0)}%)")
        report.append("")
        
        # 置信度统计
        report.append("## 置信度统计")
        report.append(f"- 高置信度 (>=80): {summary['high_confidence']}")
        report.append(f"- 中等置信度 (50-79): {summary['medium_confidence']}")
        report.append(f"- 低置信度 (<50): {summary['low_confidence']}")
        report.append("")
        
        # 保存报告
        report_text = "\n".join(report)
        report_path = os.path.join(self.output_path, "analysis_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"分析报告已生成: {report_path}")
        
        return report_text 