# Java框架语义还原工具

这是一个用于将带有框架特性（如注解、依赖注入等）的Java代码还原为纯Java代码的工具，目的是使静态分析工具能够更准确地分析安全漏洞。

## 项目概述

本工具可以处理以下Java框架特性的语义还原：

1. **依赖注入（DI）还原**：将`@Autowired`注解的字段转换为直接初始化代码
2. **配置值注入还原**：将`@Value`注解引用的配置值直接赋值给字段
3. **AOP（面向切面编程）还原**：将切面代码（前置、后置、环绕通知）展开到目标方法中
4. **Mapper接口实现**：为MyBatis等ORM框架的接口生成实现类

## 使用方法

### 准备工作

1. 使用相关工具对Java项目进行建模，得到JSON格式的建模结果文件
2. 准备好需要还原的Java源代码目录

### 执行还原

```bash
java -jar semantic-restoration.jar <建模JSON文件> <源代码目录> <输出目录>
```

例如：

```bash
java -jar semantic-restoration.jar annotated-benchmark.json src/main/java restored
```

### 参数说明

- `<建模JSON文件>`：JSON格式的建模结果文件路径
- `<源代码目录>`：需要还原的Java源代码目录
- `<输出目录>`：还原后的代码输出目录

## 建模结果格式

建模结果应为JSON格式，包含以下主要部分：

```json
{
  "autowiredFields": {
    "com.example.Controller.service": {
      "annotation": "@org.springframework.beans.factory.annotation.Autowired",
      "linkedBeans": [
        {
          "name": "serviceImpl",
          "type": "com.example.ServiceImpl",
          "scope": "SINGLETON",
          "fromSource": "SERVICE_ANNOTATION"
        }
      ],
      "name": "service",
      "declaringType": "com.example.Controller",
      "fieldType": "com.example.Service"
    }
  },
  "valueFields": {
    "com.example.Config.property": {
      "annotation": "@org.springframework.beans.factory.annotation.Value(\"${app.property}\")",
      "linkedBeans": [
        {
          "name": "app.property",
          "propertyValue": {
            "property": "value"
          },
          "fromSource": "VALUE_ANNOTATION"
        }
      ],
      "name": "property",
      "declaringType": "com.example.Config",
      "fieldType": "java.lang.String"
    }
  },
  "aspects": [
    {
      "adviceType": "before",
      "aspectClass": "com.example.LoggingAspect",
      "adviceMethod": "logBefore",
      "targetMethods": [
        "com.example.Controller.handleRequest"
      ]
    }
  ],
  "entryPoints": [
    "com.example.Controller.handleRequest"
  ],
  "sources": [
    "com.example.Controller.getParameter"
  ],
  "sinks": [
    "com.example.DbUtil.executeQuery"
  ]
}
```

## 项目结构

```
semantic-restoration/
├── src/
│   └── main/
│       └── java/
│           ├── model/
│           │   └── ModelData.java          # 建模数据模型类
│           └── restoration/
│               └── SemanticRestorer.java   # 语义还原核心类
├── build.gradle                            # Gradle构建文件
└── README.md                               # 本文档
```

## 构建项目

```bash
./gradlew build
```

构建成功后，可以在`build/libs`目录下找到可执行的JAR文件。

## 技术实现

本项目使用以下技术：

- Java 11+
- GSON库用于JSON解析
- 正则表达式用于代码分析和修改

## 优势特点

1. **简化的输入**：只需要建模JSON和源代码，无需额外的配置文件
2. **高效解析**：使用GSON直接解析JSON格式的建模结果
3. **精确还原**：针对不同的框架特性提供专门的还原策略
4. **可扩展性**：易于添加新的还原规则和支持其他框架

## 限制说明

1. 建模JSON需要符合指定格式
2. 部分复杂框架特性可能无法完全还原
3. 生成的代码主要目的是供静态分析使用，不保证可直接运行

## 许可证

MIT 