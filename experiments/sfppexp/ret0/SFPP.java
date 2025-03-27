import java.util.HashMap;
import java.util.Map;

public class SFPP {
    public static void main(String[] args) {
        // 创建配置管理器
        ConfigManager configManager = new ConfigManager();
        
        // 加载配置
        configManager.loadConfig();
        
        // 获取配置并使用
        // 这里静态分析工具可能会误报，因为它们无法确定loadConfig方法已经初始化了configs
        String serverUrl = configManager.getConfig("server.url");
        System.out.println("Server URL: " + serverUrl);
        
        int port = Integer.parseInt(configManager.getConfig("server.port"));
        System.out.println("Server Port: " + port);
    }
}

class ConfigManager {
    private Map<String, String> configs;
    
    public void loadConfig() {
        configs = new HashMap<>();
        configs.put("server.url", "http://localhost");
        configs.put("server.port", "8080");
    }
    
    public String getConfig(String key) {
        return configs.get(key);
    }
}