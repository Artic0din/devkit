---
name: video-analysis
description: "Turn a video URL (YouTube, Vimeo, or any yt-dlp site) into a visual HTML brief for Ryan: TL;DR, clickable key-moment timeline, themes, actions tied to how he works, and a resumable step-by-step guide for tutorials. Transcript only, no API keys. Use when the user shares a video link and asks to analyse, summarise, break down, or extract steps from it."
---

# Video Analysis

Turn one video into a single self-contained HTML page Ryan can skim, act on and resume.
The scripts live in `scripts/` next to this file; call that folder `SKILL_DIR/scripts`.
They need `python3` and `yt-dlp` only.

## Step 1: Get the transcript

```bash
python3 -I SKILL_DIR/scripts/fetch_transcript.py 'VIDEO_URL'
```

1. The script prints the video folder (default `~/Downloads/video-notes/YYYY-MM-DD-title/`) and the caption kind.
   It writes `meta.json` and `transcript.txt` (`[m:ss] text` lines) there.
2. It picks the creator's own captions first and falls back to auto-generated captions, recorded as `caption_kind` in `meta.json`:
   `creator`, `auto`, or `unknown` on sites other than YouTube and Vimeo, which don't say.
   Tell the user which kind you used.
3. Use only keyless methods: this script, plain `yt-dlp`, or the `youtube-transcript-api` Python package.
   Never use a method that needs an API key or paid tier (for example the YouTube Data API, Whisper API, AssemblyAI).
   If you considered one and skipped it, record it in `skipped_methods`.
4. Flags: `--lang de` for another caption language, `--out-dir PATH` to save elsewhere.

If the script fails (exit 1: yt-dlp or download error; exit 2: no captions), stop.
Report the exact error and what you tried, then offer 2–3 options, such as:
running `yt-dlp -U` and retrying, installing a JavaScript runtime with `brew install deno` (yt-dlp needs one for some YouTube videos), trying `--lang` with another language listed by `yt-dlp --list-subs URL`, or transcribing the audio locally with an installed Whisper model (free, but slow).
Never summarise from the title, description or comments.

## Step 2: Analyse

Read the whole `transcript.txt` before writing anything; for long videos read it in chunks to the end.
Then work out:

- The main subject, in one sentence.
- 3–6 key themes.
- Whether it is a tutorial: the presenter shows steps, a process, a setup or a method someone could follow.
- What the presenter **shows** (demonstrates on screen or with evidence) versus what they only **assert**.
  Auto-captions mishear names, numbers and commands; if one looks wrong, keep it as heard and list it under `uncertain`.

## Step 3: Write `analysis.json`

Write it into the video folder. Timestamps (`t`) are seconds or `"m:ss"` strings.
Paraphrase; quote only short exact wording such as commands, settings and values.

```json
{
  "tldr": "2–3 sentences: what the video is and the single most useful takeaway.",
  "subject": "One sentence.",
  "summary": [
    {"t": "0:45", "text": "Key moment in plain language; readable in 2 minutes total."},
    {"t": 312, "text": "Claim the presenter makes without evidence.", "opinion": true}
  ],
  "themes": [
    {"name": "Theme", "why": "One line: what it is and why it matters."}
  ],
  "actions": [
    {
      "action": "Concrete action to take.",
      "why": "Optional: one line linking it to Ryan's setup.",
      "area": "Home Assistant",
      "effort": "About 30 minutes",
      "when": "now"
    }
  ],
  "tutorial": {
    "goal": "What you end up with.",
    "prerequisites": ["Tools, accounts, versions and hardware mentioned."],
    "steps": [
      {"t": "2:10", "text": "One action per step.", "code": "exact command or setting, if any"}
    ],
    "gotchas": ["Warnings, errors or fixes the presenter mentions."],
    "gaps": ["Steps skipped, glossed over or done off-screen. Do not invent them."],
    "costs": ["Anything needing an API key, subscription or paid tier."]
  },
  "not_tutorial": "Only when tutorial is null: one line saying why.",
  "uncertain": ["Things you could not verify, such as possibly misheard values."],
  "skipped_methods": []
}
```

Field rules:

- `summary`: 4–10 moments, in time order. Each becomes a numbered marker on the timeline; on YouTube and Vimeo it jumps to that second of the video.
- `actions`: numbered by the page, grouped `now` / `later`. Each must fit Ryan specifically (see below).
  Leave out generic advice and anything that only loosely fits; an empty list is valid.
  `effort` is a real time estimate ("2 hours", "a weekend"), never "some work".
- `opinion: true` on any summary item, theme or action that rests on the presenter's unbacked claim.
- `tutorial`: `null` when it isn't one, with `not_tutorial` set. Copy `code` exactly as shown or said.
  `costs` is required. An empty list makes the page state that nothing needs a paid tier, so use `[]` only after checking.

## Step 4: Render and deliver

```bash
python3 -I SKILL_DIR/scripts/render_report.py VIDEO_FOLDER
```

1. The script validates `analysis.json`, names any bad field, and writes `report.html` in the folder. Fix and re-run on error.
2. Show the page: if the harness has an HTML preview or render tool, use it; otherwise run `open VIDEO_FOLDER/report.html` on macOS.
3. Reply in chat with the TL;DR, the caption kind used, any skipped methods, and the report path. Do not paste the whole analysis into chat.

## Who the actions are for

- Ryan has ADHD: answer first, short sections, numbered steps he can stop and resume, no filler.
- He doesn't write code himself. He builds by directing AI coding agents (Claude Code, Codex and others) across Python, Swift and TypeScript, tracked in GitHub issues and PRs. Phrase build ideas as something to hand an agent.
- Home Assistant at home: solar, a Tesla Powerwall, two Teslas, Daikin HVAC, GloBird Energy. He likes automating and optimising it.
- Navy Chief Petty Officer working as a Training Systems Manager (training design, systems, policy). Moving into personal training in 2027 and building toward it now.
- Avoids anything that needs an API key or quietly runs up API charges.
- Based in Melbourne, Australia: prefer Australian availability, pricing, tariffs and regulations, and say when the video's advice is US- or UK-specific.

## Rules

- Plain language; explain jargon in a few words.
- Flag uncertainty explicitly. Keep what the presenter shows separate from what they only assert.
- Don't reproduce long stretches of the transcript.
- No emojis in the page or in `analysis.json`.
