"""
实验结果分析脚本，用于分析语义还原实验结果并生成报告
"""

import os
import sys
import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Tuple

# 设置字体以支持中文
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

def load_experiment_results(results_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    加载实验结果文件
    
    参数:
        results_dir: 结果目录路径
    
    返回:
        按实验类型分组的结果字典
    """
    results = {
        "di": [],
        "aop": [],
        "complete": [],
        "model_comparison": []
    }
    
    # 遍历结果目录中的所有JSON文件
    for filename in os.listdir(results_dir):
        if not filename.endswith(".json"):
            continue
        
        file_path = os.path.join(results_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 根据文件名分类
            if "_di_experiment.json" in filename:
                results["di"].append(data)
            elif "_aop_experiment.json" in filename:
                results["aop"].append(data)
            elif "_complete_experiment.json" in filename:
                results["complete"].append(data)
            elif "_model_comparison.json" in filename:
                results["model_comparison"].append(data)
            elif "batch_di_experiment.json" == filename:
                # 批量实验结果
                for class_name, class_result in data.get("class_results", {}).items():
                    results["di"].append(class_result)
            elif "batch_aop_experiment.json" == filename:
                for class_name, class_result in data.get("class_results", {}).items():
                    results["aop"].append(class_result)
            elif "batch_complete_experiment.json" == filename:
                for class_name, class_result in data.get("class_results", {}).items():
                    results["complete"].append(class_result)
            elif "batch_model_comparison_experiment.json" == filename:
                for class_name, class_result in data.get("class_results", {}).items():
                    results["model_comparison"].append(class_result)
        except Exception as e:
            print(f"加载文件 {file_path} 时出错: {str(e)}")
    
    return results

def calculate_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算实验结果统计数据
    
    参数:
        results: 实验结果列表
    
    返回:
        统计数据字典
    """
    if not results:
        return {
            "total": 0,
            "success_rate": 0,
            "avg_time": 0,
            "min_time": 0,
            "max_time": 0
        }
    
    # 计算成功率
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    success_rate = successful / total if total > 0 else 0
    
    # 计算时间统计
    times = [r.get("time_taken", 0) for r in results if r.get("success", False)]
    if not times:
        avg_time = min_time = max_time = 0
    else:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
    
    return {
        "total": total,
        "successful": successful,
        "success_rate": success_rate,
        "avg_time": avg_time,
        "min_time": min_time,
        "max_time": max_time
    }

def analyze_model_comparison(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    分析模型对比实验结果
    
    参数:
        results: 模型对比实验结果列表
    
    返回:
        按模型分组的统计数据
    """
    model_results = {}
    
    for result in results:
        for model_name, model_result in result.get("model_results", {}).items():
            if model_name not in model_results:
                model_results[model_name] = []
            
            # 将单个模型结果添加到对应模型的列表中
            model_data = {
                "class_name": result.get("class_name", ""),
                "success": model_result.get("success", False),
                "time_taken": model_result.get("time_taken", 0)
            }
            model_results[model_name].append(model_data)
    
    # 计算每个模型的统计数据
    stats = {}
    for model_name, model_data in model_results.items():
        stats[model_name] = calculate_statistics(model_data)
    
    return stats

def generate_success_rate_chart(stats: Dict[str, Dict[str, Any]], output_path: str):
    """
    生成成功率对比图表
    
    参数:
        stats: 统计数据字典
        output_path: 输出文件路径
    """
    categories = list(stats.keys())
    success_rates = [stats[cat]["success_rate"] * 100 for cat in categories]
    
    plt.figure(figsize=(10, 6))
    plt.bar(categories, success_rates, color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12'])
    plt.xlabel('实验类型')
    plt.ylabel('成功率 (%)')
    plt.title('不同实验类型的代码还原成功率')
    plt.ylim(0, 100)
    
    # 在柱状图上显示具体数值
    for i, v in enumerate(success_rates):
        plt.text(i, v + 2, f"{v:.1f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def generate_time_comparison_chart(stats: Dict[str, Dict[str, Any]], output_path: str):
    """
    生成时间对比图表
    
    参数:
        stats: 统计数据字典
        output_path: 输出文件路径
    """
    categories = list(stats.keys())
    avg_times = [stats[cat]["avg_time"] for cat in categories]
    min_times = [stats[cat]["min_time"] for cat in categories]
    max_times = [stats[cat]["max_time"] for cat in categories]
    
    x = np.arange(len(categories))
    width = 0.25
    
    plt.figure(figsize=(12, 7))
    plt.bar(x - width, avg_times, width, label='平均时间', color='#3498db')
    plt.bar(x, min_times, width, label='最小时间', color='#2ecc71')
    plt.bar(x + width, max_times, width, label='最大时间', color='#e74c3c')
    
    plt.xlabel('实验类型')
    plt.ylabel('时间 (秒)')
    plt.title('不同实验类型的代码还原时间对比')
    plt.xticks(x, categories)
    plt.legend()
    
    # 在柱状图上显示具体数值
    for i, v in enumerate(avg_times):
        plt.text(i - width, v + 0.3, f"{v:.1f}s", ha='center')
    for i, v in enumerate(min_times):
        plt.text(i, v + 0.3, f"{v:.1f}s", ha='center')
    for i, v in enumerate(max_times):
        plt.text(i + width, v + 0.3, f"{v:.1f}s", ha='center')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def generate_model_comparison_chart(model_stats: Dict[str, Dict[str, Any]], output_path: str):
    """
    生成模型对比图表
    
    参数:
        model_stats: 模型统计数据字典
        output_path: 输出文件路径
    """
    models = list(model_stats.keys())
    success_rates = [model_stats[model]["success_rate"] * 100 for model in models]
    avg_times = [model_stats[model]["avg_time"] for model in models]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 成功率对比
    ax1.bar(models, success_rates, color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12'][:len(models)])
    ax1.set_xlabel('模型')
    ax1.set_ylabel('成功率 (%)')
    ax1.set_title('不同模型的代码还原成功率')
    ax1.set_ylim(0, 100)
    
    # 在柱状图上显示具体数值
    for i, v in enumerate(success_rates):
        ax1.text(i, v + 2, f"{v:.1f}%", ha='center')
    
    # 平均时间对比
    ax2.bar(models, avg_times, color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12'][:len(models)])
    ax2.set_xlabel('模型')
    ax2.set_ylabel('平均时间 (秒)')
    ax2.set_title('不同模型的代码还原平均时间')
    
    # 在柱状图上显示具体数值
    for i, v in enumerate(avg_times):
        ax2.text(i, v + 0.3, f"{v:.1f}s", ha='center')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def generate_report(results: Dict[str, List[Dict[str, Any]]], output_dir: str):
    """
    生成分析报告
    
    参数:
        results: 实验结果字典
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 计算各类型实验的统计数据
    stats = {
        "依赖注入": calculate_statistics(results["di"]),
        "AOP切面": calculate_statistics(results["aop"]),
        "完整还原": calculate_statistics(results["complete"])
    }
    
    # 分析模型对比实验结果
    model_stats = analyze_model_comparison(results["model_comparison"])
    
    # 生成成功率图表
    generate_success_rate_chart(stats, os.path.join(output_dir, "success_rate_chart.png"))
    
    # 生成时间对比图表
    generate_time_comparison_chart(stats, os.path.join(output_dir, "time_comparison_chart.png"))
    
    # 生成模型对比图表
    if model_stats:
        generate_model_comparison_chart(model_stats, os.path.join(output_dir, "model_comparison_chart.png"))
    
    # 生成HTML报告
    report_path = os.path.join(output_dir, "analysis_report.html")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>语义还原实验分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .chart {{ margin: 20px 0; max-width: 800px; }}
                .summary {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>语义还原实验分析报告</h1>
            
            <div class="summary">
                <h2>实验概述</h2>
                <p>
                    <strong>依赖注入实验:</strong> 总数: {stats["依赖注入"]["total"]}, 成功: {stats["依赖注入"]["successful"]}, 成功率: {stats["依赖注入"]["success_rate"]*100:.2f}%<br>
                    <strong>AOP切面实验:</strong> 总数: {stats["AOP切面"]["total"]}, 成功: {stats["AOP切面"]["successful"]}, 成功率: {stats["AOP切面"]["success_rate"]*100:.2f}%<br>
                    <strong>完整还原实验:</strong> 总数: {stats["完整还原"]["total"]}, 成功: {stats["完整还原"]["successful"]}, 成功率: {stats["完整还原"]["success_rate"]*100:.2f}%<br>
                </p>
            </div>
            
            <h2>实验类型比较</h2>
            
            <h3>成功率对比</h3>
            <div class="chart">
                <img src="success_rate_chart.png" alt="成功率对比图表">
            </div>
            
            <h3>时间对比</h3>
            <div class="chart">
                <img src="time_comparison_chart.png" alt="时间对比图表">
            </div>
            
            <h3>详细统计数据</h3>
            <table>
                <tr>
                    <th>实验类型</th>
                    <th>总数</th>
                    <th>成功数</th>
                    <th>成功率</th>
                    <th>平均时间 (秒)</th>
                    <th>最小时间 (秒)</th>
                    <th>最大时间 (秒)</th>
                </tr>
        """)
        
        # 添加实验类型统计数据
        for exp_type, exp_stats in stats.items():
            f.write(f"""
                <tr>
                    <td>{exp_type}</td>
                    <td>{exp_stats["total"]}</td>
                    <td>{exp_stats["successful"]}</td>
                    <td>{exp_stats["success_rate"]*100:.2f}%</td>
                    <td>{exp_stats["avg_time"]:.2f}</td>
                    <td>{exp_stats["min_time"]:.2f}</td>
                    <td>{exp_stats["max_time"]:.2f}</td>
                </tr>
            """)
        
        f.write("""
            </table>
        """)
        
        # 如果有模型对比数据，添加模型对比部分
        if model_stats:
            f.write(f"""
            <h2>模型对比分析</h2>
            
            <div class="chart">
                <img src="model_comparison_chart.png" alt="模型对比图表">
            </div>
            
            <h3>模型性能详细数据</h3>
            <table>
                <tr>
                    <th>模型</th>
                    <th>总数</th>
                    <th>成功数</th>
                    <th>成功率</th>
                    <th>平均时间 (秒)</th>
                    <th>最小时间 (秒)</th>
                    <th>最大时间 (秒)</th>
                </tr>
            """)
            
            # 添加模型对比统计数据
            for model, model_stats in model_stats.items():
                f.write(f"""
                <tr>
                    <td>{model}</td>
                    <td>{model_stats["total"]}</td>
                    <td>{model_stats["successful"]}</td>
                    <td>{model_stats["success_rate"]*100:.2f}%</td>
                    <td>{model_stats["avg_time"]:.2f}</td>
                    <td>{model_stats["min_time"]:.2f}</td>
                    <td>{model_stats["max_time"]:.2f}</td>
                </tr>
                """)
            
            f.write("""
            </table>
            """)
        
        f.write("""
            <div class="summary">
                <h2>结论与建议</h2>
                <p>
                    基于以上实验结果，我们可以得出以下结论：
                </p>
                <ol>
                    <li>语义还原技术在依赖注入、AOP切面和完整代码还原方面表现各不相同，需要针对不同场景进行优化。</li>
                    <li>不同模型在代码还原任务上有各自的优势和劣势，应根据具体需求选择合适的模型。</li>
                    <li>代码复杂度、依赖关系以及框架特性是影响还原成功率的关键因素。</li>
                </ol>
                <p>
                    建议：
                </p>
                <ol>
                    <li>持续优化提示工程，提高代码还原的准确性和完整性。</li>
                    <li>针对不同类型的框架特性，开发专门的还原策略。</li>
                    <li>增加更多的测试用例和实验样本，提高结果的可靠性。</li>
                </ol>
            </div>
        </body>
        </html>
        """)
    
    print(f"分析报告已生成: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="语义还原实验结果分析工具")
    parser.add_argument("--results-dir", "-r", default="./results", help="实验结果目录")
    parser.add_argument("--output-dir", "-o", default="./analysis", help="分析报告输出目录")
    
    args = parser.parse_args()
    
    # 加载实验结果
    results = load_experiment_results(args.results_dir)
    
    # 生成分析报告
    generate_report(results, args.output_dir)

if __name__ == "__main__":
    main()