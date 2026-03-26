# 环境安装问题记录

> 平台：Windows 10 + NVIDIA GPU (CUDA 12.1) + Poetry + Python 3.11.7
> 记录时间：2026-03-26

---

## 问题一：虚拟环境 Python 版本不满足要求

**现象**
```
poetry env info → Valid: False
```
`.venv` 由 Python 3.9.0 创建，而 `pyproject.toml` 要求 `>=3.10,<3.13`。

**原因**
系统默认 Python 为 3.9，`poetry env use` 未显式指定版本，自动使用了系统默认版本。

**解决方案**
```bash
# 删除旧虚拟环境
rm -rf .venv

# 用满足版本要求的 Python 重建
D:\py311\python.exe -m venv .venv
# 之后 poetry 会自动识别项目内的 .venv（需 virtualenvs.in-project = true）
```

**预防建议**
在安装前先确认 poetry 将使用的 Python 版本：
```bash
poetry env info --path
python --version
```

---

## 问题二：C 盘空间不足导致 torch 安装失败

**现象**
```
[Errno 28] No space left on device
```
Poetry 默认将包缓存写入 `C:\Users\<用户名>\AppData\Local\pypoetry\Cache`，该目录已占用 2.5 GB，torch 约 2 GB，C 盘剩余空间不足。

**原因**
torch（CUDA 版）单个 wheel 文件约 2 GB，Poetry 缓存与系统盘共用空间。

**解决方案**
安装前临时将 Poetry 缓存重定向到 D 盘（**不修改全局配置，不影响其他环境**）：
```bash
# PowerShell
$env:POETRY_CACHE_DIR = "D:/poetry_envs/poetry-cache"
poetry install
```

**永久方案（可选，影响所有 Poetry 项目）**
```bash
poetry config cache-dir D:/poetry_envs/poetry-cache
```

---

## 问题三：triton 在 Windows 下无可用 wheel

**现象**
```
poetry install 中断：找不到 triton 的 Windows 兼容版本
```

**原因**
`triton` 是 PyTorch 的传递依赖，官方只发布 Linux wheel，Windows 上无法安装。

**解决方案**
从 `pyproject.toml` 中删除对 `triton` 的显式声明（无需手动添加），Poetry 解析 torch 传递依赖时会读取其自带的 `sys_platform == 'linux'` marker，Windows 下自动跳过。

如果曾经误加过如下声明，删除即可：
```toml
# 删除这行
triton = {version = ">=2.0", markers = "sys_platform == 'linux'", optional = true}
```

---

## 问题四：openai-whisper 构建失败（pkg_resources 缺失）

**现象**
```
No module named 'pkg_resources'
```

**原因**
`setuptools` 82.x 移除了 `pkg_resources` 模块，而 `openai-whisper` 的旧版 setup.py 依赖该模块进行构建。

**解决方案**
在虚拟环境中降级 setuptools：
```bash
poetry run pip install "setuptools<72"
# 然后重新安装 whisper
poetry run pip install openai-whisper
```

---

## 问题五：numba 与 NumPy 2.x 兼容警告

**现象**
```
UserWarning: Failed to initialize NumPy: _ARRAY_API not found (Triggered internally at ...)
```
`torchaudio` 导入时出现警告。

**原因**
`numba 0.64.0` 编译时针对 NumPy 1.x API，环境中安装了 NumPy 2.2.6，存在 ABI 不兼容。

**影响**
仅为警告，`torchaudio` 核心功能和 `numba` JIT 编译均正常，**不影响本项目使用**。

**彻底消除警告的方案（可选）**
```bash
poetry run pip install "numpy<2.0"
```

---

## 最终可用的安装流程（总结）

```bash
# 0. 确认使用正确的 Python 版本
D:\py311\python.exe --version   # 应为 3.10~3.12

# 1. 进入项目目录，删除旧虚拟环境（如有）
cd D:/poetry_envs/podcast-pipeline
rm -rf .venv

# 2. 重建虚拟环境
D:\py311\python.exe -m venv .venv

# 3. 将 Poetry 缓存指向 D 盘（C 盘空间充裕可跳过）
$env:POETRY_CACHE_DIR = "D:/poetry_envs/poetry-cache"

# 4. 生成 lock 文件
poetry lock

# 5. 安装依赖（torch 从 pytorch-cu121 source 拉取，约 2 GB，需耐心）
poetry install

# 6. 若 whisper 构建失败，降级 setuptools 后重装
poetry run pip install "setuptools<72"
poetry run pip install openai-whisper

# 7. 若 torch/torchaudio 未从 CUDA source 安装，手动补装
poetry run pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# 8. 验证
poetry run python -c "import torch; print('CUDA:', torch.cuda.is_available())"
poetry run python -c "import whisper; print('whisper OK')"
poetry run python -c "import anthropic; print('anthropic OK')"
```
