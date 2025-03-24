package edu.thu.soot;

import org.objectweb.asm.ClassReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.stream.Stream;

/**
 * 使用ASM库获取字段定义行号的工具类
 */
public class FieldLineNumberFinder {
    private static final Logger logger = LoggerFactory.getLogger(FieldLineNumberFinder.class);

    /**
     * 获取字段定义的行号
     * @param classFilePath 类文件路径
     * @param fieldName 字段名称
     * @return 字段定义的行号，如果找不到返回-1
     */
    public static int findFieldLineNumber(String classFilePath, String fieldName) {
        try (FileInputStream fis = new FileInputStream(classFilePath)) {
            ClassReader classReader = new ClassReader(fis);
            FieldLineNumberVisitor visitor = new FieldLineNumberVisitor(fieldName);
            classReader.accept(visitor, 0);
            
            int lineNumber = visitor.getLineNumber();
            if (lineNumber > 0) {
                logger.info("找到字段 {} 的行号: {}", fieldName, lineNumber);
            } else {
                logger.warn("未找到字段 {} 的行号", fieldName);
            }
            return lineNumber;
        } catch (IOException e) {
            logger.error("读取类文件时发生错误: {}", e.getMessage(), e);
            return -1;
        }
    }
    
    /**
     * 递归搜索源代码目录，查找指定类名的源文件
     * @param sourceRoot 源代码根目录
     * @param className 类名（带包名）
     * @return 源文件路径，如果找不到返回null
     */
    public static String findSourceFile(String sourceRoot, String className) {
        // 将类名转换为文件路径
        String relativePath = className.replace('.', '/') + ".java";
        Path sourcePath = Paths.get(sourceRoot, relativePath);
        
        // 首先检查直接路径
        if (Files.exists(sourcePath)) {
            return sourcePath.toString();
        }
        
        // 如果直接路径不存在，则递归搜索
        try (Stream<Path> paths = Files.walk(Paths.get(sourceRoot))) {
            return paths
                .filter(Files::isRegularFile)
                .filter(path -> path.toString().endsWith(className.substring(className.lastIndexOf('.') + 1) + ".java"))
                .map(Path::toString)
                .findFirst()
                .orElse(null);
        } catch (IOException e) {
            logger.error("搜索源文件时发生错误: {}", e.getMessage(), e);
            return null;
        }
    }
    
    /**
     * 根据类文件找到相应的源文件，并查找字段行号
     * @param classFilePath 类文件路径
     * @param fieldName 字段名
     * @param sourceRoot 源代码根目录
     * @return 字段定义的行号，如果找不到返回-1
     */
    public static int findFieldLineNumberFromSource(String classFilePath, String fieldName, String sourceRoot) {
        // 从类文件路径提取类名
        String className = extractClassNameFromPath(classFilePath);
        if (className == null) {
            return -1;
        }
        
        // 查找源文件
        String sourceFilePath = findSourceFile(sourceRoot, className);
        if (sourceFilePath == null) {
            logger.warn("未找到类 {} 的源文件", className);
            return -1;
        }
        
        // 从源文件读取内容并查找字段定义
        try {
            String content = new String(Files.readAllBytes(Paths.get(sourceFilePath)));
            // 简单实现：查找字段名称后跟分号或等号的行
            String[] lines = content.split("\\n");
            for (int i = 0; i < lines.length; i++) {
                String line = lines[i].trim();
                // 匹配字段定义：包含字段名，并且是声明（包含类型）或赋值语句
                if (line.contains(fieldName) && 
                    (line.matches(".*\\s+" + fieldName + "\\s*[;=].*") || 
                     line.matches(".*\\s+" + fieldName + "\\s*;.*"))) {
                    return i + 1; // 行号从1开始
                }
            }
        } catch (IOException e) {
            logger.error("读取源文件时发生错误: {}", e.getMessage(), e);
        }
        
        return -1;
    }
    
    /**
     * 从类文件路径提取类名
     * @param classFilePath 类文件路径
     * @return 类名（带包名）
     */
    private static String extractClassNameFromPath(String classFilePath) {
        File file = new File(classFilePath);
        String fileName = file.getName();
        
        // 检查是否是类文件
        if (!fileName.endsWith(".class")) {
            logger.warn("不是类文件: {}", classFilePath);
            return null;
        }
        
        // 去掉.class后缀
        String className = fileName.substring(0, fileName.length() - 6);
        
        // 尝试从路径中提取包名
        String path = file.getParent();
        if (path != null) {
            // 查找包名的起始位置（通常是在classes或target/classes之后）
            int startIdx = path.indexOf("classes");
            if (startIdx != -1) {
                startIdx = path.indexOf(File.separator, startIdx) + 1;
                String packagePath = path.substring(startIdx).replace(File.separatorChar, '.');
                if (!packagePath.isEmpty()) {
                    className = packagePath + "." + className;
                }
            }
        }
        
        return className;
    }
    
    /**
     * 使用示例
     */
    public static void main(String[] args) {
        if (args.length < 3) {
            System.out.println("用法: java FieldLineNumberFinder <类文件路径> <字段名> <源代码根目录>");
            return;
        }
        
        String classFilePath = args[0];
        String fieldName = args[1];
        String sourceRoot = args[2];
        
        int lineNumber = findFieldLineNumberFromSource(classFilePath, fieldName, sourceRoot);
        System.out.println("字段 " + fieldName + " 的行号: " + lineNumber);
    }
} 