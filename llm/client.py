"""LLM 基础客户端：连接、调用、JSON 修复。"""
import json
import os
import re
from pathlib import Path

# 自动加载 .env
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

USE_MOCK = False
MODEL = "anthropic/claude-haiku-4-5"
MODEL_CODE = "anthropic/claude-sonnet-4-5"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_client():
    from openai import OpenAI
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("未找到 OPENROUTER_API_KEY，请检查 .env 文件。")
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)


def _strip_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip()
    return raw


def call(system: str, user: str, max_tokens: int = 600, model: str = MODEL) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
    )
    return _strip_json(resp.choices[0].message.content)


def safe_json(raw: str, fallback: dict) -> dict:
    """解析 JSON，支持多种截断修复策略。"""
    try:
        return json.loads(raw)
    except Exception:
        pass
    for closing in ["}", '"}', '"]}', "]}", '""]}', '"population_change":0}']:
        try:
            return json.loads(raw + closing)
        except Exception:
            pass
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return fallback


def strip_code_fences(raw: str) -> str:
    """去掉 ```python ... ``` 包裹，用于代码生成输出。"""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        end = next((i for i in range(len(lines) - 1, 0, -1)
                    if lines[i].strip() == "```"), len(lines))
        raw = "\n".join(lines[1:end]).strip()
    return raw
