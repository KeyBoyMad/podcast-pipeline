"""LLM 结构化总结模块：调用 Claude 或 Gemini 生成深度 Markdown 总结"""

import logging
import time
from pathlib import Path
from typing import Optional

from podcast_pipeline.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ── 配置 ─────────────────────────────────────────────────────
MAX_TOKENS = 16384
# 约 150,000 字 ≈ 100K tokens，超过则分块摘要
CHUNK_THRESHOLD_CHARS = 150_000
SUMMARY_CHUNK_CHARS = 75_000
MAX_RETRIES = 5

SYSTEM_SUMMARY = """你是一名具备研究员级别信息整合能力的分析专家。请对播客文字稿进行系统性、结构化、深度总结，输出高质量 Markdown。

**深度要求**：总结字数不少于 2000 字。每个要点必须展开说明，给出论据、背景或具体细节，禁止仅用一句话带过。保留原文中出现的所有重要数据、案例、人名、机构名、专有名词，不得省略。

输出结构（严格遵守，不要省略任何章节）：

# [根据内容自拟的具概括性标题]

## 一、核心摘要（Executive Summary）
5~8 条要点，每条 2~4 句话展开，说明"是什么 + 为什么重要 + 对应的证据/细节"。用 `-` 列举。

## 二、问题背景与动机（Why）
详细说明：这期播客讨论的核心问题是什么？产生这个问题的历史背景、行业现状、社会原因是什么？主讲人/嘉宾为什么关注这个话题、他们的立场和出发点是什么？**至少 200 字。**

## 三、核心内容拆解（What）
按对话推进的逻辑将内容分为 4~8 个子主题，每个子主题格式如下：

### 3.x [子主题名称]
**核心观点**：用 1~2 句话概括这部分的中心论点。

**展开说明**：详细阐述论点的推导过程、背后的机制或逻辑链条（3~6 句话）。

**原文证据**：直接引用或高度还原原文中的关键表述、数据、案例、类比（至少 1 条，用引号标注）。

**延伸含义**：这个观点意味着什么，有何更广泛的影响或推论（1~3 句话）。

## 四、关键方法/框架/模型解析（How）
提炼对话中涉及的分析框架、操作方法或思维模型。对每种方法：说明它解决什么问题、核心步骤或要素、适用前提和边界条件。若本期不涉及方法论，则分析嘉宾的论证方式和思维路径。

## 五、关键洞察（Insights）
列出 4~6 条洞察，每条包含：
- **洞察**：反常识认知、隐含假设或独特视角（1 句话）
- **依据**：为何这个洞察成立，原文中的支撑（2~3 句话）
- **迁移价值**：这个认知框架可以如何应用到其他领域（1~2 句话）

## 六、批判性分析（Critical Thinking）
**论点的强项**：哪些论述有充分的证据和逻辑支撑，为什么有说服力？

**潜在局限与盲点**：哪些结论依赖了未充分验证的假设？哪些视角被忽略了？有无以偏概全之处？

**补充视角**：已有哪些不同观点或反例？如果要反驳，最有力的切入点在哪里？

## 七、可实践建议（Actionable Takeaways）
列出 4~6 条具体可执行的建议，每条格式：
- **建议**：具体行动是什么（面向谁、做什么）
- **原因**：为何有效，背后的逻辑依据
- **注意事项**：执行时的前提条件或常见误区

## 八、一句话总结（Core Takeaway）
> [一句话概括本期播客的最核心价值，要求具体、有信息量，避免泛泛而谈]

## 九、思维导图
```mermaid
mindmap
  root((主题))
    分支一
      子节点
      子节点
    分支二
      子节点
    分支三
      子节点
```

写作风格要求：
- 信息密度高，每句话都有实质内容，杜绝过渡性废话
- 不使用"首先/其次/再次"等机械排列词
- 保留专业术语，不要为了通俗化而牺牲精确性
- 允许重构内容顺序以优化逻辑
- 禁止 AI 味表达（如"值得注意的是"、"不难发现"、"综上所述"、"深刻启示"）
- 数字、人名、机构名、时间节点必须与原文一致，不得推测或模糊化"""

SYSTEM_CHUNK_SUMMARY = """你是一名专业的内容分析师。以下是播客文字稿的一个片段。

任务：提炼这段内容的核心信息，为后续生成完整总结提供素材。

要求：
- 保留所有重要观点，每个观点用 2~4 句话展开说明，不要仅列标题
- 原文中出现的数据、案例、人名、引用、类比必须完整保留，不得省略
- 记录说话人的论证逻辑和推导过程，而不只是结论
- 用 Markdown 结构化输出（用 `##` 分段、`-` 列要点）
- 不要有任何前言、总结语或评价性语句，直接输出内容"""


# ── 工具函数 ──────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """按字数粗切，在段落边界处断开"""
    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        current.append(para)
        current_len += len(para)
        if current_len >= chunk_size:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append("\n\n".join(current))
    return chunks


# ── 主入口 ────────────────────────────────────────────────────

def generate_summary(
    clean_path: Path,
    output_dir: Path,
    provider: str = "auto",
    model: Optional[str] = None,
) -> bool:
    """
    读取 clean_transcript.md，生成结构化总结，
    输出 summary.md。
    """
    text = clean_path.read_text(encoding="utf-8")
    if not text.strip():
        logger.error("clean_transcript.md 为空。")
        return False

    try:
        client = LLMClient(provider=provider, model=model)
    except (RuntimeError, ValueError) as exc:
        logger.error("%s", exc)
        return False

    char_count = len(text)
    logger.info("📄 清洗文字稿: %s 字", f"{char_count:,}")

    if char_count <= CHUNK_THRESHOLD_CHARS:
        logger.info("⏳ 生成总结（单次请求）...")
        summary = client.call(
            system=SYSTEM_SUMMARY,
            user=f"以下是播客完整文字稿，请严格按照要求生成深度总结，总字数不少于 2000 字：\n\n{text}",
            max_tokens=MAX_TOKENS,
        )
        if summary is None:
            return False
    else:
        chunks = _chunk_text(text, SUMMARY_CHUNK_CHARS)
        total = len(chunks)
        logger.info("📦 文字稿较长，分 %d 块先生成摘要再合并...", total)
        partial_summaries: list[str] = []

        for i, chunk in enumerate(chunks, 1):
            logger.info("⏳ 分段摘要 %d/%d...", i, total)
            part = client.call(
                system=SYSTEM_CHUNK_SUMMARY,
                user=f"【第 {i}/{total} 段】\n\n{chunk}",
                max_tokens=4096,
            )
            if part is None:
                logger.error("第 %d 段摘要生成失败。", i)
                return False
            partial_summaries.append(f"## 第 {i} 段摘要\n\n{part}")
            time.sleep(1)

        logger.info("⏳ 合并分段摘要，生成最终总结...")
        merged = "\n\n---\n\n".join(partial_summaries)
        summary = client.call(
            system=SYSTEM_SUMMARY,
            user=f"以下是播客各分段的摘要，请整合为一份完整深度总结，总字数不少于 2000 字，不得遗漏任何分段中的重要观点、数据和案例：\n\n{merged}",
            max_tokens=MAX_TOKENS,
        )
        if summary is None:
            return False

    out_path = output_dir / "summary.md"
    out_path.write_text(summary.strip(), encoding="utf-8")
    logger.info("✅ 总结生成完成 → %s (%s 字)", out_path.name, f"{len(summary):,}")
    return True
