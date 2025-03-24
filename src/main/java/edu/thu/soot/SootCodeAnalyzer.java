package edu.thu.soot;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.DefaultParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.ParseException;
import org.objectweb.asm.ClassReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import soot.*;
import soot.jimple.*;
import soot.options.Options;
import soot.tagkit.*;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.graph.DirectedGraph;
import soot.toolkits.graph.ExceptionalUnitGraph;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

/**
 * Soot代码分析器
 * 功能：
 * 1. 生成调用图
 * 2. 生成Jimple IR
 * 3. 创建代码索引（字段、方法的定义和引用）
 */
public class SootCodeAnalyzer {
    private static final Logger logger = LoggerFactory.getLogger(SootCodeAnalyzer.class);
    private String targetPath;
    private String outputPath;
    private boolean generateCallGraph = false;
    private boolean generateJimple = false;
    private boolean generateIndex = false;

    // 存储索引信息
    private final Map<String, List<IndexEntry>> methodDefinitions = new HashMap<>();
    private final Map<String, List<IndexEntry>> methodInvocations = new HashMap<>();
    private final Map<String, List<IndexEntry>> fieldDefinitions = new HashMap<>();
    private final Map<String, List<IndexEntry>> fieldReferences = new HashMap<>();

    // 存储调用图信息
    private final Map<String, List<String>> callGraph = new HashMap<>();

    /**
     * 索引条目，记录定义或引用的位置
     */
    static class IndexEntry {
        String className;
        String memberName;
        String signature;
        String sourceFile;
        int lineNumber;

        IndexEntry(String className, String memberName, String signature, String sourceFile, int lineNumber) {
            this.className = className;
            this.memberName = memberName;
            this.signature = signature;
            this.sourceFile = sourceFile;
            this.lineNumber = lineNumber;
        }
    }

    public SootCodeAnalyzer(String targetPath, String outputPath) {
        this.targetPath = targetPath;
        this.outputPath = outputPath;
    }

    /**
     * 初始化Soot
     */
    private void initializeSoot() {
        G.reset();

        // 设置Soot选项
        Options.v().set_prepend_classpath(true);
        Options.v().set_allow_phantom_refs(true);
        Options.v().set_soot_classpath(targetPath);
        Options.v().set_output_dir(outputPath);
        Options.v().set_keep_line_number(true);
        Options.v().set_src_prec(Options.src_prec_java);

        // 设置输出格式
        if (generateJimple) {
            Options.v().set_output_format(Options.output_format_jimple);
        } else {
            Options.v().set_output_format(Options.output_format_none);
        }

        // 设置阶段选项
        if (generateCallGraph) {
            Options.v().set_whole_program(true);
            Options.v().setPhaseOption("cg", "safe-newinstance:true");
            Options.v().setPhaseOption("cg.spark", "on");
        }

        // 添加应用类路径
        Options.v().set_process_dir(Collections.singletonList(targetPath));

        // 排除一些不需要的类
        Options.v().set_exclude(getExcludeList());

        // 应用设置
        Scene.v().loadNecessaryClasses();

        logger.info("Soot初始化完成");
    }

    /**
     * 获取排除的包列表
     */
    private List<String> getExcludeList() {
        return Arrays.asList(
            "java.*", "javax.*", "sun.*", "com.sun.*", "org.xml.*", "org.w3c.*",
            "apple.awt.*", "com.apple.*"
        );
    }

    /**
     * 执行分析
     */
    public void analyze() {
        logger.info("开始分析目标代码：{}", targetPath);

        // 初始化Soot
        initializeSoot();

        // 创建输出目录
        createOutputDirectory();

        // 分析所有类
        analyzeClasses();

        // 生成调用图
        if (generateCallGraph) {
            generateCallGraph();
        }

        // 保存分析结果
        if (generateIndex) {
            saveIndexResults();
        }

        logger.info("分析完成");
    }

    /**
     * 创建输出目录
     */
    private void createOutputDirectory() {
        Path path = Paths.get(outputPath);
        if (!Files.exists(path)) {
            try {
                Files.createDirectories(path);
                logger.info("创建输出目录：{}", outputPath);
            } catch (IOException e) {
                logger.error("创建输出目录失败：{}", e.getMessage());
            }
        }
    }

    /**
     * 分析所有应用类
     */
    private void analyzeClasses() {
        logger.info("开始分析应用类...");

        // 创建应用类的副本以避免并发修改异常
        List<SootClass> applicationClasses = new ArrayList<>(Scene.v().getApplicationClasses());

        // 遍历所有应用类
        for (SootClass sootClass : applicationClasses) {
            if (sootClass.isPhantom()) {
                continue;
            }

            String className = sootClass.getName();
            logger.debug("分析类：{}", className);

            // 分析字段
            List<SootField> fields = new ArrayList<>(sootClass.getFields());
            for (SootField field : fields) {
                analyzeField(field);
            }

            // 分析方法
            List<SootMethod> methods = new ArrayList<>(sootClass.getMethods());
            for (SootMethod method : methods) {
                if (!method.hasActiveBody()) {
                    try {
                        method.retrieveActiveBody();
                    } catch (Exception e) {
                        logger.warn("无法获取方法体：{}.{}", className, method.getName());
                        continue;
                    }
                }

                analyzeMethod(method);
            }
        }
    }

    /**
     * 分析字段定义
     */
    private void analyzeField(SootField field) {
        SootClass declaringClass = field.getDeclaringClass();
        String className = declaringClass.getName();
        String fieldName = field.getName();
        String signature = field.getSignature();

        // 获取源文件和行号
        String sourceFile = getSourceFile(declaringClass);
        int lineNumber = getLineNumber(field);

        // 添加到字段定义索引
        IndexEntry entry = new IndexEntry(className, fieldName, signature, sourceFile, lineNumber);

        if (!fieldDefinitions.containsKey(fieldName)) {
            fieldDefinitions.put(fieldName, new ArrayList<>());
        }
        fieldDefinitions.get(fieldName).add(entry);
    }

    /**
     * 分析方法
     */
    private void analyzeMethod(SootMethod method) {
        SootClass declaringClass = method.getDeclaringClass();
        String className = declaringClass.getName();
        String methodName = method.getName();
        String signature = method.getSignature();

        // 获取源文件和行号
        String sourceFile = getSourceFile(declaringClass);
        int lineNumber = getLineNumber(method);

        // 添加到方法定义索引
        IndexEntry entry = new IndexEntry(className, methodName, signature, sourceFile, lineNumber);

        if (!methodDefinitions.containsKey(methodName)) {
            methodDefinitions.put(methodName, new ArrayList<>());
        }
        methodDefinitions.get(methodName).add(entry);

        // 分析方法体
        Body body = method.getActiveBody();
        analyzeMethodBody(body);

        // 如果需要，生成Jimple IR
        if (generateJimple) {
            generateJimpleIR(method);
        }
    }

    /**
     * 分析方法体
     */
    private void analyzeMethodBody(Body body) {
        SootMethod method = body.getMethod();
        SootClass declaringClass = method.getDeclaringClass();
        String className = declaringClass.getName();
        String sourceFile = getSourceFile(declaringClass);

        // 创建控制流图
        DirectedGraph<Unit> graph = new ExceptionalUnitGraph(body);

        // 创建语句的副本以避免并发修改异常
        List<Unit> units = new ArrayList<>();
        body.getUnits().forEach(units::add);

        // 遍历所有语句
        for (Unit unit : units) {
            // 获取行号
            int lineNumber = getLineNumber(unit);

            // 分析方法调用
            if (unit instanceof InvokeStmt || unit instanceof AssignStmt) {
                InvokeExpr invokeExpr = null;

                if (unit instanceof InvokeStmt) {
                    invokeExpr = ((InvokeStmt) unit).getInvokeExpr();
                } else if (unit instanceof AssignStmt) {
                    AssignStmt assignStmt = (AssignStmt) unit;
                    if (assignStmt.getRightOp() instanceof InvokeExpr) {
                        invokeExpr = (InvokeExpr) assignStmt.getRightOp();
                    }
                }

                if (invokeExpr != null) {
                    SootMethod calledMethod = invokeExpr.getMethod();
                    String calledMethodName = calledMethod.getName();
                    String calledClassName = calledMethod.getDeclaringClass().getName();
                    String calledSignature = calledMethod.getSignature();

                    // 添加到方法调用索引
                    IndexEntry entry = new IndexEntry(calledClassName, calledMethodName, calledSignature, sourceFile, lineNumber);

                    if (!methodInvocations.containsKey(calledMethodName)) {
                        methodInvocations.put(calledMethodName, new ArrayList<>());
                    }
                    methodInvocations.get(calledMethodName).add(entry);

                    // 添加到调用图
                    String caller = method.getSignature();
                    String callee = calledSignature;

                    if (!callGraph.containsKey(caller)) {
                        callGraph.put(caller, new ArrayList<>());
                    }
                    if (!callGraph.get(caller).contains(callee)) {
                        callGraph.get(caller).add(callee);
                    }
                }
            }

            // 分析字段引用
            List<ValueBox> valueBoxes = new ArrayList<>(unit.getUseAndDefBoxes());
            for (ValueBox valueBox : valueBoxes) {
                Value value = valueBox.getValue();
                if (value instanceof FieldRef) {
                    FieldRef fieldRef = (FieldRef) value;
                    SootField field = fieldRef.getField();
                    String fieldName = field.getName();
                    String fieldClassName = field.getDeclaringClass().getName();
                    String fieldSignature = field.getSignature();

                    // 添加到字段引用索引
                    IndexEntry entry = new IndexEntry(fieldClassName, fieldName, fieldSignature, sourceFile, lineNumber);

                    if (!fieldReferences.containsKey(fieldName)) {
                        fieldReferences.put(fieldName, new ArrayList<>());
                    }
                    fieldReferences.get(fieldName).add(entry);
                }
            }
        }
    }

    /**
     * 生成Jimple IR
     */
    private void generateJimpleIR(SootMethod method) {
        String className = method.getDeclaringClass().getName();
        String outputDir = outputPath + "/jimple/" + className.replace(".", "/");
        new File(outputDir).mkdirs();

        String fileName = outputDir + "/" + method.getName() + ".jimple";

        try (FileWriter writer = new FileWriter(fileName)) {
            writer.write(method.getActiveBody().toString());
            logger.debug("生成Jimple IR：{}", fileName);
        } catch (IOException e) {
            logger.error("生成Jimple IR失败：{}", e.getMessage());
        }
    }

    /**
     * 生成调用图
     */
    private void generateCallGraph() {
        logger.info("生成调用图...");

        // 保存调用图到JSON文件
        try {
            Gson gson = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
            String json = gson.toJson(callGraph);

            Path filePath = Paths.get(outputPath, "call_graph.json");
            Files.write(filePath, json.getBytes());

            logger.info("调用图已保存到：{}", filePath);
        } catch (IOException e) {
            logger.error("保存调用图失败：{}", e.getMessage());
        }
    }

    /**
     * 保存索引结果
     */
    private void saveIndexResults() {
        logger.info("保存代码索引结果...");

        Gson gson = new GsonBuilder()
                .setPrettyPrinting()
                .disableHtmlEscaping()
                .create();

        try {
            // 保存方法定义索引
            saveIndex(methodDefinitions, "method_definitions.json", gson);

            // 保存方法调用索引
            saveIndex(methodInvocations, "method_invocations.json", gson);

            // 保存字段定义索引
            saveIndex(fieldDefinitions, "field_definitions.json", gson);

            // 保存字段引用索引
            saveIndex(fieldReferences, "field_references.json", gson);

            logger.info("索引结果已保存到：{}", outputPath);
        } catch (IOException e) {
            logger.error("保存索引结果失败：{}", e.getMessage());
        }
    }

    /**
     * 保存索引到JSON文件
     */
    private void saveIndex(Map<String, List<IndexEntry>> index, String fileName, Gson gson) throws IOException {
        Path filePath = Paths.get(outputPath, fileName);
        String json = gson.toJson(index);
        Files.write(filePath, json.getBytes());
    }

    /**
     * 获取源文件名
     */
    private String getSourceFile(SootClass sootClass) {
        SourceFileTag tag = (SourceFileTag) sootClass.getTag("SourceFileTag");
        return tag != null ? tag.getSourceFile() : "Unknown";
    }

    // Soot获取基本信息
    private int getFieldLineNumberFromBytecode(SootField field) {
        // 使用Soot获取类文件
        String className = field.getDeclaringClass().getName();
        String fieldName = field.getName();

        try {
            // 使用ASM来分析类文件
            ClassReader reader = new ClassReader(className);
            FieldLineNumberVisitor visitor = new FieldLineNumberVisitor(fieldName);
            reader.accept(visitor, 0);

            int lineNumber = visitor.getLineNumber();
            if (lineNumber > 0) {
                return lineNumber;
            }
        } catch (Exception e) {
            logger.debug("通过字节码获取字段行号失败: {}", e.getMessage());
        }

        // 如果ASM方法失败，回退到源码解析方法
        return -1;
    }

    /**
     * 获取字段的行号
     */
    private int getLineNumber(SootField field) {
        // 尝试从标签获取行号（通常不会成功，因为Soot默认不为字段生成行号标签）
        Tag tag = field.getTag("LineNumberTag");
        if (tag != null && tag instanceof LineNumberTag) {
            return ((LineNumberTag) tag).getLineNumber();
        }

        // 尝试使用ASM库获取字段行号
//         try {
//             SootClass declaringClass = field.getDeclaringClass();
//             String className = declaringClass.getName();
//             String sourceFile = getSourceFile(declaringClass);
//             if (!sourceFile.equals("Unknown")) {
//                 // 查找类文件路径
//                 java.io.File classFile = findClassFile(declaringClass);
//                 if (classFile != null && classFile.exists()) {
//                     // 使用ASM解析类文件
//                     org.objectweb.asm.ClassReader classReader = new org.objectweb.asm.ClassReader(java.nio.file.Files.readAllBytes(classFile.toPath()));
//                     FieldLineNumberVisitor visitor = new FieldLineNumberVisitor(field.getName());
//                     classReader.accept(visitor, 0);
//
//                     int lineNumber = visitor.getLineNumber();
//                     if (lineNumber > 0) {
//                         logger.debug("使用ASM找到字段定义：{}.{} 在行 {}", className, field.getName(), lineNumber);
//                         return lineNumber;
//                     }
//                 }
//             }
//         } catch (Exception e) {
//             logger.debug("使用ASM获取字段行号时出错：{}", e.getMessage());
//         }

       // 如果ASM方法失败，尝试使用源文件分析方法
       try {
           // 如果标签中没有行号，尝试从源文件获取
           SootClass declaringClass = field.getDeclaringClass();
           String sourceFile = getSourceFile(declaringClass);
           if (sourceFile.equals("Unknown")) {
               return -1;
           }

           // 类路径
           String packagePath = declaringClass.getPackageName().replace('.', '/');
           String className = declaringClass.getName();

           // 尝试多种可能的源文件路径
           java.util.List<String> possiblePaths = new java.util.ArrayList<>();

           // 1. 直接在targetPath下查找
           possiblePaths.add(targetPath + "/" + packagePath + "/" + sourceFile);

           // 2. 在targetPath的根目录下查找
           possiblePaths.add(targetPath + "/" + sourceFile);

           // 3. 向上跳转2层（从classes到项目根目录），然后查找src/main/java下的文件
           java.io.File targetFile = new java.io.File(targetPath);
           if (targetFile.exists() && targetFile.isDirectory()) {
               java.io.File projectRoot = targetFile.getParentFile(); // 跳出classes
               if (projectRoot != null) {
                   projectRoot = projectRoot.getParentFile(); // 跳出target
                   if (projectRoot != null) {
                       // 项目根目录下的src/main/java
                       possiblePaths.add(projectRoot.getAbsolutePath() + "/src/main/java/" + packagePath + "/" + sourceFile);
                       // 项目根目录下的src
                       possiblePaths.add(projectRoot.getAbsolutePath() + "/src/" + packagePath + "/" + sourceFile);
                   }
               }
           }

           // 查找第一个存在的路径
           java.io.File file = null;
           for (String path : possiblePaths) {
               file = new java.io.File(path);
               if (file.exists()) {
                   break;
               }
               file = null;
           }

           // 如果所有尝试都失败，递归查找
           if (file == null || !file.exists()) {
               file = findSourceFile(sourceFile);
           }

           if (file == null || !file.exists()) {
               // 记录日志但继续处理其他字段
               logger.debug("无法找到源文件：{} 对应类：{}", sourceFile, className);
               return -1;
           }

           // 读取源文件内容
           List<String> lines = Files.readAllLines(file.toPath());

           // 在源文件中查找字段定义
           int lineNumber = findFieldDefinition(lines, field);
           if (lineNumber > 0) {
               logger.debug("找到字段定义：{}.{} 在 {} 行 {}", className, field.getName(), file.getAbsolutePath(), lineNumber);
               return lineNumber;
           }
       } catch (Exception e) {
           // 忽略异常，返回-1
           logger.debug("获取字段行号时出错：{}", e.getMessage());
       }

        return -1;
    }

    /**
     * 在源码中查找字段定义
     *
     * @param lines 源文件的所有行
     * @param field 需要查找的字段
     * @return 字段定义的行号（从1开始）
     */
    private int findFieldDefinition(List<String> lines, SootField field) {
        String fieldName = field.getName();
        String fieldType = field.getType().toString();
        String simpleFieldType = getSimpleTypeName(fieldType);
        boolean isStatic = Modifier.isStatic(field.getModifiers());
        boolean isFinal = Modifier.isFinal(field.getModifiers());
        boolean isPrivate = Modifier.isPrivate(field.getModifiers());
        boolean isPublic = Modifier.isPublic(field.getModifiers());
        boolean isProtected = Modifier.isProtected(field.getModifiers());

        // 构建正则表达式模式来匹配字段定义
        StringBuilder patternBuilder = new StringBuilder();

        // 可选的访问修饰符
        if (isPrivate || isPublic || isProtected) {
            patternBuilder.append("(");
            if (isPrivate) patternBuilder.append("private\\s+");
            if (isPublic) patternBuilder.append("public\\s+");
            if (isProtected) patternBuilder.append("protected\\s+");
            patternBuilder.append(")?");
        } else {
            patternBuilder.append("(private|public|protected)?\\s*");
        }

        // 可选的static和final修饰符
        if (isStatic) patternBuilder.append("(static\\s+)?");
        if (isFinal) patternBuilder.append("(final\\s+)?");

        // 可选的其他修饰符
        patternBuilder.append("(\\w+\\s+)*");

        // 字段类型（尝试多种可能的表示形式）
        patternBuilder.append("(");
        patternBuilder.append(java.util.regex.Pattern.quote(fieldType));
        patternBuilder.append("|");
        patternBuilder.append(java.util.regex.Pattern.quote(simpleFieldType));
        patternBuilder.append(")\\s+");

        // 字段名
        patternBuilder.append(java.util.regex.Pattern.quote(fieldName));

        // 可能的初始化和分号
        patternBuilder.append("(\\s*=.*)?;");

        try {
            java.util.regex.Pattern pattern = java.util.regex.Pattern.compile(patternBuilder.toString());

            // 直接尝试找到最精确的匹配
            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i).trim();
                if (line.isEmpty() || line.startsWith("//")) continue;

                // 跳过方法定义（包含括号但不是初始化表达式）
                if (line.contains("(") && !line.contains("=") && !line.contains("new ")) continue;

                if (pattern.matcher(line).find()) {
                    return i + 1; // 行号从1开始
                }
            }

            // 如果没有找到精确匹配，使用宽松的匹配策略
            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i).trim();
                if (line.isEmpty() || line.startsWith("//")) continue;

                // 字段名、类型和分号都存在的行
                if (line.contains(fieldName) &&
                    (line.contains(fieldType) || line.contains(simpleFieldType)) &&
                    line.contains(";") &&
                    !line.contains("(") && !line.contains("return ")) {

                    // 分词检查确保字段名是单独的标识符
                    String[] parts = line.split("[\\s\\(\\)\\{\\}\\[\\]\\;\\,\\:\\.]");
                    for (String part : parts) {
                        if (part.equals(fieldName)) {
                            return i + 1; // 行号从1开始
                        }
                    }
                }
            }

            // 最后的尝试：只匹配字段名和分号
            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i).trim();
                if (line.isEmpty() || line.startsWith("//")) continue;

                if (line.contains(fieldName) && line.contains(";") && !line.contains("(")) {
                    String[] parts = line.split("[\\s\\(\\)\\{\\}\\[\\]\\;\\,\\:\\.]");
                    for (String part : parts) {
                        if (part.equals(fieldName)) {
                            return i + 1; // 行号从1开始
                        }
                    }
                }
            }
        } catch (Exception e) {
            logger.debug("解析字段定义时出错：{}", e.getMessage());
        }

        return -1; // 未找到
    }

    /**
     * 获取类型的简单名称
     */
    private String getSimpleTypeName(String fullTypeName) {
        // 去除包名，只保留类型的简单名称
        int lastDot = fullTypeName.lastIndexOf('.');
        if (lastDot > 0) {
            return fullTypeName.substring(lastDot + 1);
        }
        return fullTypeName;
    }

    /**
     * 在整个项目中查找源文件
     */
    private java.io.File findSourceFile(String fileName) {
        try {
            // 从项目根目录开始查找
            java.io.File rootDir = new java.io.File(targetPath);
            return findFile(rootDir, fileName);
        } catch (Exception e) {
            logger.debug("查找源文件时出错：{}", e.getMessage());
            return null;
        }
    }

    /**
     * 递归查找文件
     */
    private java.io.File findFile(java.io.File dir, String fileName) {
        if (dir.isDirectory()) {
            java.io.File[] files = dir.listFiles();
            if (files != null) {
                for (java.io.File file : files) {
                    if (file.isDirectory()) {
                        java.io.File found = findFile(file, fileName);
                        if (found != null) {
                            return found;
                        }
                    } else if (file.getName().equals(fileName)) {
                        return file;
                    }
                }
            }
        }
        return null;
    }

    /**
     * 获取方法的行号
     */
    private int getLineNumber(SootMethod method) {
        if (!method.hasActiveBody()) {
            return -1;
        }

        // 尝试获取方法第一条语句的行号
        for (Unit unit : method.getActiveBody().getUnits()) {
            int lineNumber = getLineNumber(unit);
            if (lineNumber > 0) {
                return lineNumber;
            }
        }

        return -1;
    }

    /**
     * 获取语句的行号
     */
    private int getLineNumber(Unit unit) {
        LineNumberTag tag = (LineNumberTag) unit.getTag("LineNumberTag");
        return tag != null ? tag.getLineNumber() : -1;
    }

    /**
     * 设置生成调用图
     */
    public void setGenerateCallGraph(boolean generateCallGraph) {
        this.generateCallGraph = generateCallGraph;
    }

    /**
     * 设置生成Jimple
     */
    public void setGenerateJimple(boolean generateJimple) {
        this.generateJimple = generateJimple;
    }

    /**
     * 设置生成索引
     */
    public void setGenerateIndex(boolean generateIndex) {
        this.generateIndex = generateIndex;
    }

    /**
     * 主方法
     */
    public static void main(String[] args) {
        // 创建命令行选项
        org.apache.commons.cli.Options cliOptions = new org.apache.commons.cli.Options();

        cliOptions.addOption(Option.builder("t")
                .longOpt("target")
                .desc("目标Java项目路径")
                .hasArg()
                .required(true)
                .build());

        cliOptions.addOption(Option.builder("o")
                .longOpt("output")
                .desc("输出目录")
                .hasArg()
                .required(true)
                .build());

        cliOptions.addOption(Option.builder("c")
                .longOpt("callgraph")
                .desc("生成调用图")
                .build());

        cliOptions.addOption(Option.builder("j")
                .longOpt("jimple")
                .desc("生成Jimple IR")
                .build());

        cliOptions.addOption(Option.builder("i")
                .longOpt("index")
                .desc("生成代码索引")
                .build());

        cliOptions.addOption(Option.builder("h")
                .longOpt("help")
                .desc("显示帮助信息")
                .build());

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();

        try {
            // 解析命令行参数
            CommandLine cmd = parser.parse(cliOptions, args);

            if (cmd.hasOption("h")) {
                formatter.printHelp("SootCodeAnalyzer", cliOptions);
                return;
            }

            String targetPath = cmd.getOptionValue("t");
            String outputPath = cmd.getOptionValue("o");

            // 创建分析器
            SootCodeAnalyzer analyzer = new SootCodeAnalyzer(targetPath, outputPath);

            // 设置选项
            analyzer.setGenerateCallGraph(cmd.hasOption("c"));
            analyzer.setGenerateJimple(cmd.hasOption("j"));
            analyzer.setGenerateIndex(cmd.hasOption("i"));

            // 执行分析
            analyzer.analyze();

        } catch (ParseException e) {
            System.err.println("解析命令行参数出错：" + e.getMessage());
            formatter.printHelp("SootCodeAnalyzer", cliOptions);
        }
    }

    /**
     * 找到指定类的class文件
     * @param clazz Soot类
     * @return 类文件对象，如果找不到返回null
     */
    private java.io.File findClassFile(SootClass clazz) {
        String className = clazz.getName();
        String packagePath = clazz.getPackageName().replace('.', '/');
        String simpleName = className.substring(className.lastIndexOf('.') + 1);

        // 尝试多种可能的类文件路径
        java.util.List<String> possiblePaths = new java.util.ArrayList<>();

        // 1. 直接在targetPath下查找
        possiblePaths.add(targetPath + "/" + packagePath + "/" + simpleName + ".class");

        // 2. 在targetPath的根目录下查找
        possiblePaths.add(targetPath + "/" + simpleName + ".class");

        // 3. 在标准的classes目录下查找
        possiblePaths.add(targetPath + "/classes/" + packagePath + "/" + simpleName + ".class");

        // 查找第一个存在的路径
        for (String path : possiblePaths) {
            java.io.File file = new java.io.File(path);
            if (file.exists()) {
                return file;
            }
        }

        // 如果所有尝试都失败，递归查找
        java.io.File targetDir = new java.io.File(targetPath);
        if (targetDir.exists() && targetDir.isDirectory()) {
            try {
                java.nio.file.Path startPath = targetDir.toPath();

                // 使用Files.find进行递归搜索
                java.util.Optional<java.nio.file.Path> foundPath = java.nio.file.Files.find(
                    startPath,
                    10, // 最大搜索深度
                    (path, attrs) -> path.getFileName().toString().equals(simpleName + ".class"),
                    java.nio.file.FileVisitOption.FOLLOW_LINKS
                ).findFirst();

                if (foundPath.isPresent()) {
                    return foundPath.get().toFile();
                }
            } catch (Exception e) {
                logger.debug("递归查找类文件时出错：{}", e.getMessage());
            }
        }

        return null;
    }
}
