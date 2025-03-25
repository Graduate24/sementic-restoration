import json
import unittest

from src.config.config import system_prompt
from src.llm.llm_client import LLMClient
from src.llm.util import ModelingDataProcessor


class Test1(unittest.TestCase):

    def test_1(self):
        project_dir = "/home/ran/Documents/work/graduate/BenchmarkJava/annotated-benchmark"
        modeling_dir = "/home/ran/Documents/work/graduate/BenchmarkJava/annotated-benchmark/semantic-restoration/experiments"
        processor = ModelingDataProcessor(project_dir, modeling_dir)
        # 加载建模数据
        processor.load_modeling_data()
        # 扫描Java文件
        java_files = processor.scan_java_files()
        print(java_files)

        # 查看前3个文件
        for file in java_files:
            print(f"\n处理文件: {file}")
            prompt_data = processor.gather_file_modeling_data(file)
            json_pretty = json.dumps(prompt_data, indent=2)
            # print(json_pretty)
            if 'modeling_data' not in prompt_data or (len(prompt_data['modeling_data']['aop_data']) == 0 and len(
                    prompt_data['modeling_data']['ioc_data'])) == 0:
                print(f"\n无需处理处理: {file}. 跳过")
                continue
            llm = LLMClient()
            response = llm.generate_completion(json_pretty, system_prompt=system_prompt)

            print(f"-----------\n")
            print(response['choices'][0]['message']['content'])
