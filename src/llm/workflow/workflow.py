import json
import logging
import os
import shutil
import subprocess
import time
from typing import Optional, Tuple

from mpmath import eighe

from src.config.config import system_prompt_semantic_restoration
from src.llm.llm_client import LLMClient
from src.llm.util import ModelingDataProcessor
from src.llm.workflow.state import WorkflowState


def copy_directory(source_dir, target_dir):
    # 在源目录创建测试文件
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
        # raise FileExistsError(f"目标目录 {target_dir} 已存在")
    shutil.copytree(source_dir, target_dir)


def execute_command(command: str, cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """
    执行命令行命令

    Args:
        command: 要执行的命令
        cwd: 命令执行的工作目录，默认为None表示当前目录

    Returns:
        Tuple[int, str, str]: (返回码, 标准输出, 标准错误)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def write_string_to_file(content, file_path, encoding="utf-8", create_dirs=True, mode="w"):
    """
    将字符串内容写入到指定文件中

    参数:
        content: 要写入的字符串内容
        file_path: 目标文件路径
        encoding: 文件编码，默认为UTF-8
        create_dirs: 如果为True，会自动创建输出文件的目录
        mode: 文件打开模式，默认为"w"(覆盖写入)，可选"a"(追加写入)

    返回:
        bool: 写入成功返回True，否则返回False
    """
    try:
        # 创建目录（如果需要）
        if create_dirs:
            dir_path = os.path.dirname(os.path.abspath(file_path))
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

        # 写入文件
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)

        return True

    except Exception as e:
        print(f"写入文件时出错: {e}")
        return False


def load_json_file(file_path: str) -> dict:
    """
    安全地从文件中读取JSON数据

    Args:
        file_path: JSON文件路径

    Returns:
        dict: JSON数据转换的字典

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到文件：{file_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"JSON格式错误：{str(e)}", e.doc, e.pos)

class SemanticRestorationWorkflow:
    def __init__(self, project_path: str, output_path: str, tool_path: str, llm_model: str):
        self.project_path = project_path
        self.output_path = output_path
        self.tool_path = tool_path
        self.llm_model = llm_model
        self.llm_client = LLMClient(model=self.llm_model)
        self.state = WorkflowState.INIT
        self.project_summary = None
        self.framework_info = None
        self.current_file = None
        self.restored_files = []
        self.retry_count = 0
        self.max_retries = {
            WorkflowState.PROJECT_ANALYSIS: 1,
            WorkflowState.CODE_INDEXING: 1,
            WorkflowState.RESTORATION: 1,
            WorkflowState.COMPILATION: 1,
            WorkflowState.ANALYSIS: 1,
            WorkflowState.EVALUATION: 1,
        }

        self.times = {
            "project_analysis": 0.0,
            "code_indexing": 0.0,
            "restoration": 0.0,
            "compilation": 0.0,
            "analysis": 0.0,
            "evaluation": 0.0,
        }
        self.logger = self._setup_logger('info')

        self.copy_project_path = None
        self.modeling_result_path = None
        self.code_indexing_result_path = None
        self.detected_result_path = None
        self.last_llm_response = None
        self.start_time = None

    def run(self):
        while self.state not in [WorkflowState.COMPLETED, WorkflowState.FAILED]:
            try:
                self._execute_current_state()
            except Exception as e:
                self.logger.error(f"Error in state {self.state}: {str(e)}")
                self.state = WorkflowState.FAILED
                break

        self._statistic()

    def _statistic(self):
        result = {
            "times": self.times,
            "model": self.llm_model,
            "restored_files": len(self.restored_files),
            "before_detected_result":load_json_file(os.path.join(self.output_path, 'before_detailed_results.json')),
            "before_evaluation": load_json_file(os.path.join(self.output_path, 'before_evaluation_results.json')),
            "restored_detected_result": load_json_file(os.path.join(self.output_path, 'restored_detailed_results.json')),
            "restored_evaluation": load_json_file(os.path.join(self.output_path, 'restored_evaluation_results.json')),
        }
        statistics = json.dumps(result,indent=4)
        self.logger.info(statistics)
        write_string_to_file(statistics, os.path.join(self.output_path, 'statistics.json'))

    def _execute_current_state(self):
        if self.state == WorkflowState.INIT:
            self._execute_init()
        elif self.state == WorkflowState.PROJECT_ANALYSIS:
            self._execute_project_analysis()
        elif self.state == WorkflowState.CODE_INDEXING:
            self._execute_code_indexing()
        elif self.state == WorkflowState.RESTORATION:
            self._execute_restoration()
        elif self.state == WorkflowState.ANALYSIS:
            self._execute_static_analysis()
        elif self.state == WorkflowState.EVALUATION:
            self._execute_evaluation()

    def _execute_init(self):
        """初始化工作流"""
        self.start_time = time.time()
        self.logger.info("Starting semantic restoration workflow")
        # copy project to new directory as work directory
        copy_directory(self.project_path, os.path.join(self.output_path, 'project'))
        self.state = WorkflowState.PROJECT_ANALYSIS
        self.copy_project_path = os.path.join(self.output_path, 'project')
        # 对原始项目首先进行一次编译和静态分析
        self._execute_compilation()
        self._execute_static_analysis(before=True, change_state=False)
        self._execute_evaluation(before=True, change_state=False)

    def _execute_project_analysis(self):
        self.logger.info("----Starting project analysis workflow----")
        # 调用建模工具
        start_time = time.time()
        project = self.copy_project_path
        command = f"java -jar {self.tool_path}/anno-model-1.0.jar -p {project} -o {self.output_path}/model"
        self.logger.info(f"Running command: {command}")
        execute_command(command)
        self.state = WorkflowState.CODE_INDEXING
        self.modeling_result_path = os.path.join(self.output_path, 'model')
        elapsed_time = time.time() - start_time
        self.times["project_analysis"] = self.times["project_analysis"] + elapsed_time
        self.logger.info("----Completed project analysis workflow----")

    def _execute_code_indexing(self):
        self.logger.info("------Starting code indexing workflow------")
        # java -cp target/code-index-1.0-SNAPSHOT.jar edu.thu.soot.SootCodeAnalyzer -t /target/classes -o ./analysis-result -c -i -j
        code_indexing_result = os.path.join(self.output_path, 'code_indexing')
        start_time = time.time()
        command1 = f"java -jar {self.tool_path}/code-index-1.0-SNAPSHOT.jar -t {self.copy_project_path}/target/classes -o {code_indexing_result} -c -j -i"
        self.logger.info(f"Running command: {command1}")
        execute_command(command1, cwd=self.copy_project_path)
        self.code_indexing_result_path = code_indexing_result
        elapsed_time = time.time() - start_time
        self.times["code_indexing"] = self.times["code_indexing"] + elapsed_time
        self.logger.info("----Completed code indexing workflow----")
        # TODO debug
        # self.state = WorkflowState.ANALYSIS
        self.state = WorkflowState.RESTORATION

    def _execute_compilation(self):
        self.logger.info("------compile project------")
        start_time = time.time()
        command = f"mvn clean compile -Dmaven.test.skip=true"
        self.logger.info(f"Running command: {command}")
        return_code, stdout, stderr = execute_command(command, cwd=self.copy_project_path)
        if return_code != 0:
            raise RuntimeError(f"Error while executing command: {command}")
        if "BUILD SUCCESS" not in stdout:
            raise RuntimeError(f"{stdout}")
        elapsed_time = time.time() - start_time
        self.times["compilation"] = self.times["compilation"] + elapsed_time

    def _execute_restoration(self):
        """执行语义还原"""
        self.logger.info("------Starting restoration workflow------")
        start_time = time.time()
        processor = ModelingDataProcessor(self.copy_project_path, self.modeling_result_path,
                                          self.code_indexing_result_path)
        # 加载建模数据
        processor.load_modeling_data()
        # 扫描Java文件
        java_files = processor.scan_java_files()
        try:
            for file in java_files:
                prompt_data = processor.gather_file_modeling_data(file)
                json_pretty = json.dumps(prompt_data, indent=2)
                if 'modeling_data' not in prompt_data or (len(prompt_data['modeling_data']['aop_data']) == 0 and len(
                        prompt_data['modeling_data']['ioc_data'])) == 0:
                    self.logger.info(f"No need to do semantic restoration for: {file}. skip...")
                    continue
                self.logger.info(f"Processing file: {file}")
                response = self.llm_client.generate_completion(prompt=json_pretty,
                                                               system_prompt=system_prompt_semantic_restoration)
                self.last_llm_response = response
                restoration = response['choices'][0]['message']['content']
                modified = os.path.join(self.copy_project_path, file)
                self.logger.info(f"write file: {modified}")
                write_string_to_file(restoration, modified)
                elapsed_time = time.time() - start_time
                self.times["restoration"] = self.times["restoration"] + elapsed_time
                try:
                    # TODO 注释这行只执行一次,节省调试时间
                    """注释这行只执行一次,节省调试时间"""
                    # self._execute_compilation()
                except RuntimeError as e:
                    self.logger.error(f"Error while executing command: {e}")
                    # TODO try to fix
                    self.state = WorkflowState.FAILED
                    return
            self._execute_compilation()
        except Exception as e:
            self.logger.error(f"Error in semantic restoration workflow: {str(e)}")
            self.state = WorkflowState.FAILED
            return

        self.state = WorkflowState.ANALYSIS
        self.logger.info("------Completed restoration workflow------")

    def _execute_static_analysis(self, before=False, change_state=True):
        """执行静态分析"""
        self.logger.info("------Starting static analysis workflow------")
        start_time = time.time()
        if not before:
            result_file = os.path.join(self.output_path, 'detected_result_restore.json')
        else:
            result_file = os.path.join(self.output_path, 'detected_result_before.json')
        self.detected_result_path = result_file
        # TODO generate from source/sink modeling
        config_path = os.path.join(self.tool_path, 'defaultconfig1.json')
        command = (
            f"java -jar {self.tool_path}/taintanalysis.jar -p {self.copy_project_path} -j {self.tool_path}/rt.jar "
            f"-w true -o {self.detected_result_path} -c {config_path}")
        self.logger.info(f"Running command: {command}")
        return_code, stdout, stderr = execute_command(command, cwd=self.copy_project_path)
        if return_code != 0:
            self.state = WorkflowState.FAILED
            raise RuntimeError(f"Error while executing command: {command}")
        elapsed_time = time.time() - start_time
        self.times["analysis"] = self.times["analysis"] + elapsed_time
        if change_state:
            self.state = WorkflowState.EVALUATION
        self.logger.info("------Completed static analysis workflow------")

    def _execute_evaluation(self, before=False, change_state=True):
        self.logger.info("------Starting evaluation workflow------")
        start_time = time.time()
        # python3 evaluate_flowdroid_optimized.py --input test_result_restore.json --output restore
        output_name = os.path.join(self.output_path, 'before' if before else 'restored')
        command = f"python3 {self.tool_path}/evaluate_flowdroid_optimized.py --input {self.detected_result_path} --output {output_name}"
        exit_code, stdout, stderr = execute_command(command, cwd=self.tool_path)
        self.logger.info(f"---- evaluation -----\n {stdout}")
        elapsed_time = time.time() - start_time
        self.times["evaluation"] = self.times["evaluation"] + elapsed_time
        self.logger.info("------Completed evaluation workflow------")
        if change_state:
            self.state = WorkflowState.COMPLETED

    def _setup_logger(self, log_level):
        """设置日志记录器"""
        # 实现日志配置
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"无效的日志级别: {log_level}")

        logger = logging.getLogger()
        logger.setLevel(numeric_level)

        # 清除已存在的处理器
        logger.handlers = []

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        # 添加处理器到日志记录器
        logger.addHandler(console_handler)

        return logger


def main():
    workflow = SemanticRestorationWorkflow(
        project_path="/path/to/project",
        output_path="/path/to/output"
    )
    workflow.run()

    if workflow.state == WorkflowState.COMPLETED:
        print("Semantic restoration completed successfully")
    else:
        print("Semantic restoration failed")
