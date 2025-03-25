package edu.thu.soot;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import org.apache.commons.cli.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import soot.*;
import soot.jimple.*;
import soot.jimple.spark.pag.AllocNode;
import soot.jimple.spark.pag.PAG;
import soot.options.Options;
import soot.tagkit.LineNumberTag;
import soot.tagkit.SourceFileTag;
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
    private boolean generatePointsToAnalysis = false;

    // 存储索引信息
    private final Map<String, List<IndexEntry>> methodDefinitions = new HashMap<>();
    private final Map<String, List<IndexEntry>> methodInvocations = new HashMap<>();
    private final Map<String, List<IndexEntry>> fieldDefinitions = new HashMap<>();
    private final Map<String, List<IndexEntry>> fieldReferences = new HashMap<>();

    // 存储调用图信息
    private final Map<String, List<String>> callGraph = new HashMap<>();

    // 存储指针分析结果
    private final Map<String, Map<String, Set<String>>> pointsToLocals = new HashMap<>();      // 局部变量
    private final Map<String, Set<String>> pointsToInstanceFields = new HashMap<>();           // 实例字段
    private final Map<String, Set<String>> pointsToStaticFields = new HashMap<>();             // 静态字段
    private final Map<String, Map<String, Object>> pointsToArrays = new HashMap<>();           // 数组

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

        // 增加变量名称保留和调试信息
        Options.v().set_keep_line_number(true);
        Options.v().set_keep_offset(true);

        // 尝试保留变量名
        Options.v().setPhaseOption("jb", "use-original-names:true");

        // 设置输出格式
        if (generateJimple) {
            Options.v().set_output_format(Options.output_format_jimple);
        } else {
            Options.v().set_output_format(Options.output_format_none);
        }

        // 设置阶段选项
        if (generateCallGraph || generatePointsToAnalysis) {
            Options.v().set_whole_program(true);
            Options.v().setPhaseOption("cg", "safe-newinstance:true");
            Options.v().setPhaseOption("cg.spark", "on");

            // 针对指针分析的额外配置
            if (generatePointsToAnalysis) {
                // 增强指针分析配置
                Options.v().setPhaseOption("cg.spark", "verbose:true");
                Options.v().setPhaseOption("cg.spark", "on-fly-cg:true");
                Options.v().setPhaseOption("cg.spark", "propagator:worklist");
                Options.v().setPhaseOption("cg.spark", "set-impl:double");
                Options.v().setPhaseOption("cg.spark", "double-set-old:hybrid");
                Options.v().setPhaseOption("cg.spark", "double-set-new:hybrid");
                Options.v().setPhaseOption("cg.spark", "field-based:false");
                Options.v().setPhaseOption("cg.spark", "types-for-sites:true");
                Options.v().setPhaseOption("cg.spark", "merge-stringbuffer:true");
                Options.v().setPhaseOption("cg.spark", "string-constants:true");
                Options.v().setPhaseOption("cg.spark", "simulate-natives:true");
            }
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

        // 生成指针分析结果
        if (generatePointsToAnalysis) {
            generatePointsToAnalysis();
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

        // 过滤掉系统类字段
        if (isExcludedClass(className)) {
            return;
        }

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

        // 过滤掉系统类方法
        if (isExcludedClass(className)) {
            return;
        }

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

                    // 添加到调用图（不过滤系统类，保持调用图的完整性）
                    String caller = method.getSignature();
                    String callee = calledSignature;

                    if (!callGraph.containsKey(caller)) {
                        callGraph.put(caller, new ArrayList<>());
                    }
                    if (!callGraph.get(caller).contains(callee)) {
                        callGraph.get(caller).add(callee);
                    }

                    // 过滤掉系统类方法调用（仅针对方法调用索引）
                    if (isExcludedClass(calledClassName)) {
                        continue;
                    }

                    // 添加到方法调用索引
                    IndexEntry entry = new IndexEntry(calledClassName, calledMethodName, calledSignature, sourceFile, lineNumber);

                    if (!methodInvocations.containsKey(calledMethodName)) {
                        methodInvocations.put(calledMethodName, new ArrayList<>());
                    }
                    methodInvocations.get(calledMethodName).add(entry);
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

                    // 过滤掉系统类字段引用
                    if (isExcludedClass(fieldClassName)) {
                        continue;
                    }

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
     * 生成指针分析结果
     */
    private void generatePointsToAnalysis() {
        logger.info("生成指针分析结果...");

        if (!Options.v().whole_program()) {
            logger.error("指针分析需要设置whole-program选项");
            return;
        }

        // 确保Spark已启用并执行指针分析
        if (!Scene.v().hasCallGraph()) {
            logger.info("执行Spark指针分析...");
            // 显式构建调用图
            Scene.v().setEntryPoints(getEntryPoints());
            logger.info("设置入口点完成，共 {} 个入口点", Scene.v().getEntryPoints().size());

            // 执行调用图构建
            PackManager.v().getPack("cg").apply();

            if (!Scene.v().hasCallGraph()) {
                logger.error("调用图构建失败");
                return;
            }
            logger.info("调用图构建完成");
        }

        // 获取指针分析器
        PointsToAnalysis pta = Scene.v().getPointsToAnalysis();
        if (pta == null) {
            logger.error("无法获取指针分析器");
            return;
        }

        logger.info("使用指针分析器: {}", pta.getClass().getName());

        // 检查是否使用的是Spark分析器，以便获取PAG
        PAG pag = getPAG();
        if (pag != null) {
            logger.info("成功获取PAG，将使用更详细的对象分配信息");
        }

        // 分析所有变量的指向关系
        logger.info("分析变量的指向关系...");

        // 创建应用类的副本以避免并发修改异常
        List<SootClass> applicationClasses = new ArrayList<>(Scene.v().getApplicationClasses());

        for (SootClass sootClass : applicationClasses) {
            if (sootClass.isPhantom() || isExcludedClass(sootClass.getName())) {
                continue;
            }

            String className = sootClass.getName();

            // 分析静态字段
            analyzeStaticFields(sootClass, pta, pag);

            // 遍历所有方法
            for (SootMethod method : sootClass.getMethods()) {
                if (!method.hasActiveBody()) {
                    try {
                        method.retrieveActiveBody();
                    } catch (Exception e) {
                        continue;
                    }
                }

                Body body = method.getActiveBody();

                // 分析局部变量
                analyzeLocalVariables(className, method, body, pta, pag);

                // 分析字段和数组
                analyzeFieldsAndArrays(className, method, body, pta, pag);
            }
        }

        // 保存指针分析结果
        savePointsToAnalysisResults();
    }

    /**
     * 获取PAG分析器实例
     */
    private PAG getPAG() {
        try {
            PointsToAnalysis pta = Scene.v().getPointsToAnalysis();
            if (pta != null && pta.getClass().getName().contains("Spark")) {
                // 尝试使用反射获取PAG实例
                java.lang.reflect.Method method = pta.getClass().getMethod("getPag");
                if (method != null) {
                    Object pag = method.invoke(pta);
                    if (pag instanceof PAG) {
                        return (PAG) pag;
                    }
                }
            }
        } catch (Exception e) {
            logger.debug("获取PAG实例失败: {}", e.getMessage());
        }
        return null;
    }

    /**
     * 分析静态字段
     */
    private void analyzeStaticFields(SootClass sootClass, PointsToAnalysis pta, PAG pag) {
        for (SootField field : sootClass.getFields()) {
            if (!field.isStatic() || !(field.getType() instanceof RefLikeType)) {
                continue;
            }

            String fieldKey = sootClass.getName() + "." + field.getName() + " (" + field.getType() + ")";
            Set<String> pointsToSet = new HashSet<>();
            pointsToStaticFields.put(fieldKey, pointsToSet);

            // 获取静态字段指向的对象
            PointsToSet pts = pta.reachingObjects(field);
            if (pts == null) {
                logger.debug("静态字段的指向集合为null: {}", fieldKey);
                continue;
            }

            // 使用详细的分析方法
            if (pag != null) {
                // 使用PAG获取更详细的对象信息
                addPointsToFromPAG(pts, pointsToSet, pag);
            } else {
                // 使用基本方法
                addPointsToTypes(pts, pointsToSet);
            }

            logger.debug("静态字段 {} 指向 {} 个对象", fieldKey, pointsToSet.size());
        }
    }

    /**
     * 分析局部变量
     */
    private void analyzeLocalVariables(String className, SootMethod method, Body body, PointsToAnalysis pta, PAG pag) {
        String methodKey = className + "." + method.getName();
        Map<String, Set<String>> localsMap = new HashMap<>();
        pointsToLocals.put(methodKey, localsMap);

        // 创建一个本地变量名称映射，用于保存原始变量名
        Map<Local, String> localNameMap = extractOriginalVariableNames(body);

        for (Local local : body.getLocals()) {
            if (!(local.getType() instanceof RefLikeType)) {
                continue; // 只分析引用类型和数组类型
            }
            if (local.isStackLocal()) {
                continue;
            }
            // 尝试使用原始变量名，如果没有则使用Jimple变量名
            String varName = localNameMap.getOrDefault(local, local.getName());

            // 尝试记录变量类型以帮助识别
            String varNameWithType = varName + " (" + local.getType().toString() + ")";

            Set<String> pointsToSet = new HashSet<>();
            localsMap.put(varNameWithType, pointsToSet);

            // 获取变量指向的对象
            PointsToSet pts = pta.reachingObjects(local);
            if (pts == null) {
                logger.debug("变量的指向集合为null: {}.{}.{}", className, method.getName(), varName);
                continue;
            }

            // 使用详细的分析方法
            if (pag != null) {
                // 使用PAG获取更详细的对象信息
                addPointsToFromPAG(pts, pointsToSet, pag);
            } else {
                // 使用基本方法
                addPointsToTypes(pts, pointsToSet);
            }

            logger.debug("变量 {}.{}.{} 指向 {} 个对象", className, method.getName(), varName, pointsToSet.size());

            // 处理数组类型
            if (local.getType() instanceof ArrayType) {
                Map<String, Object> arrayInfo = new HashMap<>();
                arrayInfo.put("elementType", ((ArrayType) local.getType()).getElementType().toString());

                Set<String> arrayPointsTo = new HashSet<>();
                if (pag != null) {
                    addPointsToFromPAG(pts, arrayPointsTo, pag);
                } else {
                    addPointsToTypes(pts, arrayPointsTo);
                }

                arrayInfo.put("pointsTo", arrayPointsTo);
                arrayInfo.put("pointsToCount", arrayPointsTo.size()); // 添加统计信息

                String arrayKey = methodKey + "." + varName;
                pointsToArrays.put(arrayKey, arrayInfo);
            }
        }
    }

    /**
     * 分析字段和数组访问
     */
    private void analyzeFieldsAndArrays(String className, SootMethod method, Body body, PointsToAnalysis pta, PAG pag) {
        for (Unit unit : body.getUnits()) {
            for (ValueBox valueBox : unit.getUseAndDefBoxes()) {
                Value value = valueBox.getValue();

                // 分析实例字段
                if (value instanceof InstanceFieldRef) {
                    InstanceFieldRef fieldRef = (InstanceFieldRef) value;
                    SootField field = fieldRef.getField();

                    if (!(field.getType() instanceof RefLikeType)) {
                        continue; // 只分析引用类型和数组类型
                    }

                    String fieldKey = field.getDeclaringClass().getName() + "." + field.getName() + " (" + field.getType() + ")";

                    // 已经分析过的字段跳过
                    if (pointsToInstanceFields.containsKey(fieldKey)) {
                        continue;
                    }

                    Set<String> fieldPointsTo = new HashSet<>();
                    pointsToInstanceFields.put(fieldKey, fieldPointsTo);

                    // 获取字段的基对象
                    Local base = (Local) fieldRef.getBase();
                    PointsToSet basePoints = pta.reachingObjects(base);
                    if (basePoints == null || basePoints.isEmpty()) {
                        logger.debug("基对象的指向集合为空: {}.{}", base.getName(), field.getName());
                        continue;
                    }

                    // 获取字段指向的对象
                    PointsToSet fieldPoints = pta.reachingObjects(basePoints, field);
                    if (fieldPoints == null) {
                        logger.debug("字段的指向集合为null: {}", fieldKey);
                        continue;
                    }

                    // 使用详细的分析方法
                    if (pag != null) {
                        addPointsToFromPAG(fieldPoints, fieldPointsTo, pag);
                    } else {
                        addPointsToTypes(fieldPoints, fieldPointsTo);
                    }

                    logger.debug("实例字段 {} 指向 {} 个对象", fieldKey, fieldPointsTo.size());
                }
                // 分析数组元素访问
                else if (value instanceof ArrayRef) {
                    ArrayRef arrayRef = (ArrayRef) value;
                    Local baseArray = (Local) arrayRef.getBase();

                    if (!(baseArray.getType() instanceof ArrayType)) {
                        continue;
                    }

                    String varName = baseArray.getName();
                    String arrayKey = className + "." + method.getName() + "." + varName + " (" + baseArray.getType() + ")";

                    // 已经分析过的数组跳过
                    if (pointsToArrays.containsKey(arrayKey)) {
                        continue;
                    }

                    Map<String, Object> arrayInfo = new HashMap<>();
                    arrayInfo.put("elementType", ((ArrayType) baseArray.getType()).getElementType().toString());

                    Set<String> arrayPointsTo = new HashSet<>();
                    PointsToSet pts = pta.reachingObjects(baseArray);
                    if (pts == null) {
                        logger.debug("数组的指向集合为null: {}", arrayKey);
                    } else {
                        if (pag != null) {
                            addPointsToFromPAG(pts, arrayPointsTo, pag);
                        } else {
                            addPointsToTypes(pts, arrayPointsTo);
                        }
                        logger.debug("数组 {} 指向 {} 个对象", arrayKey, arrayPointsTo.size());
                    }

                    arrayInfo.put("pointsTo", arrayPointsTo);
                    arrayInfo.put("pointsToCount", arrayPointsTo.size());

                    pointsToArrays.put(arrayKey, arrayInfo);
                }
            }
        }
    }

    /**
     * 使用PAG分析器获取详细的对象分配点信息
     */
    private void addPointsToFromPAG(final PointsToSet pts, final Set<String> targetSet, final PAG pag) {
        if (pts == null) {
            return;
        }

        try {
            // 由于PointsToSetVisitorFactory可能不可用，我们需要尝试其他方式获取分配点
            // 1. 尝试使用反射获取pts内部的数据结构
            boolean added = tryGetAllocationNodesViaReflection(pts, targetSet);

            // 2. 如果不成功，尝试使用Spark直接查询某些关键类型的分配节点
            if (!added && pag != null) {
                // 遍历pts的possibleTypes
                for (Type type : pts.possibleTypes()) {
                    if (type instanceof RefType) {
                        RefType refType = (RefType) type;
                        String className = refType.getClassName();

                        // 过滤掉异常和堆栈相关的类型
                        if (!className.contains("Exception") &&
                                !className.contains("Error") &&
                                !className.contains("Throwable") &&
                                !className.contains("Stack")) {

                            // 尝试找到所有这个类型的分配点 (不一定精确，但可能有用)
                            String objectInfo = "Object: " + className + " (from analysis)";
                            targetSet.add(objectInfo);
                            added = true;
                        }
                    } else if (type instanceof ArrayType) {
                        String typeName = type.toString();

                        // 过滤掉异常和堆栈相关的类型
                        if (!typeName.contains("Exception") &&
                                !typeName.contains("Error") &&
                                !typeName.contains("Throwable") &&
                                !typeName.contains("Stack")) {

                            String objectInfo = "Array: " + typeName + " (from analysis)";
                            targetSet.add(objectInfo);
                            added = true;
                        }
                    }
                }
            }

            // 3. 如果上述方法都失败，回退到基本的toString分析
            if (!added) {
                addPointsToTypes(pts, targetSet);
            }
        } catch (Exception e) {
            logger.debug("使用PAG分析时出错: {}", e.getMessage());
            // 如果PAG分析失败，回退到基本分析
            addPointsToTypes(pts, targetSet);
        }
    }

    /**
     * 通过反射获取PointsToSet内部的分配节点
     */
    private boolean tryGetAllocationNodesViaReflection(PointsToSet pts, Set<String> targetSet) {
        try {
            // 尝试反射获取pts的内部结构
            // 注意: 这依赖于Soot的内部实现，可能会随版本变化而不可用
            String ptsClassName = pts.getClass().getName();

            // 尝试获取内部节点集合
            java.lang.reflect.Method method = null;
            Object nodeCollection = null;

            // 针对不同的PointsToSet实现，尝试不同的方法
            if (ptsClassName.contains("HybridPointsToSet") ||
                    ptsClassName.contains("DoublePointsToSet")) {
                // 尝试获取内部的nodeSet
                try {
                    method = pts.getClass().getMethod("getOldSet");
                    if (method != null) {
                        nodeCollection = method.invoke(pts);
                    }
                } catch (Exception e) {
                    // 如果getOldSet失败，尝试其他方法
                    try {
                        method = pts.getClass().getMethod("getNodes");
                        if (method != null) {
                            nodeCollection = method.invoke(pts);
                        }
                    } catch (Exception e2) {
                        // 忽略
                    }
                }
            } else if (ptsClassName.contains("PointsToSetInternal")) {
                // 尝试直接转换为Collection
                try {
                    if (pts instanceof Collection) {
                        nodeCollection = pts;
                    }
                } catch (Exception e) {
                    // 忽略
                }
            }

            // 如果找到了节点集合，遍历并提取信息
            if (nodeCollection != null) {
                if (nodeCollection instanceof Collection) {
                    Collection<?> nodes = (Collection<?>) nodeCollection;
                    for (Object node : nodes) {
                        if (node != null) {
                            // 处理AllocNode
                            if (node instanceof AllocNode) {
                                addAllocationNodeInfo((AllocNode) node, targetSet);
                            } else {
                                // 其他类型的节点
                                String nodeInfo = node.toString();
                                if (nodeInfo != null &&
                                        !nodeInfo.contains("Exception") &&
                                        !nodeInfo.contains("Error") &&
                                        !nodeInfo.contains("Throwable") &&
                                        !nodeInfo.contains("Stack")) {

                                    targetSet.add("Node: " + formatNodeInfo(nodeInfo));
                                }
                            }
                        }
                    }
                    return !nodes.isEmpty();
                }
            }
        } catch (Exception e) {
            logger.debug("通过反射获取分配节点失败: {}", e.getMessage());
        }
        return false;
    }

    /**
     * 格式化节点信息
     */
    private String formatNodeInfo(String nodeInfo) {
        if (nodeInfo == null) {
            return "null";
        }

        // 裁剪过长的信息
        if (nodeInfo.length() > 100) {
            return nodeInfo.substring(0, 97) + "...";
        }
        return nodeInfo;
    }

    /**
     * 添加分配节点的详细信息
     */
    private void addAllocationNodeInfo(AllocNode allocNode, Set<String> targetSet) {
        if (allocNode == null) {
            return;
        }

        try {
            // 获取分配点的新表达式
            Object newExpr = allocNode.getNewExpr();
            String allocInfo = null;

            if (newExpr instanceof NewExpr) {
                // 普通对象创建
                NewExpr ne = (NewExpr) newExpr;
                SootClass allocClass = ((RefType) ne.getType()).getSootClass();
                SootMethod method = allocNode.getMethod();

                // 过滤掉异常和堆栈相关的对象
                String className = allocClass.getName();
                if (className.contains("Exception") ||
                        className.contains("Error") ||
                        className.contains("Throwable") ||
                        className.contains("Stack")) {
                    return;
                }

                allocInfo = "Object: " + className;
                if (method != null) {
                    allocInfo += " created in " + method.getDeclaringClass().getShortName() + "." + method.getName();
                }
            } else if (newExpr instanceof NewArrayExpr) {
                // 数组创建
                NewArrayExpr nae = (NewArrayExpr) newExpr;
                SootMethod method = allocNode.getMethod();
                String typeName = nae.getBaseType().toString();

                // 过滤掉异常和堆栈相关的数组
                if (typeName.contains("Exception") ||
                        typeName.contains("Error") ||
                        typeName.contains("Throwable") ||
                        typeName.contains("Stack")) {
                    return;
                }

                allocInfo = "Array: " + typeName + "[]";
                if (method != null) {
                    allocInfo += " created in " + method.getDeclaringClass().getShortName() + "." + method.getName();
                }
            } else if (newExpr instanceof StringConstant) {
                // 字符串常量
                StringConstant sc = (StringConstant) newExpr;
                String value = sc.value;
                if (value.length() > 30) {
                    value = value.substring(0, 27) + "...";
                }
                allocInfo = "String: \"" + value + "\"";
            } else if (newExpr instanceof ClassConstant) {
                // 类常量
                ClassConstant cc = (ClassConstant) newExpr;
                allocInfo = "Class: " + cc.getValue();
            } else if (newExpr != null) {
                // 其他类型的分配点
                allocInfo = "Allocation: " + newExpr.toString();
                if (allocInfo.length() > 100) {
                    allocInfo = allocInfo.substring(0, 97) + "...";
                }
            }

            if (allocInfo != null) {
                targetSet.add(allocInfo);
            }
        } catch (Exception e) {
            logger.debug("处理分配节点时出错: {}", e.getMessage());
        }
    }

    /**
     * 基本方法：添加指向类型到集合
     * 改进为收集具体对象信息而不仅仅是类型
     */
    private int addPointsToTypes(PointsToSet pts, Set<String> targetSet) {
        int count = 0;
        if (pts == null) {
            return count;
        }

        try {
            // 获取分配对象的信息
            // 首先尝试直接使用toString()获取原始信息，处理为更友好的格式
            String ptsStr = pts.toString();
            if (ptsStr != null && !ptsStr.isEmpty() && !ptsStr.equals("{}")) {
                // 移除花括号，分离各个对象
                ptsStr = ptsStr.replaceAll("[{}]", "");
                String[] objects = ptsStr.split(",");

                for (String objStr : objects) {
                    objStr = objStr.trim();
                    if (!objStr.isEmpty()) {
                        // 过滤掉异常和堆栈相关的对象
                        if (!objStr.contains("Exception") &&
                                !objStr.contains("Error") &&
                                !objStr.contains("Throwable") &&
                                !objStr.contains("Stack")) {

                            // 格式化对象信息
                            String formattedInfo = formatObjectInfo(objStr);
                            targetSet.add(formattedInfo);
                            count++;
                        }
                    }
                }
            }

            // 如果无法从toString获取信息，则使用类型信息作为备份
            if (count == 0) {
                for (Type type : pts.possibleTypes()) {
                    if (type instanceof RefType) {
                        String typeName = ((RefType) type).getClassName();

                        // 过滤掉异常和堆栈相关的类型
                        if (!typeName.contains("Exception") &&
                                !typeName.contains("Error") &&
                                !typeName.contains("Throwable") &&
                                !typeName.contains("Stack")) {

                            targetSet.add("Type: " + typeName);
                            count++;
                        }
                    } else if (type instanceof ArrayType) {
                        String typeName = type.toString();

                        // 过滤掉异常和堆栈相关的数组类型
                        if (!typeName.contains("Exception") &&
                                !typeName.contains("Error") &&
                                !typeName.contains("Throwable") &&
                                !typeName.contains("Stack")) {

                            targetSet.add("ArrayType: " + typeName);
                            count++;
                        }
                    }
                }
            }
        } catch (Exception e) {
            logger.debug("处理指向集合时出错: {}", e.getMessage());
        }

        return count;
    }

    /**
     * 格式化对象信息为更易读的形式
     */
    private String formatObjectInfo(String objStr) {
        if (objStr == null) {
            return "null";
        }

        try {
            // 尝试提取更有用的信息
            if (objStr.contains("NewExpr")) {
                // 对于新创建的对象，提取对象类型和创建位置
                int typeStart = objStr.indexOf("(");
                int typeEnd = objStr.indexOf(")");
                if (typeStart >= 0 && typeEnd > typeStart) {
                    String type = objStr.substring(typeStart + 1, typeEnd);

                    // 查找创建位置
                    int locStart = objStr.indexOf("in ");
                    String location = "";
                    if (locStart >= 0) {
                        location = " at " + objStr.substring(locStart);
                    }

                    return "Object: " + type + location;
                }
            } else if (objStr.contains("StringConstant")) {
                // 对于字符串常量，提取字符串值
                int valueStart = objStr.indexOf("value:");
                if (valueStart >= 0) {
                    String value = objStr.substring(valueStart + 6).trim();
                    // 截断过长的字符串
                    if (value.length() > 30) {
                        value = value.substring(0, 27) + "...";
                    }
                    return "String: \"" + value + "\"";
                }
            } else if (objStr.contains("ClassConstant")) {
                // 对于类常量，提取类名
                int valueStart = objStr.indexOf("value:");
                if (valueStart >= 0) {
                    String value = objStr.substring(valueStart + 6).trim();
                    return "Class: " + value;
                }
            } else if (objStr.contains("Alloc")) {
                // 对于一般的分配点
                if (objStr.contains("type:")) {
                    int typeStart = objStr.indexOf("type:");
                    int typeEnd = objStr.indexOf(",", typeStart);
                    if (typeStart >= 0 && (typeEnd > typeStart || typeEnd == -1)) {
                        String type = typeEnd > typeStart
                                ? objStr.substring(typeStart + 5, typeEnd).trim()
                                : objStr.substring(typeStart + 5).trim();

                        // 查找创建位置
                        String location = "";
                        int methodStart = objStr.indexOf("method:");
                        if (methodStart >= 0) {
                            int methodEnd = objStr.indexOf(")", methodStart);
                            if (methodEnd > methodStart) {
                                location = " in " + objStr.substring(methodStart + 7, methodEnd + 1);
                            }
                        }

                        return "Allocated: " + type + location;
                    }
                }
            }

            // 尝试从字符串中提取有用的信息
            if (objStr.contains("@")) {
                // 可能是对象的哈希码引用
                int atIndex = objStr.indexOf("@");
                if (atIndex > 0) {
                    String type = objStr.substring(0, atIndex).trim();
                    return "Instance: " + type;
                }
            }

            // 如果无法提取特定信息，返回裁剪过的原始字符串
            if (objStr.length() > 100) {
                return objStr.substring(0, 97) + "...";
            }
            return objStr;
        } catch (Exception e) {
            logger.debug("获取对象信息时出错: {}", e.getMessage());
            return objStr;
        }
    }

    /**
     * 判断类是否是系统类（应该被排除的类）
     */
    private boolean isExcludedClass(String className) {
        if (className == null) {
            return true;
        }

        // 检查是否是系统类
        for (String excludePattern : getExcludeList()) {
            if (excludePattern.endsWith("*")) {
                String prefix = excludePattern.substring(0, excludePattern.length() - 1);
                if (className.startsWith(prefix)) {
                    return true;
                }
            } else if (className.equals(excludePattern)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 获取源文件名
     */
    private String getSourceFile(SootClass sootClass) {
        if (sootClass.hasTag("SourceFileTag")) {
            SourceFileTag sourceFileTag = (SourceFileTag) sootClass.getTag("SourceFileTag");
            return sourceFileTag.getSourceFile();
        }
        return null;
    }

    /**
     * 获取字段的行号
     */
    private int getLineNumber(SootField field) {
        if (field.hasTag("LineNumberTag")) {
            LineNumberTag lineNumberTag = (LineNumberTag) field.getTag("LineNumberTag");
            return lineNumberTag.getLineNumber();
        }
        return -1;
    }

    /**
     * 获取方法的行号
     */
    private int getLineNumber(SootMethod method) {
        if (method.hasTag("LineNumberTag")) {
            LineNumberTag lineNumberTag = (LineNumberTag) method.getTag("LineNumberTag");
            return lineNumberTag.getLineNumber();
        }

        // 如果方法上没有行号标签，尝试从方法体的第一条语句获取
        if (method.hasActiveBody()) {
            Body body = method.getActiveBody();
            if (!body.getUnits().isEmpty()) {
                Unit firstUnit = body.getUnits().getFirst();
                return getLineNumber(firstUnit);
            }
        }

        return -1;
    }

    /**
     * 获取语句的行号
     */
    private int getLineNumber(Unit unit) {
        if (unit.hasTag("LineNumberTag")) {
            LineNumberTag lineNumberTag = (LineNumberTag) unit.getTag("LineNumberTag");
            return lineNumberTag.getLineNumber();
        }
        return -1;
    }

    /**
     * 获取程序入口点
     */
    private List<SootMethod> getEntryPoints() {
        List<SootMethod> entryPoints = new ArrayList<>();

        // 遍历所有应用类寻找可能的入口点
        for (SootClass sootClass : Scene.v().getApplicationClasses()) {
            if (sootClass.isPhantom()) {
                continue;
            }

            // 查找main方法
            if (sootClass.declaresMethodByName("main")) {
                try {
                    SootMethod mainMethod = sootClass.getMethodByName("main");
                    if (mainMethod.isPublic() && mainMethod.isStatic()) {
                        entryPoints.add(mainMethod);
                        logger.debug("找到入口点: {}", mainMethod.getSignature());
                    }
                } catch (Exception e) {
                    logger.warn("处理main方法时出错: {}", e.getMessage());
                }
            }

            // 查找无参构造函数
            if (!sootClass.isInterface() && !sootClass.isAbstract()) {
                for (SootMethod method : sootClass.getMethods()) {
                    if (method.isConstructor() && method.getParameterCount() == 0) {
                        entryPoints.add(method);
                        logger.debug("找到入口点（构造函数）: {}", method.getSignature());
                    }
                }
            }

            // 查找公共方法
            for (SootMethod method : sootClass.getMethods()) {
                if (method.isPublic() && !method.isAbstract() && !method.isConstructor()) {
                    entryPoints.add(method);
                    logger.debug("找到入口点（公共方法）: {}", method.getSignature());
                }
            }
        }

        if (entryPoints.isEmpty()) {
            logger.warn("没有找到入口点，使用默认入口点");
            // 使用Soot的默认入口点
            entryPoints.addAll(EntryPoints.v().all());
        }

        return entryPoints;
    }

    /**
     * 保存索引结果
     */
    private void saveIndexResults() {
        logger.info("保存索引结果...");

        try {
            Gson gson = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

            // 创建结果目录
            Path indexDir = Paths.get(outputPath, "index");
            if (!Files.exists(indexDir)) {
                Files.createDirectories(indexDir);
            }

            // 保存方法定义索引
            String methodDefsJson = gson.toJson(methodDefinitions);
            Files.write(Paths.get(indexDir.toString(), "method_definitions.json"), methodDefsJson.getBytes());

            // 保存方法调用索引
            String methodInvocsJson = gson.toJson(methodInvocations);
            Files.write(Paths.get(indexDir.toString(), "method_invocations.json"), methodInvocsJson.getBytes());

            // 保存字段定义索引
            String fieldDefsJson = gson.toJson(fieldDefinitions);
            Files.write(Paths.get(indexDir.toString(), "field_definitions.json"), fieldDefsJson.getBytes());

            // 保存字段引用索引
            String fieldRefsJson = gson.toJson(fieldReferences);
            Files.write(Paths.get(indexDir.toString(), "field_references.json"), fieldRefsJson.getBytes());

            logger.info("索引结果已保存到：{}", indexDir);
        } catch (IOException e) {
            logger.error("保存索引结果失败：{}", e.getMessage());
        }
    }

    /**
     * 保存指针分析结果
     */
    private void savePointsToAnalysisResults() {
        logger.info("保存指针分析结果...");

        try {
            Gson gson = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();

            // 创建结果对象
            JsonObject resultsObject = new JsonObject();

            // 添加局部变量指向分析结果
            JsonObject localsObject = gson.toJsonTree(pointsToLocals).getAsJsonObject();
            resultsObject.add("locals", localsObject);

            // 添加实例字段指向分析结果
            JsonObject instanceFieldsObject = gson.toJsonTree(pointsToInstanceFields).getAsJsonObject();
            resultsObject.add("instanceFields", instanceFieldsObject);

            // 添加静态字段指向分析结果
            JsonObject staticFieldsObject = gson.toJsonTree(pointsToStaticFields).getAsJsonObject();
            resultsObject.add("staticFields", staticFieldsObject);

            // 添加数组指向分析结果
            JsonObject arraysObject = gson.toJsonTree(pointsToArrays).getAsJsonObject();
            resultsObject.add("arrays", arraysObject);

            // 写入文件
            String json = gson.toJson(resultsObject);
            Path filePath = Paths.get(outputPath, "points_to_analysis.json");
            Files.write(filePath, json.getBytes());

            logger.info("指针分析结果已保存到：{}", filePath);
        } catch (IOException e) {
            logger.error("保存指针分析结果失败：{}", e.getMessage());
        }
    }

    /**
     * 从方法体中提取原始变量名
     */
    private Map<Local, String> extractOriginalVariableNames(Body body) {
        Map<Local, String> nameMapping = new HashMap<>();

        // 由于Soot可能不提供直接访问Local标签的API，使用简单的映射并返回原始变量名
        // 根据需要可以实现更复杂的变量名映射逻辑
        for (Local local : body.getLocals()) {
            nameMapping.put(local, local.getName());
        }

        return nameMapping;
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

        cliOptions.addOption(Option.builder("p")
                .longOpt("points-to")
                .desc("执行指针分析")
                .build());

        cliOptions.addOption(Option.builder("h")
                .longOpt("help")
                .desc("显示帮助信息")
                .build());

        CommandLineParser parser = new DefaultParser();
        HelpFormatter formatter = new HelpFormatter();

        // 先检查是否有帮助选项
        try {
            CommandLine cmd = parser.parse(new org.apache.commons.cli.Options().addOption("h", "help", false, ""), args, true);
            if (cmd.hasOption('h')) {
                formatter.printHelp("SootCodeAnalyzer", cliOptions);
                return;
            }
        } catch (ParseException e) {
            // 忽略，继续解析完整选项
        }

        try {
            // 解析完整命令行参数
            CommandLine cmd = parser.parse(cliOptions, args);

            String targetPath = cmd.getOptionValue("t");
            String outputPath = cmd.getOptionValue("o");

            // 创建分析器
            SootCodeAnalyzer analyzer = new SootCodeAnalyzer(targetPath, outputPath);

            // 设置选项
            analyzer.setGenerateCallGraph(cmd.hasOption("c"));
            analyzer.setGenerateJimple(cmd.hasOption("j"));
            analyzer.setGenerateIndex(cmd.hasOption("i"));
            analyzer.setGeneratePointsToAnalysis(cmd.hasOption("p"));

            // 执行分析
            analyzer.analyze();

        } catch (ParseException e) {
            System.err.println("解析命令行参数出错：" + e.getMessage());
            formatter.printHelp("SootCodeAnalyzer", cliOptions);
        }
    }

    /**
     * 设置是否生成调用图
     */
    public void setGenerateCallGraph(boolean generateCallGraph) {
        this.generateCallGraph = generateCallGraph;
    }

    /**
     * 设置是否生成Jimple IR
     */
    public void setGenerateJimple(boolean generateJimple) {
        this.generateJimple = generateJimple;
    }

    /**
     * 设置是否生成代码索引
     */
    public void setGenerateIndex(boolean generateIndex) {
        this.generateIndex = generateIndex;
    }

    /**
     * 设置是否执行指针分析
     */
    public void setGeneratePointsToAnalysis(boolean generatePointsToAnalysis) {
        this.generatePointsToAnalysis = generatePointsToAnalysis;
    }
}
