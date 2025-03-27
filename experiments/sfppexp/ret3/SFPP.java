import java.util.HashMap;
import java.util.Map;

public class SFPP {
    public static void main(String[] args) {
        // 创建一个配置管理器
        ConfigManager configManager = new ConfigManager();
        
        // 加载配置
        configManager.loadConfig();
        
        // 获取配置并使用
        // 这里静态分析工具可能会误报，因为它们可能无法识别loadConfig方法确保了configs不为null
        String value = configManager.getConfig("key");
        System.out.println("Config value: " + value);
    }
}

class ConfigManager {
    private Map<String, String> configs;
    
    public void loadConfig() {
        // 初始化配置
        configs = new HashMap<>();
        configs.put("key", "value");
    }
    
    public String getConfig(String key) {
        // 静态分析工具可能会误报这里的configs可能为null
        // 但实际上，在正常使用流程中，loadConfig会在getConfig之前调用
        return configs.get(key);
    }
}