#!/usr/bin/env python
import asyncio
import logging
import os
import json
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from ai_service import AIService
from config import DEFAULT_AI_PARAMS, SUPPORTED_LANGUAGES, get_message
from database import DatabaseManager
from session_manager import SessionManager, UserState

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 获取Telegram机器人令牌
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("请在.env文件中设置TELEGRAM_TOKEN环境变量")
    exit(1)

# 初始化全局管理器
db_manager = DatabaseManager()
session_manager = SessionManager()

# 命令处理函数
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/start命令"""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # 在数据库中创建或获取用户
    db_manager.get_or_create_user(
        telegram_id=telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )
    
    # 获取用户语言
    lang = db_manager.get_language(telegram_id)
    
    # 发送欢迎消息
    await update.message.reply_text(get_message(lang, "welcome"))
    
    # 检查用户是否已设置API密钥
    api_key = db_manager.get_api_key(telegram_id)
    if not api_key:
        # 提示用户设置API密钥
        await update.message.reply_text(get_message(lang, "api_request"))
        # 更新用户状态
        session = session_manager.get_user_session(telegram_id)
        session.set_state(UserState.WAITING_API_KEY)
    else:
        # 创建新对话
        conversation_id = session_manager.create_conversation(telegram_id)
        if conversation_id:
            # 发送开始聊天消息
            await update.message.reply_text(get_message(lang, "chat_start"))
            # 更新用户状态
            session = session_manager.get_user_session(telegram_id)
            session.set_state(UserState.CHATTING)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/help命令"""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # 获取用户语言
    lang = db_manager.get_language(telegram_id)
    
    # 发送帮助消息
    await update.message.reply_text(get_message(lang, "help_message"))

async def setapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/setapi命令"""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # 获取用户语言
    lang = db_manager.get_language(telegram_id)
    
    # 提示用户输入API密钥
    await update.message.reply_text(get_message(lang, "api_request"))
    
    # 更新用户状态
    session = session_manager.get_user_session(telegram_id)
    session.set_state(UserState.WAITING_API_KEY)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/reset命令，重置当前对话"""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # 获取用户语言
    lang = db_manager.get_language(telegram_id)
    
    # 创建新对话
    conversation_id = session_manager.create_conversation(telegram_id)
    if conversation_id:
        # 发送重置消息
        await update.message.reply_text(get_message(lang, "chat_reset"))
        # 更新用户状态
        session = session_manager.get_user_session(telegram_id)
        session.set_state(UserState.CHATTING)

async def params_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/params命令，查看或修改AI参数"""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # 获取用户语言
    lang = db_manager.get_language(telegram_id)
    
    # 获取命令参数
    args = context.args
    
    if not args:
        # 没有参数，显示当前设置和使用说明
        user_settings = db_manager.get_user_settings(telegram_id)
        if user_settings:
            params = user_settings.get_ai_params()
            params_str = json.dumps(params, indent=2)
            await update.message.reply_text(
                get_message(lang, "params_current", params=params_str) + "\n\n" +
                get_message(lang, "params_usage")
            )
        else:
            await update.message.reply_text(get_message(lang, "params_usage"))
    elif len(args) >= 2:
        # 有参数，尝试修改指定参数
        param = args[0]
        value = args[1]
        
        # 更新参数
        success = db_manager.set_user_param(telegram_id, param, value)
        if success:
            await update.message.reply_text(
                get_message(lang, "params_set_success", param=param, value=value)
            )
        else:
            await update.message.reply_text(get_message(lang, "params_invalid"))
    else:
        # 参数不足
        await update.message.reply_text(get_message(lang, "params_usage"))

async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/setlang命令，设置用户语言"""
    user = update.effective_user
    telegram_id = str(user.id)
    
    # 创建语言选择按钮
    keyboard = []
    row = []
    for i, lang_code in enumerate(SUPPORTED_LANGUAGES):
        row.append(InlineKeyboardButton(lang_code, callback_data=f"lang_{lang_code}"))
        if (i + 1) % 3 == 0 or i == len(SUPPORTED_LANGUAGES) - 1:
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 获取用户当前语言
    lang = db_manager.get_language(telegram_id)
    
    # 发送语言选择消息
    await update.message.reply_text(
        get_message(lang, "language_prompt"),
        reply_markup=reply_markup
    )
    
    # 更新用户状态
    session = session_manager.get_user_session(telegram_id)
    session.set_state(UserState.SELECTING_LANGUAGE)

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理语言选择回调"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    telegram_id = str(user.id)
    
    # 解析选择的语言代码
    callback_data = query.data
    if callback_data.startswith("lang_"):
        lang_code = callback_data[5:]
        
        # 更新用户语言
        db_manager.set_language(telegram_id, lang_code)
        
        # 获取新语言的提示
        await query.edit_message_text(get_message(lang_code, "language_set"))
        
        # 将用户状态设为IDLE
        session = session_manager.get_user_session(telegram_id)
        session.set_state(UserState.IDLE)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户消息"""
    user = update.effective_user
    telegram_id = str(user.id)
    message_text = update.message.text
    
    # 获取用户会话和状态
    session = session_manager.get_user_session(telegram_id)
    state = session.get_state()
    
    # 获取用户语言
    lang = db_manager.get_language(telegram_id)
    
    # 根据用户状态处理消息
    if state == UserState.WAITING_API_KEY:
        # 处理API密钥设置
        api_key = message_text.strip()
        
        # 发送处理中消息
        processing_message = await update.message.reply_text(get_message(lang, "processing"))
        
        # 验证API密钥
        ai_service = AIService()
        is_valid = await ai_service.validate_api_key(api_key)
        
        if is_valid:
            # 保存API密钥
            db_manager.set_api_key(telegram_id, api_key)
            # 更新AI服务
            session_manager.update_ai_service(telegram_id, api_key)
            # 创建新对话
            conversation_id = session_manager.create_conversation(telegram_id)
            # 更新用户状态
            session.set_state(UserState.CHATTING)
            # 发送成功消息
            await processing_message.edit_text(get_message(lang, "api_set_success"))
        else:
            # 发送失败消息
            await processing_message.edit_text(get_message(lang, "api_invalid"))
    
    elif state == UserState.WAITING_PARAM_VALUE:
        # 处理参数值设置
        param = session.get_temp_data("param")
        value = message_text.strip()
        
        # 更新参数
        success = db_manager.set_user_param(telegram_id, param, value)
        if success:
            await update.message.reply_text(
                get_message(lang, "params_set_success", param=param, value=value)
            )
        else:
            await update.message.reply_text(get_message(lang, "params_invalid"))
        
        # 重置状态
        session.set_state(UserState.IDLE)
        session.clear_temp_data()
    
    elif state == UserState.CHATTING or state == UserState.IDLE:
        # 处理聊天消息
        # 如果用户状态是IDLE，转为CHATTING
        if state == UserState.IDLE:
            # 创建新对话
            conversation_id = session_manager.create_conversation(telegram_id)
            if not conversation_id:
                await update.message.reply_text(get_message(lang, "error", error="无法创建对话"))
                return
            session.set_state(UserState.CHATTING)
        
        conversation_id = session.get_conversation_id()
        if not conversation_id:
            # 创建新对话
            conversation_id = session_manager.create_conversation(telegram_id)
            if not conversation_id:
                await update.message.reply_text(get_message(lang, "error", error="无法创建对话"))
                return
            session.set_conversation_id(conversation_id)
        
        # 发送处理中消息
        processing_message = await update.message.reply_text(get_message(lang, "processing"))
        
        # 将用户消息保存到数据库
        db_manager.add_message(conversation_id, "user", message_text)
        
        # 获取对话历史
        messages = db_manager.get_conversation_messages(conversation_id)
        
        # 获取用户设置
        user_settings = db_manager.get_user_settings(telegram_id)
        ai_params = None
        if user_settings:
            ai_params = user_settings.get_ai_params()
        
        # 获取AI服务
        ai_service = session_manager.get_ai_service(telegram_id)
        
        # 发送请求到AI服务
        response = await ai_service.chat_completion(messages, ai_params)
        
        # 保存AI响应到数据库
        db_manager.add_message(conversation_id, "assistant", response)
        
        # 更新处理中消息为AI响应
        await processing_message.edit_text(response)
    
    # 其他状态不处理

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理错误"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # 如果更新有效，尝试向用户发送错误消息
    if update and update.effective_user:
        user = update.effective_user
        telegram_id = str(user.id)
        
        # 获取用户语言
        lang = db_manager.get_language(telegram_id)
        
        # 发送错误消息
        error_message = get_message(lang, "error", error=str(context.error))
        
        if update.effective_message:
            await update.effective_message.reply_text(error_message)

def main() -> None:
    """启动机器人"""
    # 创建应用
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 添加命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setapi", setapi_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("params", params_command))
    application.add_handler(CommandHandler("setlang", setlang_command))
    
    # 添加回调查询处理器
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^lang_"))
    
    # 添加消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 添加错误处理器
    application.add_error_handler(error_handler)
    
    # 启动机器人
    application.run_polling()

if __name__ == "__main__":
    main()
