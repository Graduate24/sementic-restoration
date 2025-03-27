import java.util.HashMap;
import java.util.Map;

public class SFPP {
    public static void main(String[] args) {
        // 创建一个配置管理器
        ConfigManager configManager = new ConfigManager();
        
        // 加载配置
        configManager.loadConfig("app.properties");
        
        // 获取配置项
        String value = configManager.getConfig("database.url");
        
        // 使用配置值
        if (value != null && value.startsWith("jdbc:")) {
            System.out.println("Valid database URL: " + value);
        } else {
            System.out.println("Invalid or missing database URL");
        }
    }
}

class ConfigManager {
    private Map<String, String> configMap;
    
    public ConfigManager() {
        configMap = new HashMap<>();
    }
    
    public void loadConfig(String filename) {
        // 模拟从文件加载配置
        // 实际应用中会从文件读取
        configMap.put("database.url", "jdbc:mysql://localhost:3306/mydb");
        configMap.put("database.user", "admin");
    }
    
    public String getConfig(String key) {
        return configMap.get(key);
    }
}