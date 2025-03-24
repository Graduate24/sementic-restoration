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
            Gson gson = new GsonBuilder().setPrettyPrinting().create();
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
        
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        
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

    /**
     * 获取字段的行号
     */
    private int getLineNumber(SootField field) {
        Tag tag = field.getTag("LineNumberTag");
        if (tag != null && tag instanceof LineNumberTag) {
            return ((LineNumberTag) tag).getLineNumber();
        }
        return -1;
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
} 