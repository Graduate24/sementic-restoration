import unittest
import os
import shutil
import subprocess
from typing import Tuple, Optional

from src.llm.workflow.state import WorkflowState
from src.llm.workflow.workflow import SemanticRestorationWorkflow


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


def copy_directory(source_dir, target_dir):
    # 在源目录创建测试文件
    if os.path.exists(target_dir):
        raise FileExistsError(f"目标目录 {target_dir} 已存在")
    shutil.copytree(source_dir, target_dir)


class TestSrWorkflow(unittest.TestCase):
    def setUp(self):
        self.base_dir = "/home/ran/Documents/work/graduate/sementic-restoration/experiments"
        self.project_path = "/home/ran/Documents/work/graduate/annotated-benchmark"
        self.output_path = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result"
        self.output_path2 = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result2"
        self.output_path3 = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result3"

    def test_copy_original(self):
        copy_directory(self.project_path, "./workdir/")

    def test_execute_command(self):
        # 测试执行简单命令
        returncode, stdout, stderr = execute_command("echo 'Hello World'")
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout.strip(), "Hello World")

        # 测试执行带工作目录的命令
        returncode, stdout, stderr = execute_command("pwd", cwd="/tmp")
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout.strip(), "/tmp")

    def test_compile_source(self):
        returncode, stdout, stderr = execute_command("mvn clean compile -Dmaven.test.skip=true", cwd="./workdir/")

        # self.assertEqual(returncode, 0)
        if (returncode != 0):
            print(stderr.strip())
        else:
            print(stdout.strip())

        self.assertEqual(returncode, 0)

    def test_workflow(self):
        """
        AVAILABLE_MODELS = {
            "claude-3-sonnet": "anthropic/claude-3.7-sonnet",
            "gpt-4o": "openai/gpt-4o",
            "o1": "openai/o1",
            "deepseek": "deepseek/deepseek-r1",
            "gemini-flash": "google/gemini-2.0-flash-001",
        }
        """
        workflow = SemanticRestorationWorkflow(self.project_path, self.output_path,
                                               os.path.join(self.base_dir, 'tools'), "claude-3-sonnet")
        workflow.run()


    def test_workflow2(self):
        """
        AVAILABLE_MODELS = {
            "claude-3-sonnet": "anthropic/claude-3.7-sonnet",
            "gpt-4o": "openai/gpt-4o",
            "o1": "openai/o1",
            "deepseek": "deepseek/deepseek-r1",
            "gemini-flash": "google/gemini-2.0-flash-001",
        }
        """
        workflow = SemanticRestorationWorkflow(self.project_path, self.output_path2,
                                               os.path.join(self.base_dir, 'tools'), "gpt-4o")
        workflow.run()


    def test_workflow3(self):
        """
        AVAILABLE_MODELS = {
            "claude-3-sonnet": "anthropic/claude-3.7-sonnet",
            "gpt-4o": "openai/gpt-4o",
            "o1": "openai/o1",
            "deepseek": "deepseek/deepseek-r1",
            "gemini-flash": "google/gemini-2.0-flash-001",
        }
        """
        workflow = SemanticRestorationWorkflow(self.project_path, self.output_path3,
                                               os.path.join(self.base_dir, 'tools'), "deepseek")
        workflow.run()


    def test_workflow_run_state(self):
        workflow = SemanticRestorationWorkflow(self.project_path, self.output_path2,
                                               os.path.join(self.base_dir, 'tools'), "gpt-4o")
        workflow.run_state(WorkflowState.INIT)