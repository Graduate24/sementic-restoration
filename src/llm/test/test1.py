import unittest

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
        for file in java_files[:]:
            print(f"\n处理文件: {file}")
            prompt_data = processor.gather_file_modeling_data(file)
            print(prompt_data)
            # 打印源代码的前100个字符和相关建模数据的统计


