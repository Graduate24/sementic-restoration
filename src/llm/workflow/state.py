from enum import Enum


class WorkflowState(Enum):
    INIT = "init"                    # 初始状态
    PROJECT_SUMMARY = "project_summary"    # 项目分析
    FRAMEWORK_DETECTION = "framework_detection" # 框架检测
    MODELING = "modeling"            # 建模阶段
    RESTORATION = "restoration"      # 还原阶段
    COMPILATION = "compilation"      # 编译阶段
    STATIC_ANALYSIS = "static_analysis"     # 静态分析
    COMPLETED = "completed"          # 完成
    FAILED = "failed"                # 失败
