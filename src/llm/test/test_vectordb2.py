import unittest

from src.llm.db.vector_db import VectorDB


class VectorDB2Test(unittest.TestCase):
    def setUp(self):
        self.db = VectorDB('/home/ran/Documents/work/graduate/llm-agent/models/codebert')

    def test_vectordb1(self):
        chunks = self.db.build_text_input(
            "这段代码实现了一个简单的配置管理器，通过loadConfig方法初始化配置映射，然后通过getConfig方法获取配置值。静态分析工具可能会误报getConfig"
            "方法中的configs字段可能为null，因为它无法识别典型的初始化-使用模式，即loadConfig必须在getConfig之前调用的隐含约定。"
            "这种模式常见于需要延迟初始化资源的场景，如配置管理、连接池或资源管理器，其中初始化和使用遵循特定顺序，但这种顺序约束对静态分析工具不可见。")
        print(chunks)

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
        code_chunks = self.db.build_code_input(code)
        print(code_chunks)

    def test_vectordb2(self):
        s = """
        这段代码实现了一个简单的配置管理器，通过loadConfig方法初始化配置映射，然后通过getConfig方法获取配置值。
        静态分析工具可能会误报configs字段在getConfig方法调用时可能为null，因为它们无法确定loadConfig方法已经完成了初始化。
        实际上，代码逻辑保证了在使用configs前已经初始化，因此不会发生空指针异常。这种模式常见于配置管理、资源加载等需要先初始化后使用的场景。
        """
        self.db.save_semantic([s], [{"name": "test"}])

        s2 = """
                这段代码实现了一个简单的配置管理器，通过loadConfig方法初始化配置映射，然后通过getConfig方法获取配置值。
                静态分析工具可能会误报configs字段在getConfig方法调用时可能为null，因为它们无法确定loadConfig方法已经完成了初始化。
                实际上，代码逻辑保证了在使用configs前已经初始化，因此不会发生空指针异常。这种模式常见于配置管理、资源加载等需要先初始化后使用的场景。
                这段代码实现了一个简单的配置管理器，通过loadConfig方法初始化配置映射，然后通过getConfig方法获取配置值。
                静态分析工具可能会误报configs字段在getConfig方法调用时可能为null，因为它们无法确定loadConfig方法已经完成了初始化。
                实际上，代码逻辑保证了在使用configs前已经初始化，因此不会发生空指针异常。这种模式常见于配置管理、资源加载等需要先初始化后使用的场景。
                这段代码实现了一个简单的配置管理器，通过loadConfig方法初始化配置映射，然后通过getConfig方法获取配置值。
                静态分析工具可能会误报configs字段在getConfig方法调用时可能为null，因为它们无法确定loadConfig方法已经完成了初始化。
                实际上，代码逻辑保证了在使用configs前已经初始化，因此不会发生空指针异常。这种模式常见于配置管理、资源加载等需要先初始化后使用的场景。
                """
        self.db.save_semantic([s2], [{"name": "test2"}])

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

        self.db.save_code([code], [{"name": "code1"}])
