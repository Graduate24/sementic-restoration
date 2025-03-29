from enum import Enum


class WorkflowState(Enum):
    INIT = "init"                    # 系统初始化状态
    PROJECT_ANALYSIS = "project_analysis"    # 项目分析与建模阶段
    CODE_INDEXING = "code_indexing" # 代码索引与知识库构建阶段
    RESTORATION = "restoration"      # 语义还原与代码生成阶段
    COMPILATION = "compilation"      # 编译验证与错误修复阶段
    ANALYSIS = "analysis"     # 静态分析与问题检测阶段
    EVALUATION = 'evaluation' # 结果评估与报告生成阶段
    COMPLETED = "completed"          # 完成
    FAILED = "failed"                # 失败
