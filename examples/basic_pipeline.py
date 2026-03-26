"""
basic_pipeline.py — Minimal end-to-end example
================================================
Runs the full pipeline on a podcast URL or local file:
  Download → Whisper Transcription → LLM Cleaning → Structured Summary

Requirements
------------
- poetry install  (from the project root)
- At least one LLM API key set as an environment variable, e.g.:
    export DEEPSEEK_API_KEY="sk-..."          # Linux / macOS
    $env:DEEPSEEK_API_KEY = "sk-..."          # Windows PowerShell

Usage
-----
    poetry run python examples/basic_pipeline.py

Or with a local file:
    poetry run python examples/basic_pipeline.py --input ./my_episode.mp3
"""

import argparse
import sys
from pathlib import Path

# Make sure the project root is on sys.path when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env from the project root (ignored if the file doesn't exist)
load_dotenv(Path(__file__).parent.parent / ".env")


def run(input_source: str, output_dir: str, whisper_model: str, provider: str) -> None:
    from pathlib import Path as _Path

    from podcast_pipeline.downloader import download_audio
    from podcast_pipeline.transcriber import transcribe_audio
    from podcast_pipeline.cleaner import clean_transcript
    from podcast_pipeline.summarizer import generate_summary

    out = _Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Download ──────────────────────────────────────────
    print("\n=== Step 1/4: Download ===")
    audio_path = download_audio(input_source, out)
    if audio_path is None:
        print("Download failed. Exiting.")
        sys.exit(1)
    print(f"Audio saved to: {audio_path}")

    # Create a per-episode subdirectory so outputs don't mix
    episode_dir = out / audio_path.stem
    episode_dir.mkdir(exist_ok=True)
    audio_path = audio_path.rename(episode_dir / audio_path.name)

    # ── Step 2: Transcribe ────────────────────────────────────────
    print(f"\n=== Step 2/4: Transcribe (model={whisper_model}) ===")
    ok = transcribe_audio(audio_path, episode_dir, model_name=whisper_model)
    if not ok:
        print("Transcription failed. Exiting.")
        sys.exit(1)

    # ── Step 3: Clean ─────────────────────────────────────────────
    print(f"\n=== Step 3/4: Clean transcript (provider={provider}) ===")
    raw_path = episode_dir / "raw_transcript.txt"
    ok = clean_transcript(raw_path, episode_dir, provider=provider)
    if not ok:
        print("Cleaning failed. Exiting.")
        sys.exit(1)

    # ── Step 4: Summarize ─────────────────────────────────────────
    print(f"\n=== Step 4/4: Generate summary (provider={provider}) ===")
    clean_path = episode_dir / "clean_transcript.md"
    ok = generate_summary(clean_path, episode_dir, provider=provider)
    if not ok:
        print("Summary generation failed. Exiting.")
        sys.exit(1)

    print(f"\nDone! Output directory: {episode_dir.resolve()}")
    print("  raw_transcript.txt   — Whisper raw output")
    print("  raw_transcript.srt   — SRT subtitles")
    print("  clean_transcript.md  — LLM-cleaned transcript with speaker labels")
    print("  summary.md           — Structured deep summary (2000+ words)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Podcast Pipeline — basic example")
    parser.add_argument(
        "--input", "-i",
        default="https://www.xiaoyuzhoufm.com/episode/REPLACE_WITH_EPISODE_ID",
        help="Audio URL or local file path",
    )
    parser.add_argument("--output", "-o", default="./output", help="Output directory")
    parser.add_argument("--model", "-m", default="turbo", help="Whisper model (turbo is fast; large-v3 is most accurate)")
    parser.add_argument("--provider", default="auto", help="LLM provider: auto|anthropic|gemini|deepseek|siliconflow|groq")
    args = parser.parse_args()

    run(args.input, args.output, args.model, args.provider)
