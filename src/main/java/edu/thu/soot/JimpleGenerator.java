package edu.thu.soot;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import soot.*;
import soot.options.Options;
import soot.tagkit.LineNumberTag;
import soot.tagkit.SourceFileTag;
import soot.tagkit.Tag;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Pattern;

/**
 * Jimple IR生成工具
 * 将Java源代码转换为Jimple中间表示，并保存文件结构
 */
public class JimpleGenerator {
    private static final Logger logger = LoggerFactory.getLogger(JimpleGenerator.class);
    
    private final String sourcePath;
    private final String outputPath;
    private final List<String> includePatterns = new ArrayList<>();
    private final List<String> excludePatterns = new ArrayList<>();
    private boolean preserveLineNumbers = true;
    private boolean annotateJimple = true;  // 为Jimple添加注释，包括原始源代码行
    
    /**
     * 创建Jimple生成器
     * 
     * @param sourcePath 源代码路径
     * @param outputPath 输出路径
     */
    public JimpleGenerator(String sourcePath, String outputPath) {
        this.sourcePath = sourcePath;
        this.outputPath = outputPath;
    }
    
    /**
     * 添加包含模式
     * 
     * @param pattern 包含模式（例如："com.example.*"）
     */
    public void addIncludePattern(String pattern) {
        includePatterns.add(pattern.replace(".", "\\.").replace("*", ".*"));
    }
    
    /**
     * 添加排除模式
     * 
     * @param pattern 排除模式（例如："com.example.util.*"）
     */
    public void addExcludePattern(String pattern) {
        excludePatterns.add(pattern.replace(".", "\\.").replace("*", ".*"));
    }
    
    /**
     * 设置是否保留行号
     * 
     * @param preserveLineNumbers 是否保留行号
     */
    public void setPreserveLineNumbers(boolean preserveLineNumbers) {
        this.preserveLineNumbers = preserveLineNumbers;
    }
    
    /**
     * 设置是否为Jimple添加注释
     * 
     * @param annotateJimple 是否添加注释
     */
    public void setAnnotateJimple(boolean annotateJimple) {
        this.annotateJimple = annotateJimple;
    }
    
    /**
     * 生成Jimple IR
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
            
            // 应用转换
            PackManager.v().runPacks();
            
            // 处理类并生成Jimple
            processClasses();
            
            logger.info("Jimple生成完成");
            return true;
            
        } catch (Exception e) {
            logger.error("生成Jimple时出错: " + e.getMessage(), e);
            return false;
        }
    }
    
    /**
     * 配置Soot
     */
    private void configureSoot() {
        G.reset();
        
        // 设置Soot选项
        Options.v().set_prepend_classpath(true);
        Options.v().set_allow_phantom_refs(true);
        Options.v().set_keep_line_number(preserveLineNumbers);
        Options.v().set_src_prec(Options.src_prec_java);
        Options.v().set_output_format(Options.output_format_jimple);
        
        // 处理路径
        List<String> processDirs = Collections.singletonList(sourcePath);
        Options.v().set_process_dir(processDirs);
        
        // 设置输出目录
        Options.v().set_output_dir(outputPath);
        
        // 排除标准库
        List<String> excludeList = Arrays.asList(
            "java.*", "javax.*", "sun.*", "com.sun.*", "jdk.*", "org.xml.*"
        );
        Options.v().set_exclude(excludeList);
    }
    
    /**
     * 处理所有类并生成Jimple
     */
    private void processClasses() throws IOException {
        logger.info("处理应用类并生成Jimple...");
        
        // 创建输出目录
        Path outputDir = Paths.get(outputPath);
        if (!Files.exists(outputDir)) {
            Files.createDirectories(outputDir);
        }
        
        // 收集所有源文件内容，用于注释
        Map<String, List<String>> sourceFiles = new HashMap<>();
        if (annotateJimple) {
            collectSourceFiles(sourceFiles, new File(sourcePath));
        }
        
        int classCount = 0;
        
        // 处理所有应用类
        for (SootClass sootClass : Scene.v().getApplicationClasses()) {
            if (shouldProcessClass(sootClass)) {
                processClass(sootClass, sourceFiles);
                classCount++;
            }
        }
        
        logger.info("已生成 {} 个类的Jimple代码", classCount);
    }
    
    /**
     * 判断是否应该处理该类
     */
    private boolean shouldProcessClass(SootClass sootClass) {
        if (sootClass.isPhantom()) {
            return false;
        }
        
        String className = sootClass.getName();
        
        // 检查是否匹配包含模式
        if (!includePatterns.isEmpty()) {
            boolean included = false;
            for (String pattern : includePatterns) {
                if (Pattern.matches(pattern, className)) {
                    included = true;
                    break;
                }
            }
            if (!included) {
                return false;
            }
        }
        
        // 检查是否匹配排除模式
        for (String pattern : excludePatterns) {
            if (Pattern.matches(pattern, className)) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * 处理单个类并生成Jimple
     */
    private void processClass(SootClass sootClass, Map<String, List<String>> sourceFiles) throws IOException {
        String className = sootClass.getName();
        logger.debug("处理类：{}", className);
        
        // 获取源文件信息
        SourceFileTag sourceFileTag = (SourceFileTag) sootClass.getTag("SourceFileTag");
        String sourceFileName = sourceFileTag != null ? sourceFileTag.getSourceFile() : null;
        List<String> sourceLines = sourceFileName != null ? sourceFiles.get(sourceFileName) : null;
        
        // 为每个方法生成注释后的Jimple
        for (SootMethod method : sootClass.getMethods()) {
            if (!method.hasActiveBody()) {
                try {
                    method.retrieveActiveBody();
                } catch (Exception e) {
                    logger.warn("无法获取方法体: {}.{}", className, method.getName());
                    continue;
                }
            }
            
            // 生成方法的Jimple代码
            Body body = method.getActiveBody();
            String jimple = annotateJimple ? annotateJimpleWithSource(body, sourceLines) : body.toString();
            
            // 保存Jimple文件
            String outputFile = outputPath + "/" + className.replace(".", "/") + "_" + method.getName() + ".jimple";
            File file = new File(outputFile);
            file.getParentFile().mkdirs();
            
            try (FileWriter writer = new FileWriter(file)) {
                writer.write(jimple);
            }
        }
    }
    
    /**
     * 收集源文件内容
     */
    private void collectSourceFiles(Map<String, List<String>> sourceFiles, File directory) {
        if (!directory.exists()) {
            return;
        }
        
        File[] files = directory.listFiles();
        if (files == null) {
            return;
        }
        
        for (File file : files) {
            if (file.isDirectory()) {
                collectSourceFiles(sourceFiles, file);
            } else if (file.getName().endsWith(".java")) {
                try {
                    List<String> lines = Files.readAllLines(file.toPath());
                    sourceFiles.put(file.getName(), lines);
                } catch (IOException e) {
                    logger.warn("无法读取源文件: {}", file.getPath());
                }
            }
        }
    }
    
    /**
     * 为Jimple添加源代码注释
     */
    private String annotateJimpleWithSource(Body body, List<String> sourceLines) {
        if (sourceLines == null) {
            return body.toString();
        }
        
        StringBuilder jimple = new StringBuilder();
        jimple.append("// Method: ").append(body.getMethod().getSignature()).append("\n");
        
        // 获取方法声明和语句
        String bodyText = body.toString();
        String[] lines = bodyText.split("\n");
        
        for (String line : lines) {
            // 查找行号标记
            int lineNumber = -1;
            
            if (line.contains("/*")) {
                int start = line.indexOf("/*");
                int end = line.indexOf("*/", start);
                if (end > start) {
                    String lineTag = line.substring(start + 2, end).trim();
                    try {
                        lineNumber = Integer.parseInt(lineTag);
                    } catch (NumberFormatException e) {
                        // 非行号注释
                    }
                }
            }
            
            // 如果找到行号，添加源代码行作为注释
            if (lineNumber > 0 && lineNumber <= sourceLines.size()) {
                String sourceLine = sourceLines.get(lineNumber - 1).trim();
                if (!sourceLine.isEmpty()) {
                    jimple.append("// Source: ").append(sourceLine).append("\n");
                }
            }
            
            jimple.append(line).append("\n");
        }
        
        return jimple.toString();
    }
    
    /**
     * 主方法
     */
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("用法: java JimpleGenerator <源代码路径> <输出路径> [包含模式...] [-e 排除模式...]");
            System.out.println("  包含模式: 类名匹配模式，支持通配符 *");
            System.out.println("  排除模式: 在 -e 后指定要排除的类名匹配模式");
            return;
        }
        
        String sourcePath = args[0];
        String outputPath = args[1];
        
        JimpleGenerator generator = new JimpleGenerator(sourcePath, outputPath);
        
        // 解析包含和排除模式
        boolean excludeMode = false;
        for (int i = 2; i < args.length; i++) {
            if (args[i].equals("-e")) {
                excludeMode = true;
                continue;
            }
            
            if (excludeMode) {
                generator.addExcludePattern(args[i]);
            } else {
                generator.addIncludePattern(args[i]);
            }
        }
        
        // 生成Jimple代码
        boolean success = generator.generate();
        System.exit(success ? 0 : 1);
    }
} 