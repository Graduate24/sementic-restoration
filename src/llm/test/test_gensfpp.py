import unittest

from click import prompt

from src.config.config import system_prompt_sfpp_generator
from src.llm.llm_client import LLMClient


class TestGenSFPP(unittest.TestCase):
    def setUp(self):
        pass

    def test_gensfpp(self):
        llm = LLMClient()
        prompt = "命令注入误报,如果代码中有一些对参数的校验,如长度,正则表达式等,然后在使用代码执行命令,那么这种情况是不会触发命令注入的"
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_generator)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])

    def test_gensfpp2(self):
        llm = LLMClient()
        prompt = "命令注入误报,如果代码中使用命令白名单,然后再执行命令,那么也可能是安全的"
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_generator)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])

    def test_gensfpp3(self):
        llm = LLMClient()
        prompt = "命令注入误报,如果代码中使用了java api替代命令行,或者验证了工作目录,那么也可能是安全的"
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_generator)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])

    def test_gensfpp4(self):
        llm = LLMClient()
        prompt = "命令注入误报,如果代码中使用了一些java的类添加命令参数,验证参数的特殊字符,那么也可能是安全的"
        response = llm.generate_completion(prompt=prompt, system_prompt=system_prompt_sfpp_generator)

        print(f"-----------\n")
        print(response['choices'][0]['message']['content'])