# Soot 代码分析工具集

这个工具集使用 Soot 框架提供了一系列用于 Java 代码分析的工具，包括代码索引、调用图生成和 Jimple IR 转换。这些工具可以帮助研究人员和开发者分析 Java 项目的结构、方法调用关系和内部实现。

## 功能特点

1. **代码索引 (SootCodeAnalyzer)**
   - 查找方法定义和引用
   - 查找字段定义和引用
   - 保留源代码行号信息
   - 生成 JSON 格式的索引文件

2. **调用图生成 (CallGraphGenerator)**
   - 支持 CHA 和 SPARK 两种算法
   - 生成详细的方法调用关系
   - 记录调用位置的行号
   - 输出 JSON 格式的调用图

3. **Jimple IR 生成 (JimpleGenerator)**
   - 将 Java 源代码转换为 Jimple 中间表示
   - 可选择保留源代码行号
   - 支持为 Jimple 添加源代码注释
   - 支持按类和方法进行过滤

## 构建项目

使用 Maven 构建项目：

```bash
cd semantic-restoration
mvn clean package
```

构建成功后会在 `target` 目录下生成 JAR 文件。

## 使用方法

### 代码索引

```bash
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.SootCodeAnalyzer \
  -t <目标项目路径> \
  -o <输出目录> \
  -c -j -i
```

参数说明：
- `-t, --target`：目标 Java 项目路径（必须）
- `-o, --output`：输出目录（必须）
- `-c, --callgraph`：生成调用图
- `-j, --jimple`：生成 Jimple IR
- `-i, --index`：生成代码索引
- `-h, --help`：显示帮助信息

### 调用图生成

```bash
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.CallGraphGenerator \
  <应用路径> \
  <输出路径> \
  [算法] \
  [入口点...]
```

参数说明：
- `<应用路径>`：Java 项目路径或 JAR 文件路径
- `<输出路径>`：输出目录
- `[算法]`：调用图算法，可选 CHA（默认）或 SPARK
- `[入口点...]`：可选的入口点列表，格式为 `类名:方法名` 或 `类名:*`（表示所有方法）

示例：
```bash
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.CallGraphGenerator \
  ./src \
  ./output \
  SPARK \
  com.example.Main:main
```

### Jimple IR 生成

```bash
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.JimpleGenerator \
  <源代码路径> \
  <输出路径> \
  [包含模式...] \
  [-e 排除模式...]
```

参数说明：
- `<源代码路径>`：Java 源代码路径
- `<输出路径>`：输出目录
- `[包含模式...]`：类名匹配模式，支持通配符 `*`
- `[-e 排除模式...]`：在 `-e` 后指定要排除的类名匹配模式

示例：
```bash
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.JimpleGenerator \
  ./src \
  ./output \
  com.example.* \
  -e com.example.util.*
```

## 输出文件说明

### 代码索引

运行 `SootCodeAnalyzer` 会生成以下 JSON 文件：

- `method_definitions.json`：方法定义索引
- `method_invocations.json`：方法调用索引
- `field_definitions.json`：字段定义索引
- `field_references.json`：字段引用索引

### 调用图

运行 `CallGraphGenerator` 会生成 `call_graph.json` 文件，包含：

- `nodes` 数组：方法节点信息
- `edges` 数组：方法调用关系

### Jimple IR

运行 `JimpleGenerator` 会生成多个 `.jimple` 文件，每个方法一个文件，并按照包结构组织。

## 示例用法

### 分析 Spring Boot 项目

```bash
# 生成代码索引
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.SootCodeAnalyzer \
  -t ./spring-boot-app/target/classes \
  -o ./analysis-results \
  -c -i

# 生成调用图
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.CallGraphGenerator \
  ./spring-boot-app/target/classes \
  ./analysis-results \
  SPARK \
  com.example.Application:main

# 生成 Jimple IR
java -cp target/soot-analyzer-1.0-SNAPSHOT.jar edu.thu.soot.JimpleGenerator \
  ./spring-boot-app/src/main/java \
  ./analysis-results/jimple \
  com.example.*
```

## 注意事项

1. Soot 分析需要能够访问项目的所有依赖，请确保类路径设置正确
2. 分析大型项目时，可能需要增加 JVM 内存：`java -Xmx4g -cp ...`
3. SPARK 算法比 CHA 算法更精确，但运行速度更慢
4. 对于大型项目，推荐使用包含和排除模式来限制分析范围
5. 源代码注释功能需要源代码文件的正确路径才能工作 