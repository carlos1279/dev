"""
main.py — VideoCreatorAI CLI Orchestrator

Interactive CLI with a Rich-powered menu to run the full pipeline
or individual stages independently.

Usage:
    python main.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from rich import print as rprint
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

import config

console = Console()


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
def _print_banner() -> None:
    banner = Text()
    banner.append("  🎬  ", style="bold yellow")
    banner.append("VideoCreatorAI", style="bold white on dark_blue")
    banner.append("  — Affiliate Video Automation", style="dim white")
    console.print(Panel(banner, border_style="blue", padding=(1, 4)))


# ---------------------------------------------------------------------------
# Step: Script Generation
# ---------------------------------------------------------------------------
def _run_script_generation() -> "script_generator.VideoScript":
    from script_generator import generate_script

    console.print(Rule("[bold cyan]Step 1 — Script Generation[/bold cyan]"))
    product = Prompt.ask(
        "[bold yellow]Enter the product name or URL[/bold yellow]"
    ).strip()
    if not product:
        console.print("[red]Product name cannot be empty.[/red]")
        sys.exit(1)

    with console.status("[cyan]Generating script via OpenRouter Llama …[/cyan]", spinner="dots"):
        script = generate_script(product)

    console.print(f"  ✅  Script generated: [bold]{len(script.segments)} segments[/bold]")
    console.print(f"  📝  Thumbnail question: [italic yellow]{script.thumbnail_question}[/italic yellow]")

    # Pretty-print visual prompts table
    table = Table(
        title="Visual Prompts (copy to Runway / Kling / Flux)",
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Narration (5s)", min_width=30)
    table.add_column("Visual Prompt", min_width=50)

    for i, seg in enumerate(script.segments, start=1):
        table.add_row(str(i), seg.text, seg.visual_prompt)

    console.print(table)
    console.print(
        f"\n  💾  Saved: [bold]{config.SCRIPT_PATH}[/bold] | "
        f"[bold]{config.VISUAL_PROMPTS_PATH}[/bold]"
    )
    return script


# ---------------------------------------------------------------------------
# Step: Audio Generation
# ---------------------------------------------------------------------------
def _run_audio_generation(
    script: "script_generator.VideoScript | None" = None,
    voice_id: str = "",
) -> Path:
    from audio_generator import generate_audio

    console.print(Rule("[bold cyan]Step 2 — Audio Generation[/bold cyan]"))

    if not voice_id:
        voice_id = Prompt.ask(
            "[bold yellow]ElevenLabs Voice ID[/bold yellow] "
            "(leave blank to use first available voice)",
            default="",
        ).strip()

    with console.status("[cyan]Generating voiceover via ElevenLabs …[/cyan]", spinner="dots"):
        path = generate_audio(script=script, voice_id=voice_id)

    console.print(f"  ✅  Voiceover saved: [bold]{path}[/bold]")
    return path


# ---------------------------------------------------------------------------
# Step: Video Assembly
# ---------------------------------------------------------------------------
def _run_assembly(num_segments: int | None = None) -> Path:
    from video_assembler import assemble_video

    console.print(Rule("[bold cyan]Step 3 — Video Assembly[/bold cyan]"))
    console.print(
        f"  📂  Place media files in: [bold]{config.MEDIA_DIR}[/bold]\n"
        "       Naming: 001.jpg, 002.mp4, 003.jpg …\n"
    )

    if not Confirm.ask("[yellow]Are media files ready?[/yellow]", default=True):
        console.print("[dim]Skipping assembly — run again when media is ready.[/dim]")
        sys.exit(0)

    with console.status("[cyan]Assembling video …[/cyan]", spinner="dots"):
        output = assemble_video(num_segments=num_segments)

    console.print(f"\n  🎉  Final video: [bold green]{output}[/bold green]")
    return output


# ---------------------------------------------------------------------------
# Step: Transcription
# ---------------------------------------------------------------------------
def _run_transcription() -> Path:
    from transcription import transcribe_audio

    console.print(Rule("[bold cyan]Step — Whisper Transcription[/bold cyan]"))

    with console.status("[cyan]Transcribing audio with Whisper …[/cyan]", spinner="dots"):
        ass_path = transcribe_audio()

    console.print(f"  ✅  Subtitles generated: [bold]{ass_path}[/bold]")
    return ass_path


# ---------------------------------------------------------------------------
# Step: Asset Hunting
# ---------------------------------------------------------------------------
def _run_asset_hunting(script: "script_generator.VideoScript | None" = None) -> list[Path]:
    from asset_hunter import fetch_assets

    console.print(Rule("[bold cyan]Step — Asset Hunting[/bold cyan]"))

    with console.status("[cyan]Fetching stock footage from Pexels/Pixabay …[/cyan]", spinner="dots"):
        media_files = fetch_assets(script=script)

    console.print(f"  ✅  Downloaded {len(media_files)} media file(s)")
    return media_files


# ---------------------------------------------------------------------------
# Step: FFmpeg Assembly
# ---------------------------------------------------------------------------
def _run_ffmpeg_assembly(media_files: list[Path] | None = None) -> Path:
    from ffmpeg_assembler import assemble_with_ffmpeg

    console.print(Rule("[bold cyan]Step — FFmpeg Assembly[/bold cyan]"))

    if media_files is None:
        # Discover media files
        media_files = []
        for i in range(1, 100):  # Check up to 100 segments
            media_path = config.MEDIA_DIR / f"{i:03d}.mp4"
            if media_path.exists():
                media_files.append(media_path)
            else:
                break

    if not media_files:
        console.print("[red]No media files found in media directory.[/red]")
        sys.exit(1)

    with console.status("[cyan]Assembling video with FFmpeg …[/cyan]", spinner="dots"):
        output = assemble_with_ffmpeg(media_files)

    console.print(f"\n  🎉  Final video: [bold green]{output}[/bold green]")
    return output


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------
def _action_full_pipeline() -> None:
    """Full pipeline: script → (user generates media) → audio → assemble."""
    config.validate_config()
    script = _run_script_generation()
    console.print(
        "\n[bold yellow]⏸  Pause here![/bold yellow] "
        "Use the visual prompts above to generate media files in Runway / Kling / Flux.\n"
        f"Save them to: [bold]{config.MEDIA_DIR}[/bold] as 001.jpg, 002.mp4 …\n"
    )
    _run_audio_generation(script=script)
    _run_assembly(num_segments=len(script.segments))


def _action_full_automated_pipeline() -> None:
    """Full automated pipeline: script → audio → whisper → assets → ffmpeg."""
    config.validate_config(require_openai=True, require_pexels=True)
    script = _run_script_generation()
    _run_audio_generation(script=script)
    _run_transcription()
    media_files = _run_asset_hunting(script=script)
    _run_ffmpeg_assembly(media_files=media_files)


def _action_script_only() -> None:
    """Generate script and visual prompts only."""
    config.validate_config(require_elevenlabs=False)
    _run_script_generation()


def _action_audio_only() -> None:
    """Generate voiceover from existing script.json."""
    config.validate_config(require_nvidia=False)
    _run_audio_generation()


def _action_assemble_only() -> None:
    """Assemble video from existing media and voiceover."""
    _run_assembly()


def _action_fetch_assets_only() -> None:
    """Fetch assets from existing script.json."""
    config.validate_config(require_pexels=True)
    _run_asset_hunting()


def _action_transcribe_only() -> None:
    """Transcribe existing voiceover.mp3 with Whisper."""
    config.validate_config(require_openai=True)
    _run_transcription()


def _action_ffmpeg_assemble_only() -> None:
    """Assemble video with FFmpeg from existing media + audio + subtitles."""
    _run_ffmpeg_assembly()


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------
_MENU_OPTIONS = {
    "1": ("Full Pipeline (manual media)", _action_full_pipeline),
    "2": ("Script Only (generate script + visual prompts)", _action_script_only),
    "3": ("Audio Only (voiceover from existing script.json)", _action_audio_only),
    "4": ("Assemble Only (video from existing media + audio)", _action_assemble_only),
    "5": ("Full Automated Pipeline (script → audio → whisper → assets → ffmpeg)", _action_full_automated_pipeline),
    "6": ("Fetch Assets Only (download stock footage from script.json)", _action_fetch_assets_only),
    "7": ("Transcribe Only (Whisper on existing voiceover.mp3)", _action_transcribe_only),
    "8": ("FFmpeg Assemble Only (Ken Burns + subtitles from existing media)", _action_ffmpeg_assemble_only),
    "q": ("Quit", None),
}


def _show_menu() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=4)
    table.add_column("Action", style="white")
    for key, (label, _) in _MENU_OPTIONS.items():
        table.add_row(f"[{key}]", label)
    console.print(Panel(table, title="[bold]What would you like to do?[/bold]", border_style="dim blue"))


def main() -> None:
    config.ensure_dirs()
    _print_banner()

    while True:
        console.print()
        _show_menu()
        choice = Prompt.ask(
            "[bold]Select option[/bold]",
            choices=list(_MENU_OPTIONS.keys()),
            default="1",
        ).strip().lower()

        if choice == "q":
            console.print("[dim]Goodbye! 👋[/dim]")
            break

        label, action = _MENU_OPTIONS[choice]
        console.print()
        console.print(Rule(f"[bold blue]{label}[/bold blue]"))

        try:
            action()
        except EnvironmentError as e:
            console.print(f"\n[bold red]Configuration Error:[/bold red]\n{e}")
        except FileNotFoundError as e:
            console.print(f"\n[bold red]File Not Found:[/bold red]\n{e}")
        except ValueError as e:
            console.print(f"\n[bold red]Validation Error:[/bold red]\n{e}")
        except RuntimeError as e:
            console.print(f"\n[bold red]Runtime Error:[/bold red]\n{e}")
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted.[/dim]")
        except Exception:
            console.print("\n[bold red]Unexpected error:[/bold red]")
            console.print_exception()

        console.print()
        if not Confirm.ask("[dim]Return to menu?[/dim]", default=True):
            console.print("[dim]Goodbye! 👋[/dim]")
            break


if __name__ == "__main__":
    main()
