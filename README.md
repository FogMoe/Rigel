# Rigel

一个功能丰富的Telegram AI聊天机器人，允许用户使用自己的OpenAI API密钥进行AI聊天。

## 功能特点

- 支持用户使用自己的OpenAI API密钥
- 完整的聊天历史记录和上下文管理
- 多语言支持（中文、英文等）
- 用户自定义AI参数（模型、温度等）
- 多线程并发安全
- 数据库存储用户信息和聊天记录
- 简单易用的命令系统

## 安装

1. 克隆仓库
```bash
git clone https://github.com/scarletkc/rigel.git
cd rigel
```

2. 创建虚拟环境并安装依赖
```bash
python -m venv .venv
source .venv/bin/activate 
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
```
编辑`.env`文件，添加您的Telegram机器人令牌。

## 获取Telegram机器人令牌

1. 在Telegram中搜索[@BotFather](https://t.me/BotFather)
2. 发送`/newbot`命令
3. 按照指示设置机器人名称和用户名
4. 获取API令牌并复制到`.env`文件中

## 运行机器人

```bash
python main.py
```

## 使用方法

机器人支持以下命令：

- `/start` - 开始使用机器人
- `/setapi` - 设置OpenAI API密钥
- `/reset` - 重置当前对话
- `/params` - 查看或修改AI参数
- `/setlang` - 设置语言
- `/help` - 显示帮助信息

### 设置API密钥

1. 发送`/setapi`命令
2. 输入您的OpenAI API密钥
3. 机器人将验证API密钥并保存

### 修改AI参数

发送`/params`命令查看当前参数。

修改参数格式：`/params [参数名] [值]`

例如：
- `/params model gpt-4`
- `/params temperature 0.8`

### 更改语言

发送`/setlang`命令，然后从列表中选择语言。

## 数据存储

用户数据、API密钥和聊天记录存储在本地SQLite数据库中，位于`data/telegrambot.db`。

## 贡献

欢迎提交问题和拉取请求。

## 许可证

[GPL-3.0 license](LICENSE)
