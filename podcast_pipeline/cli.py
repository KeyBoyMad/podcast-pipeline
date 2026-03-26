"""命令行入口"""

import argparse
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# 项目根目录（podcast_pipeline/ 的上一级）
_PROJECT_ROOT = Path(__file__).parent.parent


# ── 日志配置 ──────────────────────────────────────────────────

def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="  %(message)s",
        stream=sys.stdout,
    )


# ── 缓存目录 ──────────────────────────────────────────────────

def _setup_cache_dirs() -> None:
    """将所有运行时缓存重定向到项目目录下的 cache/，避免写用户目录。"""
    cache_root = _PROJECT_ROOT / "cache"
    cache_root.mkdir(parents=True, exist_ok=True)

    (cache_root / "whisper").mkdir(exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))

    torch_cache = cache_root / "torch"
    (torch_cache / "hub").mkdir(parents=True, exist_ok=True)
    (torch_cache / "extensions").mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_HOME", str(torch_cache))
    os.environ.setdefault("TORCH_EXTENSIONS_DIR", str(torch_cache / "extensions"))

    (cache_root / "huggingface").mkdir(exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_root / "huggingface"))

    (cache_root / "numba").mkdir(exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", str(cache_root / "numba"))

    print(f"  📁 缓存目录: {cache_root}")


# ── 每集独立目录 ──────────────────────────────────────────────

def _sanitize_dirname(name: str) -> str:
    """将字符串转为合法目录名（移除非法字符，限制长度）。"""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = name.strip(". ")
    return name[:80] or "episode"


def _get_episode_dir(output_dir: Path, audio_path: Path) -> tuple[Path, Path]:
    """
    基于音频文件名创建该集专属子目录。
    若音频不在子目录中，则将其移入。
    返回 (episode_dir, new_audio_path)。
    """
    episode_name = _sanitize_dirname(audio_path.stem)
    episode_dir = output_dir / episode_name
    episode_dir.mkdir(parents=True, exist_ok=True)

    new_audio = episode_dir / audio_path.name
    if audio_path.resolve() != new_audio.resolve():
        if not new_audio.exists():
            shutil.move(str(audio_path), str(new_audio))
        audio_path = new_audio

    return episode_dir, audio_path


def _find_in_dir(directory: Path, filename: str) -> Optional[Path]:
    """在目录及其一级子目录中查找文件，返回最新的一个。"""
    direct = directory / filename
    if direct.exists():
        return direct
    candidates = sorted(
        directory.glob(f"*/{filename}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


# ── 步骤输出 ──────────────────────────────────────────────────

def print_step(n: int, total: int, icon: str, title: str) -> None:
    print("\n" + "=" * 60)
    print(f"{icon}  Step {n}/{total}: {title}")
    print("=" * 60)


# ── 主入口 ────────────────────────────────────────────────────

def main() -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(
        prog="podcast-pipeline",
        description="播客音频 → 逐字稿 → Markdown 结构化深度总结",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  podcast-pipeline -i https://www.xiaoyuzhoufm.com/episode/xxx
  podcast-pipeline -i podcast.m4a -o ./my_output -m medium
  podcast-pipeline -i <URL> --skip-download --provider siliconflow
        """,
    )

    parser.add_argument("--input", "-i", required=True, help="音频来源（URL 或本地文件路径）")
    parser.add_argument("--output", "-o", default="./output", help="输出根目录（默认: ./output）")
    parser.add_argument(
        "--model", "-m", default="large-v3",
        help="Whisper 模型（默认: large-v3）可选: tiny/base/small/medium/large-v3/turbo",
    )
    parser.add_argument("--skip-download",   action="store_true", help="跳过下载步骤")
    parser.add_argument("--skip-transcribe", action="store_true", help="跳过转录步骤")
    parser.add_argument("--skip-clean",      action="store_true", help="跳过清洗步骤")
    parser.add_argument("--only-summary",    action="store_true", help="只生成总结（跳过前三步）")
    parser.add_argument(
        "--provider", default="auto",
        choices=["auto", "anthropic", "gemini", "deepseek", "siliconflow", "groq"],
        help="LLM 提供商（默认: auto，按环境变量自动检测）",
    )
    parser.add_argument("--llm-model", default=None, dest="llm_model", help="覆盖默认 LLM 模型名")

    args = parser.parse_args()

    _setup_cache_dirs()

    if args.only_summary:
        args.skip_download = True
        args.skip_transcribe = True
        args.skip_clean = True

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # work_dir 将在确定 audio_path 后更新为该集专属子目录
    work_dir = output_dir
    audio_path: Optional[Path] = None

    steps = []
    if not args.skip_download:   steps.append(("downloader",  "🔽",  "音频下载"))
    if not args.skip_transcribe: steps.append(("transcriber", "🎙️", "Whisper 转录"))
    if not args.skip_clean:      steps.append(("cleaner",     "✏️",  "LLM 文字稿清洗"))
    steps.append(                             ("summarizer",  "📝",  "LLM 结构化总结"))
    total = len(steps)

    for idx, (module, icon, title) in enumerate(steps, 1):
        print_step(idx, total, icon, title)

        if module == "downloader":
            from podcast_pipeline.downloader import download_audio
            audio_path = download_audio(args.input, output_dir)
            if audio_path is None:
                print("❌ 下载失败，退出。")
                sys.exit(1)
            work_dir, audio_path = _get_episode_dir(output_dir, audio_path)
            print(f"  📁 集数目录: {work_dir}")

        elif module == "transcriber":
            from podcast_pipeline.transcriber import transcribe_audio
            if audio_path is None:
                # 跳过了下载：在 output_dir 及子目录中寻找音频
                p = Path(args.input)
                if p.exists():
                    audio_path = p
                else:
                    exts = ["*.mp3", "*.m4a", "*.wav"]
                    candidates = []
                    for ext in exts:
                        candidates += list(output_dir.glob(ext))
                        candidates += list(output_dir.glob(f"*/{ext}"))
                    if not candidates:
                        print("❌ 未找到音频文件，请先运行下载步骤或提供本地文件。")
                        sys.exit(1)
                    audio_path = max(candidates, key=lambda p: p.stat().st_mtime)
                work_dir, audio_path = _get_episode_dir(output_dir, audio_path)
                print(f"  使用已有音频: {audio_path}")
                print(f"  📁 集数目录: {work_dir}")
            ok = transcribe_audio(audio_path, work_dir, args.model)
            if not ok:
                print("❌ 转录失败，退出。")
                sys.exit(1)

        elif module == "cleaner":
            from podcast_pipeline.cleaner import clean_transcript
            raw_path = _find_in_dir(work_dir, "raw_transcript.txt")
            if not raw_path:
                print(f"❌ 未找到 raw_transcript.txt，请先运行转录步骤。")
                sys.exit(1)
            work_dir = raw_path.parent
            ok = clean_transcript(raw_path, work_dir, provider=args.provider, model=args.llm_model)
            if not ok:
                print("❌ 清洗失败，退出。")
                sys.exit(1)

        elif module == "summarizer":
            from podcast_pipeline.summarizer import generate_summary
            clean_path = _find_in_dir(work_dir, "clean_transcript.md")
            if not clean_path:
                print(f"❌ 未找到 clean_transcript.md，请先运行清洗步骤。")
                sys.exit(1)
            work_dir = clean_path.parent
            ok = generate_summary(clean_path, work_dir, provider=args.provider, model=args.llm_model)
            if not ok:
                print("❌ 总结生成失败，退出。")
                sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 全部完成！")
    print(f"   输出目录: {work_dir.resolve()}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
