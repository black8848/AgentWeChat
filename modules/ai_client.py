import sys
from pathlib import Path

from openai import OpenAI

# 添加父目录到path以支持prompts导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from .config_loader import ApiConfig
from prompts.style_templates import get_system_prompt


class AIClient:
    def __init__(self, config: ApiConfig):
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._model = config.model

    def generate_reply(self, message: str, style: str, custom_prompt: str = "") -> str:
        system_prompt = get_system_prompt(style, custom_prompt)
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                max_tokens=256,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"[AI] 生成回复失败: {e}")
            return ""
