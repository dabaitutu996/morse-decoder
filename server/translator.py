import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DEFAULT_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

SYSTEM_PROMPT = """你是无线电摩斯电码翻译助手。请将摩斯解码后的英文内容翻译成中文。

规则：
1. 保留专业术语和呼号不翻译：CQ, QTH, QRM, QRN, 599, 5NN, DE, K, AR, SK, 以及 BA1AA 等格式的呼号
2. 保留信号报告中的数字不翻译
3. 翻译成自然口语化的中文，不要逐字硬译
4. 如果原文是缩写（如 PSE=please, TNX=thanks, HW=how copy），在括号内补充完整

示例：
输入: CQ CQ CQ DE BA1AA PSE K
输出: 呼叫任意台，呼叫任意台，这里是 BA1AA，请回复

输入: UR RST 599 TU
输出: 你的信号报告 599，谢谢
"""


class DeepSeekTranslator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or DEFAULT_API_KEY
        self.history = []

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    async def translate(self, text: str) -> str:
        if not self.api_key:
            return "[未配置 DeepSeek API Key，无法翻译]"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.history,
            {"role": "user", "content": text},
        ]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 256,
                    },
                )
                response.raise_for_status()
                data = response.json()
                translated = data["choices"][0]["message"]["content"].strip()

                # Keep short history for style consistency
                self.history.append({"role": "user", "content": text})
                self.history.append({"role": "assistant", "content": translated})
                if len(self.history) > 6:
                    self.history = self.history[-6:]

                return translated
        except httpx.HTTPStatusError as e:
            return f"[翻译失败: {e.response.status_code} {e.response.text[:100]}]"
        except Exception as e:
            return f"[翻译错误: {str(e)}]"
