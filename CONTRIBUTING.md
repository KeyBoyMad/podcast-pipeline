# Contributing to Podcast Pipeline

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Submitting a Pull Request](#submitting-a-pull-request)

---

## Code of Conduct

Please read and follow our [Code of Conduct](./CODE_OF_CONDUCT.md). We are committed to providing a welcoming and inclusive environment for all contributors.

---

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/KeyBoyMad/podcast-pipeline.git
   cd podcast-pipeline
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/KeyBoyMad/podcast-pipeline.git
   ```

---

## How to Contribute

### 🐛 Reporting Bugs

- Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
- Search existing issues first to avoid duplicates
- Include your OS, Python version, CUDA version (if applicable), and the full error traceback

### 💡 Suggesting Features

- Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)
- Clearly describe the problem you're trying to solve
- Explain why this feature would be useful to other users

### 🌐 Adding a New LLM Provider

New providers are easy to add! The key files are:

1. **`podcast_pipeline/llm_client.py`**:
   - Add an entry to `DEFAULT_MODELS` dict
   - Add an entry to `_OPENAI_COMPAT` dict (if OpenAI-compatible) or implement a new `_call_<provider>()` method
   - Add to `_AUTO_DETECT_ORDER` list
2. **`podcast_pipeline/cli.py`**: Add the provider name to `--provider` choices
3. **`.env.example`**: Add the new API key variable with a comment and registration link
4. **`README.md`**: Add a row to the provider comparison table

### 🌏 Adding a New Podcast Platform

New download sources go into `podcast_pipeline/downloader.py`:

1. Add a URL pattern check in `download_audio()`
2. Implement a `_extract_<platform>_audio()` function for page-based parsing, or use `_download_with_ytdlp()` if yt-dlp already supports the platform
3. Add tests in `tests/test_downloader.py`

---

## Development Setup

```bash
# 1. Install all dependencies (including dev)
poetry install

# 2. Copy environment variables
cp .env.example .env
# Fill in at least one LLM API key for integration tests

# 3. Run linter
poetry run ruff check podcast_pipeline/

# 4. Run formatter check
poetry run ruff format --check podcast_pipeline/

# 5. Run tests
poetry run pytest tests/ -v
```

### Project Layout

```
podcast_pipeline/
├── cli.py          # Entry point — add new CLI flags here
├── downloader.py   # Download logic — add new platform support here
├── transcriber.py  # Whisper transcription — GPU/model config here
├── cleaner.py      # Transcript cleaning — prompt tuning here
├── summarizer.py   # Summary generation — prompt tuning here
└── llm_client.py   # LLM abstraction — add new providers here
```

---

## Code Standards

### Style

- **Formatter**: `ruff format` (Black-compatible)
- **Linter**: `ruff check`
- **Type hints**: Required for all public functions and class methods
- **Docstrings**: Required for all public modules, classes, and functions

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
feat: add Mistral AI provider support
fix: handle Whisper download timeout gracefully
docs: update README with Groq rate limit info
refactor: extract common retry logic to utils module
test: add unit tests for transcript chunking
```

### Branch Naming

```
feat/add-mistral-provider
fix/whisper-sha256-retry
docs/update-install-guide
```

---

## Submitting a Pull Request

1. **Sync** with upstream before starting work:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create** a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```

3. **Make** your changes, following the code standards above

4. **Test** your changes:
   ```bash
   poetry run ruff check podcast_pipeline/
   poetry run pytest tests/ -v
   ```

5. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add Mistral AI provider"
   ```

6. **Push** and open a Pull Request:
   ```bash
   git push origin feat/your-feature-name
   ```
   Then open a PR against the `main` branch using the [PR template](.github/PULL_REQUEST_TEMPLATE.md).

### PR Review Process

- All PRs require at least one approving review
- CI checks (lint + tests) must pass
- Keep PRs focused — one feature or fix per PR
- Update documentation if you change behavior

---

## Questions?

Open a [Discussion](https://github.com/KeyBoyMad/podcast-pipeline/discussions) or start a new [Issue](https://github.com/KeyBoyMad/podcast-pipeline/issues).
