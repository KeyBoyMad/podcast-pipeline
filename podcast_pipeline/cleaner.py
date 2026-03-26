"""LLM 清洗文字稿模块：调用 Claude 或 Gemini 修正 ASR 错误、合并段落、标注说话人"""

import logging
import re
import time
from pathlib import Path
from typing import Optional

from podcast_pipeline.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ── 配置 ─────────────────────────────────────────────────────
CHUNK_CHARS = 3000       # 每块目标字数
OVERLAP_CHARS = 200      # 相邻块重叠字数
API_INTERVAL = 5.0       # 正常请求间隔（秒）——Gemini free tier 限 15 RPM

SYSTEM_PROMPT = """你是一名专业的播客文字稿编辑。你的任务是清洗 ASR（自动语音识别）产生的原始文字稿。

清洗规则：
1. 修正 ASR 错误，尤其是专有名词（人名、地名、品牌、技术术语、公司名）
2. 合并碎片句为完整、通顺的段落
3. 推断说话人并在每段前添加标注：【主持人】或【嘉宾】（如有多位嘉宾用【嘉宾A】【嘉宾B】）
4. 删除口语填充词：嗯、啊、那个、就是说、对对对、然后然后、就这样、好的好的
5. 保留原始内容，不添加、不删减实质性信息
6. 输出 Markdown 格式，每位说话人的发言为一段

{chunk_hint}

请直接输出清洗后的文字稿，不要有任何前言或解释。"""


# ── 分块 ─────────────────────────────────────────────────────

def _split_into_units(text: str) -> list[str]:
    """
    将文本切成小单元，优先级：
    1. 段落（\\n\\n）
    2. 句末标点（。！？.!?）
    3. 强制按 CHUNK_CHARS 字符截断（Whisper 输出无标点时的兜底）
    """
    units: list[str] = []
    # 先按段落切
    for para in re.split(r'\n\n+', text):
        para = para.strip()
        if not para:
            continue
        # 段落内按句末标点切
        sents = [s.strip() for s in re.split(r'(?<=[。！？.!?])\s*', para) if s.strip()]
        if not sents:
            sents = [para]
        for sent in sents:
            # 单句超过 CHUNK_CHARS 时强制按字符数截断
            while len(sent) > CHUNK_CHARS:
                units.append(sent[:CHUNK_CHARS])
                sent = sent[CHUNK_CHARS:]
            if sent:
                units.append(sent)
    return units


def _build_chunks(text: str) -> list[str]:
    """
    将文本切成带重叠的块：
    - 每块约 CHUNK_CHARS 字
    - 相邻块有 OVERLAP_CHARS 字重叠
    """
    units = _split_into_units(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for unit in units:
        current.append(unit)
        current_len += len(unit)
        if current_len >= CHUNK_CHARS:
            chunks.append("\n\n".join(current))
            # 保留末尾 OVERLAP_CHARS 作为下一块开头
            overlap = "\n\n".join(current)[-OVERLAP_CHARS:]
            current = [overlap] if overlap else []
            current_len = len(overlap)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# ── 去重拼接 ─────────────────────────────────────────────────

def _deduplicate_overlap(prev: str, curr: str) -> str:
    """
    在 prev 末尾 / curr 开头找重叠区，取 curr 版本拼接。
    """
    search_window = min(OVERLAP_CHARS * 2, len(prev), len(curr))
    tail = prev[-search_window:]
    head = curr[:search_window]

    best_pos = 0
    for length in range(min(len(tail), len(head)), 20, -1):
        sub = head[:length]
        if sub in tail:
            idx = curr.find(sub)
            if idx >= 0:
                best_pos = idx + length
                break

    return prev + curr[best_pos:]


# ── 主入口 ───────────────────────────────────────────────────

def clean_transcript(
    raw_path: Path,
    output_dir: Path,
    provider: str = "auto",
    model: Optional[str] = None,
) -> bool:
    """
    读取 raw_transcript.txt，分块调用 LLM 清洗，
    输出 clean_transcript.md。
    """
    raw_text = raw_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        logger.error("raw_transcript.txt 为空。")
        return False

    try:
        client = LLMClient(provider=provider, model=model)
    except (RuntimeError, ValueError) as exc:
        logger.error("%s", exc)
        return False

    logger.info("📄 原始文字稿: %s 字", f"{len(raw_text):,}")
    chunks = _build_chunks(raw_text)
    total = len(chunks)
    logger.info("📦 分块数: %d（每块约 %d 字，重叠 %d 字）", total, CHUNK_CHARS, OVERLAP_CHARS)

    cleaned_parts: list[str] = []

    for i, chunk in enumerate(chunks, 1):
        logger.info("✏️  清洗第 %d/%d 块（%d 字）...", i, total, len(chunk))
        chunk_hint = f"【当前为第 {i}/{total} 块，请保持与前后文连贯的说话人标注风格】"
        system = SYSTEM_PROMPT.format(chunk_hint=chunk_hint)
        cleaned = client.call(system=system, user=chunk, max_tokens=4096)
        if cleaned is None:
            logger.error("第 %d 块清洗失败。", i)
            return False
        cleaned_parts.append(cleaned)
        if i < total:
            time.sleep(API_INTERVAL)

    if len(cleaned_parts) == 1:
        final_text = cleaned_parts[0]
    else:
        final_text = cleaned_parts[0]
        for part in cleaned_parts[1:]:
            final_text = _deduplicate_overlap(final_text, part)

    out_path = output_dir / "clean_transcript.md"
    out_path.write_text(final_text.strip(), encoding="utf-8")
    logger.info("✅ 清洗完成 → %s (%s 字)", out_path.name, f"{len(final_text):,}")
    return True
