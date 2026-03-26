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
| **SiliconFlow** | `deepseek-ai/DeepSeek-V3` | ⭐⭐⭐⭐⭐ | Credits on signup | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) |
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

### 主要特性

- **多平台下载**：小宇宙、音频直链、YouTube/RSS（yt-dlp）、本地文件
- **URL 缓存**：同一链接再次运行自动跳过下载
- **GPU 加速转录**：openai-whisper + CUDA，支持从 `tiny` 到 `large-v3` 和 `turbo` 等模型
- **5 种 LLM 服务商**：Anthropic Claude、Google Gemini、DeepSeek、SiliconFlow、Groq，自动检测可用 Key
- **智能分块**：通过滑动窗口分块处理超长文字稿
- **每集独立目录**：每期播客输出到以标题命名的专属子目录
- **断点续跑**：`--skip-download / --skip-transcribe / --skip-clean / --only-summary`

### 安装

```bash
git clone https://github.com/KeyBoyMad/podcast-pipeline.git
cd podcast-pipeline
poetry install
```

### 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入至少一个 LLM 服务商的 Key
```

### 运行示例

```bash
# 完整流水线
poetry run podcast-pipeline -i "https://www.xiaoyuzhoufm.com/episode/xxx"

# 指定国内免费 LLM（推荐 SiliconFlow 或 DeepSeek）
poetry run podcast-pipeline -i <URL> --provider siliconflow --model turbo

# 跳过已完成步骤
poetry run podcast-pipeline -i <URL> --only-summary --provider deepseek
```

详细参数说明及常见问题请参阅英文部分。
