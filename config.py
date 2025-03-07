from typing import Dict, Any

# 支持的语言
SUPPORTED_LANGUAGES = ['zh', 'en', 'ru', 'es', 'fr', 'de', 'ja', 'ko']
DEFAULT_LANGUAGE = 'zh'

# 默认AI模型参数
DEFAULT_AI_PARAMS = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
}

# 多语言提示文本
MESSAGES: Dict[str, Dict[str, str]] = {
    "zh": {
        "welcome": "欢迎使用AI聊天机器人！请使用 /setapi 命令设置您的API密钥。",
        "api_request": "请输入您的OpenAI API密钥:",
        "api_set_success": "API密钥设置成功！现在您可以开始聊天了。",
        "api_invalid": "API密钥无效，请重新设置。",
        "chat_start": "AI聊天已开始，您可以随时发送消息。使用 /help 查看更多命令。",
        "chat_reset": "聊天历史已重置。",
        "help_message": """
可用命令列表:
/start - 开始使用机器人
/setapi - 设置OpenAI API密钥
/reset - 重置当前对话
/params - 查看或修改AI参数
/setlang - 设置语言
/help - 显示帮助信息
        """,
        "params_current": "当前AI参数设置:\n{params}",
        "params_usage": "/params [参数名] [值] - 修改AI参数\n可用参数: model, temperature, max_tokens, top_p, frequency_penalty, presence_penalty",
        "params_set_success": "参数 {param} 已更新为 {value}",
        "params_invalid": "无效的参数或值。",
        "language_set": "语言已设置为中文。",
        "language_prompt": "请选择语言:",
        "processing": "正在处理您的请求...",
        "error": "发生错误: {error}",
    },
    "en": {
        "welcome": "Welcome to the AI Chat Bot! Please use the /setapi command to set your API key.",
        "api_request": "Please enter your OpenAI API key:",
        "api_set_success": "API key set successfully! You can now start chatting.",
        "api_invalid": "Invalid API key, please set it again.",
        "chat_start": "AI chat started, you can send messages anytime. Use /help to see more commands.",
        "chat_reset": "Chat history has been reset.",
        "help_message": """
Available commands:
/start - Start using the bot
/setapi - Set OpenAI API key
/reset - Reset current conversation
/params - View or modify AI parameters
/setlang - Set language
/help - Show help information
        """,
        "params_current": "Current AI parameters:\n{params}",
        "params_usage": "/params [parameter] [value] - Modify AI parameters\nAvailable parameters: model, temperature, max_tokens, top_p, frequency_penalty, presence_penalty",
        "params_set_success": "Parameter {param} has been updated to {value}",
        "params_invalid": "Invalid parameter or value.",
        "language_set": "Language set to English.",
        "language_prompt": "Please select a language:",
        "processing": "Processing your request...",
        "error": "An error occurred: {error}",
    },
    # 其他语言可以根据需要添加
}

# 为不存在的语言提供默认值
def get_message(lang: str, key: str, **kwargs) -> str:
    """
    获取指定语言的消息，如果不存在则返回英文消息
    """
    if lang not in MESSAGES:
        lang = DEFAULT_LANGUAGE
    
    if key not in MESSAGES[lang]:
        # 如果特定语言中不存在该消息，使用英文
        message = MESSAGES["en"].get(key, f"Message '{key}' not found")
    else:
        message = MESSAGES[lang][key]
    
    # 替换参数
    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError:
            pass
    
    return message 