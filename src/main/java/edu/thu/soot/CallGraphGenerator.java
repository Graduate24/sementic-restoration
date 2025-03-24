package edu.thu.soot;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import soot.*;
import soot.jimple.spark.SparkTransformer;
import soot.jimple.toolkits.callgraph.CHATransformer;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.options.Options;
import soot.tagkit.LineNumberTag;
import soot.tagkit.SourceFileTag;
import soot.tagkit.Tag;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

/**
 * 调用图生成工具
 * 使用Soot生成Java项目的调用图，并以JSON格式输出
 */
public class CallGraphGenerator {
    private static final Logger logger = LoggerFactory.getLogger(CallGraphGenerator.class);
    
    private final String appPath;
    private final String outputPath;
    private final String algorithm;
    private final Set<String> entryPoints = new HashSet<>();
    
    // 记录方法的行号信息
    private final Map<SootMethod, Integer> methodLineNumbers = new HashMap<>();
    
    /**
     * 调用图类型
     */
    public enum CallGraphAlgorithm {
        CHA,   // Class Hierarchy Analysis (快速但不精确)
        SPARK  // Spark points-to analysis (慢但更精确)
    }
    
    /**
     * 创建调用图生成器
     * 
     * @param appPath     应用路径（类路径或JAR文件）
     * @param outputPath  输出路径
     * @param algorithm   调用图算法（CHA或SPARK）
     */
    public CallGraphGenerator(String appPath, String outputPath, String algorithm) {
        this.appPath = appPath;
        this.outputPath = outputPath;
        this.algorithm = algorithm;
    }
    
    /**
     * 添加入口点
     * 
     * @param className   类名
     * @param methodName  方法名
     */
    public void addEntryPoint(String className, String methodName) {
        entryPoints.add(className + ":" + methodName);
    }
    
    /**
     * 生成调用图
     * 
     * @return 是否生成成功
     */
    public boolean generate() {
        try {
            logger.info("初始化Soot...");
            
            // 配置Soot
            configureSoot();
            
            // 加载类
            Scene.v().loadNecessaryClasses();
            
            // 设置入口点
            if (!entryPoints.isEmpty()) {
                setupEntryPoints();
            } else {
                logger.info("未指定入口点，使用默认入口点");
            }
            
            // 收集方法行号信息
            collectMethodLineNumbers();
            
            // 生成调用图
            CallGraph callGraph = generateCallGraph();
            
            // 处理并保存调用图
            processAndSaveCallGraph(callGraph);
            
            logger.info("调用图生成完成");
            return true;
            
        } catch (Exception e) {
            logger.error("生成调用图时出错: " + e.getMessage(), e);
            return false;
        }
    }
    
    /**
     * 配置Soot
     */
    private void configureSoot() {
        G.reset();
        
        Options.v().set_prepend_classpath(true);
        Options.v().set_allow_phantom_refs(true);
        Options.v().set_whole_program(true);
        Options.v().set_app(true);
        Options.v().set_keep_line_number(true);
        Options.v().set_src_prec(Options.src_prec_java);
        Options.v().set_output_format(Options.output_format_none);
        
        List<String> processDirs = Collections.singletonList(appPath);
        Options.v().set_process_dir(processDirs);
        
        // 排除一些包
        List<String> excludeList = Arrays.asList(
            "java.*", "javax.*", "sun.*", "com.sun.*", "com.ibm.*", 
            "org.xml.*", "org.w3c.*", "apple.awt.*", "com.apple.*"
        );
        Options.v().set_exclude(excludeList);
    }
    
    /**
     * 设置入口点
     */
    private void setupEntryPoints() {
        List<SootMethod> entryPointList = new ArrayList<>();
        
        for (String entryPoint : entryPoints) {
            String[] parts = entryPoint.split(":");
            if (parts.length != 2) {
                logger.warn("无效的入口点格式: {}", entryPoint);
                continue;
            }
            
            String className = parts[0];
            String methodName = parts[1];
            
            try {
                SootClass sootClass = Scene.v().getSootClass(className);
                
                if (methodName.equals("*")) {
                    // 添加类的所有方法
                    for (SootMethod method : sootClass.getMethods()) {
                        if (!method.isAbstract()) {
                            entryPointList.add(method);
                            logger.debug("添加入口点: {}.{}", className, method.getName());
                        }
                    }
                } else {
                    // 添加指定方法
                    SootMethod method = sootClass.getMethodByName(methodName);
                    entryPointList.add(method);
                    logger.debug("添加入口点: {}.{}", className, methodName);
                }
            } catch (Exception e) {
                logger.warn("找不到入口点: {}.{}", className, methodName);
            }
        }
        
        if (!entryPointList.isEmpty()) {
            logger.info("设置 {} 个自定义入口点", entryPointList.size());
            Scene.v().setEntryPoints(entryPointList);
        } else {
            logger.info("未找到有效的入口点，使用默认入口点");
        }
    }
    
    /**
     * 收集方法行号信息
     */
    private void collectMethodLineNumbers() {
        logger.info("收集方法行号信息...");
        
        for (SootClass sootClass : Scene.v().getApplicationClasses()) {
            if (sootClass.isPhantom()) {
                continue;
            }
            
            for (SootMethod method : sootClass.getMethods()) {
                int lineNumber = findMethodLineNumber(method);
                if (lineNumber > 0) {
                    methodLineNumbers.put(method, lineNumber);
                }
            }
        }
        
        logger.info("收集到 {} 个方法的行号信息", methodLineNumbers.size());
    }
    
    /**
     * 查找方法的行号
     */
    private int findMethodLineNumber(SootMethod method) {
        if (!method.hasActiveBody()) {
            try {
                method.retrieveActiveBody();
            } catch (Exception e) {
                return -1;
            }
        }
        
        Body body = method.getActiveBody();
        for (Unit unit : body.getUnits()) {
            LineNumberTag tag = (LineNumberTag) unit.getTag("LineNumberTag");
            if (tag != null) {
                return tag.getLineNumber();
            }
        }
        
        return -1;
    }
    
    /**
     * 生成调用图
     */
    private CallGraph generateCallGraph() {
        logger.info("使用 {} 算法生成调用图...", algorithm);
        
        if (CallGraphAlgorithm.SPARK.name().equalsIgnoreCase(algorithm)) {
            // 使用Spark算法
            HashMap<String, String> sparkOptions = new HashMap<>();
            sparkOptions.put("verbose", "true");
            sparkOptions.put("propagator", "worklist");
            sparkOptions.put("simple-edges-bidirectional", "false");
            sparkOptions.put("on-fly-cg", "true");
            sparkOptions.put("set-impl", "double");
            sparkOptions.put("double-set-old", "hybrid");
            sparkOptions.put("double-set-new", "hybrid");
            
            SparkTransformer.v().transform("", sparkOptions);
        } else {
            // 默认使用CHA算法
            CHATransformer.v().transform();
        }
        
        return Scene.v().getCallGraph();
    }
    
    /**
     * 处理并保存调用图
     */
    private void processAndSaveCallGraph(CallGraph callGraph) throws IOException {
        logger.info("处理调用图...");
        
        // 创建输出目录
        Path outputDir = Paths.get(outputPath);
        if (!Files.exists(outputDir)) {
            Files.createDirectories(outputDir);
        }
        
        // 准备JSON对象
        JsonObject rootObject = new JsonObject();
        JsonArray nodesArray = new JsonArray();
        JsonArray edgesArray = new JsonArray();
        
        // 记录已添加的方法
        Set<SootMethod> addedMethods = new HashSet<>();
        int methodCount = 0;
        int edgeCount = 0;
        
        // 处理调用关系
        Iterator<Edge> edgeIterator = callGraph.iterator();
        while (edgeIterator.hasNext()) {
            Edge edge = edgeIterator.next();
            SootMethod src = edge.src();
            SootMethod tgt = edge.tgt();
            
            // 跳过库方法之间的调用
            if (isLibraryMethod(src) && isLibraryMethod(tgt)) {
                continue;
            }
            
            // 添加源方法节点
            if (!addedMethods.contains(src)) {
                addMethodNode(nodesArray, src);
                addedMethods.add(src);
                methodCount++;
            }
            
            // 添加目标方法节点
            if (!addedMethods.contains(tgt)) {
                addMethodNode(nodesArray, tgt);
                addedMethods.add(tgt);
                methodCount++;
            }
            
            // 添加边
            addCallEdge(edgesArray, src, tgt, edge.kind());
            edgeCount++;
        }
        
        rootObject.add("nodes", nodesArray);
        rootObject.add("edges", edgesArray);
        
        // 保存为JSON文件
        Gson gson = new GsonBuilder()
                .setPrettyPrinting()
                .disableHtmlEscaping() // 禁用HTML转义，让<>符号正常显示
                .create();
        try (FileWriter writer = new FileWriter(outputPath + "/call_graph.json")) {
            gson.toJson(rootObject, writer);
        }
        
        logger.info("调用图已保存: {} 个方法, {} 条调用边", methodCount, edgeCount);
    }
    
    /**
     * 添加方法节点
     */
    private void addMethodNode(JsonArray nodesArray, SootMethod method) {
        JsonObject methodObject = new JsonObject();
        
        methodObject.addProperty("id", method.getSignature());
        methodObject.addProperty("name", method.getName());
        methodObject.addProperty("class", method.getDeclaringClass().getName());
        methodObject.addProperty("returnType", method.getReturnType().toString());
        methodObject.addProperty("modifier", Modifier.toString(method.getModifiers()));
        methodObject.addProperty("isApplicationMethod", !isLibraryMethod(method));
        
        // 添加源文件和行号信息
        SootClass declaringClass = method.getDeclaringClass();
        SourceFileTag sourceFileTag = (SourceFileTag) declaringClass.getTag("SourceFileTag");
        if (sourceFileTag != null) {
            methodObject.addProperty("sourceFile", sourceFileTag.getSourceFile());
        }
        
        Integer lineNumber = methodLineNumbers.get(method);
        if (lineNumber != null) {
            methodObject.addProperty("lineNumber", lineNumber);
        }
        
        // 添加参数信息
        JsonArray paramsArray = new JsonArray();
        for (int i = 0; i < method.getParameterCount(); i++) {
            JsonObject paramObject = new JsonObject();
            paramObject.addProperty("type", method.getParameterType(i).toString());
            paramsArray.add(paramObject);
        }
        methodObject.add("parameters", paramsArray);
        
        nodesArray.add(methodObject);
    }
    
    /**
     * 添加调用边
     */
    private void addCallEdge(JsonArray edgesArray, SootMethod src, SootMethod tgt, Kind kind) {
        JsonObject edgeObject = new JsonObject();
        
        edgeObject.addProperty("source", src.getSignature());
        edgeObject.addProperty("target", tgt.getSignature());
        edgeObject.addProperty("type", kind.toString());
        
        // 添加源方法行号
        Integer srcLineNumber = methodLineNumbers.get(src);
        if (srcLineNumber != null) {
            edgeObject.addProperty("sourceLineNumber", srcLineNumber);
        }
        
        // 添加目标方法行号
        Integer tgtLineNumber = methodLineNumbers.get(tgt);
        if (tgtLineNumber != null) {
            edgeObject.addProperty("targetLineNumber", tgtLineNumber);
        }
        
        edgesArray.add(edgeObject);
    }
    
    /**
     * 判断是否为库方法
     */
    private boolean isLibraryMethod(SootMethod method) {
        SootClass declaringClass = method.getDeclaringClass();
        return declaringClass.isLibraryClass() || declaringClass.isJavaLibraryClass();
    }
    
    /**
     * 主方法
     */
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("用法: java CallGraphGenerator <应用路径> <输出路径> [算法] [入口点...]");
            System.out.println("  算法: CHA (默认) 或 SPARK");
            System.out.println("  入口点格式: 类名:方法名 (例如 com.example.Main:main)");
            System.out.println("            或 类名:* (表示类的所有方法)");
            return;
        }
        
        String appPath = args[0];
        String outputPath = args[1];
        String algorithm = args.length > 2 ? args[2] : CallGraphAlgorithm.CHA.name();
        
        CallGraphGenerator generator = new CallGraphGenerator(appPath, outputPath, algorithm);
        
        // 添加自定义入口点
        for (int i = 3; i < args.length; i++) {
            generator.addEntryPoint(args[i].split(":")[0], args[i].split(":")[1]);
        }
        
        // 生成调用图
        boolean success = generator.generate();
        System.exit(success ? 0 : 1);
    }
} 