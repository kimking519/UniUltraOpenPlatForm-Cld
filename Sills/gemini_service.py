"""
Gemini AI 服务模块
用于邮件智能回复建议等功能
"""
import os
from google import genai
from google.genai import types

# 模型ID
MODEL_ID = "gemini-2.0-flash"

_client = None

def get_gemini_client():
    """获取 Gemini 客户端（单例）"""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        _client = genai.Client(api_key=api_key)
    return _client

def is_gemini_configured() -> bool:
    """检查 Gemini API Key 是否已配置"""
    return bool(os.environ.get("GEMINI_API_KEY"))

def set_gemini_api_key(api_key: str) -> bool:
    """
    设置 Gemini API Key 到环境变量

    Args:
        api_key: Gemini API Key

    Returns:
        是否设置成功
    """
    try:
        # 设置到当前进程环境变量
        os.environ["GEMINI_API_KEY"] = api_key

        # 重置客户端，下次使用时会重新初始化
        global _client
        _client = None

        return True
    except Exception as e:
        print(f"Set Gemini API Key error: {e}")
        return False

def set_gemini_api_key_permanent(api_key: str) -> dict:
    """
    永久设置 Gemini API Key 到系统环境变量

    Args:
        api_key: Gemini API Key

    Returns:
        {"windows": bool, "wsl": bool} 表示各平台是否设置成功
    """
    import platform
    import subprocess

    result = {"windows": False, "wsl": False, "message": ""}

    # 先设置到当前进程
    os.environ["GEMINI_API_KEY"] = api_key
    global _client
    _client = None

    # 检测当前环境
    is_wsl = False
    if platform.system() == 'Linux':
        try:
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    is_wsl = True
        except:
            pass

    if platform.system() == 'Windows' or is_wsl:
        # Windows 环境
        try:
            # 使用 PowerShell 设置用户级环境变量
            ps_cmd = f'[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "{api_key}", "User")'
            subprocess.run(
                ["powershell", "-Command", ps_cmd],
                check=True,
                capture_output=True
            )
            result["windows"] = True
        except Exception as e:
            result["message"] += f"Windows 设置失败: {str(e)}\n"

        # 如果是 WSL，同时设置到 WSL 环境
        if is_wsl:
            try:
                # 写入 ~/.bashrc
                bashrc_path = os.path.expanduser("~/.bashrc")
                export_line = f'export GEMINI_API_KEY="{api_key}"\n'

                # 检查是否已存在
                existing = False
                if os.path.exists(bashrc_path):
                    with open(bashrc_path, 'r') as f:
                        content = f.read()
                        if 'GEMINI_API_KEY' in content:
                            existing = True

                if not existing:
                    with open(bashrc_path, 'a') as f:
                        f.write(f'\n# Gemini API Key\n{export_line}')
                result["wsl"] = True
            except Exception as e:
                result["message"] += f"WSL 设置失败: {str(e)}\n"

    return result

def get_gemini_api_key() -> str:
    """获取当前配置的 Gemini API Key（部分隐藏）"""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key and len(api_key) > 8:
        return api_key[:4] + "****" + api_key[-4:]
    return api_key

def suggest_email_reply(
    email_content: str,
    user_instruction: str,
    sender_name: str = "",
    email_subject: str = ""
) -> dict:
    """
    根据邮件内容和用户指示生成回复建议

    Args:
        email_content: 原邮件内容
        user_instruction: 用户想要回复的内容/方向
        sender_name: 发件人名称
        email_subject: 邮件主题

    Returns:
        {"success": bool, "reply": str, "error": str}
    """
    client = get_gemini_client()
    if not client:
        return {"success": False, "error": "Gemini API Key 未配置"}

    try:
        # 构建系统提示
        system_instruction = """你是一个专业的邮件回复助手。请根据用户的指示和原邮件内容，生成一封专业、礼貌的邮件回复。

要求：
1. 回复内容要简洁明了，直接回应用户想要表达的内容
2. 语气要专业、礼貌
3. 不要添加多余的开头语如"以下是回复建议"等
4. 直接输出邮件正文内容，不需要主题"""

        # 构建用户提示
        prompt = f"""请帮我撰写一封邮件回复。

原邮件主题：{email_subject}
发件人：{sender_name}

原邮件内容：
---
{email_content[:3000]}
---

我的回复意图：
{user_instruction}

请生成邮件回复内容："""

        # 配置生成参数
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=1000,
            temperature=0.7,
        )

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=config
        )

        return {
            "success": True,
            "reply": response.text,
            "usage": {
                "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

def analyze_email(email_content: str) -> dict:
    """
    分析邮件内容

    Args:
        email_content: 邮件内容

    Returns:
        {"success": bool, "analysis": str, "error": str}
    """
    client = get_gemini_client()
    if not client:
        return {"success": False, "error": "Gemini API Key 未配置"}

    try:
        system_instruction = """你是一个邮件分析助手。请分析邮件内容并提取以下信息：
1. 邮件主题/目的
2. 关键信息点
3. 是否需要回复
4. 建议的回复方向

请用简洁的中文回答。"""

        prompt = f"请分析以下邮件内容：\n\n{email_content[:3000]}"

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=500,
            temperature=0.3,
        )

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=config
        )

        return {
            "success": True,
            "analysis": response.text
        }

    except Exception as e:
        return {"success": False, "error": str(e)}