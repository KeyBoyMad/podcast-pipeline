"""
custom_provider.py — Multi-provider & programmatic API example
==============================================================
Demonstrates how to:
  1. Use LLMClient directly (without the CLI) to call different providers
  2. Override the default model for any provider
  3. Run only specific pipeline steps programmatically
  4. Batch-process multiple episodes

Requirements
------------
    poetry install
    # Set at least one of:
    export DEEPSEEK_API_KEY="sk-..."
    export SILICONFLOW_API_KEY="sk-..."
    export GROQ_API_KEY="gsk_..."
    export GEMINI_API_KEY="AIza..."
    export ANTHROPIC_API_KEY="sk-ant-..."

Usage
-----
    poetry run python examples/custom_provider.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


# ── Example 1: Call LLMClient directly ───────────────────────────────────────

def example_llm_client():
    """Show how to call the unified LLM client outside of the pipeline."""
    from podcast_pipeline.llm_client import LLMClient

    print("=== Example 1: Direct LLMClient usage ===\n")

    # auto — picks the first available key from environment
    client = LLMClient(provider="auto")
    print(f"Auto-selected provider: {client.provider}, model: {client.model}")

    response = client.call(
        system="You are a concise assistant. Reply in one sentence.",
        user="What is OpenAI Whisper?",
        max_tokens=200,
    )
    print(f"Response: {response}\n")


# ── Example 2: Override provider and model ───────────────────────────────────

def example_override_model():
    """Use SiliconFlow with a Qwen model instead of the default DeepSeek-V3."""
    from podcast_pipeline.llm_client import LLMClient
    import os

    if not os.environ.get("SILICONFLOW_API_KEY"):
        print("=== Example 2: Skipped (SILICONFLOW_API_KEY not set) ===\n")
        return

    print("=== Example 2: SiliconFlow with Qwen2.5-72B ===\n")

    client = LLMClient(
        provider="siliconflow",
        model="Qwen/Qwen2.5-72B-Instruct",   # override default model
    )
    response = client.call(
        system="你是一个简洁的助手，用一句话回答。",
        user="简单介绍一下 OpenAI Whisper。",
        max_tokens=200,
    )
    print(f"Response: {response}\n")


# ── Example 3: Summary-only mode on an existing transcript ───────────────────

def example_summary_only(clean_transcript_path: str):
    """
    Re-generate summary from an existing clean transcript.
    Useful for experimenting with prompts without re-running Whisper.

    Args:
        clean_transcript_path: Path to a clean_transcript.md file
    """
    from podcast_pipeline.summarizer import generate_summary

    print("=== Example 3: Summary-only from existing transcript ===\n")

    clean_path = Path(clean_transcript_path)
    if not clean_path.exists():
        print(f"File not found: {clean_path}. Skipping.\n")
        return

    output_dir = clean_path.parent
    ok = generate_summary(clean_path, output_dir, provider="auto")
    if ok:
        print(f"Summary written to: {output_dir / 'summary.md'}\n")
    else:
        print("Summary generation failed.\n")


# ── Example 4: Batch process multiple local audio files ──────────────────────

def example_batch(audio_dir: str, whisper_model: str = "turbo", provider: str = "auto"):
    """
    Transcribe and summarize all .mp3 files in a directory.

    Args:
        audio_dir: Directory containing .mp3 files
        whisper_model: Whisper model to use (turbo is a good balance of speed/quality)
        provider: LLM provider
    """
    from podcast_pipeline.transcriber import transcribe_audio
    from podcast_pipeline.cleaner import clean_transcript
    from podcast_pipeline.summarizer import generate_summary

    print(f"=== Example 4: Batch processing {audio_dir} ===\n")

    audio_files = list(Path(audio_dir).glob("*.mp3"))
    if not audio_files:
        print(f"No .mp3 files found in {audio_dir}. Skipping.\n")
        return

    for audio_path in audio_files:
        print(f"\n--- Processing: {audio_path.name} ---")
        episode_dir = audio_path.parent / audio_path.stem
        episode_dir.mkdir(exist_ok=True)

        # Transcribe
        ok = transcribe_audio(audio_path, episode_dir, model_name=whisper_model)
        if not ok:
            print(f"Transcription failed for {audio_path.name}, skipping.")
            continue

        # Clean
        raw_path = episode_dir / "raw_transcript.txt"
        ok = clean_transcript(raw_path, episode_dir, provider=provider)
        if not ok:
            print(f"Cleaning failed for {audio_path.name}, skipping.")
            continue

        # Summarize
        clean_path = episode_dir / "clean_transcript.md"
        ok = generate_summary(clean_path, episode_dir, provider=provider)
        if ok:
            print(f"Done: {episode_dir / 'summary.md'}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run Example 1 and 2 (no audio files needed)
    example_llm_client()
    example_override_model()

    # Example 3: uncomment and point to a real transcript
    # example_summary_only("./output/MyEpisode/clean_transcript.md")

    # Example 4: uncomment and point to a directory of mp3 files
    # example_batch("./my_audio_files", whisper_model="turbo", provider="deepseek")
