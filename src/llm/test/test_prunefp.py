import json
import os
import unittest

from src.llm.prunefp.workflow import PruneFalsePositivesWorkflow
from src.llm.util.evaluate_flowdroid_optimized import load_flowdroid_results


class TestPrunefp(unittest.TestCase):
    def test_prunefp(self):
        result_path = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/detected_result_restore.json"
        result = load_flowdroid_results(result_path)
        print(json.dumps(result, indent=2))

    def test_prunefp2(self):
        result_path = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/detected_result_raw.json"
        result = json.load(open(result_path))
        print(result)

    def test_prunefp3(self):
        base = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/"
        result_path = os.path.join(base, "detected_result_raw1.json")
        project_path = os.path.join(base, "project")
        code_index = os.path.join(base, "code_indexing")
        workflow = PruneFalsePositivesWorkflow(
            raw_result_path=result_path,
            project_path=project_path,
            output_path="./output_dir",
            code_index=code_index,
            llm_model="gpt-4o"
        )

        workflow.run()

    def test_prunefp4(self):
        base = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/"
        result_path = os.path.join(base, "detected_result_raw2.json")
        project_path = os.path.join(base, "project")
        code_index = os.path.join(base, "code_indexing")
        workflow = PruneFalsePositivesWorkflow(
            raw_result_path=result_path,
            project_path=project_path,
            output_path="./output_dir2",
            code_index=code_index,
            llm_model="gpt-4o"
        )

        workflow.run()

    def test_prunefp3(self):
        base = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/"
        result_path = os.path.join(base, "detected_result_raw3.json")
        project_path = os.path.join(base, "project")
        code_index = os.path.join(base, "code_indexing")
        workflow = PruneFalsePositivesWorkflow(
            raw_result_path=result_path,
            project_path=project_path,
            output_path="./output_dir3",
            code_index=code_index,
            llm_model="gpt-4o"
        )

        workflow.run()

    def test_prunefp_test1(self):
        base = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/"
        result_path = os.path.join(base, "detected_result_raw_test1.json")
        project_path = os.path.join(base, "project")
        code_index = os.path.join(base, "code_indexing")
        workflow = PruneFalsePositivesWorkflow(
            raw_result_path=result_path,
            project_path=project_path,
            output_path="./output_dir0",
            code_index=code_index,
            llm_model='deepseek'
        )
        """
        AVAILABLE_MODELS = {
            "claude-3-sonnet": "anthropic/claude-3.7-sonnet",
            "gpt-4o": "openai/gpt-4o",
            "o1": "openai/o1",
            "deepseek": "deepseek/deepseek-r1",
            "gemini-flash": "google/gemini-2.0-flash-001",
        }
        """
        workflow.run()

    def test_prunefp_all(self):
        base = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/"
        result_path = os.path.join(base, "detected_result_raw.json")
        project_path = os.path.join(base, "project")
        code_index = os.path.join(base, "code_indexing")
        workflow = PruneFalsePositivesWorkflow(
            raw_result_path=result_path,
            project_path=project_path,
            output_path="./output_dir_all",
            code_index=code_index,
            llm_model='claude-3-sonnet'
        )
        """
        AVAILABLE_MODELS = {
            "claude-3-sonnet": "anthropic/claude-3.7-sonnet",
            "gpt-4o": "openai/gpt-4o",
            "o1": "openai/o1",
            "deepseek": "deepseek/deepseek-r1",
            "gemini-flash": "google/gemini-2.0-flash-001",
        }
        """
        workflow.run()

    def test_prunefp_4(self):
        base = "/home/ran/Documents/work/graduate/sementic-restoration/src/llm/test/workflow_result/"
        result_path = os.path.join(base, "detected_result_raw0.json")
        project_path = os.path.join(base, "project")
        code_index = os.path.join(base, "code_indexing")
        workflow = PruneFalsePositivesWorkflow(
            raw_result_path=result_path,
            project_path=project_path,
            output_path="./output_dir_test",
            code_index=code_index,
            llm_model='claude-3-sonnet'
        )
        """
        AVAILABLE_MODELS = {
            "claude-3-sonnet": "anthropic/claude-3.7-sonnet",
            "gpt-4o": "openai/gpt-4o",
            "o1": "openai/o1",
            "deepseek": "deepseek/deepseek-r1",
            "gemini-flash": "google/gemini-2.0-flash-001",
        }
        """
        workflow.run()



