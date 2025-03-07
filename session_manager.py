import json
import logging
import threading
from enum import Enum
from typing import Dict, Any, Optional

from database import DatabaseManager
from ai_service import AIService

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UserState(Enum):
    """用户状态枚举"""
    IDLE = "idle"                # 空闲状态
    WAITING_API_KEY = "waiting_api_key"  # 等待用户输入API密钥
    WAITING_PARAM_VALUE = "waiting_param_value"  # 等待用户输入参数值
    SELECTING_LANGUAGE = "selecting_language"  # 用户正在选择语言
    CHATTING = "chatting"        # 正在聊天状态


class UserSession:
    """用户会话类，存储用户的当前状态和临时数据"""
    
    def __init__(self, telegram_id: str):
        self.telegram_id = telegram_id
        self.state = UserState.IDLE
        self.conversation_id = None
        self.temp_data = {}  # 存储临时数据，如正在设置的参数名称
    
    def set_state(self, state: UserState):
        """设置用户状态"""
        self.state = state
    
    def get_state(self) -> UserState:
        """获取用户状态"""
        return self.state
    
    def set_conversation_id(self, conversation_id: int):
        """设置当前对话ID"""
        self.conversation_id = conversation_id
    
    def get_conversation_id(self) -> Optional[int]:
        """获取当前对话ID"""
        return self.conversation_id
    
    def set_temp_data(self, key: str, value: Any):
        """设置临时数据"""
        self.temp_data[key] = value
    
    def get_temp_data(self, key: str) -> Any:
        """获取临时数据"""
        return self.temp_data.get(key)
    
    def clear_temp_data(self):
        """清除临时数据"""
        self.temp_data.clear()


class SessionManager:
    """会话管理器，管理所有用户会话"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SessionManager, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance
    
    def __init__(self):
        if not self.initialized:
            self.sessions: Dict[str, UserSession] = {}  # 用户会话字典，键为telegram_id
            self.db_manager = DatabaseManager()
            self.ai_services: Dict[str, AIService] = {}  # 用户AI服务字典，键为telegram_id
            self.initialized = True
    
    def get_user_session(self, telegram_id: str) -> UserSession:
        """获取用户会话，如果不存在则创建新会话"""
        if telegram_id not in self.sessions:
            self.sessions[telegram_id] = UserSession(telegram_id)
        return self.sessions[telegram_id]
    
    def get_ai_service(self, telegram_id: str) -> AIService:
        """获取用户AI服务，如果不存在则创建新服务"""
        if telegram_id not in self.ai_services:
            # 从数据库获取API密钥
            api_key = self.db_manager.get_api_key(telegram_id)
            self.ai_services[telegram_id] = AIService(api_key)
        return self.ai_services[telegram_id]
    
    def update_ai_service(self, telegram_id: str, api_key: str):
        """更新用户AI服务的API密钥"""
        if telegram_id in self.ai_services:
            self.ai_services[telegram_id].setup_client(api_key)
        else:
            self.ai_services[telegram_id] = AIService(api_key)
    
    def create_conversation(self, telegram_id: str) -> Optional[int]:
        """为用户创建新对话"""
        conversation_id = self.db_manager.create_conversation(telegram_id)
        if conversation_id:
            session = self.get_user_session(telegram_id)
            session.set_conversation_id(conversation_id)
        return conversation_id 