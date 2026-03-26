"""
统一 LLM 客户端：支持 Anthropic、Gemini、DeepSeek、SiliconFlow、Groq。

自动检测优先级（provider="auto"）：
  ANTHROPIC_API_KEY → GEMINI_API_KEY → DEEPSEEK_API_KEY
  → SILICONFLOW_API_KEY → GROQ_API_KEY

默认模型：
  anthropic   → claude-sonnet-4-20250514
  gemini      → gemini-2.0-flash
  deepseek    → deepseek-chat          （DeepSeek-V3，中文最佳）
  siliconflow → deepseek-ai/DeepSeek-V3（注册送额度）
  groq        → llama-3.3-70b-versatile（30 RPM 免费）
"""

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 5

# ── Provider 配置 ──────────────────────────────────────────────

DEFAULT_MODELS = {
    "anthropic":   "claude-sonnet-4-20250514",
    "gemini":      "gemini-2.0-flash",
    "deepseek":    "deepseek-chat",
    "siliconflow": "deepseek-ai/DeepSeek-V3",
    "groq":        "llama-3.3-70b-versatile",
}

# OpenAI 兼容接口的 provider 配置
_OPENAI_COMPAT = {
    "deepseek":    {"base_url": "https://api.deepseek.com/v1",        "env_key": "DEEPSEEK_API_KEY"},
    "siliconflow": {"base_url": "https://api.siliconflow.cn/v1",      "env_key": "SILICONFLOW_API_KEY"},
    "groq":        {"base_url": "https://api.groq.com/openai/v1",     "env_key": "GROQ_API_KEY"},
}

_AUTO_DETECT_ORDER = [
    ("anthropic",   "ANTHROPIC_API_KEY"),
    ("gemini",      "GEMINI_API_KEY"),
    ("deepseek",    "DEEPSEEK_API_KEY"),
    ("siliconflow", "SILICONFLOW_API_KEY"),
    ("groq",        "GROQ_API_KEY"),
]


def resolve_provider(provider: str = "auto") -> tuple[str, str]:
    """返回 (provider_name, api_key)。"""
    if provider == "auto":
        for name, env_key in _AUTO_DETECT_ORDER:
            key = os.environ.get(env_key, "")
            if key:
                return name, key
        keys = " / ".join(k for _, k in _AUTO_DETECT_ORDER)
        raise RuntimeError(
            f"未检测到任何 API Key。请设置以下环境变量之一：\n  {keys}"
        )

    # 显式指定
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("请设置环境变量 ANTHROPIC_API_KEY。")
        return "anthropic", key
    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("请设置环境变量 GEMINI_API_KEY。")
        return "gemini", key
    if provider in _OPENAI_COMPAT:
        env_key = _OPENAI_COMPAT[provider]["env_key"]
        key = os.environ.get(env_key, "")
        if not key:
            raise RuntimeError(f"请设置环境变量 {env_key}。")
        return provider, key

    all_providers = "auto / anthropic / gemini / deepseek / siliconflow / groq"
    raise ValueError(f"未知 provider: {provider}，可选值：{all_providers}")


class LLMClient:
    """
    统一调用接口。

    用法：
        client = LLMClient(provider="auto")
        client = LLMClient(provider="deepseek")
        client = LLMClient(provider="siliconflow", model="Qwen/Qwen2.5-72B-Instruct")
        result = client.call(system="你是...", user="内容...")
    """

    def __init__(self, provider: str = "auto", model: Optional[str] = None):
        self.provider, self.api_key = resolve_provider(provider)
        self.model = model or DEFAULT_MODELS[self.provider]
        self._client = self._build_client()
        logger.info("🤖 LLM Provider: %s | 模型: %s", self.provider, self.model)

    def _build_client(self):
        if self.provider == "anthropic":
            import anthropic
            return anthropic.Anthropic(api_key=self.api_key)
        if self.provider == "gemini":
            from google import genai
            return genai.Client(api_key=self.api_key)
        # OpenAI 兼容 provider 不需要预建 client（用 requests 直接调用）
        return None

    def call(self, system: str, user: str, max_tokens: int = 8192) -> Optional[str]:
        """调用 LLM，带指数退避重试。失败返回 None。"""
        if self.provider == "anthropic":
            return self._call_anthropic(system, user, max_tokens)
        if self.provider == "gemini":
            return self._call_gemini(system, user, max_tokens)
        if self.provider in _OPENAI_COMPAT:
            return self._call_openai_compat(system, user, max_tokens)
        raise ValueError(f"未知 provider: {self.provider}")

    # ── Anthropic ────────────────────────────────────────────

    def _call_anthropic(self, system: str, user: str, max_tokens: int) -> Optional[str]:
        import anthropic
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return resp.content[0].text
            except anthropic.RateLimitError:
                wait = 60 * attempt
                logger.warning("Anthropic 限流，%ds 后重试（%d/%d）...", wait, attempt, MAX_RETRIES)
                time.sleep(wait)
            except anthropic.APIError as exc:
                logger.error("Anthropic API 错误: %s", exc)
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                else:
                    return None
        return None

    # ── Gemini ───────────────────────────────────────────────

    def _call_gemini(self, system: str, user: str, max_tokens: int) -> Optional[str]:
        from google import genai
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        )
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._client.models.generate_content(
                    model=self.model,
                    contents=user,
                    config=config,
                )
                return resp.text
            except Exception as exc:
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                is_rate_limit = status == 429 or "429" in str(exc) or "quota" in str(exc).lower()
                if is_rate_limit:
                    wait = 60 * attempt
                    logger.warning("Gemini 限流（429），%ds 后重试（%d/%d）...", wait, attempt, MAX_RETRIES)
                    time.sleep(wait)
                else:
                    logger.error("Gemini 错误: %s", exc)
                    if attempt < MAX_RETRIES:
                        time.sleep(2 ** attempt)
                    else:
                        return None
        return None

    # ── OpenAI 兼容（DeepSeek / SiliconFlow / Groq）──────────

    def _call_openai_compat(self, system: str, user: str, max_tokens: int) -> Optional[str]:
        base_url = _OPENAI_COMPAT[self.provider]["base_url"]
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=120)
                if resp.status_code == 429:
                    wait = 60 * attempt
                    logger.warning("%s 限流（429），%ds 后重试（%d/%d）...", self.provider, wait, attempt, MAX_RETRIES)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except requests.RequestException as exc:
                logger.error("%s 请求错误: %s", self.provider, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                else:
                    return None
        return None
