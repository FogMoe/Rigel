import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

from config import DEFAULT_AI_PARAMS, DEFAULT_LANGUAGE

# 创建数据库目录
os.makedirs('data', exist_ok=True)

# 创建数据库引擎
engine = create_engine('sqlite:///data/telegrambot.db', 
                      poolclass=QueuePool,
                      connect_args={'check_same_thread': False},
                      pool_size=20,
                      max_overflow=0)

# 创建会话工厂
session_factory = sessionmaker(bind=engine)
# 创建线程安全的会话
Session = scoped_session(session_factory)

# 声明基类
Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    language_code = Column(String(10), default=DEFAULT_LANGUAGE)
    api_key = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    user_settings = relationship("UserSettings", uselist=False, back_populates="user", cascade="all, delete-orphan")
    
    def __init__(self, telegram_id, username=None, first_name=None, last_name=None, language_code=DEFAULT_LANGUAGE):
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.language_code = language_code
        self.user_settings = UserSettings()

class UserSettings(Base):
    """用户设置模型"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    ai_params = Column(Text, default=json.dumps(DEFAULT_AI_PARAMS))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="user_settings")
    
    def get_ai_params(self) -> Dict[str, Any]:
        """获取AI参数"""
        return json.loads(self.ai_params)
    
    def set_ai_params(self, params: Dict[str, Any]) -> None:
        """设置AI参数"""
        current_params = self.get_ai_params()
        current_params.update(params)
        self.ai_params = json.dumps(current_params)
    
    def set_param(self, param: str, value: Any) -> bool:
        """设置单个参数"""
        params = self.get_ai_params()
        if param not in params:
            return False
        
        # 类型转换
        if param == "model":
            value = str(value)
        elif param in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
            try:
                value = float(value)
            except ValueError:
                return False
        elif param == "max_tokens":
            try:
                value = int(value)
            except ValueError:
                return False
        else:
            return False
        
        params[param] = value
        self.ai_params = json.dumps(params)
        return True

class Conversation(Base):
    """对话模型"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.timestamp")
    
    def add_message(self, role: str, content: str) -> 'Message':
        """添加消息到对话"""
        message = Message(conversation_id=self.id, role=role, content=content)
        return message
    
    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """获取适用于OpenAI API的消息格式"""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

class Message(Base):
    """消息模型"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    role = Column(String(20))  # 'system', 'user', 或 'assistant'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")


# 创建数据库表
def init_db():
    Base.metadata.create_all(engine)


# 数据库操作函数
class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance
    
    def __init__(self):
        if not self.initialized:
            init_db()
            self.initialized = True
    
    def get_session(self):
        """获取线程安全的会话"""
        return Session()
    
    def close_session(self, session):
        """关闭会话"""
        session.close()
        Session.remove()
    
    def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None, language_code=None):
        """获取或创建用户"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code or DEFAULT_LANGUAGE
                )
                session.add(user)
                session.commit()
            return user
        finally:
            self.close_session(session)
    
    def set_api_key(self, telegram_id, api_key):
        """设置用户API密钥"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.api_key = api_key
                session.commit()
                return True
            return False
        finally:
            self.close_session(session)
    
    def get_api_key(self, telegram_id) -> Optional[str]:
        """获取用户API密钥"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            return user.api_key if user else None
        finally:
            self.close_session(session)
    
    def create_conversation(self, telegram_id):
        """创建新对话"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                conversation = Conversation(user_id=user.id)
                session.add(conversation)
                session.commit()
                return conversation.id
            return None
        finally:
            self.close_session(session)
    
    def add_message(self, conversation_id, role, content):
        """添加消息"""
        session = self.get_session()
        try:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                message = Message(conversation_id=conversation_id, role=role, content=content)
                session.add(message)
                session.commit()
                return True
            return False
        finally:
            self.close_session(session)
    
    def get_conversation_messages(self, conversation_id):
        """获取对话消息"""
        session = self.get_session()
        try:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                return conversation.get_messages_for_api()
            return []
        finally:
            self.close_session(session)
    
    def get_user_settings(self, telegram_id):
        """获取用户设置"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user and user.user_settings:
                return user.user_settings
            return None
        finally:
            self.close_session(session)
    
    def set_user_param(self, telegram_id, param, value):
        """设置用户参数"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user and user.user_settings:
                result = user.user_settings.set_param(param, value)
                if result:
                    session.commit()
                return result
            return False
        finally:
            self.close_session(session)
    
    def set_language(self, telegram_id, language_code):
        """设置用户语言"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.language_code = language_code
                session.commit()
                return True
            return False
        finally:
            self.close_session(session)
    
    def get_language(self, telegram_id):
        """获取用户语言"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            return user.language_code if user else DEFAULT_LANGUAGE
        finally:
            self.close_session(session) 