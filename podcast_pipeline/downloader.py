"""音频获取模块：支持本地文件、音频直链、小宇宙链接"""

import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# ── 网络请求配置 ──────────────────────────────────────────────
TIMEOUT = 60
MAX_RETRIES = 3
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def _request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    """带指数退避重试的 HTTP 请求"""
    kwargs.setdefault("headers", HEADERS)
    kwargs.setdefault("timeout", TIMEOUT)
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                logger.warning("请求失败（%d/%d），%ds 后重试: %s", attempt, MAX_RETRIES, wait, exc)
                time.sleep(wait)
    raise RuntimeError(f"请求失败，已重试 {MAX_RETRIES} 次: {last_exc}") from last_exc


# ── ffmpeg 转换 ───────────────────────────────────────────────

def _find_ffmpeg() -> str:
    """返回 ffmpeg 可执行文件的完整路径，找不到则报错"""
    # 1. 环境变量优先
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2. shutil.which（依赖 PATH）
    path = shutil.which("ffmpeg")
    if path:
        return path

    # 3. 常见 Windows 安装位置兜底
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        r"D:\ffmpeg\bin\ffmpeg.exe",
        r"D:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # 4. imageio-ffmpeg 内置二进制（兜底）
    try:
        import imageio_ffmpeg
        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and os.path.isfile(bundled):
            return bundled
    except Exception:
        pass

    raise RuntimeError(
        "未找到 ffmpeg 可执行文件。\n"
        "运行以下命令安装内置 ffmpeg：\n"
        "  poetry run pip install imageio-ffmpeg\n"
        "或设置环境变量指向系统 ffmpeg：\n"
        "  $env:FFMPEG_PATH = 'C:\\path\\to\\ffmpeg.exe'"
    )


def _convert_to_mp3(src: Path, dst: Path) -> None:
    """将 m4a/wav 等格式转为 mp3"""
    logger.info("🔄 ffmpeg 转换: %s → %s", src.name, dst.name)
    ffmpeg = _find_ffmpeg()
    result = subprocess.run(
        [
            ffmpeg, "-y", "-i", str(src),
            "-acodec", "libmp3lame", "-q:a", "2",
            str(dst),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 转换失败:\n{result.stderr.decode('utf-8', errors='replace')}"
        )
    logger.info("✅ 转换完成 → %s", dst.name)


# ── 下载辅助 ─────────────────────────────────────────────────

def _stream_download(url: str, dest: Path) -> None:
    """流式下载并打印进度"""
    resp = _request_with_retry("GET", url, stream=True)
    total = int(resp.headers.get("Content-Length", 0))
    downloaded = 0
    chunk_size = 1024 * 64  # 64 KB
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  ⬇️  下载中... {pct:.1f}%  ({downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB)", end="", flush=True)
    print()  # 换行


def _is_audio_url(url: str) -> bool:
    """判断 URL 是否为音频直链"""
    path = urlparse(url).path.lower()
    if any(path.endswith(ext) for ext in (".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac")):
        return True
    # HEAD 请求检查 Content-Type
    try:
        resp = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        ct = resp.headers.get("Content-Type", "")
        return "audio" in ct
    except Exception:
        return False


# ── 小宇宙解析 ───────────────────────────────────────────────

def _extract_xiaoyuzhou_audio(url: str) -> str:
    """从小宇宙剧集页面提取音频直链"""
    logger.info("🔍 解析小宇宙页面...")
    resp = _request_with_retry("GET", url)
    html = resp.text

    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        raise RuntimeError("未找到 __NEXT_DATA__ script 标签，小宇宙页面结构可能已变更。")

    data = json.loads(match.group(1))

    audio_url = _find_audio_url_in_json(data)
    if not audio_url:
        raise RuntimeError("在小宇宙页面 JSON 中未找到音频地址（enclosure.url / mediaUrl / playUrl）。")

    logger.info("✅ 找到音频地址: %s...", audio_url[:80])
    return audio_url


def _find_audio_url_in_json(obj, depth: int = 0) -> Optional[str]:
    """递归搜索 JSON 对象中的音频 URL"""
    if depth > 20:
        return None
    if isinstance(obj, dict):
        for key in ("enclosure", ):
            if key in obj and isinstance(obj[key], dict):
                for sub_key in ("url", "mediaUrl", "playUrl"):
                    if sub_key in obj[key] and isinstance(obj[key][sub_key], str):
                        val = obj[key][sub_key]
                        if val.startswith("http"):
                            return val
        for key in ("mediaUrl", "playUrl", "audioUrl", "streamingUrl"):
            if key in obj and isinstance(obj[key], str) and obj[key].startswith("http"):
                return obj[key]
        for v in obj.values():
            result = _find_audio_url_in_json(v, depth + 1)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_audio_url_in_json(item, depth + 1)
            if result:
                return result
    return None


# ── 下载缓存 ─────────────────────────────────────────────────

_CACHE_FILE = "download_cache.json"


def _load_cache(output_dir: Path) -> dict:
    path = output_dir / _CACHE_FILE
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(output_dir: Path, url: str, filename: str) -> None:
    cache = _load_cache(output_dir)
    cache[url] = filename
    (output_dir / _CACHE_FILE).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _check_cache(input_str: str, output_dir: Path) -> Optional[Path]:
    """若该 URL 已下载过且文件仍存在，直接返回路径；否则返回 None。"""
    cache = _load_cache(output_dir)
    filename = cache.get(input_str)
    if filename:
        cached_path = output_dir / filename
        if cached_path.exists():
            return cached_path
    return None


# ── 主入口 ───────────────────────────────────────────────────

def download_audio(input_str: str, output_dir: Path) -> Optional[Path]:
    """
    根据输入类型下载/复制音频到 output_dir，返回最终 mp3 路径。
    失败返回 None。
    """
    try:
        # 0. 本地文件不做缓存检查；URL 先查缓存
        if not Path(input_str).exists():
            cached = _check_cache(input_str, output_dir)
            if cached:
                logger.info("⚡ 命中缓存，跳过下载 → %s", cached.name)
                return cached
        # 1. 本地文件
        local = Path(input_str)
        if local.exists():
            logger.info("📂 检测到本地文件: %s", local)
            suffix = local.suffix.lower()
            dest_raw = output_dir / local.name
            if dest_raw.resolve() != local.resolve():
                shutil.copy2(local, dest_raw)
            if suffix == ".mp3":
                logger.info("✅ 已复制 → %s", dest_raw.name)
                return dest_raw
            else:
                mp3_path = output_dir / (local.stem + ".mp3")
                _convert_to_mp3(dest_raw, mp3_path)
                return mp3_path

        # 2. 小宇宙链接：优先 yt-dlp，失败降级页面解析
        if "xiaoyuzhoufm.com/episode/" in input_str:
            logger.info("🌐 小宇宙链接，尝试 yt-dlp 下载...")
            try:
                result = _download_with_ytdlp(input_str, output_dir)
            except Exception as exc:
                logger.warning("yt-dlp 失败（%s），降级到页面解析...", exc)
                audio_url = _extract_xiaoyuzhou_audio(input_str)
                result = _download_from_url(audio_url, output_dir, filename_hint="xiaoyuzhou_episode")
            _save_cache(output_dir, input_str, result.name)
            return result

        # 3. 音频直链
        if _is_audio_url(input_str):
            result = _download_from_url(input_str, output_dir)
            _save_cache(output_dir, input_str, result.name)
            return result

        # 4. 其他 URL（YouTube、RSS 等），尝试 yt-dlp
        logger.info("🌐 非直链 URL，尝试 yt-dlp 下载...")
        result = _download_with_ytdlp(input_str, output_dir)
        _save_cache(output_dir, input_str, result.name)
        return result

    except Exception as exc:
        logger.error("下载出错: %s", exc)
        return None


def _download_from_url(url: str, output_dir: Path, filename_hint: str = "") -> Path:
    """从 URL 流式下载音频，返回 mp3 路径"""
    parsed = urlparse(url)
    raw_name = Path(parsed.path).name or filename_hint or "audio"
    # 去掉查询参数可能带来的乱码
    raw_name = re.sub(r"[?&=].*", "", raw_name) or "audio"
    suffix = Path(raw_name).suffix.lower()
    if suffix not in (".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"):
        suffix = ".mp3"
        raw_name = Path(raw_name).stem + suffix

    dest_raw = output_dir / raw_name
    logger.info("⬇️  开始下载: %s", raw_name)
    _stream_download(url, dest_raw)
    file_size_mb = dest_raw.stat().st_size / 1024 / 1024
    logger.info("✅ 下载完成 → %s (%.1f MB)", dest_raw.name, file_size_mb)

    if suffix != ".mp3":
        mp3_path = output_dir / (Path(raw_name).stem + ".mp3")
        _convert_to_mp3(dest_raw, mp3_path)
        return mp3_path
    return dest_raw


def _download_with_ytdlp(url: str, output_dir: Path) -> Path:
    """使用 yt-dlp 下载并提取音频为 mp3"""
    import yt_dlp

    # 让 yt-dlp 也能找到 ffmpeg
    try:
        ffmpeg_loc = str(Path(_find_ffmpeg()).parent)
    except RuntimeError:
        ffmpeg_loc = None

    output_template = str(output_dir / "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "2",
            }
        ],
        "quiet": False,
        "no_warnings": False,
    }
    if ffmpeg_loc:
        ydl_opts["ffmpeg_location"] = ffmpeg_loc
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "audio")
        # yt-dlp 后处理后文件名后缀变为 mp3
        mp3_path = output_dir / f"{title}.mp3"
        if mp3_path.exists():
            return mp3_path
        # 模糊搜索
        candidates = list(output_dir.glob("*.mp3"))
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_mtime)
        raise RuntimeError("yt-dlp 下载后未找到 mp3 文件。")
