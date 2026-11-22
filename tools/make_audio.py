#!/usr/bin/env python3
"""Generate tab narration MP3s from audio/scripts/*.txt.

Default engine: Piper neural TTS (en_US-ryan-high), offline and reliable.
Optional: Microsoft edge-tts (en-US-AndrewNeural) via --engine edge, with
per-sentence retries. edge-tts was flaky on long passages in this environment.

Usage (from the repo root):

    python3 tools/make_audio.py
    python3 tools/make_audio.py --engine edge --voice en-US-AndrewNeural --rate -5%

Writes mono ~64 kbps MP3s to audio/<tab>.mp3 and audio/manifest.json.
Requires ffmpeg, and either a Piper voice or an edge-tts install.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "audio" / "scripts"
OUT_DIR = ROOT / "audio"
MANIFEST = OUT_DIR / "manifest.json"

TABS = [
    ("ov", "Overview"),
    ("co", "Companies"),
    ("sc", "Scenario"),
    ("cap", "Capacity & supply"),
    ("cmp", "AI vs 2008"),
    ("src", "Sources & method"),
]

PIPER_BIN = Path("/home/box/.venvs/ncd-tts/bin/piper")
PIPER_VOICE = Path("/home/box/.local/share/piper-voices/en_US-ryan-high.onnx")
DEFAULT_ENGINE = "piper"
DEFAULT_VOICE = "en_US-ryan-high"
DEFAULT_BITRATE = "64k"


def find_edge_tts() -> Path | None:
    exe = shutil.which("edge-tts")
    if exe:
        return Path(exe)
    alt = Path("/home/box/.venvs/ncd-tts/bin/edge-tts")
    return alt if alt.exists() else None


def find_piper() -> Path | None:
    for c in (PIPER_BIN, Path(sys.executable).resolve().parent / "piper", shutil.which("piper")):
        if c and Path(c).exists():
            return Path(c)
    return None


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def fmt_mmss(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def transcode_mp3(src: Path, dest: Path, bitrate: str) -> None:
    subprocess.check_call(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-ac", "1", "-ar", "24000", "-b:a", bitrate, "-codec:a", "libmp3lame", str(dest)]
    )


def concat_wavs(wavs: list[Path], dest: Path) -> None:
    lst = dest.with_suffix(".txt")
    lst.write_text("".join(f"file '{w}'\n" for w in wavs), encoding="utf-8")
    subprocess.check_call(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(dest)]
    )
    lst.unlink(missing_ok=True)


def synth_piper(text: str, dest: Path, piper: Path, voice: Path, length: float) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(piper), "-m", str(voice), "-f", str(dest),
         "--sentence-silence", "0.45", "--length-scale", str(length)],
        input=text + "\n",
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0 or not dest.exists() or dest.stat().st_size < 1000:
        raise SystemExit(f"piper failed: {proc.stderr[-500:]}")


def synth_edge(text_file: Path, dest: Path, edge: Path, voice: str, rate: str) -> None:
    subprocess.check_call(
        [str(edge), "--voice", voice, f"--rate={rate}", "-f", str(text_file),
         "--write-media", str(dest)]
    )
    if not dest.exists() or dest.stat().st_size < 500:
        raise RuntimeError("edge-tts produced no audio")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine", choices=["piper", "edge"], default=DEFAULT_ENGINE)
    ap.add_argument("--voice", default=None, help="Piper model name or edge-tts voice")
    ap.add_argument("--rate", default="-5%", help="edge-tts rate")
    ap.add_argument("--bitrate", default=DEFAULT_BITRATE)
    ap.add_argument("--length-scale", type=float, default=1.08, help="Piper speaking pace (>1 = slower)")
    ap.add_argument("--piper-voice", type=Path, default=PIPER_VOICE)
    args = ap.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg and ffprobe are required")

    engine = args.engine
    voice_label = args.voice
    piper = find_piper()
    edge = find_edge_tts()

    if engine == "piper":
        if not piper:
            raise SystemExit("piper not found. pip install piper-tts")
        voice_path = args.piper_voice
        if not voice_path.exists():
            raise SystemExit(f"Piper voice missing: {voice_path}")
        voice_label = voice_label or voice_path.stem
    else:
        if not edge:
            raise SystemExit("edge-tts not found")
        voice_label = voice_label or "en-US-AndrewNeural"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    with tempfile.TemporaryDirectory(prefix="ncd-audio-") as td:
        tmp = Path(td)
        for tab, title in TABS:
            script = SCRIPT_DIR / f"{tab}.txt"
            if not script.exists():
                raise SystemExit(f"missing script: {script}")
            text = script.read_text(encoding="utf-8").strip().replace("—", " - ")
            if not text:
                raise SystemExit(f"empty script: {script}")
            print(f"synthesising {tab} ({title}) with {engine} {voice_label} …")
            raw = tmp / f"{tab}.raw.wav"
            out = OUT_DIR / f"{tab}.mp3"
            if engine == "piper":
                synth_piper(text, raw, piper, args.piper_voice, args.length_scale)
            else:
                synth_edge(script, tmp / f"{tab}.raw.mp3", edge, voice_label, args.rate)
                raw = tmp / f"{tab}.raw.mp3"
            transcode_mp3(raw, out, args.bitrate)
            dur = ffprobe_duration(out)
            entries.append({
                "id": tab, "title": title, "file": f"audio/{tab}.mp3",
                "script": f"audio/scripts/{tab}.txt",
                "duration": round(dur, 3), "label": fmt_mmss(dur),
                "bytes": out.stat().st_size,
            })
            print(f"  {out.name}: {fmt_mmss(dur)}  {out.stat().st_size} bytes")

    manifest = {
        "engine": "piper-tts" if engine == "piper" else "edge-tts",
        "voice": voice_label,
        "rate": args.rate if engine == "edge" else None,
        "length_scale": args.length_scale if engine == "piper" else None,
        "bitrate": args.bitrate,
        "channels": 1,
        "sample_rate": 24000,
        "clips": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
