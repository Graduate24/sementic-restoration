import java.util.*;
import java.io.*;
import soot.*;
import soot.jimple.InstanceFieldRef;
import soot.jimple.StaticFieldRef;
import soot.jimple.spark.pag.Node;
import soot.jimple.spark.pag.PAG;
import soot.jimple.spark.pag.AllocNode;
import soot.jimple.spark.sets.P2SetVisitor;
import soot.options.Options;
import soot.PointsToAnalysis;
import soot.PointsToSet;
import soot.util.Chain;
import java.util.*;
import java.io.*;

public class Test1 {

    public static void main(String[] args) {
        // 1. 重置 Soot 并设置基本参数
        G.reset();
        Options.v().set_prepend_classpath(true);
        Options.v().set_allow_phantom_refs(true);
        // 设置待分析的项目目录（支持class文件或jar包），请修改为你的项目路径
        Options.v().set_process_dir(Collections.singletonList("/home/ran/Documents/work/graduate/BenchmarkJava/annotated-benchmark/target/classes"));
        Options.v().set_whole_program(true);

        // 2. 增加 Spark 指针分析配置
        Options.v().setPhaseOption("cg.spark", "on");
        Options.v().setPhaseOption("cg.spark", "verbose");
        Options.v().setPhaseOption("cg.spark", "set-impl:double");
        // 添加更多高级配置
        Options.v().setPhaseOption("cg.spark", "field-based:false");
        Options.v().setPhaseOption("cg.spark", "types-for-sites:true");
        Options.v().setPhaseOption("cg.spark", "merge-stringbuffer:true");
        Options.v().setPhaseOption("cg.spark", "string-constants:true");
        Options.v().setPhaseOption("cg.spark", "simulate-natives:true");
        Options.v().setPhaseOption("cg.spark", "empties-as-allocs:true");

        // 载入必要类并运行分析 Pack
        Scene.v().loadNecessaryClasses();
        PackManager.v().runPacks();

        // 获取指针分析结果
        PointsToAnalysis pta = Scene.v().getPointsToAnalysis();
        
        // 尝试获取Spark的PAG（指针赋值图）以获取更详细的分配点信息
        PAG pag = null;
        try {
            if (pta.getClass().getName().contains("SPARK")) {
                java.lang.reflect.Method pagMethod = pta.getClass().getMethod("getPag");
                Object pagObj = pagMethod.invoke(pta);
                if (pagObj instanceof PAG) {
                    pag = (PAG) pagObj;
                    System.out.println("成功获取PAG，可以提供更详细的指针信息");
                }
            }
        } catch (Exception e) {
            System.out.println("无法获取PAG: " + e.getMessage());
        }

        // 定义存储结果的 Map，按照"局部变量"、"实例字段"、"静态字段"分类保存，
        // key中包含方法签名以保留原始变量名上下文信息
        Map<String, Map<String, List<String>>> analysisResult = new HashMap<>();
        Map<String, List<String>> localsMap = new HashMap<>();
        Map<String, List<String>> instanceFieldsMap = new HashMap<>();
        Map<String, List<String>> staticFieldsMap = new HashMap<>();

        // 遍历所有应用类及其方法
        for (SootClass sc : Scene.v().getApplicationClasses()) {
            for (SootMethod method : sc.getMethods()) {
                if (!method.isConcrete())
                    continue;
                Body body = method.retrieveActiveBody();

                // 分析局部变量：保留原始变量名
                for (Local local : body.getLocals()) {
                    // 过滤掉临时栈变量
                    String localName = local.getName();
                    if (localName.startsWith("$stack") || localName.startsWith("$r") || 
                        localName.startsWith("$i") || localName.startsWith("$z") ||
                        localName.startsWith("$b") || localName.startsWith("$d") ||
                        localName.startsWith("$f") || localName.startsWith("$l")) {
                        continue; // 跳过临时变量
                    }
                    
                    // 过滤掉异常类型变量
                    String localType = local.getType().toString();
                    if (isExceptionType(localType)) {
                        continue; // 跳过异常类型
                    }
                    
                    PointsToSet pts = pta.reachingObjects(local);
                    List<String> ptsList = getPointsToInfo(pts, pag);
                    
                    // 检查结果是否为空或只包含JDK内部类
                    if (ptsList.isEmpty() || onlyContainsJdkClasses(ptsList)) {
                        continue; // 跳过没有有用信息的变量
                    }
                    
                    // 用"方法签名 - Local:变量名"作为 key
                    String key = method.getSignature() + " - Local: " + local.getName();
                    localsMap.put(key, ptsList);
                }

                // 遍历方法中所有表达式，检测实例字段和静态字段引用
                for (Unit unit : body.getUnits()) {
                    for (ValueBox vb : unit.getUseAndDefBoxes()) {
                        Value v = vb.getValue();
                        if (v instanceof InstanceFieldRef) {
                            InstanceFieldRef ifr = (InstanceFieldRef) v;
                            // 过滤掉异常类型的字段
                            if (isExceptionType(ifr.getField().getType().toString())) {
                                continue;
                            }
                            
                            // 修复bug：先获取基对象的指向集合，再获取字段指向的对象
                            Value base = ifr.getBase();
                            PointsToSet basePoints = null;
                            // 基对象可能是Local或其他表达式
                            if (base instanceof Local) {
                                basePoints = pta.reachingObjects((Local) base);
                            } else {
                                // 如果不是Local，无法直接分析，跳过
                                System.err.println("基对象不是Local，无法分析: " + ifr);
                                continue;
                            }
                            
                            if (basePoints == null || basePoints.isEmpty()) {
                                // 基对象没有指向关系，跳过
                                continue;
                            }
                            
                            PointsToSet pts = pta.reachingObjects(basePoints, ifr.getField());
                            List<String> ptsList = getPointsToInfo(pts, pag);
                            
                            // 过滤结果
                            if (ptsList.isEmpty() || onlyContainsJdkClasses(ptsList)) {
                                continue; // 跳过没有有用信息的字段
                            }
                            
                            // key格式：方法签名 - InstanceField: [base].[fieldName]
                            String key = method.getSignature() + " - InstanceField: "
                                    + ifr.getBase() + "." + ifr.getField().getName();
                            instanceFieldsMap.put(key, ptsList);
                        } else if (v instanceof StaticFieldRef) {
                            StaticFieldRef sfr = (StaticFieldRef) v;
                            // 过滤掉异常类型的字段
                            if (isExceptionType(sfr.getField().getType().toString())) {
                                continue;
                            }
                            
                            // 修复bug：直接使用字段而非字段引用
                            PointsToSet pts = pta.reachingObjects(sfr.getField());
                            List<String> ptsList = getPointsToInfo(pts, pag);
                            
                            // 过滤结果
                            if (ptsList.isEmpty() || onlyContainsJdkClasses(ptsList)) {
                                continue; // 跳过没有有用信息的字段
                            }
                            
                            // key格式：方法签名 - StaticField: [declaringClass].[fieldName]
                            String key = method.getSignature() + " - StaticField: "
                                    + sfr.getField().getDeclaringClass().getName() + "." + sfr.getField().getName();
                            staticFieldsMap.put(key, ptsList);
                        }
                    }
                }
            }
        }

        analysisResult.put("locals", localsMap);
        analysisResult.put("instanceFields", instanceFieldsMap);
        analysisResult.put("staticFields", staticFieldsMap);

        // 输出结果
        System.out.println("\n===== 指针分析结果 =====");
        int totalVars = 0;
        for (Map.Entry<String, Map<String, List<String>>> category : analysisResult.entrySet()) {
            String categoryName = category.getKey();
            Map<String, List<String>> itemsMap = category.getValue();
            totalVars += itemsMap.size();
            
            System.out.println("\n***** 类别: " + categoryName + " (" + itemsMap.size() + "项) *****");
            
            // 按字母顺序排序输出
            List<String> sortedKeys = new ArrayList<>(itemsMap.keySet());
            Collections.sort(sortedKeys);
            
            for (String key : sortedKeys) {
                List<String> pointsToInfo = itemsMap.get(key);
                System.out.println("\n\t" + key + " 指向: ");
                for (String info : pointsToInfo) {
                    System.out.println("\t\t- " + info);
                }
            }
        }
        System.out.println("\n===== 总计: " + totalVars + " 个变量/字段被分析 =====");
    }

    /**
     * 从PointsToSet中提取详细信息，使用PAG获取更精确的分配点信息
     */
    private static List<String> getPointsToInfo(PointsToSet pts, PAG pag) {
        List<String> ptsList = new ArrayList<>();
        
        if (pts == null || pts.isEmpty()) {
            ptsList.add("空集合");
            return ptsList;
        }
        
        // 获取包含的非JDK类型信息（只关注用户代码）
        try {
            Set<Type> types = pts.possibleTypes();
            if (types != null && !types.isEmpty()) {
                for (Type t : types) {
                    String typeStr = t.toString();
                    
                    // 过滤JDK内部类和异常类型
                    if (isJdkInternalClass(typeStr) || isExceptionType(typeStr)) {
                        continue;
                    }
                    
                    // 过滤掉Object或Any_subtype标记
                    if (typeStr.contains("java.lang.Object") || typeStr.contains("Any_subtype")) {
                        continue;
                    }
                    
                    if (t instanceof RefType) {
                        RefType refType = (RefType) t;
                        ptsList.add("类型: " + refType.getClassName());
                    } else if (t instanceof ArrayType) {
                        ArrayType arrayType = (ArrayType) t;
                        Type elemType = arrayType.getElementType();
                        
                        // 只添加非JDK数组类型
                        if (!isJdkInternalClass(elemType.toString()) && !isExceptionType(elemType.toString())) {
                            ptsList.add("数组类型: " + arrayType.toString());
                        }
                    }
                }
            }
        } catch (Exception e) {
            // 忽略类型分析异常
        }
        
        // 如果已经获取到非JDK类型，直接返回
        if (!ptsList.isEmpty()) {
            return ptsList;
        }
        
        // 尝试使用PAG获取分配点信息（重点关注用户代码的分配点）
        if (pag != null) {
            try {
                final List<AllocNode> userAllocNodes = new ArrayList<>();
                
                // 获取所有分配节点
                if (pts.getClass().getName().contains("spark")) {
                    java.lang.reflect.Method forallMethod = pts.getClass().getMethod("forall", P2SetVisitor.class);
                    
                    P2SetVisitor visitor = new P2SetVisitor() {
                        @Override
                        public void visit(Node n) {
                            if (n instanceof AllocNode) {
                                AllocNode allocNode = (AllocNode) n;
                                SootMethod method = allocNode.getMethod();
                                
                                // 只保留非JDK类且非异常类的分配节点
                                if (method != null) {
                                    String className = method.getDeclaringClass().getName();
                                    Type type = allocNode.getType();
                                    
                                    if (!isJdkInternalClass(className) && !isExceptionType(type.toString())) {
                                        userAllocNodes.add(allocNode);
                                    }
                                }
                            }
                        }
                    };
                    
                    forallMethod.invoke(pts, visitor);
                    
                    // 限制最多显示5个分配点，避免输出过多
                    int nodesToShow = Math.min(userAllocNodes.size(), 5);
                    
                    // 提取用户代码的分配点信息
                    for (int i = 0; i < nodesToShow; i++) {
                        AllocNode allocNode = userAllocNodes.get(i);
                        Type type = allocNode.getType();
                        SootMethod method = allocNode.getMethod();
                        
                        // 只关注用户代码中的分配
                        String allocInfo = null;
                        if (method != null) {
                            String className = method.getDeclaringClass().getName();
                            if (!isJdkInternalClass(className) && !isExceptionType(className)) {
                                allocInfo = "在 " + className + 
                                           "." + method.getName() + " 中分配对象";
                                ptsList.add(allocInfo);
                            }
                        }
                    }
                    
                    // 如果还有更多节点未显示，添加提示信息
                    if (userAllocNodes.size() > 5) {
                        ptsList.add("... 还有 " + (userAllocNodes.size() - 5) + " 个分配点未显示");
                    }
                }
            } catch (Exception e) {
                // 忽略PAG分析异常
            }
        }
        
        // 如果找不到任何用户代码相关信息
        if (ptsList.isEmpty()) {
            // 尝试获取非JDK类型信息
            boolean hasUserType = false;
            for (Type t : pts.possibleTypes()) {
                String typeStr = t.toString();
                
                // 过滤JDK内部类和异常类型，但接受java.lang.String等常用类
                if (isCommonUsefulType(typeStr) && !isExceptionType(typeStr)) {
                    if (t instanceof RefType) {
                        ptsList.add("类型: " + ((RefType) t).getClassName());
                        hasUserType = true;
                    } else if (t instanceof ArrayType) {
                        ptsList.add("数组类型: " + t.toString());
                        hasUserType = true;
                    }
                }
            }
            
            // 如果还是没有找到有用信息，只提供简单的提示
            if (!hasUserType) {
                // 检查是否包含Object类型
                boolean hasObjectType = false;
                for (Type t : pts.possibleTypes()) {
                    if (t.toString().contains("java.lang.Object")) {
                        hasObjectType = true;
                        break;
                    }
                }
                
                if (hasObjectType) {
                    ptsList.add("指向一个未知的对象");
                } else {
                    ptsList.add("无确定的指向信息");
                }
            }
        }
        
        return ptsList;
    }
    
    /**
     * 检查是否是JDK内部类
     */
    private static boolean isJdkInternalClass(String className) {
        return className.startsWith("java.") || 
               className.startsWith("javax.") ||
               className.startsWith("sun.") ||
               className.startsWith("com.sun.") ||
               className.startsWith("jdk.") ||
               className.startsWith("org.w3c.") ||
               className.startsWith("org.xml.");
    }
    
    /**
     * 检查是否是常用的有用类型
     */
    private static boolean isCommonUsefulType(String typeName) {
        // 常用的Java类
        if (typeName.equals("java.lang.String") ||
            typeName.equals("java.lang.Integer") ||
            typeName.equals("java.lang.Boolean") ||
            typeName.equals("java.lang.Long") ||
            typeName.equals("java.lang.Double") ||
            typeName.equals("java.lang.Float") ||
            typeName.equals("java.util.ArrayList") ||
            typeName.equals("java.util.HashMap") ||
            typeName.equals("java.util.List") ||
            typeName.equals("java.util.Map")) {
            return true;
        }
        
        // 用户自定义类
        return !isJdkInternalClass(typeName);
    }

    /**
     * 检查点集合是否只包含JDK内部类
     */
    private static boolean onlyContainsJdkClasses(List<String> ptsList) {
        if (ptsList.isEmpty()) {
            return true;
        }
        
        for (String info : ptsList) {
            // 检查是否包含用户类（非JDK内部类）
            if (!info.contains("java.") && !info.contains("javax.") &&
                !info.contains("sun.") && !info.contains("com.sun.") &&
                !info.contains("jdk.") && !info.contains("org.w3c.") &&
                !info.contains("org.xml.") && !info.contains("Empty") &&
                !info.contains("空集合") && !info.contains("无法确定")) {
                return false; // 包含非JDK类
            }
        }
        
        return true; // 只包含JDK类
    }

    /**
     * 检查是否是异常类型
     */
    private static boolean isExceptionType(String typeName) {
        return typeName.contains("Exception") || 
               typeName.contains("Error") || 
               typeName.contains("Throwable");
    }

}

