import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

import aiohttp
from openai import AsyncOpenAI, APIError

from config import DEFAULT_AI_PARAMS

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIService:
    """AI服务类，处理与OpenAI API的通信"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = None
        if api_key:
            self.setup_client(api_key)

    def setup_client(self, api_key: str):
        """设置OpenAI客户端"""
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def validate_api_key(self, api_key: str) -> bool:
        """验证API密钥是否有效"""
        try:
            client = AsyncOpenAI(api_key=api_key)
            # 尝试列出模型以验证API密钥
            await client.models.list()
            return True
        except APIError as e:
            logger.error(f"API密钥验证失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"验证API密钥时发生错误: {str(e)}")
            return False
    
    async def chat_completion(self, messages: List[Dict[str, str]], params: Dict[str, Any] = None) -> Optional[str]:
        """
        发送聊天完成请求到OpenAI API
        
        Args:
            messages: 聊天消息列表
            params: 请求参数
            
        Returns:
            生成的响应文本或错误信息
        """
        if not self.client:
            return "API密钥未设置，请使用 /setapi 命令设置您的OpenAI API密钥。"
        
        # 合并默认参数和用户参数
        request_params = DEFAULT_AI_PARAMS.copy()
        if params:
            request_params.update(params)
        
        try:
            response = await self.client.chat.completions.create(
                messages=messages,
                model=request_params.get("model", "gpt-3.5-turbo"),
                temperature=request_params.get("temperature", 0.7),
                max_tokens=request_params.get("max_tokens", 1000),
                top_p=request_params.get("top_p", 1.0),
                frequency_penalty=request_params.get("frequency_penalty", 0.0),
                presence_penalty=request_params.get("presence_penalty", 0.0),
            )
            
            if not response.choices:
                return "AI没有生成响应。"
            
            return response.choices[0].message.content
            
        except APIError as e:
            error_message = f"OpenAI API错误: {str(e)}"
            logger.error(error_message)
            return error_message
        except Exception as e:
            error_message = f"请求处理错误: {str(e)}"
            logger.error(error_message)
            return error_message 