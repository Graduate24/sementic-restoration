import java.util.HashMap;
import java.util.Map;

public class SFPP {
    public static void main(String[] args) {
        // 创建一个配置管理器
        ConfigManager configManager = new ConfigManager();
        
        // 加载配置
        configManager.loadConfig();
        
        // 获取配置并使用
        String value = configManager.getConfig("key");
        System.out.println("Config value: " + value);
        
        // 更新配置
        configManager.updateConfig("key", "new_value");
    }
}

class ConfigManager {
    private Map<String, String> configMap;
    
    public ConfigManager() {
        // 在构造函数中初始化configMap
        configMap = new HashMap<>();
        // 添加一些默认配置
        configMap.put("key", "default_value");
    }
    
    public void loadConfig() {
        // 模拟从外部加载配置
        configMap.put("loaded_key", "loaded_value");
    }
    
    public String getConfig(String key) {
        // 直接访问configMap，因为构造函数已确保其初始化
        return configMap.get(key);
    }
    
    public void updateConfig(String key, String value) {
        // 更新配置
        configMap.put(key, value);
    }
}