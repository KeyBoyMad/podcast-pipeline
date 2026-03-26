"""Whisper 转录模块：输出 raw_transcript.txt 和 raw_transcript.srt"""

import datetime
import logging
import os
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).parent.parent
_WHISPER_CACHE = _PROJECT_ROOT / "cache" / "whisper"

logger = logging.getLogger(__name__)


# Whisper large-v3 在 CUDA 上大约是音频时长 × 0.3~0.5 倍的转录时间
_MODEL_SPEED = {
    "tiny": 0.05,
    "base": 0.08,
    "small": 0.12,
    "medium": 0.2,
    "large": 0.4,
    "large-v2": 0.4,
    "large-v3": 0.4,
    "turbo": 0.1,
}


def _get_audio_duration(audio_path: Path) -> Optional[float]:
    """用 ffprobe 获取音频时长（秒）"""
    import shutil
    import subprocess
    import json

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        # 尝试 imageio-ffmpeg 同目录下的 ffprobe
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            candidate = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe.exe")
            if os.path.isfile(candidate):
                ffprobe = candidate
        except Exception:
            pass
    if not ffprobe:
        return None  # 找不到 ffprobe 就跳过时长检测

    result = subprocess.run(
        [
            ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(audio_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    try:
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            dur = stream.get("duration")
            if dur:
                return float(dur)
    except Exception:
        pass
    return None


def _seconds_to_srt_time(seconds: float) -> str:
    """将秒转为 SRT 时间格式 HH:MM:SS,mmm"""
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    s = s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(segments: list, srt_path: Path) -> None:
    """将 Whisper segments 写成 SRT 文件"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    srt_path.write_text("\n".join(lines), encoding="utf-8")


def _write_txt(segments: list, txt_path: Path) -> None:
    """将 Whisper segments 写成纯文本，每段之间空行分隔"""
    paragraphs = []
    current: list[str] = []
    # 每隔约 30 秒或句末换段
    seg_start_time = 0.0
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        current.append(text)
        # 超过 30 秒或遇到句末标点时换段
        if seg["end"] - seg_start_time > 30 or text[-1] in ("。", "！", "？", ".", "!", "?"):
            paragraphs.append("".join(current))
            current = []
            seg_start_time = seg["end"]
    if current:
        paragraphs.append("".join(current))

    txt_path.write_text("\n\n".join(paragraphs), encoding="utf-8")


def _ensure_ffmpeg_in_path() -> None:
    """确保 ffmpeg 可执行文件在 PATH 中；如系统没有，则尝试 imageio-ffmpeg。"""
    import shutil
    if shutil.which("ffmpeg"):
        return  # 系统已有 ffmpeg，无需处理
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        # 将 imageio-ffmpeg 的目录加到 PATH 最前面
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        # 若可执行文件名不是 ffmpeg/ffmpeg.exe，在同目录创建一个副本/链接
        ffmpeg_name = os.path.basename(ffmpeg_exe)
        if ffmpeg_name not in ("ffmpeg", "ffmpeg.exe"):
            import shutil as _shutil
            target = os.path.join(ffmpeg_dir, "ffmpeg.exe")
            if not os.path.exists(target):
                _shutil.copy2(ffmpeg_exe, target)
        # 再次刷新 which 缓存（importlib 重新导入不影响，shutil.which 每次调用均实时查找）
    except Exception as e:
        logger.warning("无法自动配置 ffmpeg：%s", e)


def transcribe_audio(audio_path: Path, output_dir: Path, model_name: str = "large-v3") -> bool:
    """
    用 Whisper 转录音频，输出：
      output_dir/raw_transcript.txt  — 纯文本
      output_dir/raw_transcript.srt  — SRT 字幕
    返回 True 表示成功。
    """
    _ensure_ffmpeg_in_path()

    try:
        import whisper
    except ImportError:
        logger.error("未安装 openai-whisper，请先运行 poetry install。")
        return False

    # 检查 CUDA
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        logger.warning("未检测到 CUDA，使用 CPU 转录（速度较慢）。")

    # 获取音频时长
    duration_sec = _get_audio_duration(audio_path)
    if duration_sec:
        duration_min = duration_sec / 60
        speed_factor = _MODEL_SPEED.get(model_name, 0.4)
        est_min = duration_min * speed_factor
        logger.info("模型: %s | 设备: %s | 音频: %.0f 分钟 | 预计耗时: ~%.0f 分钟",
                    model_name, device, duration_min, est_min)
    else:
        logger.info("模型: %s | 设备: %s", model_name, device)

    _WHISPER_CACHE.mkdir(parents=True, exist_ok=True)
    logger.info("⏳ 加载模型（缓存: %s）...", _WHISPER_CACHE)
    model = whisper.load_model(model_name, device=device, download_root=str(_WHISPER_CACHE))
    logger.info("⏳ 转录中（verbose 模式）...")

    result = model.transcribe(
        str(audio_path),
        language="zh",
        verbose=True,
        task="transcribe",
    )

    segments = result.get("segments", [])
    txt_path = output_dir / "raw_transcript.txt"
    srt_path = output_dir / "raw_transcript.srt"

    _write_txt(segments, txt_path)
    _write_srt(segments, srt_path)

    char_count = len(txt_path.read_text(encoding="utf-8"))
    logger.info("✅ 转录完成 → %s (%s 字)", txt_path.name, f"{char_count:,}")
    logger.info("✅ SRT 字幕 → %s (%d 段)", srt_path.name, len(segments))
    return True
