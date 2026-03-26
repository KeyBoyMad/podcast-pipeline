# 🎙️ Podcast Pipeline

<p align="center">
  <a href="https://github.com/KeyBoyMad/podcast-pipeline/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python Version"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
  <img src="https://img.shields.io/badge/whisper-large--v3%20%7C%20turbo-orange" alt="Whisper Model">
  <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20Gemini%20%7C%20DeepSeek%20%7C%20Groq-purple" alt="LLM Support">
</p>

<p align="center">
  <b>English</b> | <a href="#中文说明">中文</a>
</p>

A fully automated pipeline that transforms podcast audio into structured, in-depth Markdown summaries — powered by **OpenAI Whisper** for transcription and any of **5 LLM providers** for analysis.

```
Audio URL / File  →  Whisper Transcription  →  LLM Cleaning  →  Structured Summary
```

---

## ✨ Features

- **Multi-source Download** — Xiaoyuzhou (小宇宙), direct audio URLs, YouTube/RSS via yt-dlp, or local files
- **URL Caching** — Re-running the same URL skips download automatically
- **GPU-Accelerated Transcription** — openai-whisper with CUDA support; models from `tiny` to `large-v3` and `turbo`
- **5 LLM Providers** — Anthropic Claude, Google Gemini, DeepSeek, SiliconFlow, Groq; auto-detected from environment variables
- **Smart Chunking** — Handles arbitrarily long transcripts via sliding-window chunking with overlap deduplication
- **Per-episode Output Directories** — Each episode gets its own named folder under `output/`
- **Resumable Pipeline** — Skip any completed step with `--skip-download`, `--skip-transcribe`, `--skip-clean`, `--only-summary`

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10 – 3.12 | Recommended: 3.11 |
| Poetry | ≥ 1.7 | Dependency management |
| CUDA (optional) | 12.1+ | GPU acceleration for Whisper |
| ffmpeg | Any | Auto-detected or bundled via `imageio-ffmpeg` |

### Installation

```bash
git clone https://github.com/KeyBoyMad/podcast-pipeline.git
cd podcast-pipeline

# Install dependencies
poetry install

# GPU (CUDA 12.1) — PyTorch is pulled from the official CUDA source automatically
# CPU only — override with:
# poetry run pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Configure API Keys

```bash
cp .env.example .env
# Edit .env and fill in at least one LLM provider key
```

Or set temporarily in your shell:

```bash
# Linux / macOS
export SILICONFLOW_API_KEY="sk-..."

# Windows PowerShell
$env:SILICONFLOW_API_KEY = "sk-..."
```

### Run

```bash
# Full pipeline: download → transcribe → clean → summarize
poetry run podcast-pipeline -i "https://www.xiaoyuzhoufm.com/episode/YOUR_EPISODE_ID"

# Specify LLM provider and Whisper model
poetry run podcast-pipeline -i <URL> --provider siliconflow --model turbo

# Local audio file
poetry run podcast-pipeline -i ./episode.mp3 --provider deepseek
```

---

## 📖 Usage

### All Options

```
podcast-pipeline [OPTIONS]

Required:
  -i, --input TEXT          Audio source: URL or local file path

Optional:
  -o, --output TEXT         Output root directory  [default: ./output]
  -m, --model TEXT          Whisper model          [default: large-v3]
                            Choices: tiny | base | small | medium | large-v3 | turbo
      --provider TEXT       LLM provider           [default: auto]
                            Choices: auto | anthropic | gemini | deepseek | siliconflow | groq
      --llm-model TEXT      Override default LLM model name
      --skip-download       Skip download step (use existing audio)
      --skip-transcribe     Skip transcription step (use existing raw_transcript.txt)
      --skip-clean          Skip cleaning step (use existing clean_transcript.md)
      --only-summary        Generate summary only (skip first three steps)
```

### Resumable Pipeline

```bash
# Already downloaded — skip download
poetry run podcast-pipeline -i <URL> --skip-download

# Already transcribed — skip download + transcription
poetry run podcast-pipeline -i <URL> --skip-download --skip-transcribe

# Clean transcript ready — generate summary only
poetry run podcast-pipeline -i <URL> --only-summary --provider deepseek
```

### Using Different LLM Providers

```bash
# DeepSeek — Best Chinese quality, free tier
DEEPSEEK_API_KEY=sk-... poetry run podcast-pipeline -i <URL> --provider deepseek

# SiliconFlow — Free credits, supports DeepSeek/Qwen models
SILICONFLOW_API_KEY=sk-... poetry run podcast-pipeline -i <URL> --provider siliconflow

# Use Qwen model on SiliconFlow
poetry run podcast-pipeline -i <URL> --provider siliconflow --llm-model "Qwen/Qwen2.5-72B-Instruct"

# Groq — Fastest inference, 30 RPM free tier
GROQ_API_KEY=gsk_... poetry run podcast-pipeline -i <URL> --provider groq
```

---

## 🤖 LLM Provider Comparison

| Provider | Default Model | Chinese Quality | Free Tier | API Registration |
|----------|--------------|-----------------|-----------|-----------------|
| **DeepSeek** | `deepseek-chat` | ⭐⭐⭐⭐⭐ | Free quota | [platform.deepseek.com](https://platform.deepseek.com) |
| **SiliconFlow** | `deepseek-ai/DeepSeek-V3` | ⭐⭐⭐⭐⭐ | Credits on signup | [cloud.siliconflow.cn](https://cloud.siliconflow.cn/i/K0OSdprd) (invite code: `K0OSdprd`) |
| **Gemini** | `gemini-2.0-flash` | ⭐⭐⭐⭐ | 15 RPM free | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| **Groq** | `llama-3.3-70b-versatile` | ⭐⭐⭐ | 30 RPM free | [console.groq.com](https://console.groq.com) |
| **Anthropic** | `claude-sonnet-4-20250514` | ⭐⭐⭐⭐⭐ | Paid only | [console.anthropic.com](https://console.anthropic.com) |

Auto-detection order: `ANTHROPIC_API_KEY` → `GEMINI_API_KEY` → `DEEPSEEK_API_KEY` → `SILICONFLOW_API_KEY` → `GROQ_API_KEY`

---

## 📁 Project Structure

```
podcast-pipeline/
├── podcast_pipeline/          # Core package
│   ├── cli.py                 # CLI entry point & pipeline orchestration
│   ├── downloader.py          # Audio acquisition (yt-dlp, requests, page parsing)
│   ├── transcriber.py         # Whisper transcription → .txt + .srt
│   ├── cleaner.py             # LLM-based transcript cleaning & speaker labeling
│   ├── summarizer.py          # LLM structured deep summary generation
│   └── llm_client.py          # Unified LLM client (5 providers)
├── examples/                  # Ready-to-run example scripts
│   ├── basic_pipeline.py      # Minimal full-pipeline example
│   └── custom_provider.py     # Multi-provider usage example
├── .github/                   # GitHub templates & workflows
├── .env.example               # API key configuration template
├── pyproject.toml             # Poetry project & dependency config
└── INSTALL_NOTES.md           # Troubleshooting for common install issues
```

### Pipeline Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│  downloader │───▶│ transcriber  │───▶│   cleaner   │───▶│ summarizer  │
│             │    │              │    │             │    │             │
│ URL / File  │    │   Whisper    │    │  LLM clean  │    │ LLM summary │
│  → .mp3     │    │ → .txt/.srt  │    │ → .md       │    │ → .md       │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
```

### Output Structure

```
output/
└── {Episode Title}/
    ├── episode.mp3              # Downloaded audio
    ├── raw_transcript.txt       # Whisper raw transcription
    ├── raw_transcript.srt       # Whisper SRT subtitles
    ├── clean_transcript.md      # LLM-cleaned transcript with speaker labels
    └── summary.md               # Structured deep summary (2000+ words)
```

The summary includes: Executive Summary · Background · Content Breakdown · Key Insights · Critical Analysis · Actionable Takeaways · Mermaid Mind Map.

---

## 🔧 Troubleshooting

**Whisper model SHA256 mismatch (interrupted download)**
```bash
rm cache/whisper/large-v3-turbo.pt   # Delete corrupted file, then re-run
```

**`RuntimeError: Numpy is not available`**
```bash
poetry run pip install "numpy<2"
```

**Gemini 429 rate limit**
Switch to DeepSeek or SiliconFlow which have higher free-tier limits:
```bash
poetry run podcast-pipeline -i <URL> --provider deepseek
```

**Xiaoyuzhou download fails**
Ensure your proxy is running, or download the audio manually and pass the local path:
```bash
poetry run podcast-pipeline -i ./episode.mp3
```

See [INSTALL_NOTES.md](./INSTALL_NOTES.md) for detailed troubleshooting on Windows + CUDA setup.

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📄 License

MIT © [podcast-pipeline contributors](./LICENSE)

---

<h2 id="中文说明">📖 中文说明</h2>

一个将播客音频全自动转化为结构化 Markdown 深度总结的完整流水线，使用 **OpenAI Whisper** 进行转录，支持 **5 种 LLM 服务商**进行分析。

```
音频链接 / 本地文件  →  Whisper 转录  →  LLM 清洗  →  结构化深度总结
```

---

### ✨ 主要特性

- **多平台下载**：支持小宇宙（xiaoyuzhoufm.com）、音频直链、YouTube/RSS（via yt-dlp）及本地文件，自动识别输入类型
- **URL 下载缓存**：同一链接再次运行自动跳过下载，避免重复流量消耗
- **GPU 加速转录**：openai-whisper + CUDA 支持，可选模型从 `tiny`（极速）到 `large-v3`（最准确）和 `turbo`
- **5 种 LLM 服务商**：Anthropic Claude、Google Gemini、DeepSeek、SiliconFlow、Groq，根据环境变量自动检测，无需手动指定
- **智能滑动分块**：带重叠去重的分块策略，可处理任意长度的文字稿，无上下文长度限制
- **每集独立输出目录**：每期播客以标题命名专属子目录，多集并行处理互不干扰
- **断点续跑**：任意步骤均可单独跳过，转录慢、清洗失败均可从中断处继续

---

### 🚀 快速开始

#### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10 – 3.12 | 推荐 3.11 |
| Poetry | ≥ 1.7 | 依赖管理 |
| CUDA（可选） | 12.1+ | GPU 加速 Whisper，无 GPU 也可 CPU 运行 |
| ffmpeg | 任意版本 | 自动检测系统安装或使用内置 imageio-ffmpeg |

#### 安装

```bash
git clone https://github.com/KeyBoyMad/podcast-pipeline.git
cd podcast-pipeline

# 安装所有依赖（PyTorch CUDA 版本自动从官方源拉取）
poetry install

# 仅 CPU 环境，手动覆盖 PyTorch：
# poetry run pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

#### 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入至少一个 LLM 服务商的 Key
```

或在 Shell 中临时设置：

```powershell
# Windows PowerShell
$env:SILICONFLOW_API_KEY = "sk-..."

# Linux / macOS
export SILICONFLOW_API_KEY="sk-..."
```

#### 运行

```bash
# 完整流水线：下载 → 转录 → 清洗 → 总结
poetry run podcast-pipeline -i "https://www.xiaoyuzhoufm.com/episode/xxx"

# 指定 LLM 服务商和 Whisper 模型
poetry run podcast-pipeline -i <URL> --provider siliconflow --model turbo

# 本地音频文件
poetry run podcast-pipeline -i ./episode.mp3 --provider deepseek
```

---

### 📖 全部参数

```
podcast-pipeline [OPTIONS]

必填：
  -i, --input TEXT          音频来源：URL 或本地文件路径

可选：
  -o, --output TEXT         输出根目录              [默认: ./output]
  -m, --model TEXT          Whisper 模型            [默认: large-v3]
                            可选: tiny | base | small | medium | large-v3 | turbo
      --provider TEXT       LLM 服务商              [默认: auto]
                            可选: auto | anthropic | gemini | deepseek | siliconflow | groq
      --llm-model TEXT      覆盖默认 LLM 模型名
      --skip-download       跳过下载步骤（使用已有音频）
      --skip-transcribe     跳过转录步骤（使用已有 raw_transcript.txt）
      --skip-clean          跳过清洗步骤（使用已有 clean_transcript.md）
      --only-summary        仅生成总结（跳过前三步）
```

#### 断点续跑示例

```bash
# 已下载，跳过下载
poetry run podcast-pipeline -i <URL> --skip-download

# 已转录，跳过下载+转录
poetry run podcast-pipeline -i <URL> --skip-download --skip-transcribe

# 已有清洗稿，直接生成总结
poetry run podcast-pipeline -i <URL> --only-summary --provider deepseek
```

#### 切换 LLM 服务商

```bash
# DeepSeek — 中文质量最佳，有免费额度
DEEPSEEK_API_KEY=sk-... poetry run podcast-pipeline -i <URL> --provider deepseek

# SiliconFlow — 注册即送额度，支持 DeepSeek/Qwen 等多种模型
# 注册领取免费额度：https://cloud.siliconflow.cn/i/K0OSdprd（邀请码 K0OSdprd）
SILICONFLOW_API_KEY=sk-... poetry run podcast-pipeline -i <URL> --provider siliconflow

# 使用 Qwen 模型
poetry run podcast-pipeline -i <URL> --provider siliconflow --llm-model "Qwen/Qwen2.5-72B-Instruct"

# Groq — 推理速度最快，30 RPM 免费额度
GROQ_API_KEY=gsk_... poetry run podcast-pipeline -i <URL> --provider groq
```

---

### 🤖 LLM 服务商对比

| 服务商 | 默认模型 | 中文质量 | 免费额度 | 注册地址 |
|--------|---------|---------|---------|---------|
| **DeepSeek** | `deepseek-chat` | ⭐⭐⭐⭐⭐ | 有免费额度 | [platform.deepseek.com](https://platform.deepseek.com) |
| **SiliconFlow** | `deepseek-ai/DeepSeek-V3` | ⭐⭐⭐⭐⭐ | 注册即送额度 | [cloud.siliconflow.cn](https://cloud.siliconflow.cn/i/K0OSdprd)（邀请码 `K0OSdprd`） |
| **Gemini** | `gemini-2.0-flash` | ⭐⭐⭐⭐ | 15 RPM 免费 | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| **Groq** | `llama-3.3-70b-versatile` | ⭐⭐⭐ | 30 RPM 免费 | [console.groq.com](https://console.groq.com) |
| **Anthropic** | `claude-sonnet-4-20250514` | ⭐⭐⭐⭐⭐ | 仅付费 | [console.anthropic.com](https://console.anthropic.com) |

自动检测优先级：`ANTHROPIC_API_KEY` → `GEMINI_API_KEY` → `DEEPSEEK_API_KEY` → `SILICONFLOW_API_KEY` → `GROQ_API_KEY`

---

### 📁 项目结构

```
podcast-pipeline/
├── podcast_pipeline/          # 核心包
│   ├── cli.py                 # CLI 入口与流水线编排
│   ├── downloader.py          # 音频获取（yt-dlp、requests、页面解析）
│   ├── transcriber.py         # Whisper 转录 → .txt + .srt
│   ├── cleaner.py             # LLM 文字稿清洗与说话人标注
│   ├── summarizer.py          # LLM 结构化深度总结生成
│   └── llm_client.py          # 统一 LLM 客户端（5 种服务商）
├── examples/                  # 可直接运行的示例脚本
│   ├── basic_pipeline.py      # 最简完整流水线示例
│   └── custom_provider.py     # 多服务商 / 批量处理示例
├── .env.example               # API Key 配置模板
├── pyproject.toml             # Poetry 项目与依赖配置
└── INSTALL_NOTES.md           # Windows + CUDA 安装常见问题
```

#### 流水线示意

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│  downloader │───▶│ transcriber  │───▶│   cleaner   │───▶│ summarizer  │
│             │    │              │    │             │    │             │
│ URL / 文件  │    │   Whisper    │    │  LLM 清洗   │    │ LLM 总结    │
│  → .mp3     │    │ → .txt/.srt  │    │ → .md       │    │ → .md       │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
```

#### 输出目录结构

```
output/
└── {播客标题}/
    ├── episode.mp3              # 下载的音频
    ├── raw_transcript.txt       # Whisper 原始转录
    ├── raw_transcript.srt       # SRT 字幕文件
    ├── clean_transcript.md      # LLM 清洗后文字稿（含说话人标注）
    └── summary.md               # 结构化深度总结（2000+ 字）
```

总结包含：核心摘要 · 问题背景 · 内容拆解 · 关键洞察 · 批判性分析 · 可实践建议 · Mermaid 思维导图

---

### 🔧 常见问题

**Whisper 模型 SHA256 校验失败（下载中断）**
```bash
rm cache/whisper/large-v3-turbo.pt   # 删除损坏文件后重新运行
```

**`RuntimeError: Numpy is not available`**
```bash
poetry run pip install "numpy<2"
```

**Gemini 429 限流**
切换到 DeepSeek 或 SiliconFlow，免费额度更充裕：
```bash
poetry run podcast-pipeline -i <URL> --provider deepseek
```

**小宇宙下载失败**
确认代理正常，或手动下载音频后传入本地路径：
```bash
poetry run podcast-pipeline -i ./episode.mp3
```

详细的 Windows + CUDA 安装问题排查请参阅 [INSTALL_NOTES.md](./INSTALL_NOTES.md)。

---

### 🤝 贡献

欢迎提交 Issue 和 PR！详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

### 📄 许可证

MIT © [podcast-pipeline contributors](./LICENSE)
