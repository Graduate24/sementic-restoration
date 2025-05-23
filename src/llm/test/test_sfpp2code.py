import json
import os.path
import subprocess
import unittest
import time
import uuid

from numpy.ma.extras import average

from src.config.config import system_prompt_sfpp_to_semantic, system_prompt_code_to_semantic
from src.llm.db.vector_db import VectorDB
from src.llm.llm_client import LLMClient


def extract_between_markers(text, start_marker="++++++++++++++++++++++++++++++++",
                            end_marker="-----------------------------"):
    """提取两个标记之间的内容"""
    try:
        # 查找开始标记的位置
        start_index = text.find(start_marker)
        if start_index == -1:
            return None  # 没找到开始标记

        # 计算内容开始的位置（开始标记之后）
        content_start = start_index + len(start_marker)

        # 从内容开始处查找结束标记
        end_index = text.find(end_marker, content_start)
        if end_index == -1:
            return None  # 没找到结束标记

        # 提取两个标记之间的内容
        extracted_content = text[content_start:end_index].strip()
        return extracted_content

    except Exception as e:
        print(f"提取内容时出错: {e}")
        return None


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
    import os

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


class TestSFPPP2Code(unittest.TestCase):
    def setUp(self):
        self.db = VectorDB('/home/ran/Documents/work/graduate/llm-agent/models/codebert')

    def test_sfpp2code(self):
        llm = LLMClient()
        prompt = """
        {
          "sfpp_id": "SFPP-CMDI-001",
          "metadata": {
            "type": "命令注入误报",
            "severity": "高",
            "related_rules": ["SonarQube:S2076", "FindBugs:COMMAND_INJECTION", "OWASP:A1-Injection"],
            "tools": ["SonarQube", "Fortify", "Checkmarx", "SpotBugs"]
          },
          "semantic_description": {
            "summary": "在执行系统命令前对输入参数进行严格校验后被误报为命令注入漏洞",
            "false_positive_reason": "静态分析工具无法识别或追踪输入验证逻辑与命令执行之间的关系，导致即使有充分的安全校验也会触发警报",
            "safety_explanation": "通过长度限制、正则表达式匹配等方式对命令参数进行严格校验，可以有效防止恶意输入，确保只有合法参数才能传递给命令执行函数"
          },
          "code_pattern": {
            "abstract_representation": "String input = getInput(); if (input.matches(\"^[a-zA-Z0-9]+$\") && input.length() < MAX_LENGTH) { Runtime.getRuntime().exec(\"command \" + input); }",
            "key_operations": ["输入获取", "参数校验", "正则表达式匹配", "长度检查", "命令执行"],
            "variants": [
              "使用白名单验证：if (ALLOWED_VALUES.contains(input)) { exec(command + input); }",
              "多重验证：if (validateFormat(input) && validateLength(input) && validateCharacters(input)) { exec(command + input); }",
              "参数预处理：String sanitized = sanitizeInput(input); if (isValid(sanitized)) { exec(command + sanitized); }"
            ]
          },
          "context_features": {
            "architectural_context": "系统集成场景、命令行工具包装器、系统管理功能",
            "dependencies": ["输入验证工具类", "字符串处理函数", "系统命令执行API"],
            "business_scenarios": ["系统管理界面", "文件处理工具", "外部程序集成", "自动化脚本执行"]
          }
        }
        """
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_to_semantic)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])
        res = json.loads(response['choices'][0]['message']['content'])
        write_string_to_file(res['code'], './SFPP.java')

    def test_sfpp2code2(self):
        llm = LLMClient()
        prompt = """
           {
              "sfpp_id": "SFPP-CMDI-001",
              "metadata": {
                "type": "命令注入误报",
                "severity": "高",
                "related_rules": ["SonarQube:S2076", "FindBugs:COMMAND_INJECTION", "OWASP:A1-Injection"],
                "tools": ["SonarQube", "Checkmarx", "Fortify", "SpotBugs"]
              },
              "semantic_description": {
                "summary": "使用命令白名单验证后执行系统命令被误报为命令注入漏洞",
                "false_positive_reason": "静态分析工具无法识别白名单验证的有效性，仅检测到命令执行函数的调用",
                "safety_explanation": "通过预先定义的命令白名单严格限制可执行命令，确保只有安全的、预期的命令才能执行，从而防止注入攻击"
              },
              "code_pattern": {
                "abstract_representation": "List<String> allowedCommands = Arrays.asList(\"safe_cmd1\", \"safe_cmd2\"); if(allowedCommands.contains(userInput)) { Runtime.getRuntime().exec(userInput); }",
                "key_operations": ["白名单定义", "命令验证", "条件执行"],
                "variants": [
                  "使用Set/Map等其他集合类型存储白名单",
                  "使用正则表达式验证命令格式: Pattern.matches(\"^(safe_cmd1|safe_cmd2)$\", userInput)",
                  "使用枚举类型定义允许的命令",
                  "使用配置文件或数据库存储白名单",
                  "命令参数的白名单验证: cmd + \" \" + (allowedParams.contains(param) ? param : \"\")"
                ]
              },
              "context_features": {
                "architectural_context": "系统管理功能、自动化脚本、命令行工具包装器",
                "dependencies": ["系统命令执行API", "集合类或验证工具"],
                "business_scenarios": [
                  "系统管理界面",
                  "开发工具集成",
                  "有限功能的命令行界面",
                  "自动化部署脚本",
                  "受控环境中的系统操作"
                ]
              }
            }
           """
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_to_semantic)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])
        res = json.loads(response['choices'][0]['message']['content'])
        write_string_to_file(res['code'], './SFPP.java')
        print(res['semantic'])

    def test_sfpp2code3(self):
        llm = LLMClient()
        prompt = """
             {
              "sfpp_id": "SFPP-CMDI-001",
              "metadata": {
                "type": "命令注入误报",
                "severity": "高",
                "related_rules": ["SonarQube:S2076", "FindBugs:COMMAND_INJECTION", "SpotBugs:COMMAND_INJECTION"],
                "tools": ["SonarQube", "FindBugs", "SpotBugs", "Checkmarx"]
              },
              "semantic_description": {
                "summary": "使用Java API替代命令行执行或验证工作目录的命令执行被误报为命令注入漏洞",
                "false_positive_reason": "静态分析工具无法识别Java API的安全性或工作目录验证的防护措施",
                "safety_explanation": "通过Java原生API执行文件操作或在验证工作目录后执行命令可以有效防止命令注入攻击"
              },
              "code_pattern": {
                "abstract_representation": "// 使用Java API替代命令行\nFile file = new File(path);\nboolean exists = file.exists();\n\n// 或验证工作目录后执行命令\nif (isInSafeDirectory(command)) {\n  Runtime.getRuntime().exec(command);\n}",
                "key_operations": ["Java文件API使用", "工作目录验证", "安全上下文检查"],
                "variants": [
                  "使用Files.exists()代替ls命令",
                  "使用Files.delete()代替rm命令",
                  "使用Files.copy()代替cp命令",
                  "验证命令字符串不包含特殊字符后执行",
                  "使用白名单验证命令后执行",
                  "使用ProcessBuilder并设置安全的工作目录"
                ]
              },
              "context_features": {
                "architectural_context": "系统管理工具、文件操作组件、DevOps自动化工具",
                "dependencies": ["java.io.File", "java.nio.file.Files", "java.lang.Runtime", "java.lang.ProcessBuilder"],
                "business_scenarios": ["文件系统管理", "系统维护操作", "自动化部署", "日志文件处理"]
              }
            }
             """
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_to_semantic)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])
        res = json.loads(response['choices'][0]['message']['content'])
        write_string_to_file(res['code'], './SFPP.java')
        print(res['semantic'])

    def test_sfpp2code4(self):
        llm = LLMClient()
        prompt = """
             {
              "sfpp_id": "SFPP-CMDI-001",
              "metadata": {
                "type": "命令注入误报",
                "severity": "高",
                "related_rules": ["SonarQube:S2076", "FindBugs:COMMAND_INJECTION", "SpotBugs:COMMAND_INJECTION"],
                "tools": ["SonarQube", "FindBugs", "SpotBugs", "Checkmarx"]
              },
              "semantic_description": {
                "summary": "使用Java安全API验证和过滤命令参数后的系统命令执行被误报为命令注入漏洞",
                "false_positive_reason": "静态分析工具无法识别参数验证和特殊字符过滤的安全措施，仅基于Runtime.exec或ProcessBuilder的使用进行标记",
                "safety_explanation": "通过严格验证输入参数、过滤特殊字符、使用参数化命令执行方式，可以安全地执行系统命令而不存在注入风险"
              },
              "code_pattern": {
                "abstract_representation": "String input = getInput(); if(validateInput(input)) { String[] cmdArray = {\"command\", input}; ProcessBuilder pb = new ProcessBuilder(cmdArray); Process p = pb.start(); }",
                "key_operations": ["输入验证", "特殊字符过滤", "参数化命令执行", "安全API使用"],
                "variants": [
                  "使用正则表达式验证：if(input.matches(\"^[a-zA-Z0-9_\\-\\.]+$\")) { ... }",
                  "使用白名单验证：if(ALLOWED_COMMANDS.contains(input)) { ... }",
                  "使用ProcessBuilder数组形式：new ProcessBuilder(\"command\", validatedInput).start()",
                  "使用Commons Lang进行转义：StringEscapeUtils.escapeJava(input)"
                ]
              },
              "context_features": {
                "architectural_context": "系统集成、自动化工具、命令行工具包装器",
                "dependencies": ["java.lang.ProcessBuilder", "java.lang.Runtime", "org.apache.commons.lang.StringEscapeUtils", "自定义验证工具类"],
                "business_scenarios": ["系统管理工具", "文件处理应用", "外部程序集成", "DevOps自动化工具"]
              }
            }
             """
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_to_semantic)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])
        res = json.loads(response['choices'][0]['message']['content'])
        write_string_to_file(res['code'], './SFPP.java')
        print(res['semantic'])

    # TODO 使用大模型根据SFPP生成语义和代码
    def test_sfpp2code5(self):
        # read sfpp.json
        base_dir = '/home/ran/Documents/work/graduate/sementic-restoration/experiments/sfppexp/'
        sfppsource = os.path.join(base_dir, 'sfpp/sfpp.json')
        with open(sfppsource, 'r') as f:
            sfpps = json.load(f)
            for index, sfpp in enumerate(sfpps):
                print(sfpp)
                ret_dir = os.path.join(base_dir, f"ret{index}")
                if not os.path.exists(ret_dir):
                    os.makedirs(ret_dir)
                llm = LLMClient()
                response = llm.generate_completion(prompt=sfpp, system_prompt=system_prompt_sfpp_to_semantic)
                res = json.loads(response['choices'][0]['message']['content'])
                write_string_to_file(res['code'], os.path.join(ret_dir, f"SFPP.java"))
                write_string_to_file(res['semantic'], os.path.join(ret_dir, f"SFPP.semantic"))

    # TODO 保存<semantic,code>对
    def test_save_vectordb(self):
        base_dir = '/home/ran/Documents/work/graduate/sementic-restoration/experiments/sfppexp/'
        for d in os.listdir(base_dir):
            if os.path.isdir(os.path.join(base_dir, d)) and os.path.exists(os.path.join(base_dir, d, "SFPP.java")):
                union_id = str(uuid.uuid4())
                with open(os.path.join(base_dir, d, "SFPP.java"), 'r') as f:
                    self.db.save_code([f.read()], [{"cwe": "78", "type": "SFPP", "id": union_id}])
                with open(os.path.join(base_dir, d, "SFPP.semantic"), 'r') as f:
                    self.db.save_semantic([f.read()], [{"cwe": "78", "type": "SFPP", "id": union_id}])

    def test_query1(self):
        # 查询示例
        filtered_result = self.db.semantic_collection.query(
            query_texts=['静态分析'],
            where={"cwe": "78"},
            n_results=5,  # 返回前5个最相似的结果
            include=['documents', 'metadatas', 'distances'],  # 包含文档内容、元数据和距离分数
        )

        # 打印详细结果
        print("\n查询结果:")
        for i, (doc, metadata, distance) in enumerate(zip(
                filtered_result['documents'][0],
                filtered_result['metadatas'][0],
                filtered_result['distances'][0]
        )):
            print(f"\n结果 {i + 1}:")
            print(f"文档内容: {doc}")
            print(f"元数据: {metadata}")
            print(f"距离分数: {distance}")

    # TODO 获取cwe78检测结果,尝试sfpp匹配
    def test_retrieve_defects_codes(self):
        base_dir = '/home/ran/Documents/work/graduate/sementic-restoration/experiments/'
        detect_result = os.path.join(base_dir, 'restore_detailed_results.json')
        cwe78_results = []
        with open(detect_result, 'r') as f:
            result_list = json.loads(f.read())['78']
            for result in result_list:
                if result['result_type'] == "TP" or result['result_type'] == "FP":
                    cwe78_results.append(result['flowdroid_item'])
        if not cwe78_results:
            print("cwe78_result is None!")
            return
        llm = LLMClient()

        query_results = []

        for result in cwe78_results:
            # get source code
            # java -jar target/code-index-1.0-SNAPSHOT.jar  -o ./output -s /home/ran/Documents/work/graduate/annotated-benchmark/src/main/java -extract -m "<edu.thu.benchmark.annotated.controller.XmlController: java.util.Map processXml(java.lang.String)>"
            # java -jar target/code-index-1.0-SNAPSHOT.jar -s /home/ran/Documents/work/graduate/annotated-benchmark/src/main/java -extract -m "<edu.thu.benchmark.annotated.controller.CommandInjectionController: java.lang.String executeArraySafe03(java.lang.String)>"
            command = f"java -jar /home/ran/Documents/work/graduate/code-index/target/code-index-1.0-SNAPSHOT.jar -s /home/ran/Documents/work/graduate/annotated-benchmark/src/main/java -extract -m \"{result['soot_signature']}\""
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            code = extract_between_markers(result.stdout)

            # 添加异常处理和重试逻辑
            max_retries = 3
            retry_count = 0
            retry_delay = 5  # 重试间隔5秒

            while retry_count < max_retries:
                try:
                    response = llm.generate_completion(prompt=code, system_prompt=system_prompt_code_to_semantic)
                    # 不再尝试解析为JSON，直接使用文本响应
                    res = response['choices'][0]['message']['content']
                    # 成功执行，跳出循环
                    break
                except KeyError as key_err:
                    # 返回数据结构错误
                    error_msg = f"返回数据结构错误 (尝试 {retry_count + 1}/{max_retries}): {key_err}"
                    print(error_msg)
                except Exception as e:
                    # 其他异常
                    error_msg = f"API调用异常 (尝试 {retry_count + 1}/{max_retries}): {str(e)}"
                    print(error_msg)

                # 增加重试计数
                retry_count += 1

                # 如果已经尝试了最大次数，则抛出最后一个异常
                if retry_count >= max_retries:
                    print(f"达到最大重试次数 ({max_retries})，操作失败")
                    raise Exception(f"LLM API调用失败，已重试{max_retries}次")

                # 等待一段时间后重试
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)

            filtered_result = self.db.semantic_collection.query(
                query_texts=[res],
                where={"cwe": "78"},
                n_results=1,
                include=['documents', 'metadatas', 'distances'],  # 包含文档内容、元数据和距离分数
            )
            query_result = {
                "cwe": "78"
            }
            semantic_result = {}
            union_id = None
            # 打印详细结果
            for i, (doc, metadata, distance) in enumerate(zip(
                    filtered_result['documents'][0],
                    filtered_result['metadatas'][0],
                    filtered_result['distances'][0]
            )):
                semantic_result['documents'] = doc
                semantic_result['distance'] = distance
                union_id = metadata['id']
                break

            query_result['semantic'] = semantic_result

            chunks = self.db.build_code_input(code)
            chunk_score = []
            for index, chunk in enumerate(chunks):
                chunk_query = self.db.code_collection.query(
                    query_texts=chunk,
                    where={"$and": [
                        {"cwe": "78"},
                        {"id": union_id}
                    ]},
                    n_results=5,
                    include=['documents', 'metadatas', 'distances'],  # 包含文档内容、元数据和距离分数
                )

                # 所有文档相似度平均
                scores = []
                for i, (doc, metadata, distance) in enumerate(zip(
                        chunk_query['documents'][0],
                        chunk_query['metadatas'][0],
                        chunk_query['distances'][0]
                )):
                    scores.append(distance)

                chunk_score.append(scores)

            # 将所有元素展平为一维列表
            flat_list = [item for sublist in chunk_score for item in sublist]
            # 计算平均值
            avg = sum(flat_list) / len(flat_list)
            query_result['code'] = {'distance': avg}

            query_results.append(query_result)

        print(query_results)
        with open(os.path.join(base_dir, 'query_result.json'), 'w', encoding='utf-8') as ff:
            json.dump(query_results, ff, ensure_ascii=False, indent=4)

        # Ran 1 test in 153.293s

        """
        实际应用中的数值解读  
        | 距离值范围 | 相似度范围 | 解读 |
        |-----------|-----------|------|
        | 0 - 0.1 | 0.9 - 1.0 | 非常相似，几乎相同 |
        | 0.1 - 0.3 | 0.7 - 0.9 | 高度相似 |
        | 0.3 - 0.5 | 0.5 - 0.7 | 中等相似 |
        | 0.5 - 0.7 | 0.3 - 0.5 | 低相似度 |
        | 0.7 - 1.0 | 0 - 0.3 | 几乎不相关 |
        """

    def test_chunk_code(self):
        code = """
        public class SFPP {
            public static void main(String[] args) {
                // 创建配置管理器
                ConfigManager configManager = new ConfigManager();
                
             
        """
        chunks = self.db.build_code_input(code)
        print(chunks)
