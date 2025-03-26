import unittest
import torch
from transformers import AutoTokenizer, AutoModel


def sliding_window(text, tokenizer, max_length=512, stride=256):
       encoded = tokenizer.encode(text)
       result = []
       for i in range(0, len(encoded), stride):
           chunk = encoded[i:i + max_length]
           result.append(chunk)
       return result

def restore_text_from_tokens(tokens, tokenizer):
    """
    根据token列表还原原始文本
    
    参数:
        tokens: token列表或token列表的列表(2维)
        tokenizer: 用于解码的tokenizer对象
        
    返回:
        还原的原始文本或文本列表
    """
    # 检查是否是2维列表
    if isinstance(tokens, list):
        if len(tokens) > 0 and isinstance(tokens[0], list):
            # 处理2维列表情况
            results = []
            for token_seq in tokens:
                text = tokenizer.decode(token_seq, skip_special_tokens=True)
                results.append(text)
            return results
        else:
            # 处理1维列表情况
            return tokenizer.decode(tokens, skip_special_tokens=True)
    else:
        raise TypeError("输入的tokens必须是列表类型")

class TestTokenizer(unittest.TestCase):

    def setUp(self):
        self.tokenizer = AutoTokenizer.from_pretrained("/home/ran/Documents/work/graduate/llm-agent/models/codebert")

    
    def test_tokenizer(self):
        code = "public class HelloWorld { 你好"
        # 基本分词
        tokens = self.tokenizer.encode(code)
        print(tokens)
        restored_text = restore_text_from_tokens(tokens, self.tokenizer)
        print(restored_text)

        # 获取完整的tokenization结果（包含token_ids和其他信息）
        encoding = self.tokenizer("这是一个需要分词的句子")
        print(encoding)

    def test_sliding_window(self):
        code = """
        @Vulnerability(type = VulnerabilityType.XXE, cwe = 611, description = "此方法存在XML外部实体(XXE)注入漏洞，允许攻击者包含外部DTD", remediation = "禁用XML处理器中的外部DTD处理", level = VulnerabilityLevel.HIGH, isRealVulnerability = true)
        @PostMapping("/process")
        @ResponseBody
        public Map<String, Object> processXml(@RequestBody String xmlContent) {
            Map<String, Object> response = new HashMap<>();
            try {
                // 另一种不安全的XML解析方式
                DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
                // 危险：显式启用DTD处理
                factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", false);
                DocumentBuilder builder = factory.newDocumentBuilder();
                Document document = builder.parse(new InputSource(new StringReader(xmlContent)));
                // 处理解析结果
                Element rootElement = document.getDocumentElement();
                response.put("rootElement", rootElement.getNodeName());
                response.put("success", true);
            } catch (Exception e) {
                response.put("success", false);
                response.put("error", e.getMessage());
            }
            return response;
        }
        """

        # 滑动窗口
        chunks = sliding_window(code, self.tokenizer)
        print(len(chunks))
        restored_text = restore_text_from_tokens(chunks, self.tokenizer)
        print(restored_text)

    

    

if __name__ == '__main__':
    unittest.main() 