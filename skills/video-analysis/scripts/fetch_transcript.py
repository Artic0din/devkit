#!/usr/bin/env python3
"""Fetch a video's metadata and timestamped transcript with yt-dlp, no API keys.

Writes meta.json and transcript.txt into a per-video folder and prints the folder path.
Exit codes: 0 ok, 1 yt-dlp or download failure, 2 no usable captions.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MELBOURNE = ZoneInfo("Australia/Melbourne")
DEFAULT_OUT_DIR = Path.home() / "Downloads" / "video-notes"
# Merge caption fragments into lines of about this many seconds so the agent reads fewer, fuller lines.
LINE_WINDOW_SECONDS = 20
FORMAT_PREFERENCE = ("json3", "vtt", "srt")
TIME = r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})"
CUE_TIMING = re.compile(rf"{TIME}\s*-->\s*{TIME}")
# Rolling auto-captions start the next cue exactly when the previous one ends; allow for rounding.
ROLLING_GAP_SECONDS = 0.5
# Sites whose yt-dlp extractor separates creator captions from machine ones; elsewhere provenance is unknown.
PROVENANCE_SITES = {"Youtube", "Vimeo"}
TAG = re.compile(r"<[^>]+>")


class FetchError(Exception):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def is_autogen(language: str) -> bool:
    # Vimeo lists its machine captions under subtitles with this BCP 47 private-use tag.
    return "-x-autogen" in language


def choose_track(info: dict, lang: str) -> tuple[str, str] | None:
    """Return (kind, language) where kind is "creator" or "auto"; creator captions win."""
    subtitles = {k: v for k, v in (info.get("subtitles") or {}).items() if k != "live_chat"}
    creator = {k: v for k, v in subtitles.items() if not is_autogen(k)}
    auto = {**(info.get("automatic_captions") or {}), **{k: v for k, v in subtitles.items() if is_autogen(k)}}
    for key in sorted(creator):
        if key == lang or key.startswith(f"{lang}-"):
            return ("creator", key)
    for key in (f"{lang}-orig", lang):
        if key in auto:
            return ("auto", key)
    for key in sorted(auto):
        if key.startswith(f"{lang}-"):
            return ("auto", key)
    if creator:
        return ("creator", sorted(creator)[0])
    originals = sorted(k for k in auto if k.endswith("-orig")) or sorted(auto)
    if originals:
        return ("auto", originals[0])
    return None


def collection(info: dict, kind: str, language: str) -> str:
    """Which yt-dlp collection holds the track; this sets the download flag, separately from its provenance."""
    if kind == "creator" or language in (info.get("subtitles") or {}) and is_autogen(language):
        return "subtitles"
    return "automatic_captions"


def choose_format(info: dict, kind: str, language: str) -> str:
    tracks = info.get(collection(info, kind, language)) or {}
    available = {fmt.get("ext") for fmt in tracks.get(language, [])}
    for ext in FORMAT_PREFERENCE:
        if ext in available:
            return ext
    raise FetchError(f"captions in {language} only offered as {sorted(available)}; need one of {FORMAT_PREFERENCE}")


def parse_json3(text: str) -> list[tuple[float, str]]:
    segments = []
    for event in json.loads(text).get("events", []):
        words = "".join(seg.get("utf8", "") for seg in event.get("segs") or []).replace("\n", " ").strip()
        if words:
            segments.append((event.get("tStartMs", 0) / 1000, words))
    return segments


def parse_cues(text: str, rolling_captions: bool = True) -> list[tuple[float, str]]:
    """Parse VTT or SRT. Rolling auto-captions carry the previous cue's last line up to the top of a
    multi-line cue that starts as it ends; drop only that carried line. Any other repeat is real speech."""
    segments: list[tuple[float, str]] = []
    carried = ""
    previous_end = float("-inf")
    # Split on truly empty lines only: rolling cues end with a line holding a single space, and that
    # line is what marks the carried text as not the cue's last line.
    for block in re.split(r"\r?\n\r?\n", text):
        lines = block.splitlines()
        timing = next(((i, m) for i, line in enumerate(lines) if (m := CUE_TIMING.search(line))), None)
        if timing is None:
            continue
        timing_index, match = timing
        start, end = to_seconds(match.groups()[:4]), to_seconds(match.groups()[4:])
        rolling = rolling_captions and start - previous_end <= ROLLING_GAP_SECONDS
        cue_lines = [html.unescape(TAG.sub("", line)).strip() for line in lines[timing_index + 1 :]]
        for index, clean in enumerate(cue_lines):
            is_carryover = rolling and index < len(cue_lines) - 1 and clean == carried
            if clean and not is_carryover:
                segments.append((start, clean))
        carried = next((line for line in reversed(cue_lines) if line), "")
        previous_end = end
    return segments


def to_seconds(parts: tuple[str | None, ...]) -> float:
    hours, minutes, seconds, millis = parts
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(seconds or 0) + int(millis or 0) / 1000


def format_timestamp(seconds: float) -> str:
    whole = int(seconds)
    hours, rem = divmod(whole, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def merge_lines(segments: list[tuple[float, str]], window: float = LINE_WINDOW_SECONDS) -> list[str]:
    lines: list[str] = []
    start: float | None = None
    words: list[str] = []
    for seg_start, text in segments:
        if start is not None and seg_start - start >= window:
            lines.append(f"[{format_timestamp(start)}] {' '.join(words)}")
            start, words = None, []
        if start is None:
            start = seg_start
        words.append(text)
    if words and start is not None:
        lines.append(f"[{format_timestamp(start)}] {' '.join(words)}")
    return lines


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60].rstrip("-") or "video"


def folder_name(day: str, title: str, video_id: str) -> str:
    """The video ID keeps two same-titled videos fetched on one day from sharing a folder."""
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "", video_id)
    return "-".join(part for part in (day, slugify(title), safe_id) if part)


def run_ytdlp(args: list[str], workdir: str) -> subprocess.CompletedProcess[str]:
    """Ignore every yt-dlp config and run in our own empty temp folder: a yt-dlp.conf in whatever checkout the
    agent sits in could add --exec hooks, and user configs can add languages or convert the caption file."""
    binary = shutil.which("yt-dlp")
    if not binary:
        raise FetchError("yt-dlp is not installed. Install it with: brew install yt-dlp (macOS) or pipx install yt-dlp")
    result = subprocess.run([binary, "--ignore-config", "--no-update", "--ignore-no-formats-error", *args], capture_output=True, text=True, cwd=workdir)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        raise FetchError(f"yt-dlp exited {result.returncode}:\n{tail}")
    return result


def fetch(url: str, lang: str, out_dir: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        # Some extractors (Vimeo, for example) only list caption tracks when a subtitle flag is set.
        info = json.loads(
            run_ytdlp(
                ["--dump-single-json", "--skip-download", "--no-playlist", "--write-subs", "--write-auto-subs", url], tmp
            ).stdout
        )
        track = choose_track(info, lang)
        if track is None:
            raise FetchError("no creator or auto-generated captions are published for this video", exit_code=2)
        kind, language = track
        ext = choose_format(info, kind, language)
        provenance = kind if info.get("extractor_key") in PROVENANCE_SITES else "unknown"

        info_path = Path(tmp) / "info.json"
        info_path.write_text(json.dumps(info), encoding="utf-8")
        write_flag = "--write-subs" if collection(info, kind, language) == "subtitles" else "--write-auto-subs"
        run_ytdlp(
            ["--load-info-json", str(info_path), "--skip-download", write_flag,
             "--sub-langs", re.escape(language), "--sub-format", ext, "-o", str(Path(tmp) / "subs")],
            tmp,
        )
        caption_file = Path(tmp) / f"subs.{language}.{ext}"
        if not caption_file.is_file():
            raise FetchError(f"yt-dlp reported success but wrote no {caption_file.name} caption file")
        raw = caption_file.read_text(encoding="utf-8")

    segments = parse_json3(raw) if ext == "json3" else parse_cues(raw, rolling_captions=kind == "auto")
    lines = merge_lines(segments)
    if not lines:
        raise FetchError("caption file was empty after cleaning", exit_code=2)

    now = datetime.now(tz=MELBOURNE)
    upload = info.get("upload_date") or ""
    folder = out_dir / folder_name(f"{now:%Y-%m-%d}", info.get("title") or "", str(info.get("id") or ""))
    folder.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "url": info.get("webpage_url") or url,
        "site": info.get("extractor_key"),
        "duration_seconds": round(info["duration"]) if isinstance(info.get("duration"), (int, float)) else None,
        "upload_date": f"{upload[:4]}-{upload[4:6]}-{upload[6:]}" if len(upload) == 8 else None,
        "caption_kind": provenance,
        "caption_language": language,
        "transcript_method": f"yt-dlp {write_flag} ({ext})",
        "transcript_words": sum(len(line.split()) - 1 for line in lines),
        "fetched_at": now.isoformat(timespec="seconds"),
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (folder / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--lang", default="en", help="preferred caption language (default: en)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    try:
        folder = fetch(args.url, args.lang, args.out_dir.expanduser())
    except FetchError as error:
        print(f"error: {error}", file=sys.stderr)
        return error.exit_code
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    print(folder)
    print(f"captions: {meta['caption_kind']} ({meta['caption_language']}), {meta['transcript_words']} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
