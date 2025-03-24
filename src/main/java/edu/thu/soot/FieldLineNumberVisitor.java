package edu.thu.soot;

import org.objectweb.asm.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

/**
 * ASM访问者类，用于获取字段定义的行号
 */
public class FieldLineNumberVisitor extends ClassVisitor {
    private static final Logger logger = LoggerFactory.getLogger(FieldLineNumberVisitor.class);
    
    private final String targetFieldName;
    private int lineNumber = -1;
    private boolean found = false;
    
    // 存储最后访问的行号
    private int lastLineNumber = -1;
    
    // 存储每个字段名对应的行号，为了处理多个字段的情况
    private Map<String, Integer> fieldLineNumbers = new HashMap<>();
    
    // 静态初始化器的访问者，用于捕获静态字段的行号
    private MethodVisitor clinitVisitor = null;
    
    // 构造函数访问者，用于捕获实例字段的行号
    private MethodVisitor initVisitor = null;

    public FieldLineNumberVisitor(String fieldName) {
        super(Opcodes.ASM9);
        this.targetFieldName = fieldName;
    }

    @Override
    public void visit(int version, int access, String name, String signature, String superName, String[] interfaces) {
        super.visit(version, access, name, signature, superName, interfaces);
    }
    
    @Override
    public FieldVisitor visitField(int access, String name, String descriptor, String signature, Object value) {
        // 记录当前字段的名称，但行号暂时设为-1（将在方法中更新）
        fieldLineNumbers.put(name, -1);
        
        if (name.equals(targetFieldName)) {
            found = true;
            logger.debug("找到目标字段: {}", name);
            
            // 创建一个字段访问者来检测字段的初始值
            return new FieldVisitor(Opcodes.ASM9) {
                @Override
                public void visitEnd() {
                    // 这里我们可以尝试获取字段的行号，但可能不可靠
                    if (lastLineNumber > 0) {
                        lineNumber = lastLineNumber;
                        logger.debug("暂定字段 {} 的行号为 {}", name, lineNumber);
                    }
                    super.visitEnd();
                }
            };
        }
        return super.visitField(access, name, descriptor, signature, value);
    }

    @Override
    public MethodVisitor visitMethod(int access, String name, String descriptor, String signature, String[] exceptions) {
        // 处理静态初始化器，可能包含静态字段初始化
        if ("<clinit>".equals(name)) {
            clinitVisitor = new LineNumberTrackingMethodVisitor(Opcodes.ASM9, targetFieldName);
            return clinitVisitor;
        }
        
        // 处理构造函数，可能包含实例字段初始化
        if ("<init>".equals(name)) {
            initVisitor = new LineNumberTrackingMethodVisitor(Opcodes.ASM9, targetFieldName);
            return initVisitor;
        }
        
        // 普通方法，只跟踪行号
        return new MethodVisitor(Opcodes.ASM9) {
            @Override
            public void visitLineNumber(int line, Label start) {
                lastLineNumber = line;
                super.visitLineNumber(line, start);
            }
        };
    }
    
    /**
     * 跟踪行号和字段访问的方法访问者
     */
    private class LineNumberTrackingMethodVisitor extends MethodVisitor {
        private int currentLine = -1;
        private final String targetField;
        
        public LineNumberTrackingMethodVisitor(int api, String targetField) {
            super(api);
            this.targetField = targetField;
        }
        
        @Override
        public void visitLineNumber(int line, Label start) {
            currentLine = line;
            super.visitLineNumber(line, start);
        }
        
        @Override
        public void visitFieldInsn(int opcode, String owner, String name, String descriptor) {
            // 检查是否是PUTFIELD或PUTSTATIC操作，即字段赋值
            if ((opcode == Opcodes.PUTFIELD || opcode == Opcodes.PUTSTATIC) && name.equals(targetField)) {
                // 找到对目标字段的写入操作，记录当前行号
                if (currentLine > 0) {
                    fieldLineNumbers.put(name, currentLine);
                    
                    // 如果是目标字段，更新行号
                    if (name.equals(targetFieldName)) {
                        lineNumber = currentLine;
                        logger.debug("找到字段 {} 的初始化代码在行 {}", name, lineNumber);
                    }
                }
            }
            super.visitFieldInsn(opcode, owner, name, descriptor);
        }
    }

    @Override
    public void visitEnd() {
        super.visitEnd();
        
        // 如果在访问结束时仍然没有找到行号，尝试从初始化方法中获取
        if (lineNumber <= 0 && found) {
            Integer line = fieldLineNumbers.get(targetFieldName);
            if (line != null && line > 0) {
                lineNumber = line;
                logger.debug("从字段初始化中获取字段 {} 的行号: {}", targetFieldName, lineNumber);
            } else if (lastLineNumber > 0) {
                // 最后尝试使用最后一个记录的行号
                lineNumber = lastLineNumber;
                logger.debug("使用最后记录的行号作为字段 {} 的行号: {}", targetFieldName, lineNumber);
            }
        }
    }

    public int getLineNumber() {
        return lineNumber;
    }

    public boolean isFieldFound() {
        return found;
    }
} 